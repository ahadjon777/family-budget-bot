"""Tezkor kiritish: "ovqat 45000 tushlik" kabi matndan summa, kategoriya va izohni ajratadi."""
import re
from dataclasses import dataclass
from typing import Optional

from categories import find_category

# Eng katta ruxsat etilgan summa (10 mlrd so'm) - bema'ni qiymatlardan himoya
MAX_AMOUNT = 10_000_000_000

_APOSTROPHES = "'`’ʻʼ‘´"
_STRIP_APOS = str.maketrans("", "", _APOSTROPHES)

# Izohga qo'shilmaydigan valyuta so'zlari (apostrofsiz)
CURRENCY_WORDS = {"som", "sum", "soum", "somga", "sumga", "сум", "сўм"}

_MULTIPLIERS = {
    "k": 1_000,
    "ming": 1_000,
    "m": 1_000_000,
    "mln": 1_000_000,
    "million": 1_000_000,
}

# Summa: "45000", "45 000", "45,000", "45.000", "12,5 ming", "2.5 mln", "15k"
_AMOUNT_RE = re.compile(
    r"(?<![\w.,])"
    r"(?P<num>\d{1,3}(?:[  .,]\d{3})+(?!\d)|\d+(?:[.,]\d+)?)"
    r"(?:\s*(?P<mul>mln|million|ming|k|m)(?![^\W\d_]))?",
    re.IGNORECASE,
)


@dataclass
class ParsedExpense:
    amount: int
    category: Optional[str]  # kategoriya kaliti yoki None (aniqlanmadi)
    note: str


def _norm_word(word: str) -> str:
    """So'zni kichik harfga o'tkazadi, apostrof va tinish belgilarini olib tashlaydi."""
    return word.lower().translate(_STRIP_APOS).strip(".,!?:;()\"")


def _value(num: str, mul: Optional[str]) -> Optional[int]:
    s = num.replace(" ", " ")
    try:
        if mul:
            s = s.replace(" ", "")
            if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", s):
                value = float(re.sub(r"[.,]", "", s))
            else:
                value = float(s.replace(",", "."))
            return int(round(value * _MULTIPLIERS[mul.lower()]))
        if re.fullmatch(r"\d{1,3}(?:[ .,]\d{3})+", s):
            return int(re.sub(r"[ .,]", "", s))
        if re.fullmatch(r"\d+[.,]\d+", s):
            return int(round(float(s.replace(",", "."))))
        return int(s)
    except ValueError:
        return None


def _find_amount(text: str):
    """Matndagi eng mos summani topadi: ko'paytirgichli (k, ming, mln) afzal,
    keyin eng kattasi. (match, qiymat) qaytaradi yoki None."""
    best = None
    for m in _AMOUNT_RE.finditer(text):
        value = _value(m.group("num"), m.group("mul"))
        if value is None or value <= 0 or value > MAX_AMOUNT:
            continue
        key = (1 if m.group("mul") else 0, value)
        if best is None or key > best[0]:
            best = (key, m, value)
    if best is None:
        return None
    return best[1], best[2]


def parse_amount(text: str) -> Optional[int]:
    """Faqat summa kutilgan joy uchun: '45000', '45 000', '45k', '1.5 mln so'm'.
    Summadan boshqa so'z bo'lsa (valyutadan tashqari) None qaytaradi."""
    found = _find_amount(text)
    if not found:
        return None
    match, value = found
    rest = text[: match.start()] + " " + text[match.end():]
    for word in rest.split():
        if _norm_word(word) not in CURRENCY_WORDS:
            return None
    return value


def parse_quick(text: str) -> Optional[ParsedExpense]:
    """'ovqat 45000 tushlik' -> ParsedExpense(45000, 'food', 'tushlik').
    Matnda summa bo'lmasa None qaytaradi."""
    found = _find_amount(text)
    if not found:
        return None
    match, value = found
    rest = text[: match.start()] + " " + text[match.end():]

    category = None
    note_words = []
    for token in rest.split():
        norm = _norm_word(token)
        if not norm or norm in CURRENCY_WORDS:
            continue
        if category is None:
            key = find_category(norm)
            if key:
                category = key
                continue
        note_words.append(token)

    note = " ".join(note_words).strip(" ,.-:;")
    return ParsedExpense(amount=value, category=category, note=note[:200])
