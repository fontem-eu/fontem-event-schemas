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
