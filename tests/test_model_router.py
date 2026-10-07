import pytest

from backend.app.core.config import settings
from backend.app.services.llm import model_router
from backend.app.services.llm.openai_compatible_provider import ThinkFilter, strip_think


@pytest.fixture(autouse=True)
def _reasoning_model(monkeypatch):
    monkeypatch.setattr(settings, "REASONING_MODEL", "deepseek-r1-8k:latest")


@pytest.mark.parametrize("text", [
    "Do'konda 3 ta ruchka 4500 so'm. 7 ta ruchka necha so'm?",
    "47*89 ni hisobla",
    "120 + 85 + 97",
    "Ali Validan katta. Vali Sardordan katta. Eng kichigi kim?",
    "Murojaatlar: Oqdaryo 120, Jomboy 85. Jami nechta?",
    "Narx 15% oshsa qancha bo'ladi? Hozir 200000",
    "Неча фоиз ошди? 120 дан 150 га",
])
def test_reasoning_questions(text):
    assert model_router.choose_model(text) == "deepseek-r1-8k:latest"


@pytest.mark.parametrize("text", [
    "salom",
    "Rahbarga dam olish kuni so'rab ariza yoz.",
    "Toshkent haqida 2 gapda ma'lumot ber.",
    "Ertaga soat 10 da yig'ilish bor, xodimlarga e'lon matnini yoz.",
    "2024-yil hisobotini qisqacha tushuntir.",
])
def test_chat_questions(text):
    assert model_router.choose_model(text) is None


def test_spreadsheet_context_routes_calc_words_without_digits():
    history = [{"role": "user", "content": "[Yuklangan jadval: a.xlsx]\nRows: 4"},
               {"role": "assistant", "content": "Jadvalni ko'rib chiqdim."}]
    assert model_router.choose_model("Qaysi tumanda eng ko'p?", history) == "deepseek-r1-8k:latest"
    # Without a spreadsheet in context and without numbers it stays with the chat model.
    assert model_router.choose_model("Qaysi tumanda eng ko'p?") is None


def test_disabled_without_setting(monkeypatch):
    monkeypatch.setattr(settings, "REASONING_MODEL", "")
    assert model_router.choose_model("47*89") is None


def test_strip_think():
    assert strip_think("<think>\nhmm 3+4\n</think>\n\n7") == "7"
    assert strip_think("javob") == "javob"
    assert strip_think("<think>unfinished") == ""


def test_think_filter_streaming():
    f = ThinkFilter()
    chunks = ["<th", "ink>reason", "ing...</thi", "nk>\n\nJa", "vob: 7"]
    out = "".join(f.feed(c) for c in chunks) + f.flush()
    assert out == "Javob: 7"
