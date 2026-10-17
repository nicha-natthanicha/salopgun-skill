from theme import contrast_ratio, ensure_contrast, extract_theme, neutral_theme


def test_pptx_theme_colors(blue_pptx):
    t = extract_theme(blue_pptx)
    assert t["primary"] == "#1E5AA8" and t["source"] == "extracted"
    assert t["secondary"] == "#F2A541"


def test_text_only_pdf_falls_back_to_neutral(plain_pdf):
    assert extract_theme(plain_pdf)["source"] == "neutral"


def test_colored_pdf_picks_dominant_color(colored_pdf):
    t = extract_theme(colored_pdf)
    assert t["source"] == "extracted"
    r, g, b = (int(t["primary"][i:i + 2], 16) for i in (1, 3, 5))
    assert r < 30 and 110 < g < 145 and 110 < b < 145


def test_unknown_file_type_is_neutral(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello")
    assert extract_theme(str(f)) == neutral_theme()


def test_contrast_ratio_black_white():
    assert round(contrast_ratio("#000000", "#FFFFFF"), 1) == 21.0


def test_low_contrast_primary_is_fixed_light_and_dark():
    t = {**neutral_theme(), "primary": "#CCCCCC", "text": "#BBBBBB"}
    for dark in (False, True):
        fixed = ensure_contrast(t, dark=dark)
        bg = "#121417" if dark else fixed["background"]
        assert contrast_ratio(fixed["text"], bg) >= 4.5
        assert contrast_ratio(fixed["primary"], bg) >= 4.5


def test_good_colors_left_alone():
    t = neutral_theme()
    assert ensure_contrast(t, dark=False)["primary"] == t["primary"]
