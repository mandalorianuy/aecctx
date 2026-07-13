from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable


class AtomicCreateError(OSError):
    def __init__(self, reason: str) -> None:
        if reason not in {"exists", "failed"}:
            raise ValueError("reason must be exists or failed")
        super().__init__("output already exists" if reason == "exists" else "output publication failed safely")
        self.reason = reason


def atomic_create_many(items: Iterable[tuple[str | Path, bytes]]) -> None:
    materialized = tuple((Path(path), data) for path, data in items)
    if not materialized:
        return
    resolved = tuple(path.resolve(strict=False) for path, _data in materialized)
    if len(set(resolved)) != len(resolved):
        raise AtomicCreateError("exists")
    if any(not isinstance(data, bytes) for _path, data in materialized):
        raise TypeError("atomic output data must be bytes")
    if any(path.exists() or path.is_symlink() for path, _data in materialized):
        raise AtomicCreateError("exists")

    staged: list[tuple[Path, Path]] = []
    published: list[Path] = []
    try:
        for output, data in materialized:
            descriptor, temporary_name = tempfile.mkstemp(dir=output.parent, prefix=f".{output.name}.")
            temporary = Path(temporary_name)
            staged.append((temporary, output))
            try:
                os.chmod(temporary, 0o600)
                with os.fdopen(descriptor, "wb") as handle:
                    descriptor = -1
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
            finally:
                if descriptor >= 0:
                    os.close(descriptor)
        for temporary, output in staged:
            os.link(temporary, output)
            published.append(output)
    except FileExistsError as error:
        for output in reversed(published):
            output.unlink(missing_ok=True)
        raise AtomicCreateError("exists") from error
    except OSError as error:
        for output in reversed(published):
            output.unlink(missing_ok=True)
        raise AtomicCreateError("failed") from error
    finally:
        for temporary, _output in staged:
            temporary.unlink(missing_ok=True)


def atomic_create(path: str | Path, data: bytes) -> None:
    atomic_create_many(((path, data),))
