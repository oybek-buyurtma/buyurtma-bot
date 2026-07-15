# Buyurtma bot

Guruhga tashlanadigan buyurtma xabarlarini (mijoz, taomlar, jami summa) avtomatik
o'qib, statistikasini saqlab boradigan Telegram bot.

## 1. Bot yaratish

1. Telegram'da **@BotFather** ga yozing.
2. `/newbot` buyrug'ini yuboring, botga nom va username bering.
3. Sizga **token** beriladi (masalan `123456789:AAExampleTokenHere`) — uni saqlab qo'ying.
4. Muhim: shu botga yana `/mybots` -> botingizni tanlang -> **Bot Settings** ->
   **Group Privacy** -> **Turn off**.
   (Bu o'chirilmasa, bot guruhdagi oddiy xabarlarni ko'ra olmaydi, faqat
   `/buyruq` bilan boshlangan xabarlarni ko'radi.)

## 2. Kompyuterda/serverda ishga tushirish

```bash
pip install -r requirements.txt

# Linux/Mac:
export BOT_TOKEN="sizning_tokeningiz"
# Windows (PowerShell):
$env:BOT_TOKEN="sizning_tokeningiz"

python3 bot.py
```

Bot ishlab turgan vaqtda konsolda "Bot ishga tushdi..." deb chiqadi.

## 3. Guruhga qo'shish

1. Botni oddiy a'zo sifatida guruhga qo'shing (admin qilish shart emas).
2. Guruhda kimdir buyurtma xabarini yozganda, bot uni orqa fonda o'qib,
   bazaga (`orders.db` fayli) yozib qo'yadi — hech qanday javob yozmaydi.

## 4. Statistikani ko'rish

Guruhda quyidagi buyruqlarni yozing:

- `/bugun` — bugungi kun statistikasi (har bir taomdan nechta sotilgani + jami savdo)
- `/bugun 2026-07-15` — ko'rsatilgan sanadagi statistika
- `/yordam` — yordam matni

## 5. Bepul serverga joylashtirish (faqat telefon orqali, Render.com)

Bu bot avtomatik ravishda Render.com'ni aniqlab, kerak bo'lsa **webhook** rejimiga
o'tadi — shuning uchun terminal yoki kompyuter kerak emas, hammasi brauzer orqali.

### A) GitHub'ga fayllarni joylash
1. Telefon brauzerida **github.com** ga kiring, akkaunt oching (bepul).
2. Yuqori o'ngdan **+** → **New repository** → nom bering (masalan `buyurtma-bot`) → **Create repository**.
3. Repo ochilgach **"Add file" → "Upload files"** ni bosing.
4. Shu paketdagi 3 ta faylni (`bot.py`, `requirements.txt`, `README.md`) yuklang → **Commit changes**.

### B) Render.com'da servis yaratish
1. **render.com** ga kiring, **Sign up** → "Sign up with GitHub" orqali ro'yxatdan o'ting.
2. **New +** → **Web Service** ni tanlang.
3. GitHub repo'ingizni (`buyurtma-bot`) tanlang.
4. Sozlamalar:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 bot.py`
   - **Instance Type**: Free
5. **Environment Variables** bo'limiga o'ting → **Add Environment Variable**:
   - Key: `BOT_TOKEN`, Value: sizning tokeningiz
6. **Create Web Service** ni bosing — Render avtomatik qura boshlaydi (2-3 daqiqa).
7. Loglarda `"Bot webhook rejimida ishga tushdi..."` chiqsa — tayyor!

### Muhim eslatmalar
- Render'ning bepul tarifi 15 daqiqa harakatsiz qolsa "uxlab qoladi". Uni doimo
  uyg'oq tutish uchun **uptimerobot.com**'da bepul akkaunt oching va Render bergan
  URL manzilingizni (masalan `https://buyurtma-bot.onrender.com`) har 5 daqiqada
  bir marta "ping" qiladigan monitor qo'shing.
- Bepul tarifda `orders.db` fayli har safar qayta ishga tushganda (masalan deploy
  yangilansa) o'chib ketishi mumkin — statistikani doimiy saqlash kerak bo'lsa,
  keyinroq Render'ning bepul PostgreSQL bazasiga o'tkazib qo'yaman, ayting.

## Eslatma — xabar formati

Bot xabarlarni quyidagi tuzilishga yaqin deb kutadi:

```
Mijoz nomi
+998 90-123-45-67

Taom nomi 2
Boshqa taom 1
Jami 75
```

- Agar "Jami" qatori bo'lmasa, bot har bir taomni standart narx
  (1 dona = 25 ming so'm) bo'yicha hisoblab, o'zi jami summani chiqaradi.
  Kerak bo'lsa `bot.py` faylidagi `DEFAULT_PRICE` qiymatini o'zgartiring.
- Format juda xilma-xil bo'lsa (masalan matn ichida hisob-kitob bo'lsa),
  ba'zan noto'g'ri o'qishi mumkin — shunday holatlar uchraса ayting, parserni
  yaxshilab boraman.
