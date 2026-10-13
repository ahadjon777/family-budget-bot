import pytest

from quick_parser import parse_amount, parse_quick


@pytest.mark.parametrize("text, amount, category, note", [
    ("ovqat 45000 tushlik", 45000, "food", "tushlik"),
    ("taksi 15k", 15000, "transport", ""),
    ("45 000 benzin", 45000, "fuel", ""),
    ("yoqilg'i 200 000", 200000, "fuel", ""),
    ("yoqilg‘i 200000 so'm", 200000, "fuel", ""),
    ("kommunal 350 000 so'm", 350000, "utilities", ""),
    ("pampers 180 ming", 180000, "kids", ""),
    ("kredit 1.2 mln", 1200000, "debt", ""),
    ("kredit 1,5 mln", 1500000, "debt", ""),
    ("dori 85000 bola uchun", 85000, "health", "bola uchun"),
    ("2 ta non 15000", 15000, "groceries", "2 ta"),
    ("Internet 120.000", 120000, "internet", ""),
    ("Ovqat 45,000 Kechki", 45000, "food", "Kechki"),
    ("45000 mehmon", 45000, None, "mehmon"),
    ("sovg'a 300 000 tug'ilgan kun", 300000, "gifts", "tug'ilgan kun"),
    ("bozor 12,5 ming", 12500, "groceries", ""),
    ("mashina 45000", 45000, None, "mashina"),
])
def test_parse_quick(text, amount, category, note):
    parsed = parse_quick(text)
    assert parsed is not None, text
    assert parsed.amount == amount
    assert parsed.category == category
    assert parsed.note == note


@pytest.mark.parametrize("text", ["salom", "", "ovqat", "bugun qanday"])
def test_parse_quick_no_amount(text):
    assert parse_quick(text) is None


@pytest.mark.parametrize("text, expected", [
    ("45000", 45000),
    ("45 000", 45000),
    ("45k", 45000),
    ("45 ming", 45000),
    ("1.5 mln", 1500000),
    ("5 000 000 so'm", 5000000),
    ("abc", None),
    ("0", None),
    ("45000 ovqat", None),
    ("-5", None),  # manfiy summa qabul qilinmaydi
])
def test_parse_amount(text, expected):
    assert parse_amount(text) == expected
