from __future__ import annotations

import aecctx.records as records
import pytest


def test_v02_typed_models_are_public() -> None:
    assert hasattr(records, "InferenceMetadata")
    assert hasattr(records, "CoordinateQualification")
    assert hasattr(records, "RepresentationFidelity")
    assert hasattr(records, "ProviderAttestation")


def test_inference_metadata_preserves_separate_confidence_and_reproducibility() -> None:
    digest = "a" * 64

    value = records.InferenceMetadata.from_dict(
        {
            "execution_mode": "local",
            "extraction_confidence": 0.92,
            "input_artifact_sha256": digest,
            "input_region_sha256": digest,
            "interpretation_confidence": 0.61,
            "provider_id": "org.example.ocr",
            "provider_version": "1.2.3",
            "reproducibility": "seeded",
            "request_digest": digest,
            "response_digest": digest,
            "verification_state": "unverified",
        }
    )

    assert value.provider_id == "org.example.ocr"
    assert value.extraction_confidence == 0.92
    assert value.interpretation_confidence == 0.61
    assert value.reproducibility == "seeded"


def test_inference_metadata_rejects_non_hash_digest() -> None:
    with pytest.raises(records.RecordModelError) as captured:
        records.InferenceMetadata.from_dict(
            {
                "execution_mode": "local",
                "extraction_confidence": 1.0,
                "input_artifact_sha256": "not-a-hash",
                "input_region_sha256": "a" * 64,
                "interpretation_confidence": 0.5,
                "provider_id": "org.example.ocr",
                "provider_version": "1",
                "reproducibility": "deterministic",
                "request_digest": "a" * 64,
                "response_digest": "a" * 64,
                "verification_state": "unverified",
            }
        )

    assert captured.value.code == "AECCTX_INFERENCE_DIGEST_INVALID"


def test_coordinate_model_rejects_known_global_location_with_unknown_link() -> None:
    with pytest.raises(records.RecordModelError) as captured:
        records.CoordinateQualification.from_dict(
            {
                "global_location": {"state": "known", "value": "EPSG:32721"},
                "transform_chain": [
                    {
                        "from_frame": "source-local",
                        "reason_code": "AECCTX_TRANSFORM_NOT_OBSERVED",
                        "state": "unknown",
                        "to_frame": "project",
                    }
                ],
            }
        )

    assert captured.value.code == "AECCTX_COORDINATE_GLOBAL_STATE_INVALID"


def test_preview_fidelity_must_remain_derived() -> None:
    with pytest.raises(records.RecordModelError) as captured:
        records.RepresentationFidelity.from_dict(
            {"class": "preview", "derived": False, "source_representation_ids": ["prim_1"]}
        )

    assert captured.value.code == "AECCTX_FIDELITY_DERIVATION_INVALID"


def test_provider_attestation_preserves_execution_boundary() -> None:
    digest = "b" * 64

    value = records.ProviderAttestation.from_dict(
        {
            "deterministic": True,
            "execution_mode": "local",
            "network_mode": "disabled",
            "provider_id": "org.example.provider",
            "provider_version": "2.0",
            "request_digest": digest,
            "response_digest": digest,
            "runtime_version": "3.12",
        }
    )

    assert value.provider_id == "org.example.provider"
    assert value.execution_mode == "local"
    assert value.network_mode == "disabled"
    assert value.deterministic is True


def test_network_provider_attestation_requires_allowlisted_network_mode() -> None:
    digest = "c" * 64

    with pytest.raises(records.RecordModelError) as captured:
        records.ProviderAttestation.from_dict(
            {
                "deterministic": False,
                "execution_mode": "network",
                "network_mode": "disabled",
                "provider_id": "org.example.remote",
                "provider_version": "2.0",
                "request_digest": digest,
                "response_digest": digest,
                "runtime_version": "remote-1",
            }
        )

    assert captured.value.code == "AECCTX_PROVIDER_ATTESTATION_NETWORK_INVALID"
