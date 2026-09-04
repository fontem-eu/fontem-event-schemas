"""Every builder must emit a payload its own schema accepts.

Two of the seventeen builders had tests. The rest were published to the
event log on trust: a builder that emits a field the schema forbids, or
omits one it requires, produces events that every sink rejects into the
DLQ — and nothing here would have caught it, because the schema-parity
tests pin the *schemas* to each other, not the builders to the schemas.

Each case below is the minimal call a producer actually makes. If a
schema gains a required field, or a builder starts emitting a stray key,
these fail at the builder rather than in production.
"""
from __future__ import annotations

import pytest

from fontem_event_schemas import builders, validate

# (event_type, builder, minimal kwargs a real producer passes)
_CASES = [
    ("UpsertSanctionedEntity", builders.upsert_sanctioned_entity,
     {"entity_id": "e-1", "eu_reference": "EU.27.1"}),
    ("UpsertFiling", builders.upsert_filing,
     {"gmr_id": "g-1", "year": 2026, "source": "edgar"}),
    ("UpsertCompany", builders.upsert_company,
     {"gmr_id": "g-1", "name": "ACME S.A.", "country": "PRT"}),
    ("UpsertInvestmentFund", builders.upsert_investment_fund,
     {"gmr_id": "g-2", "name": "Fund I"}),
    ("UpsertListing", builders.upsert_listing,
     {"ticker": "ACME", "company_gmr_id": "g-1"}),
    ("UpsertAuthority", builders.upsert_authority,
     {"authority_id": "a-1", "name": "Camara Municipal"}),
    ("UpsertTaxonomyCode", builders.upsert_taxonomy_code,
     {"system": "cpv", "code": "35611500"}),
    ("UpsertRelationship", builders.upsert_relationship,
     {"src_iri": "urn:a", "dst_iri": "urn:b", "predicate": "SUBSIDIARY_OF"}),
    ("UpsertDisclosure", builders.upsert_disclosure,
     {"system": "cdp", "disclosure_id": "d-1"}),
    ("UpsertExchangeRate", builders.upsert_exchange_rate,
     {"base": "USD", "target": "EUR", "date": "2026-08-26", "rate": 0.92}),
    ("TranslateAuthorityName", builders.translate_authority_name,
     {"authority_id": "a-1", "name": "Câmara",
      "translations": {"en": "City Council"}}),
    ("AssertSameAs", builders.assert_same_as,
     {"a_iri": "urn:a", "b_iri": "urn:b", "confidence": 0.97,
      "method": "lei_exact"}),
    ("UpsertPetition", builders.upsert_petition,
     {"system": "eci", "petition_id": "p-1"}),
    ("RetractSameAs", builders.retract_same_as,
     {"a_iri": "urn:a", "b_iri": "urn:b",
      "reason": "different registration numbers"}),
]


@pytest.mark.parametrize("event_type,builder,kwargs",
                         _CASES, ids=[c[0] for c in _CASES])
def test_builder_output_validates_against_its_schema(event_type, builder, kwargs):
    validate(event_type, 1, builder(**kwargs))


def test_begin_graph_replace_validates():
    validate("BeginGraphReplace", 1, builders.begin_graph_replace(
        graph_iri="urn:graph:ted", label="TED"))


def test_end_graph_replace_validates():
    validate("EndGraphReplace", 1, builders.end_graph_replace(
        graph_iri="urn:graph:ted"))


def test_graph_replace_bracket_agrees_on_the_graph_iri():
    """The sink pairs these by graph_iri; a mismatch strands the replace
    bracket open and the graph never swaps."""
    begin = builders.begin_graph_replace(graph_iri="urn:g", label="L")
    end = builders.end_graph_replace(graph_iri="urn:g")
    assert begin["graph_iri"] == end["graph_iri"]


# ── null hygiene ──────────────────────────────────────────────────────────
# Unset optionals must be absent, not present-and-null. A sink that does
# `if "field" in payload` would otherwise overwrite good data with None,
# and several schemas type their optionals without allowing null.

@pytest.mark.parametrize("event_type,builder,kwargs",
                         _CASES, ids=[c[0] for c in _CASES])
def test_builder_never_emits_a_null(event_type, builder, kwargs):
    payload = builder(**kwargs)
    nulls = [k for k, v in payload.items() if v is None]
    assert not nulls, f"{event_type} emitted null for {nulls}"


# ── falsy values that carry meaning ───────────────────────────────────────
# These are guarded with `is not None`, not truthiness. Rewriting one of
# them to `if value:` would silently drop the field — an inactive company
# would stay active downstream, and a level-0 taxonomy code would lose its
# level. Cheap to break, invisible when broken.

def test_active_false_survives_on_company():
    assert builders.upsert_company(
        gmr_id="g", name="X", active=False)["active"] is False


def test_active_false_survives_on_listing():
    assert builders.upsert_listing(
        ticker="T", company_gmr_id="g", active=False)["active"] is False


def test_active_false_survives_on_investment_fund():
    assert builders.upsert_investment_fund(
        gmr_id="g", name="F", active=False)["active"] is False


def test_level_zero_survives_on_taxonomy_code():
    assert builders.upsert_taxonomy_code(
        system="cpv", code="1", level=0)["level"] == 0


def test_zero_supporters_survives_on_petition():
    assert builders.upsert_petition(
        system="eci", petition_id="p", total_supporters=0
    )["total_supporters"] == 0


def test_empty_string_is_dropped_rather_than_emitted():
    """"" is how upstream spells 'absent'; storing it creates a fake value."""
    p = builders.upsert_sanctioned_entity(
        entity_id="e", eu_reference="r", name="", nationality="PT")
    assert "name" not in p
    assert p["nationality"] == "PT"
