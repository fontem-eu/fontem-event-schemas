"""Builder coverage for the value-quality fields on upsert_contract.

The schema/example tests validate shapes; this exercises the builder
itself — that it threads the new value-quality fields through, drops
None/empty, and that its output validates against the schema (including
the bool fields, which must survive even when False).
"""
from fontem_event_schemas import builders, validate


def test_upsert_contract_threads_value_quality_fields():
    """All value-quality fields land on the payload and it validates."""
    p = builders.upsert_contract(
        ted_notice_id="35ecc2b8",
        title="AQUISICAO DE AERONAVES",
        value_eur=7_274_615.93,
        value_currency="EUR",
        value_original=7_274_615.93,
        estimated_value_eur=7_317_073.17,
        value_payable_eur=7_274_615_930.0,
        value_confidence=0.71,
        value_confidence_consistency=0.71,
        value_confidence_plausibility=1.0,
        value_quality_flag="ok",
        value_low_confidence=False,
        value_payable_discrepancy=True,
        cpv="35611500",
        country="PRT",
    )
    assert p["estimated_value_eur"] == 7_317_073.17
    assert p["value_payable_eur"] == 7_274_615_930.0
    assert p["value_confidence"] == 0.71
    assert p["value_quality_flag"] == "ok"
    # False bool must be preserved (it is meaningful: kept and counted).
    assert p["value_low_confidence"] is False
    assert p["value_payable_discrepancy"] is True
    validate("UpsertContract", 1, p)  # raises on failure


def test_upsert_contract_flagged_value_validates():
    """A flagged (low-confidence) contract payload validates."""
    p = builders.upsert_contract(
        ted_notice_id="greek-drama",
        value_eur=1_073_062_200_000.0,
        estimated_value_eur=1_083_901.24,
        value_confidence=0.0,
        value_quality_flag="implausible_magnitude",
        value_low_confidence=True,
    )
    assert p["value_low_confidence"] is True
    assert p["value_quality_flag"] == "implausible_magnitude"
    validate("UpsertContract", 1, p)


def test_upsert_contract_omits_unset_value_quality_fields():
    """Unset value-quality fields are omitted from the payload."""
    p = builders.upsert_contract(ted_notice_id="minimal")
    for k in (
        "estimated_value_eur", "value_payable_eur", "value_confidence",
        "value_quality_flag", "value_low_confidence",
        "value_payable_discrepancy",
    ):
        assert k not in p
    validate("UpsertContract", 1, p)
