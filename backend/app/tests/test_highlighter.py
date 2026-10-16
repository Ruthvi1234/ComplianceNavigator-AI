from app.services.highlight.highlighter import find_match_offsets, highlight_terms


def test_highlight_wraps_matched_terms():
    result = highlight_terms("Plastic waste rules for producers", "plastic producers")
    assert "<mark>Plastic</mark>" in result
    assert "<mark>producers</mark>" in result
    assert "waste" not in result.replace("waste rules", "")  # untouched term stays plain


def test_highlight_is_case_insensitive():
    result = highlight_terms("HAZARDOUS waste handling", "hazardous")
    assert "<mark>HAZARDOUS</mark>" in result


def test_highlight_empty_query_returns_original_text():
    text = "No changes expected here"
    assert highlight_terms(text, "") == text


def test_find_match_offsets_returns_correct_spans():
    text = "battery waste rules"
    offsets = find_match_offsets(text, "battery")
    assert offsets == [(0, 7)]
    assert text[offsets[0][0] : offsets[0][1]] == "battery"
