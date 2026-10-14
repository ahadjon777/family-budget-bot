# Oilaviy harajatlar boti: foydalanish qo'llanmasi

Bu qo'llanma oila a'zolari uchun. Botni o'rnatish shart emas: u Telegram'da ishlaydi, telefon va kompyuter kerak bo'lmaydi.

## 1. Boshlash

1. Telegram'da bot havolasini oching (egasi yuboradi).
2. **/start** bosing.
3. Ikki variant chiqadi:
   - **✨ Yangi hisob ochish**: o'z oilangizni yaratasiz, siz oila egasi bo'lasiz. Bepul sinov muddati boshlanadi.
   - **🔑 Taklif kodi bilan qo'shilish**: oila egasidan olgan 6 belgili kodni kiritasiz.

## 2. Oila a'zolarini qo'shish (egasi uchun)

1. Egasi **/oila** buyrug'ini yuboradi va **Taklif kodi**ni ko'radi.
2. Kodni oila a'zolariga yuboradi.
3. A'zo botda **/start** → **🔑 Taklif kodi bilan qo'shilish** → kodni yuboradi.

Bitta oilada eng ko'pi 6 kishi bo'lishi mumkin. Hamma a'zolar bitta umumiy hisobni ko'radi va yozadi.

## 3. Harajat yozish

**Tezkor usul**: shunchaki yozing.
- `ovqat 45000 tushlik`
- `taksi 15k`
- `benzin 200 000`
- `kredit 1.5 mln`

Summa: `45000`, `45 000`, `45k`, `45 ming`, `1.2 mln`. Kategoriya aniqlanmasa, bot tugmalar bilan so'raydi.

**Tugmalar bilan**: **➕ Harajat qo'shish** → kategoriya → summa → izoh (ixtiyoriy).

## 4. Hisobotlar

| Buyruq | Nima ko'rsatadi |
|---|---|
| /bugun | Bugungi harajatlar, kategoriyalar bo'yicha |
| /hafta | Shu haftaning hisoboti va kunlik grafik |
| /oy | Shu oyning hisoboti |
| /kategoriya | Bitta kategoriya bo'yicha |
| /statistika | O'rtacha kunlik, oy oxiri prognozi, o'tgan oy bilan solishtirish |

## 5. Xatoni tuzatish

**/oxirgi** yoki **✏️ Oxirgi harajat** bosing. Summani, kategoriyani, izohni o'zgartirish yoki yozuvni o'chirish mumkin.

## 6. Oylik limit

**/limit 5000000** yozing (yoki **💰 Limit** tugmasi). Limitning 80% va 100% qismida bot ogohlantiradi.

## 7. Eksport

**/eksport** → Excel (.xlsx) yoki CSV. Shu oy yoki hammasi.

## 8. Kunlik eslatma

Kuniga **3 marta** (09:00, 15:00 va 21:00, Toshkent vaqti) bot harajatlarni kiritishni eslatadi: ertalab, kunduzi va kechqurun.
Bugun hech narsa kiritilmagan bo'lsa, shuni ham aytadi. Vaqtlarni bot egasi o'zgartirishi mumkin.

## Izoh yozish

Har bir harajatga izoh qo'shish mumkin:

- Tezkor kiritishda summadan keyin yozing: `ovqat 45000 tushlik`.
- Izohsiz saqlangan harajat tagida **📝 Izoh qo'shish** tugmasi chiqadi, bosing va izohni yozing.
- **➕ Harajat qo'shish** orqali kiritganda summadan keyin izoh so'raladi (kerak bo'lmasa «Izohsiz saqlash»).
- **/bugun** hisobotida har bir yozuv vaqti, izohi va kim kiritgani bilan ko'rinadi, oxirida esa kechagi jami.

## 9. Obuna

- **/oila** buyrug'ida obuna muddati ko'rinadi.
- Muddat tugagan bo'lsa, harajat yozish va hisobotlar vaqtincha to'xtaydi. Ma'lumotlar o'chib ketmaydi.
- Obunani uzaytirish uchun bot egasi bilan bog'laning. To'lov tasdiqlangach, obuna darhol faollashadi.

## Savollar

| Savol | Javob |
|---|---|
| Noto'g'ri summa yozdim | **/oxirgi** → 💵 Summa |
| Kategoriyani adashtirdim | **/oxirgi** → 🏷 Kategoriya |
| Taklif kodi ishlamayapti | Harfni kattaroq yozing, bo'sh joy qoldirmang. Egasidan yangi kod so'rang |
| Bot javob bermayapti | Bir daqiqa kuting, keyin **/start** yuboring |
| "Obuna muddati tugagan" yozilgan | Bot egasi bilan bog'laning |
| Hamma harajatni ko'rishi kerakmi? | Ha, oiladagi hamma bitta hisobni ko'radi |

## Maxfiylik

Oila hisobi faqat shu oila a'zolariga ko'rinadi. Boshqa oilalarning ma'lumotlari aralashmaydi.


## Fikr va taklif yuborish
Botda nimadir yetishmasa yoki yaxshilash kerak bo'lsa, **/fikr** buyrug'i bilan yozing, masalan:
`/fikr Eksport faylida sana ustuni bo'lsa yaxshi bo'lardi`. Yoki `/fikr` yozib, keyingi xabarda fikringizni yuboring.
Fikringiz bot egasiga yetkaziladi.
