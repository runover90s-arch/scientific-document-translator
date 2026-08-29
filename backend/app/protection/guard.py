from __future__ import annotations

import re
from dataclasses import dataclass


PLACEHOLDER_PREFIX = "__SDT_KEEP_"

# Order matters: protect large math spans before numbers inside them.
PATTERNS = [
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\\\[.*?\\\]", re.DOTALL),
    re.compile(r"\\\(.*?\\\)", re.DOTALL),
    re.compile(r"(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)", re.DOTALL),
    re.compile(r"https?://[^\s<>()]+"),
    re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", re.IGNORECASE),
    re.compile(r"\[(?:\d{1,4}(?:\s*[-,]\s*\d{1,4})*)\]"),
    # Scientific values and numbers, including Unicode super/subscript exponents.
    re.compile(
        r"(?<![\w])[-+]?\d+(?:[.,]\d+)?(?:[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?"
        r"(?:\s*[×x]\s*10(?:\s*[\^]?[−\-+]?\d+|[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)|[eE][−\-+]?\d+)?"
        r"(?:\s*(?:%|‰|°[CFK]?|[A-Za-zµμΩÅÅ]+(?:[·⋅*/^−\-]?[A-Za-z0-9µμΩÅÅ]+)*))?"
    ),
    # Common compact math tokens such as x₁, mc², a⁻¹.
    re.compile(r"(?<![\w])[A-Za-z]{1,8}(?:[₊₋₀₁₂₃₄₅₆₇₈₉⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+)(?![\w])"),
    # Greek-variable tokens (Δt, ψ, α2) and standalone mathematical operators/symbols.
    re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF](?:[A-Za-z0-9_₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]*)"),
    re.compile(r"[\u2200-\u22FF]"),
]

GREEK_AND_MATH_RE = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF\u2200-\u22FF]")
NUMBER_RE = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?(?:\s*[×x]\s*10(?:\s*\^?[−\-+]?\d+|[⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)|[eE][−\-+]?\d+)?")


@dataclass
class GuardedText:
    protected: str
    mapping: dict[str, str]


def protect(text: str) -> GuardedText:
    mapping: dict[str, str] = {}
    counter = 0
    result = text

    for pattern in PATTERNS:
        def repl(match: re.Match[str]) -> str:
            nonlocal counter
            token = f"{PLACEHOLDER_PREFIX}{counter:06d}__"
            counter += 1
            mapping[token] = match.group(0)
            return token

        result = pattern.sub(repl, result)

    return GuardedText(protected=result, mapping=mapping)


def restore(text: str, mapping: dict[str, str], strict: bool = True) -> str:
    restored = text
    missing: list[str] = []
    for token, original in mapping.items():
        count = restored.count(token)
        if count != 1:
            missing.append(f"{token}:{count}")
        restored = restored.replace(token, original)
    if strict and missing:
        raise ValueError("Protected placeholders were modified or duplicated: " + ", ".join(missing))
    return restored


def extract_numbers(text: str) -> list[str]:
    return NUMBER_RE.findall(text)


def extract_math_symbols(text: str) -> list[str]:
    return GREEK_AND_MATH_RE.findall(text)
