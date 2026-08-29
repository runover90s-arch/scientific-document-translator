from app.protection.guard import protect, restore


def test_protect_restore_scientific_content():
    source = "For Δt = 10⁻⁹ s, see $E=mc^2$ and https://example.org/x [12]."
    guarded = protect(source)
    assert "$E=mc^2$" not in guarded.protected
    assert "https://example.org/x" not in guarded.protected
    assert restore(guarded.protected, guarded.mapping) == source


def test_placeholder_tamper_is_rejected():
    source = "Value is 9.81 m/s."
    guarded = protect(source)
    broken = guarded.protected.replace("__SDT_KEEP_", "__BROKEN_", 1)
    try:
        restore(broken, guarded.mapping, strict=True)
    except ValueError:
        return
    raise AssertionError("Expected placeholder tamper detection")


def test_unicode_scientific_notation_and_greek_are_protected():
    source = "For Δt = 10⁻⁹ s, ψ changes while mc² remains fixed."
    guarded = protect(source)
    assert "10⁻⁹" not in guarded.protected
    assert "Δt" not in guarded.protected
    assert "ψ" not in guarded.protected
    assert "mc²" not in guarded.protected
    assert restore(guarded.protected, guarded.mapping) == source
