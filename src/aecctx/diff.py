from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .records import RECORD_PATHS, RecordStore


@dataclass(frozen=True, slots=True)
class PackageDiff:
    before_version: str
    after_version: str
    before_digest: str
    after_digest: str
    added_records: tuple[str, ...]
    removed_records: tuple[str, ...]
    changed_records: tuple[str, ...]
    artifact_changes: dict[str, dict[str, Any]]
    authoritative_artifact_changes: dict[str, dict[str, Any]]
    capability_changes: dict[str, dict[str, Any]]
    loss_changed: bool
    loss_change: dict[str, Any] | None
    identity_changed: bool
    identity_field_changes: dict[str, dict[str, Any]]
    producer_changed: bool
    producer_field_changes: dict[str, dict[str, Any]]

    @property
    def version_changed(self) -> bool:
        return self.before_version != self.after_version

    @property
    def semantic_change(self) -> bool:
        return any(
            (
                self.added_records,
                self.removed_records,
                self.changed_records,
                self.authoritative_artifact_changes,
                self.capability_changes,
                self.loss_changed,
                self.identity_changed,
                self.producer_changed,
                self.version_changed,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "added_records": list(self.added_records),
            "after_version": self.after_version,
            "after_digest": self.after_digest,
            "artifact_changes": self.artifact_changes,
            "authoritative_artifact_changes": self.authoritative_artifact_changes,
            "before_digest": self.before_digest,
            "before_version": self.before_version,
            "capability_changes": self.capability_changes,
            "changed_records": list(self.changed_records),
            "identity_changed": self.identity_changed,
            "identity_field_changes": self.identity_field_changes,
            "loss_change": self.loss_change,
            "loss_changed": self.loss_changed,
            "producer_changed": self.producer_changed,
            "producer_field_changes": self.producer_field_changes,
            "removed_records": list(self.removed_records),
            "semantic_change": self.semantic_change,
            "version_changed": self.version_changed,
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
    before_inventory = {item["path"]: item for item in before.manifest["artifacts"]}
    after_inventory = {item["path"]: item for item in after.manifest["artifacts"]}
    before_artifacts = {path: item["sha256"] for path, item in before_inventory.items()}
    after_artifacts = {path: item["sha256"] for path, item in after_inventory.items()}
    artifact_changes = _mapping_diff(before_artifacts, after_artifacts)
    authoritative_artifact_changes: dict[str, dict[str, Any]] = {}
    for path in sorted(set(before_inventory) | set(after_inventory)):
        before_item = before_inventory.get(path)
        after_item = after_inventory.get(path)
        before_authoritative = bool(before_item and before_item.get("authoritative") is True)
        after_authoritative = bool(after_item and after_item.get("authoritative") is True)
        if path in RECORD_PATHS or not (before_authoritative or after_authoritative):
            continue
        before_value = before_item.get("sha256") if before_item else None
        after_value = after_item.get("sha256") if after_item else None
        if before_value != after_value or before_authoritative != after_authoritative:
            authoritative_artifact_changes[path] = {
                "before": before_value,
                "after": after_value,
            }
    identity_fields = ("package_id", "source_ids", "source_embedding_policy")
    identity_field_changes = _mapping_diff(
        {key: before.manifest.get(key) for key in identity_fields},
        {key: after.manifest.get(key) for key in identity_fields},
    )
    producer_field_changes = _mapping_diff(
        dict(before.manifest.get("producer", {})),
        dict(after.manifest.get("producer", {})),
    )
    before_loss = before.manifest.get("loss_summary")
    after_loss = after.manifest.get("loss_summary")
    loss_change = None
    if before_loss != after_loss:
        loss_change = {"before": before_loss, "after": after_loss}
    return PackageDiff(
        before_version=str(before.manifest["aecctx_version"]),
        after_version=str(after.manifest["aecctx_version"]),
        before_digest=before.logical_digest,
        after_digest=after.logical_digest,
        added_records=tuple(sorted(after_ids - before_ids)),
        removed_records=tuple(sorted(before_ids - after_ids)),
        changed_records=changed,
        artifact_changes=artifact_changes,
        authoritative_artifact_changes=authoritative_artifact_changes,
        capability_changes=_mapping_diff(before.manifest.get("capabilities", {}), after.manifest.get("capabilities", {})),
        loss_changed=loss_change is not None,
        loss_change=loss_change,
        identity_changed=bool(identity_field_changes),
        identity_field_changes=identity_field_changes,
        producer_changed=bool(producer_field_changes),
        producer_field_changes=producer_field_changes,
    )
