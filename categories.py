"""Harajat kategoriyalari va tezkor kiritish uchun kalit so'zlar."""

# (kalit, emoji, to'liq nomi, tugmadagi qisqa nomi)
CATEGORIES = [
    ("fuel", "⛽", "Mashina yoqilg'isi", "Yoqilg'i"),
    ("food", "🍽", "Kunlik ovqatlanish", "Ovqatlanish"),
    ("daily", "🧾", "Kunlik rasxodlar", "Kunlik rasxod"),
    ("kids", "👶", "Bolalar uchun pampers va qo'shimchalar", "Bolalar (pampers)"),
    ("phone", "📱", "Telefon abonent to'lovlari", "Telefon"),
    ("utilities", "💡", "Kommunal to'lovlar", "Kommunal"),
    ("groceries", "🛒", "Uy uchun produktlar", "Produktlar"),
    ("transport", "🚕", "Transport / taksi", "Transport / taksi"),
    ("health", "💊", "Sog'liq va dori-darmon", "Sog'liq / dori"),
    ("clothes", "👕", "Kiyim-kechak", "Kiyim-kechak"),
    ("internet", "🌐", "Internet va TV", "Internet / TV"),
    ("education", "🎓", "Ta'lim / kurslar", "Ta'lim / kurs"),
    ("repair", "🛠", "Uy ta'miri va jihozlar", "Uy ta'miri"),
    ("gifts", "🎁", "Sovg'a va bayramlar", "Sovg'a / bayram"),
    ("debt", "💳", "Qarz / kredit to'lovi", "Qarz / kredit"),
    ("other", "📦", "Boshqa", "Boshqa"),
]

# kalit -> (emoji, to'liq nom)
CAT_BY_KEY = {key: (emoji, name) for key, emoji, name, _short in CATEGORIES}


def cat_title(key: str) -> str:
    """'⛽ Mashina yoqilg'isi' ko'rinishidagi sarlavha."""
    emoji, name = CAT_BY_KEY.get(key, ("📦", "Boshqa"))
    return f"{emoji} {name}"


# Tezkor kiritish uchun kalit so'zlar. Apostroflar olib tashlangan holda yoziladi
# (yoqilg'i -> yoqilgi), chunki parser ham matnni shunday normallashtiradi.
# Moslik qoidasi: so'z aynan teng bo'lsa yoki (kalit >= 4 harf bo'lsa) so'z
# shu kalit bilan boshlansa.
KEYWORDS = {
    "fuel": (
        "yoqilgi", "yonilgi", "benzin", "dizel", "solyarka", "zapravka",
        "metan", "propan", "ai80", "ai91", "ai92", "ai95",
    ),
    "food": (
        "ovqat", "tushlik", "nonushta", "kechki", "restoran", "kafe",
        "fastfood", "osh", "shashlik", "lavash", "pitsa", "burger", "choy",
        "kofe", "kolbasa", "ichimlik",
    ),
    "daily": ("rasxod", "harajat", "xarajat", "mayda", "rasxodlar"),
    "kids": (
        "pampers", "podguznik", "bola", "bolalar", "bolajon", "oyinchoq",
        "qoshimcha", "qoshimchalar", "detskiy",
    ),
    "phone": (
        "telefon", "abonent", "mobil", "beeline", "ucell", "uzmobile",
        "mobiuz", "humans",
    ),
    "utilities": (
        "kommunal", "svet", "elektr", "suv", "suvga", "gaz", "gazga",
        "issiqlik", "kvartplata", "musor", "tok",
    ),
    "groceries": (
        "produkt", "bozor", "market", "supermarket", "magazin", "korzinka",
        "makro", "havas", "oziq", "meva", "sabzavot", "gosht", "non", "nonga",
        "sut", "tuxum", "yogurt",
    ),
    "transport": (
        "taksi", "taxi", "yandex", "mytaxi", "avtobus", "metro", "transport",
        "yolkira", "marshrutka",
    ),
    "health": (
        "dori", "doridarmon", "dorixona", "apteka", "shifokor", "doktor",
        "klinika", "tish", "analiz", "tibbiy", "vrach", "vitamin",
        "kasalxona", "sogliq",
    ),
    "clothes": (
        "kiyim", "kiyimkechak", "oyoqkiyim", "krossovka", "koylak", "shim",
        "kurtka", "poyabzal", "palto", "tufli",
    ),
    "internet": (
        "internet", "wifi", "wi-fi", "tv", "televizor", "uztelecom",
        "sarkor", "iptv", "netflix", "youtube", "comnet",
    ),
    "education": (
        "talim", "kurs", "kurslar", "kursga", "repetitor", "maktab",
        "oqish", "universitet", "kitob", "daftar", "ielts", "kontrakt",
    ),
    "repair": (
        "tamir", "remont", "jihoz", "mebel", "santexnik", "usta",
        "qurilish", "maishiy",
    ),
    "gifts": (
        "sovga", "bayram", "tugilgan", "tabrik", "toy", "toyga", "gul",
        "nikoh", "hadya",
    ),
    "debt": (
        "qarz", "qarzi", "qarzga", "qarzni", "kredit", "nasiya", "ipoteka",
        "rassrochka",
    ),
    "other": ("boshqa",),
}


def find_category(word: str):
    """Normallashtirilgan so'z bo'yicha kategoriya kalitini topadi (yoki None)."""
    for key, stems in KEYWORDS.items():
        for stem in stems:
            if word == stem or (len(stem) >= 4 and word.startswith(stem)):
                return key
    return None
