"""PurgeSubject — deleting a subject the sink can no longer address.

The Virtuoso sink percent-encodes every subject IRI it writes (since
2026-06-07), and percent-encoding is idempotent: quote() maps the
encoded form to itself and there is no input it maps to the raw form.
So a pre-2026-06-07 subject holding raw non-ASCII is unreachable — a
Delete* event naming it would encode the IRI and delete the LIVE
record instead, which is worse than doing nothing.

Shared holds 3,166 such subjects, all in graph/listing (tickers are the
only non-ASCII natural key; everything else is UUID-keyed). Each is a
stale twin of a live listing, contradicting it and never expiring.
"""
import pytest

from fontem_event_schemas import builders, validate
from fontem_event_schemas.validate import EventValidationError

_RAW = "http://data.fontem.eu/id/Listing/BJÖRN.ST"
_G = "http://data.fontem.eu/graph/listing"


def test_builds_and_validates():
    payload = builders.purge_subject(
        graph_iri=_G, subject_iri=_RAW,
        reason="stranded by the 2026-06-07 IRI percent-encoding fix",
    )
    validate("PurgeSubject", 1, payload)
    assert payload["subject_iri"] == _RAW


def test_subject_iri_is_not_normalised():
    """The whole point: the IRI survives byte-for-byte. If anything in
    this path encoded it, the event would name the live subject."""
    payload = builders.purge_subject(
        graph_iri=_G, subject_iri=_RAW, reason="x",
    )
    assert "%C3%96" not in payload["subject_iri"]
    assert "Ö" in payload["subject_iri"]


def test_reason_is_required():
    """A destructive verbatim delete should never enter the log without
    a stated cause."""
    with pytest.raises(ValueError):
        builders.purge_subject(graph_iri=_G, subject_iri=_RAW, reason="")
    with pytest.raises(EventValidationError):
        validate("PurgeSubject", 1, {"graph_iri": _G, "subject_iri": _RAW})


def test_rejects_unknown_fields():
    with pytest.raises(EventValidationError):
        validate("PurgeSubject", 1, {
            "graph_iri": _G, "subject_iri": _RAW, "reason": "x",
            "cascade": True,
        })


def test_only_predicates_rides_in_the_payload_when_given():
    """The evidence half of a case-(2) purge: the subject's IRI is
    ordinary, so the event must declare what the subject may carry and
    let the sink check it against the store."""
    payload = builders.purge_subject(
        graph_iri=_G,
        subject_iri="http://data.fontem.eu/id/Notice/639139-2020",
        reason="orphan Notice subject from a mis-routed rollup",
        only_predicates=[
            "http://data.fontem.eu/ontology#isCurrent",
            "http://data.fontem.eu/ontology#currentValue",
        ],
    )
    assert payload["only_predicates"] == [
        "http://data.fontem.eu/ontology#isCurrent",
        "http://data.fontem.eu/ontology#currentValue",
    ]
    validate("PurgeSubject", 1, payload)


def test_only_predicates_is_absent_when_not_given():
    """Case (1) — an unproducible IRI — needs no predicate evidence, and
    the payload must not grow an empty field that the sink would then
    have to interpret."""
    payload = builders.purge_subject(
        graph_iri=_G, subject_iri=_RAW, reason="stranded by the encoding fix",
    )
    assert "only_predicates" not in payload
    validate("PurgeSubject", 1, payload)


def test_duplicate_predicates_are_collapsed():
    """The schema declares uniqueItems, so a caller passing the same
    predicate twice would fail validation rather than be tidied up."""
    payload = builders.purge_subject(
        graph_iri=_G, subject_iri="http://data.fontem.eu/id/Notice/n-1",
        reason="orphan", only_predicates=["urn:p", "urn:p", "urn:q"],
    )
    assert payload["only_predicates"] == ["urn:p", "urn:q"]
    validate("PurgeSubject", 1, payload)


def test_an_empty_only_predicates_is_refused():
    """An empty set asserts the subject carries no triples at all, which
    is not something a purge can be based on -- and would silently
    become 'refuse everything' in the sink."""
    with pytest.raises(ValueError):
        builders.purge_subject(
            graph_iri=_G, subject_iri="http://data.fontem.eu/id/Notice/n-1",
            reason="orphan", only_predicates=[],
        )
