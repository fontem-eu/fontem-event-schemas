"""The repo ships every schema twice: the repo-root ``v1/`` tree (the
reviewable source of truth) and the packaged copy under
``fontem_event_schemas/schemas/`` (what an installed producer/sink
actually loads — loader._candidate_roots prefers it even from a source
checkout). Commit 1ea8036 proved they can silently drift: fields were
added to the packaged copy only, so the root tree lied to reviewers.

These tests pin the two trees byte-identical so drift is a CI failure,
and pin the upsert_contract builder to the schema's full field set so
producers never need the payload.update() escape hatch again.
"""
from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from fontem_event_schemas import builders, load_schema

_REPO_ROOT = Path(__file__).resolve().parent.parent
_ROOT_TREE = _REPO_ROOT / "v1"
_PACKAGED_TREE = _REPO_ROOT / "fontem_event_schemas" / "schemas" / "v1"


def _rel_files(tree: Path) -> set[Path]:
    return {p.relative_to(tree) for p in tree.rglob("*.json")}


def test_both_trees_ship_the_same_schema_files() -> None:
    root_files = _rel_files(_ROOT_TREE)
    packaged_files = _rel_files(_PACKAGED_TREE)
    assert root_files, "root v1/ tree is empty — running outside a checkout?"
    only_root = sorted(map(str, root_files - packaged_files))
    only_packaged = sorted(map(str, packaged_files - root_files))
    assert not only_root, f"missing from packaged tree: {only_root}"
    assert not only_packaged, f"missing from root tree: {only_packaged}"


@pytest.mark.parametrize(
    "rel", sorted(_rel_files(_ROOT_TREE), key=str), ids=str,
)
def test_schema_trees_are_byte_identical(rel: Path) -> None:
    root_bytes = (_ROOT_TREE / rel).read_bytes()
    packaged_bytes = (_PACKAGED_TREE / rel).read_bytes()
    assert root_bytes == packaged_bytes, (
        f"schema drift: v1/{rel} != fontem_event_schemas/schemas/v1/{rel} — "
        "edit both copies identically (the packaged copy is the one the "
        "loader actually uses)"
    )


def test_upsert_contract_builder_covers_every_schema_field() -> None:
    """Every UpsertContract property is an explicit builder kwarg (and
    vice versa), so producers never bypass the builder with
    payload.update({...}) for fields the builder doesn't know."""
    schema_fields = set(load_schema("UpsertContract", 1)["properties"])
    builder_kwargs = set(
        inspect.signature(builders.upsert_contract).parameters
    )
    assert schema_fields == builder_kwargs


def test_contract_party_builder_covers_every_party_field() -> None:
    party_schema = load_schema("UpsertContract", 1)["properties"]["parties"]
    party_fields = set(party_schema["items"]["properties"])
    helper_kwargs = set(
        inspect.signature(builders.contract_party).parameters
    )
    assert party_fields == helper_kwargs


def test_loaded_schema_matches_root_tree() -> None:
    """Whatever tree the loader picked, it parses to the same document
    as the reviewable root copy."""
    loaded = load_schema("UpsertContract", 1)
    root = json.loads(
        (_ROOT_TREE / "entities" / "UpsertContract.json").read_text()
    )
    assert loaded == root
