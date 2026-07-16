from encyclopedia.cabook_annotate.variant_expander import expand_surface_forms


def test_plural_variants():
    forms = expand_surface_forms(
        "democracy",
        expand_plurals=True,
        expand_verbs=False,
        min_length=3,
    )
    assert "democracy" in forms
    assert "democracies" in forms


def test_verb_variants_disabled():
    forms = expand_surface_forms(
        "adapt",
        expand_plurals=False,
        expand_verbs=False,
        min_length=3,
    )
    assert forms == {"adapt"}
