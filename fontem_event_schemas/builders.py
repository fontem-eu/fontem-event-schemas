"""Typed builders for common event payloads.

Producers should prefer these over hand-rolling dicts: they keep
the field set in lockstep with the schema and let mypy / IDE flag
typos at edit time. Each returns a dict conforming to the
corresponding JSON Schema.
"""
from __future__ import annotations

import re
from typing import Any, Mapping


def upsert_sanctioned_entity(
    *,
    entity_id: str,
    eu_reference: str,
    name: str | None = None,
    aliases: list[str] | None = None,
    nationality: str | None = None,
    designation_date: str | None = None,
    sanction_regime: str | None = None,
    legal_basis: str | None = None,
    listing_reason: str | None = None,
    subject_type: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertSanctionedEntity payload (v1)."""
    out: dict[str, Any] = {
        "entity_id":    entity_id,
        "eu_reference": eu_reference,
    }
    for k, v in (
        ("name", name), ("aliases", aliases),
        ("nationality", nationality),
        ("designation_date", designation_date),
        ("sanction_regime", sanction_regime),
        ("legal_basis", legal_basis),
        ("listing_reason", listing_reason),
        ("subject_type", subject_type),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


def upsert_filing(
    *,
    gmr_id: str,
    year: int,
    source: str,
    filing_date: str | None = None,
    **financials: float | None,
) -> dict[str, Any]:
    """Build an UpsertFiling payload (v1).

    ``financials`` accepts any of the optional numeric Filing
    fields (revenue, net_income, …); None/missing values are
    dropped so the JSON stays compact and schema-clean.
    """
    out: dict[str, Any] = {
        "gmr_id": gmr_id, "year": year, "source": source,
    }
    if filing_date:
        out["filing_date"] = filing_date
    for k, v in financials.items():
        if v is not None:
            out[k] = float(v)
    return out


# GLEIF identity block (LEI-CDF v3.1) — carried on `identity`. Stored
# verbatim from the source, never inferred; a source that says nothing
# about a field simply omits it. `aliases` is a list; every other key is
# a scalar mapped straight onto the schema.
COMPANY_IDENTITY_FIELDS = (
    "entity_kind", "registered_as", "registered_at", "jurisdiction",
    "registration_status", "entity_creation_date", "address", "city",
    "region", "hq_address", "hq_city", "hq_region", "hq_country",
    "hq_postal_code", "aliases",
)


def upsert_company(
    *,
    gmr_id: str,
    name: str | None = None,
    country: str | None = None,
    lei: str | None = None,
    vat: str | None = None,
    cik: str | None = None,
    active: bool | None = None,
    legal_form: str | None = None,
    postal_code: str | None = None,
    identity: "Mapping[str, Any] | None" = None,
) -> dict[str, Any]:
    """Build an UpsertCompany payload (v1).

    `identity` bundles the optional GLEIF identity block — see
    ``COMPANY_IDENTITY_FIELDS``. Keys map straight onto the schema;
    None/"" values drop out and `aliases` is emitted only when non-empty.
    Unknown keys are forwarded and fail schema validation loudly rather
    than being silently swallowed."""
    out: dict[str, Any] = {"gmr_id": gmr_id}
    for k, v in (
        ("name", name), ("country", country), ("lei", lei),
        ("vat", vat), ("cik", cik), ("active", active),
        ("legal_form", legal_form), ("postal_code", postal_code),
    ):
        if v is not None and v != "":
            out[k] = v
    for k, v in (identity or {}).items():
        if k == "aliases":
            if v:
                out["aliases"] = list(v)
        elif v is not None and v != "":
            out[k] = v
    return out


def upsert_investment_fund(
    *,
    gmr_id: str,
    name: str | None = None,
    country: str | None = None,
    lei: str | None = None,
    active: bool | None = None,
    legal_form: str | None = None,
    fund_type: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertInvestmentFund payload (v1). Same gmr_id
    derivation as companies so an entity that first landed as a
    Company keeps its identity; sinks relabel the node."""
    out: dict[str, Any] = {"gmr_id": gmr_id}
    for k, v in (
        ("name", name), ("country", country), ("lei", lei),
        ("active", active), ("legal_form", legal_form),
        ("fund_type", fund_type),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


def upsert_listing(
    *,
    ticker: str,
    company_gmr_id: str,
    exchange: str | None = None,
    currency: str | None = None,
    active: bool | None = None,
    isin: str | None = None,
    mic: str | None = None,
    security_type: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertListing payload (v1)."""
    out: dict[str, Any] = {
        "ticker": ticker, "company_gmr_id": company_gmr_id,
    }
    for k, v in (
        ("exchange", exchange), ("currency", currency),
        ("active", active), ("isin", isin), ("mic", mic),
        ("security_type", security_type),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


def upsert_authority(
    *,
    authority_id: str,
    name: str | None = None,
    country: str | None = None,
    authority_type: str | None = None,
    national_id: str | None = None,
    url: str | None = None,
    postal_code: str | None = None,
    city: str | None = None,
    nuts: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertAuthority payload (v1)."""
    out: dict[str, Any] = {"authority_id": authority_id}
    for k, v in (
        ("name", name), ("country", country),
        ("authority_type", authority_type),
        ("national_id", national_id), ("url", url),
        ("postal_code", postal_code), ("city", city), ("nuts", nuts),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


def contract_party(
    *,
    company_gmr_id: str,
    name: str,
    role: str,
    rank: int | None = None,
    is_consortium_member: bool = False,
    tendering_party_id: str | None = None,
    match_tier: str | None = None,
    match_confidence: float | None = None,
    match_layer: int | None = None,
) -> dict[str, Any]:
    """Build one item of UpsertContract ``parties`` (v1).

    ``role`` is 'winner' (referenced by a selec-w LotResult, or legacy
    CONTRACTOR/ECONOMIC_OPERATOR) or 'named_tenderer' (named in the
    notice but not in a winning result — rare, eForms only).
    ``is_consortium_member`` marks a supplier that shares one undivided
    tender value with its co-members (grouped by ``tendering_party_id``);
    the schema default is false, so it is emitted only when True.
    ``match_*`` carry the consolidator resolution metadata, same
    semantics as the top-level fields on the contract itself.
    """
    out: dict[str, Any] = {
        "company_gmr_id": company_gmr_id, "name": name, "role": role,
    }
    if is_consortium_member:
        out["is_consortium_member"] = True
    for k, v in (
        ("rank", rank),
        ("tendering_party_id", tendering_party_id),
        ("match_tier", match_tier),
        ("match_confidence", match_confidence),
        ("match_layer", match_layer),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


# The OPT-100 Framework Notice Identifier is a GROUPING key: every award
# notice of one framework carries the same value, so any difference in
# spelling splits one framework into several. Two spellings do differ in
# the wild. BT-125 publishes the publication number zero-padded
# ('00536632-2024' for the notice TED's own framework-notice-id index
# calls '536632-2024' — the padded form returns 0 results there), and the
# UUID form carries the publishing notice's own version as a '-NN'
# suffix, which differs between two notices of the SAME framework.
# Normalising here rather than in each producer keeps every producer on
# one key.
_PUBLICATION_NUMBER = re.compile(r"^0*(\d+)-(\d{4})$")
_UUID_WITH_VERSION = re.compile(
    r"^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})-\d{2}$"
)


def normalise_framework_id(value: str | None) -> str | None:
    """Return an OPT-100 Framework Notice Identifier in grouping form.

    Unpads the publication number ('00536632-2024' -> '536632-2024')
    and drops the '-NN' version suffix of the UUID form
    ('45d7e260-...-8beea8b77-01' -> '45d7e260-...-8beea8b77'). Anything
    that matches neither form is returned unchanged — the key is
    whatever the notice published, and inventing a shape for an
    unexpected value would group notices that do not belong together.
    Idempotent, so a producer may call it on an already-normalised id.
    """
    if not value:
        return value
    v = value.strip()
    if m := _PUBLICATION_NUMBER.match(v):
        return f"{int(m.group(1))}-{m.group(2)}"
    if m := _UUID_WITH_VERSION.match(v):
        return m.group(1)
    return v


def withheld_supplier(
    *,
    name_raw: str,
    reason: str,
    role: str,
    org_id: str | None = None,
) -> dict[str, Any]:
    """Build one item of UpsertContract ``suppliers_withheld`` (v1).

    A supplier the cleaning stage refused to turn into an entity: the
    name field held a sentence, a placeholder or other non-name text.
    It goes here instead of ``parties`` and no company is created for
    it — the sink MATCHes both ends of AWARDED_TO, so a reference to a
    company that does not exist would re-create the junk node.
    ``name_raw`` is kept verbatim (it is often the only pointer to
    where the real award is published), ``reason`` is the rule id that
    fired (e.g. ``it.notice_text_in_supplier_name``), ``role`` is what
    the supplier would have been in ``parties``, and ``org_id`` is the
    notice's own organisation id so the supplier can be found in the
    XML again.
    """
    out: dict[str, Any] = {
        "name_raw": name_raw, "reason": reason, "role": role,
    }
    if org_id is not None and org_id != "":
        out["org_id"] = org_id
    return out


def upsert_contract(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    *,
    ted_notice_id: str,
    ted_publication_number: str | None = None,
    title: str | None = None,
    authority_id: str | None = None,
    company_gmr_id: str | None = None,
    publication_date: str | None = None,
    award_date_raw: str | None = None,
    tender_result_award_date_raw: str | None = None,
    value_eur: float | None = None,
    value_currency: str | None = None,
    value_original: float | None = None,
    value_raw: str | None = None,
    value_before_eur: float | None = None,
    value_before_original: float | None = None,
    estimated_value_eur: float | None = None,
    value_payable_eur: float | None = None,
    value_confidence: float | None = None,
    value_confidence_consistency: float | None = None,
    value_confidence_plausibility: float | None = None,
    value_quality_flag: str | None = None,
    value_low_confidence: bool | None = None,
    value_payable_discrepancy: bool | None = None,
    value_quarantined: bool | None = None,
    value_quarantine_reason: str | None = None,
    value_scale_corrected: str | None = None,
    match_tier: str | None = None,
    match_confidence: float | None = None,
    match_layer: int | None = None,
    cpv: str | None = None,
    nuts: str | None = None,
    language: str | None = None,
    notice_language: str | None = None,
    country: str | None = None,
    procedure_type: str | None = None,
    tenders_received: int | None = None,
    award_criterion_type: str | None = None,
    submission_deadline: str | None = None,
    is_framework: bool | None = None,
    framework_id: str | None = None,
    framework_id_source: str | None = None,
    framework_max_value_eur: float | None = None,
    framework_reestimated_value_eur: float | None = None,
    framework_duration_months: int | None = None,
    framework_max_operators: int | None = None,
    eu_funded: bool | None = None,
    funding_programme: str | None = None,
    procedure_id: str | None = None,
    legacy_procedure_id: str | None = None,
    tender_reference: str | None = None,
    notice_type: str | None = None,
    notice_version: str | None = None,
    eforms_sdk: str | None = None,
    notice_kind: str | None = None,
    modifies_publication_number: str | None = None,
    modifies_notice_id: str | None = None,
    current_value: float | None = None,
    is_current: bool | None = None,
    contract_key: str | None = None,
    award_ingested: bool | None = None,
    parties: list[dict[str, Any]] | None = None,
    suppliers_withheld: list[dict[str, Any]] | None = None,
    cleaning_rules: list[str] | None = None,
) -> dict[str, Any]:
    """Build an UpsertContract payload (v1).

    ``value_scale_corrected`` marks a notice whose monetary fields were
    rescaled /1000 at load time to undo the milli-euro fixed-point leak
    in a national eForms gateway (see fontem-api scale_normalization).
    Values: "ratio" (sibling-estimate evidence) or "country_prior".

    ``ted_notice_id`` is the eForms internal UUID (the cbc:ID root
    identifier). ``ted_publication_number`` is the human-readable
    ``<seq>-<year>`` identifier TED assigns at publish time and which
    TED's public detail URL is keyed by — capturing it at ETL time
    lets readers skip the runtime UUID→pub-num search call.

    ``country`` is the alpha-3 country of the contracting authority (the
    acquirer). Cascaded onto the Contract at write time so jurisdictional
    panels can group contracts without traversing to Authority.

    Value-quality fields (all derived by ``contract_confidence``):
    ``value_eur`` is the awarded value the loader chose to trust (the
    eForms ``TotalAmount``, falling back to ``PayableAmount``).
    ``estimated_value_eur`` and ``value_payable_eur`` are the two
    cross-check signals kept alongside it. ``value_confidence`` in
    ``[0, 1]`` is consistency × plausibility; ``value_low_confidence`` is
    the boolean gate consumers use to exclude a contract from default
    aggregates. ``value_quality_flag`` explains why (ok /
    value_disagreement / implausible_magnitude / concession_negative /
    zero_value / no_awarded_value / unverified_single_signal).
    ``value_payable_discrepancy`` marks a notice whose payable disagrees
    with the stored total (an internal source inconsistency) even when the
    contract is otherwise kept.

    Contract-chain fields (all stamped from the notice XML by the
    parser, not from the search API): ``procedure_id`` (BT-04) is the
    contract identity for eForms notices and ``contract_key`` equals it;
    legacy notices are keyed by their publication number and keep the
    authority's file reference as ``legacy_procedure_id``.
    ``notice_version`` (BT-757) makes ``(ted_notice_id, notice_version)``
    the loader's skip unit. ``notice_kind`` ('award' | 'modification')
    is the normalised classification; ``notice_type`` the raw eForms
    code. A modification's back-link (BT-1501) arrives as exactly one of
    ``modifies_publication_number`` / ``modifies_notice_id``; the sink
    resolves it on write, so a modification adopts its root award's
    entity and the chain is linked from the first event. ``is_current``
    is true on the latest notice of a chain, ``current_value`` the
    contract's last restated value, and ``award_ingested`` tells whether
    the entity has seen its award yet — the sink maintains all three.

    ``parties`` is the full list of named suppliers on the notice —
    build items with ``contract_party`` so unset fields drop out. The
    top-level ``company_gmr_id`` + ``match_*`` fields are kept as the
    primary winner for backward compatibility.

    Cleaning-stage fields (data-backlog Part 5; the cleaner never
    rewrites silently, so every rule leaves the raw value and its name
    on the event): ``suppliers_withheld`` lists the suppliers the
    cleaner refused to turn into entities — build items with
    ``withheld_supplier``; each is absent from ``parties`` and has no
    company, its raw text kept as a pointer. ``cleaning_rules`` names
    every rule id that fired on the notice, in firing order and each
    once (duplicates are collapsed here; an empty list means the
    notice was cleaned and nothing fired). ``value_raw`` is the award
    amount verbatim as published, before scale correction or FX;
    ``value_quarantine_reason`` says why a value was withheld and now
    also carries cleaning rule ids such as
    ``ambiguous_scale_x100_or_x1000``.

    Watermark and provenance fields, all verbatim from the notice XML
    and persisted so the gateway-watermark census can run from the
    graph: ``award_date_raw`` (the contract's award/conclusion date,
    BT-145 / DATE_CONCLUSION_CONTRACT, kept even when a placeholder
    like ``2000-01-01`` is discarded from the typed field);
    ``tender_result_award_date_raw`` (the lot result's winner-decision
    date, BT-1451 — where the PT gateway writes its ``2000-01-01``
    watermark); ``tender_reference`` (the winning tender's id, BT-3201
    — ``0.0`` under the same watermark); ``notice_language`` (the
    declared language as published, BT-702, before normalisation to
    ``language``); ``eforms_sdk`` (the ``CustomizationID``, e.g.
    ``eforms-sdk-1.14``, the version gateway-specific rules scope on).

    Framework-agreement fields. ``framework_id`` is the normalised
    OPT-100 Framework Notice Identifier — the grouping key every award
    notice of one framework carries, the establishing notice and every
    call-off alike, so it never says which of the two a notice is.
    ``normalise_framework_id`` is applied on the way out, so the
    zero-padding a BT-125 reference publishes (``00536632-2024`` ->
    ``536632-2024``, the form TED's own framework-notice-id index
    matches) and the ``-NN`` version suffix of the UUID form never
    split one framework into several groups. ~80% of the time it names a
    call-for-competition notice, which this platform does not ingest,
    so it is a key and not a reference to a contract we hold.
    ``framework_id_source`` says which reference it was read from:
    ``"opt-100"`` (efac:SettledContract — the strong signal) or
    ``"bt-125"`` (cac:TenderingProcess — the general previous-notice
    back-link, which may name a planning notice instead).
    ``is_framework`` means the notice belongs to a framework procedure,
    not that it established one: call-offs carry it too. The terms
    below are what this notice published, with no claim about which
    notice established the framework — ``framework_max_value_eur`` is
    the ceiling (BT-118 / BT-709 — capacity, never spend, so it must
    never enter a sum), ``framework_reestimated_value_eur`` the buyer's
    re-estimate (BT-660), ``framework_duration_months`` the validity
    (BT-36) and ``framework_max_operators`` how many operators the
    framework admits (BT-113).
    """
    out: dict[str, Any] = {"ted_notice_id": ted_notice_id}
    for k, v in (
        ("ted_publication_number", ted_publication_number),
        ("title", title), ("authority_id", authority_id),
        ("company_gmr_id", company_gmr_id),
        ("publication_date", publication_date),
        ("award_date_raw", award_date_raw),
        ("tender_result_award_date_raw", tender_result_award_date_raw),
        ("value_eur", value_eur), ("value_currency", value_currency),
        ("value_original", value_original),
        ("value_raw", value_raw),
        ("value_before_eur", value_before_eur),
        ("value_before_original", value_before_original),
        ("estimated_value_eur", estimated_value_eur),
        ("value_payable_eur", value_payable_eur),
        ("value_confidence", value_confidence),
        ("value_confidence_consistency", value_confidence_consistency),
        ("value_confidence_plausibility", value_confidence_plausibility),
        ("value_quality_flag", value_quality_flag),
        ("value_low_confidence", value_low_confidence),
        ("value_payable_discrepancy", value_payable_discrepancy),
        ("value_quarantined", value_quarantined),
        ("value_quarantine_reason", value_quarantine_reason),
        ("value_scale_corrected", value_scale_corrected),
        ("match_tier", match_tier),
        ("match_confidence", match_confidence),
        ("match_layer", match_layer),
        ("cpv", cpv), ("nuts", nuts), ("language", language),
        ("notice_language", notice_language),
        ("country", country),
        ("procedure_type", procedure_type),
        ("tenders_received", tenders_received),
        ("award_criterion_type", award_criterion_type),
        ("submission_deadline", submission_deadline),
        ("is_framework", is_framework),
        ("framework_id", normalise_framework_id(framework_id)),
        ("framework_id_source", framework_id_source),
        ("framework_max_value_eur", framework_max_value_eur),
        ("framework_reestimated_value_eur", framework_reestimated_value_eur),
        ("framework_duration_months", framework_duration_months),
        ("framework_max_operators", framework_max_operators),
        ("eu_funded", eu_funded),
        ("funding_programme", funding_programme),
        ("procedure_id", procedure_id),
        ("legacy_procedure_id", legacy_procedure_id),
        ("tender_reference", tender_reference),
        ("notice_type", notice_type),
        ("notice_version", notice_version),
        ("eforms_sdk", eforms_sdk),
        ("notice_kind", notice_kind),
        ("modifies_publication_number", modifies_publication_number),
        ("modifies_notice_id", modifies_notice_id),
        ("current_value", current_value),
        ("is_current", is_current),
        ("contract_key", contract_key),
        ("award_ingested", award_ingested),
        ("parties", parties),
        ("suppliers_withheld", suppliers_withheld),
    ):
        if v is not None and v != "":
            out[k] = v
    if cleaning_rules is not None:
        out["cleaning_rules"] = list(dict.fromkeys(cleaning_rules))
    return out


def framework_supplier(
    *,
    company_gmr_id: str,
    lot: str | None = None,
    rank: int | None = None,
) -> dict[str, Any]:
    """Build one item of UpsertFrameworkAgreement ``suppliers`` (v1).

    One economic operator admitted to the framework (a PARTY_TO edge).
    ``lot`` is the lot it is admitted for and ``rank`` its cbc:RankCode
    in the lot's cascade; both drop out when unknown.
    """
    out: dict[str, Any] = {"company_gmr_id": company_gmr_id}
    for k, v in (("lot", lot), ("rank", rank)):
        if v is not None and v != "":
            out[k] = v
    return out


def upsert_framework_agreement(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    framework_id: str,
    buyer_authority_id: str | None = None,
    establishing_notice_id: str | None = None,
    country: str | None = None,
    ceiling_eur: float | None = None,
    ceiling_currency: str | None = None,
    ceiling_original: float | None = None,
    reestimated_value_eur: float | None = None,
    duration_start: str | None = None,
    duration_end: str | None = None,
    duration_months: int | None = None,
    cpv: str | None = None,
    lot_count: int | None = None,
    supplier_count: int | None = None,
    title: str | None = None,
    suppliers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an UpsertFrameworkAgreement payload (v1).

    A framework agreement as a first-class entity, keyed by the
    framework's own grouping key: ``framework_id`` is the normalised
    OPT-100 Framework Notice Identifier (an unpadded publication
    number, or the UUID form without its ``-NN`` version suffix), which
    every award notice of the framework carries, so they all converge
    on one node. It is NOT the establishing procedure's contract key:
    OPT-100 names a notice in the same ContractFolderID only 53.5% of
    the time, a different folder 17.2%, and legacy targets have no
    folder at all. It is passed through ``normalise_framework_id``, as
    on the contract side, so both ends of CALL_OFF_OF agree. Contracts
    point back at it through ``upsert_contract(framework_id=...)``.

    ``ceiling_eur`` (with ``ceiling_currency`` / ``ceiling_original``)
    is capacity, not spend — no aggregate may sum it; call-off spend is
    consumed against it. ``reestimated_value_eur`` is the buyer's later
    expectation of what will actually be called off. ``suppliers`` is
    every operator admitted to the framework — build items with
    ``framework_supplier`` — and ``supplier_count`` the number the
    notice published, which may exceed it when the cleaning stage
    withheld some. ``buyer_authority_id``, ``establishing_notice_id``
    and ``country`` are provenance — the authority and the notice this
    event was built from, not proof that that notice established the
    framework; nothing in the data tells an establishment from a
    call-off.
    """
    out: dict[str, Any] = {
        "framework_id": normalise_framework_id(framework_id),
    }
    for k, v in (
        ("buyer_authority_id", buyer_authority_id),
        ("establishing_notice_id", establishing_notice_id),
        ("country", country),
        ("ceiling_eur", ceiling_eur),
        ("ceiling_currency", ceiling_currency),
        ("ceiling_original", ceiling_original),
        ("reestimated_value_eur", reestimated_value_eur),
        ("duration_start", duration_start),
        ("duration_end", duration_end),
        ("duration_months", duration_months),
        ("cpv", cpv),
        ("lot_count", lot_count),
        ("supplier_count", supplier_count),
        ("title", title),
        ("suppliers", suppliers),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


def upsert_taxonomy_code(
    *,
    system: str,
    code: str,
    label: str | None = None,
    label_lang: str | None = None,
    parent_code: str | None = None,
    level: int | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertTaxonomyCode payload (v1)."""
    out: dict[str, Any] = {"system": system, "code": code}
    for k, v in (
        ("label", label), ("label_lang", label_lang),
        ("parent_code", parent_code),
        ("level", level), ("description", description),
    ):
        if v is not None and v != "":
            out[k] = v
    return out


def upsert_relationship(
    *,
    src_iri: str,
    dst_iri: str,
    predicate: str,
    properties: dict[str, Any] | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertRelationship payload (v1)."""
    out: dict[str, Any] = {
        "src_iri": src_iri, "dst_iri": dst_iri, "predicate": predicate,
    }
    if properties:
        out["properties"] = properties
    if valid_from:
        out["valid_from"] = valid_from
    if valid_to:
        out["valid_to"] = valid_to
    return out


def upsert_disclosure(
    *,
    system: str,
    disclosure_id: str,
    company_gmr_id: str | None = None,
    disclosure_type: str | None = None,
    filed_date: str | None = None,
    year: int | None = None,
    title: str | None = None,
    url: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an UpsertDisclosure payload (v1).

    ``company_gmr_id`` is optional — some regimes (EU lobbying)
    file under non-Company registrants, in which case the
    registrant identity rides in ``details``.
    """
    out: dict[str, Any] = {
        "system": system,
        "disclosure_id": disclosure_id,
    }
    if company_gmr_id:
        out["company_gmr_id"] = company_gmr_id
    for k, v in (
        ("disclosure_type", disclosure_type),
        ("filed_date", filed_date), ("year", year),
        ("title", title), ("url", url),
    ):
        if v is not None and v != "":
            out[k] = v
    if details:
        out["details"] = details
    return out


def upsert_exchange_rate(
    *,
    base: str,
    target: str,
    date: str,
    rate: float,
    source: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertExchangeRate payload (v1)."""
    out: dict[str, Any] = {
        "base": base, "target": target,
        "date": date, "rate": float(rate),
    }
    if source:
        out["source"] = source
    return out


def translate_authority_name(
    *,
    authority_id: str,
    name: str,
    translations: dict[str, str],
    source_lang: str | None = None,
    method: str | None = None,
    translated_at: str | None = None,
) -> dict[str, Any]:
    """Build a TranslateAuthorityName payload (v1).

    Multilingual name enrichment for one authority. ``translations``
    maps ISO 639-1 code -> translated name; blank values are dropped.
    Carries the canonical ``name`` so sinks recompose derived state
    (embed_text, name_<lang> props, labels) statelessly — no read of
    prior sink state, order-independent on replay.
    """
    out: dict[str, Any] = {
        "authority_id": authority_id,
        "name": name,
        "translations": {
            k: v for k, v in translations.items() if v and str(v).strip()
        },
    }
    if source_lang:
        out["source_lang"] = source_lang
    if method:
        out["method"] = method
    if translated_at:
        out["translated_at"] = translated_at
    return out


def assert_same_as(
    *,
    a_iri: str,
    b_iri: str,
    confidence: float,
    method: str,
    tier: str | None = None,
    matched_via_alias: bool = False,
    rule: str | None = None,
) -> dict[str, Any]:
    """Build an AssertSameAs payload (v1)."""
    out: dict[str, Any] = {
        "a_iri": a_iri, "b_iri": b_iri,
        "confidence": float(confidence), "method": method,
        "matched_via_alias": bool(matched_via_alias),
    }
    if tier is not None:
        out["tier"] = tier
    if rule is not None:
        out["rule"] = rule
    return out


def retract_same_as(
    *,
    a_iri: str,
    b_iri: str,
    reason: str,
    reviewer: str | None = None,
    retracted_method: str | None = None,
) -> dict[str, Any]:
    """Build a RetractSameAs payload (v1).

    Withdraws an equivalence that was actually asserted. Declining a
    review candidate is NOT a retraction — a candidate never asserted
    anything, so there is nothing to withdraw.
    """
    out: dict[str, Any] = {"a_iri": a_iri, "b_iri": b_iri, "reason": reason}
    if reviewer is not None:
        out["reviewer"] = reviewer
    if retracted_method is not None:
        out["retracted_method"] = retracted_method
    return out


def begin_graph_replace(
    *, graph_iri: str, label: str, domain: str | None = None,
) -> dict[str, Any]:
    """Build a BeginGraphReplace control payload (v1)."""
    out: dict[str, Any] = {"graph_iri": graph_iri, "label": label}
    if domain:
        out["domain"] = domain
    return out


def end_graph_replace(
    *, graph_iri: str, domain: str | None = None,
) -> dict[str, Any]:
    """Build an EndGraphReplace control payload (v1)."""
    out: dict[str, Any] = {"graph_iri": graph_iri}
    if domain:
        out["domain"] = domain
    return out


def purge_subject(
    *, graph_iri: str, subject_iri: str, reason: str,
    only_predicates: "list[str] | None" = None,
) -> dict[str, Any]:
    """Build a PurgeSubject control payload (v1).

    For subjects a sink can no longer address through its normal write
    path. A subject gets there two ways.

    The IRI is unproducible: the Virtuoso sink percent-encodes every
    subject IRI it writes, and percent-encoding is idempotent, so a
    Delete* event naming a raw non-ASCII subject encodes to the LIVE
    subject and deletes that instead — the opposite of the intent.
    ``subject_iri`` here is used byte-for-byte.

    Or the IRI is ordinary but nothing routes there any more: a renderer
    that used to write a subject family stops doing so and its leftovers
    are refreshed by no upsert and named by no Delete*. Those subjects
    are indistinguishable from live ones by IRI alone, so pass
    ``only_predicates`` — every predicate the subject may carry. The
    sink checks the store against it and refuses the purge if the
    subject holds anything else, which is what stops a mistaken event
    from deleting a record in use.

    ``reason`` is required, not optional: this is the one event that
    deletes by an IRI the normal rules cannot produce, and the log
    should say why on every occurrence.
    """
    if not reason or not reason.strip():
        raise ValueError("purge_subject requires a non-empty reason")
    payload: dict[str, Any] = {
        "graph_iri": graph_iri,
        "subject_iri": subject_iri,
        "reason": reason,
    }
    if only_predicates is not None:
        if not only_predicates:
            raise ValueError(
                "purge_subject only_predicates must be non-empty when given; "
                "an empty set would assert the subject carries no triples at "
                "all, which no purge can be based on"
            )
        payload["only_predicates"] = list(dict.fromkeys(only_predicates))
    return payload


def upsert_petition(  # pylint: disable=too-many-arguments,too-many-locals
    *,
    system: str,
    petition_id: str,
    title: str | None = None,
    status: str | None = None,
    objectives: str | None = None,
    registration_date: str | None = None,
    collection_start_date: str | None = None,
    collection_deadline: str | None = None,
    closed_date: str | None = None,
    submitted_date: str | None = None,
    answered_date: str | None = None,
    total_supporters: int | None = None,
    support_link: str | None = None,
    organizer_names: list[str] | None = None,
    organizer_roles: list[str] | None = None,
    organizer_countries: list[str] | None = None,
    funding_total_eur: float | None = None,
    funding_sponsor_count: int | None = None,
    registration_decision_celex: str | None = None,
    answer_refs: list[str] | None = None,
    latest_update: str | None = None,
) -> dict[str, Any]:
    """Build an UpsertPetition payload (v1)."""
    out: dict[str, Any] = {
        "system": system,
        "petition_id": petition_id,
    }
    for k, v in (
        ("title", title), ("status", status), ("objectives", objectives),
        ("registration_date", registration_date),
        ("collection_start_date", collection_start_date),
        ("collection_deadline", collection_deadline),
        ("closed_date", closed_date), ("submitted_date", submitted_date),
        ("answered_date", answered_date),
        ("total_supporters", total_supporters),
        ("support_link", support_link),
        ("organizer_names", organizer_names),
        ("organizer_roles", organizer_roles),
        ("organizer_countries", organizer_countries),
        ("funding_total_eur", funding_total_eur),
        ("funding_sponsor_count", funding_sponsor_count),
        ("registration_decision_celex", registration_decision_celex),
        ("answer_refs", answer_refs), ("latest_update", latest_update),
    ):
        if v is not None:
            out[k] = v
    return out
