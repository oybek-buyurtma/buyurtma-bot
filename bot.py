"""
Buyurtmalarni kuzatuvchi Telegram bot.
Guruhga tashlanadigan xabarlarni (masalan: "Tovuq 4 / Osh 2 / Jami 175")
avtomatik o'qib, taomlar va savdo statistikasini SQLite bazasida saqlaydi.

ISHGA TUSHIRISH:
1) pip install -r requirements.txt
2) BOT_TOKEN muhit o'zgaruvchisini o'rnating (BotFather'dan olingan token)
3) python3 bot.py

Guruhda ishlashi uchun:
- @BotFather -> /mybots -> botingiz -> Bot Settings -> Group Privacy -> Turn off
  (aks holda bot guruhdagi oddiy xabarlarni ko'ra olmaydi)
- Botni guruhga qo'shing (admin qilish shart emas, lekin Privacy o'chirilgan bo'lishi kerak)
"""

import os
import re
import sqlite3
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.db")
DEFAULT_PRICE = 25  # "Jami" ko'rsatilmasa, taom narxi (ming so'mda) shu deb olinadi

PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{6,}\d)")
JAMI_RE = re.compile(r"^\s*jam[io]", re.IGNORECASE)
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
ITEM_LINE_RE = re.compile(r"^([^\d]+?)\s*[:\-]?\s*(\d+(?:\.\d+)?)")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            msg_date TEXT,
            customer TEXT,
            phone TEXT,
            total REAL,
            raw_text TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_name TEXT,
            qty REAL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)
    conn.commit()
    conn.close()


def normalize_item_name(name: str) -> str:
    name = name.strip(" \t-:")
    return name


def parse_order(text: str):
    """Xabar matnidan mijoz, telefon, taomlar ro'yxati va jamini ajratib oladi."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return None

    customer = None
    phone = None
    items = []
    total = None

    # Xabarda telefon raqami bo'lsa, undan oldingi qatorlar mijoz nomi hisoblanadi
    # (masalan "Charxiy 24" kabi nom ichidagi raqam taom sifatida noto'g'ri o'qilmasin)
    has_phone_line = any(PHONE_RE.search(l) for l in lines)
    seen_phone = False

    for line in lines:
        # Jami qatori
        if JAMI_RE.match(line):
            nums = NUM_RE.findall(line)
            if nums:
                total = float(nums[-1])
            continue

        # Telefon raqami bor qatorlar (mijoz ma'lumoti)
        phone_match = PHONE_RE.search(line)
        if phone_match:
            seen_phone = True

        item_match = ITEM_LINE_RE.match(line)
        before_phone = has_phone_line and not seen_phone and not phone_match

        if item_match and item_match.group(1).strip() and not phone_match and not before_phone:
            name = normalize_item_name(item_match.group(1))
            # juda qisqa yoki faqat harflardan iborat bo'lmagan holatlarni tashlab yuborish
            if len(name) >= 2 and any(c.isalpha() for c in name):
                qty_str = item_match.group(2)
                # "2x25=50" kabi holatda faqat birinchi son (miqdor) olinadi
                qty = float(qty_str)
                items.append((name, qty))
                continue

        if phone_match and customer is None:
            phone = phone_match.group(1).strip()
            name_part = line[: phone_match.start()].strip(" ,:-")
            if name_part:
                customer = name_part
            continue

        if customer is None and (not item_match or before_phone):
            customer = line

    if not items and total is None:
        return None  # bu xabar buyurtma emas shekilli

    if total is None:
        total = sum(qty * DEFAULT_PRICE for _, qty in items)

    return {
        "customer": customer,
        "phone": phone,
        "items": items,
        "total": total,
    }


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return

    parsed = parse_order(msg.text)
    if not parsed:
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO orders (chat_id, msg_date, customer, phone, total, raw_text) VALUES (?, ?, ?, ?, ?, ?)",
        (
            update.effective_chat.id,
            msg.date.isoformat(),
            parsed["customer"],
            parsed["phone"],
            parsed["total"],
            msg.text,
        ),
    )
    order_id = cur.lastrowid
    for name, qty in parsed["items"]:
        conn.execute(
            "INSERT INTO order_items (order_id, item_name, qty) VALUES (?, ?, ?)",
            (order_id, name, qty),
        )
    conn.commit()
    conn.close()


def day_bounds(d: date):
    start = f"{d.isoformat()}T00:00:00"
    end = f"{d.isoformat()}T23:59:59"
    return start, end


async def bugun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_date = date.today()
    if context.args:
        try:
            target_date = datetime.strptime(context.args[0], "%Y-%m-%d").date()
        except ValueError:
            await update.message.reply_text("Sana formati: YYYY-MM-DD (masalan 2026-07-15)")
            return

    start, end = day_bounds(target_date)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    orders = conn.execute(
        "SELECT id, total FROM orders WHERE chat_id=? AND msg_date BETWEEN ? AND ?",
        (update.effective_chat.id, start, end),
    ).fetchall()

    if not orders:
        await update.message.reply_text(f"{target_date.isoformat()} uchun buyurtma topilmadi.")
        conn.close()
        return

    order_ids = [o["id"] for o in orders]
    placeholders = ",".join("?" * len(order_ids))
    items = conn.execute(
        f"SELECT item_name, SUM(qty) as total_qty FROM order_items WHERE order_id IN ({placeholders}) GROUP BY item_name ORDER BY total_qty DESC",
        order_ids,
    ).fetchall()
    conn.close()

    total_sales = sum(o["total"] or 0 for o in orders)

    lines = [f"📊 {target_date.isoformat()} statistikasi", f"Buyurtmalar soni: {len(orders)}", ""]
    lines.append("Taomlar bo'yicha:")
    for it in items:
        qty = it["total_qty"]
        qty_str = f"{qty:g}"
        lines.append(f"  {it['item_name']}: {qty_str}")
    lines.append("")
    lines.append(f"💰 Umumiy savdo: {total_sales:g}")

    await update.message.reply_text("\n".join(lines))


async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Men guruhdagi buyurtma xabarlarini o'qib, avtomatik hisoblab boraman.\n\n"
        "Buyruqlar:\n"
        "/bugun - bugungi statistika\n"
        "/bugun 2026-07-15 - shu sanadagi statistika"
    )


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit("BOT_TOKEN muhit o'zgaruvchisi topilmadi. Avval uni o'rnating.")

    init_db()

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("bugun", bugun))
    app.add_handler(CommandHandler(["yordam", "start", "help"], yordam))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Render.com kabi bepul xosting-servislar PORT va RENDER_EXTERNAL_HOSTNAME
    # muhit o'zgaruvchilarini avtomatik beradi -> shu holatda webhook rejimida ishlaymiz.
    # Kompyuterda lokal ishga tushirilsa (bu o'zgaruvchilar bo'lmasa) -> polling rejimi.
    port = os.environ.get("PORT")
    hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

    if port and hostname:
        webhook_url = f"https://{hostname}/{token}"
        print(f"Bot webhook rejimida ishga tushdi: {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(port),
            url_path=token,
            webhook_url=webhook_url,
        )
    else:
        print("Bot polling rejimida ishga tushdi...")
        app.run_polling()


if __name__ == "__main__":
    main()
