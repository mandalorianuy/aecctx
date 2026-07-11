from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .records import NeutralRecord, RecordStore


PROFILES = {"agent", "audit", "compact"}


def estimate_tokens(content: bytes | str) -> int:
    byte_size = len(content.encode("utf-8") if isinstance(content, str) else content)
    return (byte_size + 3) // 4


@dataclass(frozen=True, slots=True)
class ContextProjection:
    files: dict[str, bytes]
    token_estimate: int
    included_record_ids: tuple[str, ...]
    omitted_record_ids: tuple[str, ...]
    profile: str
    logical_digest: str

    def to_dict(self) -> dict[str, object]:
        return {
            "files": {path: content.decode("utf-8") for path, content in self.files.items()},
            "included_record_ids": list(self.included_record_ids),
            "logical_digest": self.logical_digest,
            "omitted_record_ids": list(self.omitted_record_ids),
            "profile": self.profile,
            "token_estimate": self.token_estimate,
        }


def _priority(record: NeutralRecord, profile: str) -> tuple[int, str]:
    if profile == "audit":
        order = {"source": 0, "diagnostic": 1, "primitive": 2, "assertion": 3, "entity": 4, "relation": 5}
    elif profile == "compact":
        order = {"source": 0, "entity": 1, "relation": 2, "diagnostic": 3, "assertion": 4, "primitive": 5}
    else:
        order = {"source": 0, "entity": 1, "relation": 2, "diagnostic": 3, "assertion": 4, "primitive": 5}
    return order.get(record.record_type, 9), record.record_id


def _section(record: NeutralRecord) -> bytes:
    compact = json.dumps(record.raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (
        f"## `{record.record_id}` ({record.record_type})\n\n"
        f"Authority: `{record.location.path}:{record.location.line}`\n\n"
        f"```json\n{compact}\n```\n"
    ).encode("utf-8")


def _build_chunks(sections: list[tuple[str, bytes]], chunk_budget: int) -> list[tuple[str, bytes]]:
    chunks: list[tuple[str, bytes]] = []
    current = b""
    for _, section in sections:
        header = f"# AECCTX context chunk {len(chunks) + 1}\n\n".encode("utf-8")
        candidate = (current or header) + section
        if current and estimate_tokens(candidate) > chunk_budget:
            chunks.append((f"context/chunk-{len(chunks) + 1:03d}.md", current))
            current = f"# AECCTX context chunk {len(chunks) + 1}\n\n".encode("utf-8") + section
        else:
            current = candidate
    if current:
        chunks.append((f"context/chunk-{len(chunks) + 1:03d}.md", current))
    return chunks


def _index(store: RecordStore, profile: str, budget: int, included: int, omitted: int, chunks: list[tuple[str, bytes]], estimate: int) -> bytes:
    capabilities = json.dumps(store.manifest.get("capabilities", {}), sort_keys=True, separators=(",", ":"))
    losses = json.dumps(store.manifest.get("loss_summary", []), sort_keys=True, separators=(",", ":"))
    links = "\n".join(f"- [{Path(path).name}]({Path(path).name})" for path, _ in chunks) or "- No record chunks fit the selected budget."
    return (
        "# AECCTX generated context index\n\n"
        f"Package: `{store.manifest['package_id']}`  \nLogical digest: `{store.logical_digest}`  \n"
        f"Generator: `aecctx/0.1.0.dev0`  \nProfile: `{profile}`  \nToken budget: {budget}  \n"
        f"Token estimate: {estimate}  \nIncluded records: {included}  \nOmitted records: {omitted}\n\n"
        f"Capabilities: `{capabilities}`\n\nLoss summary: `{losses}`\n\n"
        "## Authoritative record chunks\n\n"
        f"{links}\n\nExact queries must use the JSON/JSONL record APIs, not this projection.\n"
    ).encode("utf-8")


def render_context(
    package_path: str | Path,
    *,
    profile: str = "agent",
    token_budget: int = 40_000,
    chunk_token_budget: int = 4_000,
) -> ContextProjection:
    if profile not in PROFILES:
        raise ValueError(f"unknown context profile: {profile}")
    if token_budget < 1 or chunk_token_budget < 1:
        raise ValueError("token budgets must be positive")
    store = RecordStore.open(package_path)
    ordered = sorted(store.records.values(), key=lambda record: _priority(record, profile))
    selected: list[tuple[str, bytes]] = []
    omitted: list[str] = []
    for record in ordered:
        section = _section(record)
        if estimate_tokens(section) > chunk_token_budget:
            omitted.append(record.record_id)
            continue
        tentative = selected + [(record.record_id, section)]
        chunks = _build_chunks(tentative, chunk_token_budget)
        missing = len(ordered) - len(tentative)
        index = _index(store, profile, token_budget, len(tentative), missing, chunks, 999999)
        if estimate_tokens(index) + sum(estimate_tokens(content) for _, content in chunks) <= token_budget:
            selected = tentative
        else:
            omitted.append(record.record_id)
    included_ids = tuple(record_id for record_id, _ in selected)
    omitted_ids = tuple(record.record_id for record in ordered if record.record_id not in included_ids)
    chunks = _build_chunks(selected, chunk_token_budget)
    placeholder = _index(store, profile, token_budget, len(included_ids), len(omitted_ids), chunks, 999999)
    estimate = estimate_tokens(placeholder) + sum(estimate_tokens(content) for _, content in chunks)
    index = _index(store, profile, token_budget, len(included_ids), len(omitted_ids), chunks, estimate)
    estimate = estimate_tokens(index) + sum(estimate_tokens(content) for _, content in chunks)
    files = {"context/index.md": index, **dict(chunks)}
    return ContextProjection(files, estimate, included_ids, omitted_ids, profile, store.logical_digest)

