from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .records import RecordStore


@dataclass(frozen=True, slots=True)
class PackageDiff:
    before_digest: str
    after_digest: str
    added_records: tuple[str, ...]
    removed_records: tuple[str, ...]
    changed_records: tuple[str, ...]
    artifact_changes: dict[str, dict[str, Any]]
    capability_changes: dict[str, dict[str, Any]]
    loss_changed: bool
    identity_changed: bool
    producer_changed: bool

    @property
    def semantic_change(self) -> bool:
        return any(
            (
                self.added_records,
                self.removed_records,
                self.changed_records,
                self.artifact_changes,
                self.capability_changes,
                self.loss_changed,
                self.identity_changed,
                self.producer_changed,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_records": list(self.added_records),
            "after_digest": self.after_digest,
            "artifact_changes": self.artifact_changes,
            "before_digest": self.before_digest,
            "capability_changes": self.capability_changes,
            "changed_records": list(self.changed_records),
            "identity_changed": self.identity_changed,
            "loss_changed": self.loss_changed,
            "producer_changed": self.producer_changed,
            "removed_records": list(self.removed_records),
            "semantic_change": self.semantic_change,
        }


def _mapping_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    changes: dict[str, dict[str, Any]] = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changes[key] = {"before": before.get(key), "after": after.get(key)}
    return changes


def diff_packages(before_path: str | Path, after_path: str | Path) -> PackageDiff:
    before = RecordStore.open(before_path)
    after = RecordStore.open(after_path)
    before_ids = set(before.records)
    after_ids = set(after.records)
    shared = before_ids & after_ids
    changed = tuple(
        record_id
        for record_id in sorted(shared)
        if dict(before.records[record_id].raw) != dict(after.records[record_id].raw)
    )
    before_artifacts = {item["path"]: item["sha256"] for item in before.manifest["artifacts"]}
    after_artifacts = {item["path"]: item["sha256"] for item in after.manifest["artifacts"]}
    identity_fields = ("package_id", "source_ids", "source_embedding_policy")
    identity_changed = any(before.manifest.get(key) != after.manifest.get(key) for key in identity_fields)
    return PackageDiff(
        before_digest=before.logical_digest,
        after_digest=after.logical_digest,
        added_records=tuple(sorted(after_ids - before_ids)),
        removed_records=tuple(sorted(before_ids - after_ids)),
        changed_records=changed,
        artifact_changes=_mapping_diff(before_artifacts, after_artifacts),
        capability_changes=_mapping_diff(before.manifest.get("capabilities", {}), after.manifest.get("capabilities", {})),
        loss_changed=before.manifest.get("loss_summary") != after.manifest.get("loss_summary"),
        identity_changed=identity_changed,
        producer_changed=before.manifest.get("producer") != after.manifest.get("producer"),
    )

