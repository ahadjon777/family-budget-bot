# Bot egasi uchun: oilalarni boshqarish

Admin buyruqlari faqat `ADMIN_IDS` (yoki `ALLOWED_USERS`) dagi Telegram ID larda ishlaydi.

| Buyruq | Vazifasi |
|---|---|
| /admin | Umumiy holat: oilalar, faol obunalar, a'zolar, harajatlar soni |
| /oilalar | So'nggi 15 ta oila: ID, nomi, a'zolar, obuna holati, egasi |
| /fikrlar | Foydalanuvchilar yuborgan yangi fikr-mulohazalar (so'nggi 20 ta). `/fikrlar hammasi` — barchasi |
| /fikrok ID | Fikrni ko'rib chiqildi deb belgilash |
| /holat | Bot holati: foydalanuvchilar, oilalar, bugungi harajatlar, ishlash vaqti. Shu xabar har `STATUS_INTERVAL` soniyada tahrirlanib turadi (standart 60 s, 0 = o'chirilgan) |
| /foydalanuvchilar | Kim botdan foydalanyapti: ism, @username, ID, oilasi, harajatlari soni va **oxirgi faolligi** (so'nggi 20 ta) |
| /uzaytir ID KUN | Obunani uzaytirish. Agar obuna tugagan bo'lsa, bugundan boshlab hisoblanadi, faol bo'lsa tugash sanasiga qo'shiladi. Egasiga xabar boradi |
| /cheksiz ID | Obunani cheksiz qilish |
| /yopish ID | Obunani darhol tugatish |

## To'lov kelganda

1. Oila egasi to'lov qilganini sizga yozadi (yoki to'lov tizimingizdan bilasiz).
2. /oilalar bilan oila ID sini topasiz.
3. `/uzaytir ID 30` yozasiz (oyiga 30 kun). Egasiga "obunangiz uzaytirildi" xabari boradi.

## Muhim

- Yangi oila /start orqali o'zi ochiladi. Sinov muddati `TRIAL_DAYS` bilan belgilanadi. `TRIAL_DAYS=0` bo'lsa, yangi oila sinovsiz boshlanadi va siz uni /uzaytir bilan faollashtirasiz.
- Oilani o'chirish buyrug'i yo'q, ataylab. Obuna tugatilganda ma'lumotlar saqlanib qoladi.
- Har kuni `data/budget.db` ni zaxiralang (docs/VPS.md dagi 11-bo'lim).


## Sizga avtomatik keladigan xabarlar

| Xabar | Qachon |
|---|---|
| 👤 Yangi foydalanuvchi botni ochdi | Kimdir birinchi marta `/start` bosganda (ism, @username, ID bilan) |
| 🆕 Yangi oila ro'yxatdan o'tdi | Kimdir yangi hisob ochganda (obuna holati bilan) |
| ➕ Oilaga yangi a'zo qo'shildi | Kimdir taklif kodi bilan qo'shilganda |
| 💡 Yangi fikr #ID | Foydalanuvchi `/fikr` yuborganda |
| ⚠️ Xatolik | Botda kutilmagan xato bo'lganda (5 daqiqada ko'pi bilan bir marta) |
| 🟢 Bot ishga tushdi / 🟢 Server qayta ishga tushdi | Bot yoqilganda. Oldingi to'xtash **tartibli** bo'lgan bo'lsa, o'chiq turgan vaqt ko'rsatiladi. **Kutilmaganda** to'xtagan bo'lsa (elektr o'chdi, server qotdi, internet uzildi), oxirgi faollik vaqti va taxminiy o'chiq turgan vaqt yoziladi |
| 🔴 Bot to'xtadi | Bot tartibli to'xtatilganda yoki xato bilan to'xtaganda (sababi bilan) |

Sizning o'zingiz ochgan hisob uchun bunday xabarlar kelmaydi.

## Server o'chib qolganini o'sha zahoti bilish

O'chgan dastur o'zi haqida xabar yubora olmaydi, u faqat qayta yonganda "server ochdi" deydi.
O'chgan paytning o'zida ogohlantirish olish uchun tashqi kuzatuvchi kerak (bepul):

1. https://healthchecks.io da ro'yxatdan o'ting va yangi **Check** yarating: *Period* = 2 daqiqa, *Grace time* = 3 daqiqa.
2. **Integrations** bo'limida **Telegram** ni ulang (xabar sizning Telegramingizga keladi).
3. Check'ning ping manzilini (`https://hc-ping.com/...`) nusxalab, `.env` ga yozing:
   ```
   HEARTBEAT_URL=https://hc-ping.com/sizning-uuid
   ```
4. Botni qayta ishga tushiring. Bot har daqiqa shu manzilga ping yuboradi. Ping to'xtasa (kompyuter yoki server o'chsa),
   healthchecks.io 3-5 daqiqada sizga "DOWN", qaytganda "UP" xabarini yuboradi.

## Zaxira nusxa

Bot o'zi har kuni soat 03:30 da (va ishga tushganda, bugungi nusxa hali bo'lmasa) bazadan nusxa oladi:
`data/backups/budget_YYYY-MM-DD.db`. Oxirgi 14 tasi saqlanadi (`BACKUP_KEEP` bilan o'zgartirasiz, `0` = o'chirish).
Tiklash: botni to'xtating, kerakli nusxani `data/budget.db` nomi bilan joyiga qo'ying, botni ishga tushiring.
Zaxirani baribir vaqti-vaqti bilan boshqa joyga (flesh, bulut) nusxalab turing: kompyuterning o'zi buzilsa, `data/` ham yo'qoladi.

## Fikr-mulohazalar bilan ishlash
Foydalanuvchilar `/fikr matn` yoki `/fikr` yuboradi. Har bir fikr darhol sizga keladi (`💡 Yangi fikr #ID`).
Ko'rib chiqib bo'lgach `/fikrok ID` yozing. Fikrlar bazada (`feedback` jadvali) saqlanadi.
