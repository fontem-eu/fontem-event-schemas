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


def test_upsert_contract_threads_integrity_fields():
    """Tender-integrity fields land on the payload and it validates."""
    p = builders.upsert_contract(
        ted_notice_id="integrity-1",
        procedure_type="open",
        tenders_received=1,
        award_criterion_type="price",
        submission_deadline="2026-03-01",
        is_framework=False,
        eu_funded=True,
        funding_programme="RRF",
    )
    assert p["procedure_type"] == "open"
    assert p["tenders_received"] == 1            # single-bidder signal
    assert p["award_criterion_type"] == "price"
    assert p["submission_deadline"] == "2026-03-01"
    assert p["is_framework"] is False            # meaningful False preserved
    assert p["eu_funded"] is True
    assert p["funding_programme"] == "RRF"
    validate("UpsertContract", 1, p)             # raises on failure


def test_upsert_contract_threads_modification_before_values():
    """The pre-modification before-values thread through and validate —
    the corruption-signal delta pairs value_before_* with value_*
    (here the €1,092 -> €2,184 doubling from a real legacy F20)."""
    p = builders.upsert_contract(
        ted_notice_id="24082-2024",
        value_eur=2184.6,
        value_currency="EUR",
        value_original=2184.6,
        value_before_eur=1092.3,
        value_before_original=1092.3,
    )
    assert p["value_before_eur"] == 1092.3
    assert p["value_before_original"] == 1092.3
    validate("UpsertContract", 1, p)


def test_upsert_contract_omits_unset_before_values():
    """Non-modification contracts carry no before-values."""
    p = builders.upsert_contract(ted_notice_id="minimal")
    assert "value_before_eur" not in p
    assert "value_before_original" not in p


def test_upsert_investment_fund_validates_and_omits_unset():
    from fontem_event_schemas import validate
    from fontem_event_schemas.builders import upsert_investment_fund
    payload = upsert_investment_fund(
        gmr_id="0b6cbfa6-6a30-5efc-9b4f-3e56d0f3f5a2",
        name="EXAMPLE UCITS FUND",
        lei="2138008K5B3Z4E8DHN12",
        fund_type="Open-End Fund",
    )
    assert "country" not in payload      # unset fields stay absent
    assert payload["fund_type"] == "Open-End Fund"
    validate("UpsertInvestmentFund", 1, payload)   # raises on failure


def test_upsert_listing_threads_security_type():
    from fontem_event_schemas import validate
    from fontem_event_schemas.builders import upsert_listing
    payload = upsert_listing(
        ticker="EGL", company_gmr_id="0b6cbfa6-6a30-5efc-9b4f-3e56d0f3f5a2",
        exchange="PL", security_type="Common Stock",
    )
    assert payload["security_type"] == "Common Stock"
    validate("UpsertListing", 1, payload)


def test_upsert_listing_omits_unset_security_type():
    from fontem_event_schemas.builders import upsert_listing
    payload = upsert_listing(
        ticker="EGL", company_gmr_id="0b6cbfa6-6a30-5efc-9b4f-3e56d0f3f5a2",
    )
    assert "security_type" not in payload


def test_fund_security_type_taxonomy():
    from fontem_event_schemas.securities import (
        COMPANY_SECURITY_TYPES2,
        FUND_SECURITY_TYPES2,
        is_fund_security_type,
    )
    assert "Common Stock" in COMPANY_SECURITY_TYPES2
    assert "Mutual Fund" in FUND_SECURITY_TYPES2
    assert not COMPANY_SECURITY_TYPES2 & FUND_SECURITY_TYPES2
    assert is_fund_security_type("Open-End Fund")
    assert is_fund_security_type("ETP")
    assert not is_fund_security_type("Common Stock")
    assert not is_fund_security_type(None)


def test_upsert_contract_threads_quarantine_fields():
    from fontem_event_schemas import validate
    from fontem_event_schemas.builders import upsert_contract
    payload = upsert_contract(
        ted_notice_id="n-1",
        value_quarantined=True,
        value_quarantine_reason="implausible_magnitude",
    )
    assert payload["value_quarantined"] is True
    assert payload["value_quarantine_reason"] == "implausible_magnitude"
    validate("UpsertContract", 1, payload)
    # unset stays absent — a normal contract carries neither key
    clean = upsert_contract(ted_notice_id="n-2")
    assert "value_quarantined" not in clean
