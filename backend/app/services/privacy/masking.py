"""Replace sensitive values with placeholders before text leaves the machine, and restore them after.

Rule-based, tuned for Uzbek workplace text: phones, passports, PINFL (JSHSHIR), TIN (STIR),
card and bank account numbers, e-mails, money amounts, street addresses and Uzbek-style
personal names. It is best-effort — the user always sees the masked text before sending.
"""
import re
from dataclasses import dataclass, field

_APOS = "'’ʻʼ`‘"
_WORD = rf"[A-Za-zА-Яа-яЎўҚқҒғҲҳЁё{_APOS}]"
_SURNAME_END = r"(?:ovich|ovna|evich|evna|ova|eva|yeva|ov|ev|yev)\b"

# Order matters: longer / more specific number formats must win over shorter ones.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("KARTA", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
    ("HISOB", re.compile(r"\b\d{20}\b")),
    ("JSHSHIR", re.compile(r"\b\d{14}\b")),
    ("TEL", re.compile(
        r"(?<![\w+])(?:\+?998[\s-]?)?\(?(?:33|50|55|77|88|90|91|93|94|95|97|98|99|71)\)?"
        r"[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}\b"
    )),
    ("PASPORT", re.compile(r"\b[A-Z]{2}\s?\d{7}\b")),
    ("STIR", re.compile(r"\b\d{9}\b")),
    ("SUMMA", re.compile(
        r"(?:[$€]\s?\d[\d\s.,]*\d|\b\d[\d\s.,]*\d?\s?"
        r"(?:so['’ʻʼ]?m|сўм|сум|mln|million|mlrd|milliard|ming|USD|dollar|EUR|evro|rubl|₽)\b)",
        re.IGNORECASE,
    )),
    # Names before addresses, so "Karimov Sardor Navoiy ko'chasi" splits into a name and a street.
    # Surname = word with an Uzbek/Russian patronymic-style ending. Try "Surname Name" first;
    # "Name Surname" only when no capitalized word follows (else "Fuqaro Karimov" would win).
    ("ISM", re.compile(
        rf"\b[A-ZЎҚҒҲА-Я]{_WORD}*{_SURNAME_END}\s[A-ZЎҚҒҲА-Я]{_WORD}+"
        rf"|\b[A-ZЎҚҒҲА-Я]{_WORD}+\s[A-ZЎҚҒҲА-Я]{_WORD}*{_SURNAME_END}(?!\s[A-ZЎҚҒҲА-Я])"
        rf"|\b[A-ZЎҚҒҲА-Я]{_WORD}*{_SURNAME_END}"
    )),
    ("MANZIL", re.compile(
        rf"\b{_WORD}+(?:\s{_WORD}+)?\s(?:ko[{_APOS}]?chasi|tor\sko[{_APOS}]?chasi|shoh\sko[{_APOS}]?chasi|"
        rf"mahallasi|MFY|massivi|dahasi)\b(?:,?\s*\d+[\w/-]*(?:-uy)?)?(?:,?\s*\d+-(?:uy|xonadon))?",
        re.IGNORECASE,
    )),
    ("MANZIL", re.compile(r"\b\d+[\w/]*-(?:uy|xonadon)\b|\bkv\.?\s?\d+\b", re.IGNORECASE)),
]

_PLACEHOLDER = re.compile(r"\[?\b(" + "|".join(sorted({k for k, _ in _PATTERNS})) + r")[_ ](\d+)\b\]?")


@dataclass
class MaskResult:
    masked: str
    # placeholder (e.g. "[TEL_1]") -> original value; stays on this machine
    mapping: dict[str, str] = field(default_factory=dict)

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for placeholder in self.mapping:
            kind = placeholder.strip("[]").rsplit("_", 1)[0]
            result[kind] = result.get(kind, 0) + 1
        return result


def mask(texts: list[str], mapping: dict[str, str] | None = None) -> tuple[list[str], dict[str, str]]:
    """Mask several texts with one shared mapping, so the same value gets the same placeholder."""
    mapping = dict(mapping or {})
    reverse = {v: k for k, v in mapping.items()}
    counters: dict[str, int] = {}
    for placeholder in mapping:
        kind, num = placeholder.strip("[]").rsplit("_", 1)
        counters[kind] = max(counters.get(kind, 0), int(num))

    def substitute(kind: str, value: str) -> str:
        value = value.strip()
        if value not in reverse:
            counters[kind] = counters.get(kind, 0) + 1
            placeholder = f"[{kind}_{counters[kind]}]"
            reverse[value] = placeholder
            mapping[placeholder] = value
        return reverse[value]

    out = []
    for text in texts:
        for kind, pattern in _PATTERNS:
            text = pattern.sub(lambda m, k=kind: _keep_edges(m.group(0), substitute(k, m.group(0))), text)
        out.append(text)
    return out, mapping


def mask_text(text: str) -> MaskResult:
    (masked,), mapping = mask([text])
    return MaskResult(masked=masked, mapping=mapping)


def unmask(text: str, mapping: dict[str, str]) -> str:
    """Restore originals; tolerant of models that drop brackets or write 'TEL 1'."""
    def restore(m: re.Match) -> str:
        return mapping.get(f"[{m.group(1)}_{m.group(2)}]", m.group(0))

    return _PLACEHOLDER.sub(restore, text)


def _keep_edges(original: str, placeholder: str) -> str:
    # Patterns may swallow surrounding whitespace; keep it so sentences stay readable.
    lead = original[: len(original) - len(original.lstrip())]
    trail = original[len(original.rstrip()):]
    return f"{lead}{placeholder}{trail}"
