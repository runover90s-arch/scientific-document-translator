from app.protection.validators import validate_text


def test_numeric_integrity():
    n_ok, s_ok, details = validate_text("Energy 1.23 × 10^-4 J and α", "Năng lượng 1.23 × 10^-4 J và α")
    assert n_ok and s_ok and not details


def test_numeric_change_fails():
    n_ok, _, _ = validate_text("Value 42", "Giá trị 43")
    assert not n_ok
