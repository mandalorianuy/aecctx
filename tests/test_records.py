from __future__ import annotations

import pytest

from aecctx.records import RecordModelError, ValueState
from aecctx.vocabulary import resolve_neutral_term


@pytest.mark.parametrize("state", ["unknown", "not_applicable", "conflicted", "explicit_null", "unsupported"])
def test_non_known_value_states_require_reason_code(state: str) -> None:
    with pytest.raises(RecordModelError) as captured:
        ValueState.from_dict({"state": state})

    assert captured.value.code == "AECCTX_VALUE_STATE_REASON_REQUIRED"


def test_known_value_state_preserves_falsey_value() -> None:
    value = ValueState.from_dict({"state": "known", "value": 0, "unit": "m"})

    assert value.state == "known"
    assert value.value == 0
    assert value.unit == "m"


def test_unknown_value_state_never_synthesizes_default() -> None:
    value = ValueState.from_dict({"state": "unknown", "reason_code": "AECCTX_NOT_OBSERVED"})

    assert value.value is None
    assert value.reason_code == "AECCTX_NOT_OBSERVED"


def test_project_neutral_term_resolves_to_versioned_uri() -> None:
    assert resolve_neutral_term("aecctx:linear-element") == "https://aecctx.dev/vocabulary/v0.1#linear-element"


def test_external_or_unregistered_terms_remain_explicit() -> None:
    assert resolve_neutral_term("https://example.org/classification/Thing") is None
