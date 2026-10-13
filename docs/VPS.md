# Botni VPS serverda 24/7 ishlatish

Bu yo'riqnoma botni Ubuntu serverda (VPS) ishlatadi. Server o'chmaydi, bot kompyuter yoki telefon o'chsa ham ishlashda davom etadi, xato bo'lsa o'zi qayta ishga tushadi.

## 0. Nima kerak

- **VPS**: Ubuntu 22.04 yoki 24.04, kamida 1 GB RAM, 10 GB disk. Oyiga bir necha dollar (masalan Hetzner, DigitalOcean, Contabo, yoki O'zbekistondagi hosting).
- **SSH kirish**: VPS sotib olganda IP manzil, login (odatda `root`) va parol yoki kalit beriladi.
- **Bot tokeni** (@BotFather) va o'z Telegram ID ingiz (@userinfobot).
- **Kod**: GitHub'dagi repo (`family-budget-bot`).

## 1. Serverga ulanish

Windows'da PowerShell oching:

```bash
ssh root@SERVER_IP
```

Birinchi marta "Are you sure you want to continue connecting" so'rasa, `yes` yozing va parolni kiriting.

## 2. Tizimni yangilash va kerakli dasturlar

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git
```

## 3. Alohida foydalanuvchi yaratish (xavfsizlik uchun)

Botni `root` bilan ishlatmang:

```bash
adduser --disabled-password --gecos "" bot
su - bot
```

Endi siz `bot` foydalanuvchisidasiz. Qolgan qadamlar shu yerda bajariladi.

## 4. Kodni yuklash

```bash
git clone https://github.com/ahadjon777/family-budget-bot.git
cd family-budget-bot
```

Repo private bo'lsa, GitHub so'raganda Personal Access Token ishlating (parol o'rniga).

## 5. Virtual muhit va kutubxonalar

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## 6. Sozlamalar (.env)

```bash
cp .env.example .env
nano .env
```

Kamida shu qatorlarni to'ldiring:

```
BOT_TOKEN=sizning_bot_tokeningiz
ALLOWED_USERS=sizning_telegram_id
```

Saqlash: `CTRL` + `x`, `y`, Enter.

Fayl huquqini cheklang (faqat `bot` o'qiy olsin):

```bash
chmod 600 .env
```

## 7. Birinchi marta sinab ko'rish

```bash
./venv/bin/python main.py
```

Telegram'da botga `/start` yozing. Ishlasa, `CTRL` + `c` bilan to'xtating.

## 8. Avtomatik ishga tushirish (systemd)

Root sifatida chiqing (`exit` yozing) va xizmat faylini yarating:

```bash
exit
nano /etc/systemd/system/family-budget-bot.service
```

Ichiga:

```ini
[Unit]
Description=Oilaviy harajatlar boti
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=bot
WorkingDirectory=/home/bot/family-budget-bot
ExecStart=/home/bot/family-budget-bot/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/bot/family-budget-bot/.env

[Install]
WantedBy=multi-user.target
```

Ishga tushiring:

```bash
systemctl daemon-reload
systemctl enable --now family-budget-bot
systemctl status family-budget-bot
```

`active (running)` yashil rangda chiqsa, bot ishlayapti.

## 9. Kundalik boshqaruv

| Amal | Buyruq |
|---|---|
| Holatni ko'rish | `systemctl status family-budget-bot` |
| Loglarni ko'rish (oxirgi 100 qator) | `journalctl -u family-budget-bot -n 100` |
| Jonli loglar | `journalctl -u family-budget-bot -f` (chiqish: `CTRL` + `c`) |
| To'xtatish | `systemctl stop family-budget-bot` |
| Qayta ishga tushirish | `systemctl restart family-budget-bot` |
| .env o'zgartirgandan keyin | `systemctl restart family-budget-bot` |

## 10. Kodni yangilash

Yangi versiya chiqqanda:

```bash
su - bot
cd family-budget-bot
git pull
./venv/bin/pip install -r requirements.txt
exit
systemctl restart family-budget-bot
```

## 11. Zaxira nusxa (muhim)

Ma'lumotlar `data/budget.db` faylida. Har kuni nusxa oling:

```bash
mkdir -p /home/bot/backups
cp /home/bot/family-budget-bot/data/budget.db /home/bot/backups/budget_$(date +%F).db
```

Bu buyruqni har kuni avtomatik bajarish uchun `crontab -e` (bot foydalanuvchisi sifatida) va quyidagi qatorni qo'shing:

```
0 3 * * * cp /home/bot/family-budget-bot/data/budget.db /home/bot/backups/budget_$(date +\%F).db
```

Eski nusxalarni tozalash uchun 30 kundan eskisini o'chiring:

```
0 4 * * * find /home/bot/backups -name "budget_*.db" -mtime +30 -delete
```

Zaxirani VPS'dan tashqariga ham nusxalab turing (masalan kompyuteringizga `scp` bilan), serverning o'zi buzilsa, zaxira ham yo'qolmasin.

## 12. Muammolar

| Belgi | Sabab va yechim |
|---|---|
| `status` da `failed` | `journalctl -u family-budget-bot -n 50` bilan xatoni ko'ring. Ko'pincha `.env` noto'g'ri. |
| `BOT_TOKEN topilmadi` | `.env` fayli `/home/bot/family-budget-bot/` da ekanini va `chmod 600` bo'lsa ham `bot` o'qiy olishini tekshiring. |
| Bot javob bermaydi | `ALLOWED_USERS` da sizning ID borligini tekshiring. |
| `Unauthorized` | Token noto'g'ri yoki bekor qilingan. @BotFather dan yangisini oling. |
| Server qayta yonganda bot ishlamaydi | `systemctl is-enabled family-budget-bot` `enabled` deb chiqishi kerak. |

## Xavfsizlik bo'yicha eslatma

- Parolni yoki SSH kalitni hech kimga bermang.
- Bot tokenini ochiq joyga (skrinshot, chat, GitHub) yozmang. Agar tasodifan chiqib ketsa, @BotFather → `/revoke` qiling.
- `.env` ni GitHub'ga yuklamang (`.gitignore` da bor).
- Muhim: ssh kirishni parol bilan emas, kalit bilan cheklash yaxshiroq. Buni keyinroq qilishingiz mumkin.
