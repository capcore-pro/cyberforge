from tools.project_title import clean_project_title


def test_strips_trailing_quote():
    assert clean_project_title('Exemple restaurant"') == "Exemple restaurant"


def test_first_quoted_segment():
    assert (
        clean_project_title("« CRM », « Dashboard ventes », « Facturation »")
        == "CRM"
    )


def test_first_segment_before_comma():
    assert clean_project_title("CRM, Dashboard ventes, Facturation") == "CRM"


def test_max_length():
    long = "A" * 60
    assert len(clean_project_title(long)) == 50
    assert clean_project_title(long).endswith("…")
