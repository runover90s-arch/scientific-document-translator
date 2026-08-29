from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict

from .guard import extract_math_symbols, extract_numbers


@dataclass
class ValidationReport:
    ok: bool
    numeric_integrity: bool
    symbol_integrity: bool
    equation_integrity: bool
    details: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def validate_text(source: str, target: str) -> tuple[bool, bool, list[str]]:
    source_numbers = Counter(extract_numbers(source))
    target_numbers = Counter(extract_numbers(target))
    source_symbols = Counter(extract_math_symbols(source))
    target_symbols = Counter(extract_math_symbols(target))

    details: list[str] = []
    numeric_ok = source_numbers == target_numbers
    symbol_ok = source_symbols == target_symbols
    if not numeric_ok:
        details.append(f"Numeric mismatch: source={dict(source_numbers)} target={dict(target_numbers)}")
    if not symbol_ok:
        details.append(f"Math-symbol mismatch: source={dict(source_symbols)} target={dict(target_symbols)}")
    return numeric_ok, symbol_ok, details
