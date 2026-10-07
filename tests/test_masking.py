from backend.app.services.privacy.masking import mask, mask_text, unmask


def _masked_values(text: str) -> tuple[str, set[str]]:
    result = mask_text(text)
    return result.masked, set(result.mapping.values())


def test_phone_formats():
    for phone in ["+998 90 123 45 67", "+998901234567", "90 123-45-67", "(93) 555 12 34"]:
        masked, values = _masked_values(f"Menga {phone} raqamiga qo'ng'iroq qiling")
        assert phone in values, (phone, masked)
        assert "[TEL_1]" in masked


def test_ids_cards_accounts():
    text = ("Pasport AB1234567, JSHSHIR 31234567890123, STIR 305123456, "
            "karta 8600 1234 5678 9012, hisob 20208000900123456789, email ali.valiyev@mail.uz")
    masked, values = _masked_values(text)
    for v in ["AB1234567", "31234567890123", "305123456", "8600 1234 5678 9012",
              "20208000900123456789", "ali.valiyev@mail.uz"]:
        assert v in values, (v, masked)
    for v in values:
        assert v not in masked


def test_amounts():
    masked, values = _masked_values("Shartnoma summasi 15 000 000 so'm, avans $1,200 va 3 mln so'm")
    assert any("15 000 000" in v for v in values), masked
    assert any("1,200" in v for v in values), masked
    assert "15 000 000" not in masked


def test_address_and_names():
    text = "Fuqaro Karimov Sardor Navoiy ko'chasi 12-uy, 5-xonadonda yashaydi. Salimova Dilnoza ham keldi."
    masked, values = _masked_values(text)
    assert "Karimov Sardor" in values, masked
    assert "Salimova Dilnoza" in values, masked
    assert "Navoiy" not in masked, masked
    assert "12-uy" not in masked, masked


def test_same_value_same_placeholder_and_roundtrip():
    texts = ["Karimov Sardor +998901234567 raqamidan yozdi.", "Karimov Sardor ga javob yozing."]
    masked, mapping = mask(texts)
    assert masked[0].count("[ISM_1]") == 1 and masked[1].count("[ISM_1]") == 1
    reply = "Hurmatli [ISM_1], so'rovingiz bo'yicha [TEL_1] raqamiga qo'ng'iroq qilamiz. ISM 1 ga rahmat."
    restored = unmask(reply, mapping)
    assert restored == ("Hurmatli Karimov Sardor, so'rovingiz bo'yicha +998901234567 raqamiga "
                        "qo'ng'iroq qilamiz. Karimov Sardor ga rahmat.")


def test_ordinary_text_untouched():
    text = "Ertaga soat 10 da yig'ilish bor, 3 ta masala muhokama qilinadi."
    result = mask_text(text)
    assert result.masked == text and not result.mapping
