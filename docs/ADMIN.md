# Bot egasi uchun: oilalarni boshqarish

Admin buyruqlari faqat `ADMIN_IDS` (yoki `ALLOWED_USERS`) dagi Telegram ID larda ishlaydi.

| Buyruq | Vazifasi |
|---|---|
| /admin | Umumiy holat: oilalar, faol obunalar, a'zolar, harajatlar soni |
| /oilalar | So'nggi 15 ta oila: ID, nomi, a'zolar, obuna holati, egasi |
| /fikrlar | Foydalanuvchilar yuborgan yangi fikr-mulohazalar (so'nggi 20 ta). `/fikrlar hammasi` — barchasi |
| /fikrok ID | Fikrni ko'rib chiqildi deb belgilash |
| /holat | Bot holati: foydalanuvchilar, oilalar, bugungi harajatlar, ishlash vaqti. Shu xabar har `STATUS_INTERVAL` soniyada tahrirlanib turadi (standart 60 s, 0 = o'chirilgan) |
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


## Fikr-mulohazalar bilan ishlash
Foydalanuvchilar `/fikr matn` yoki `/fikr` yuboradi. Har bir fikr darhol sizga keladi (`💡 Yangi fikr #ID`).
Ko'rib chiqib bo'lgach `/fikrok ID` yozing. Fikrlar bazada (`feedback` jadvali) saqlanadi.
