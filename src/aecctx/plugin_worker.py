from __future__ import annotations

import base64
import importlib
import json
import os
import socket
import sys
from typing import Any


BUILTIN_PLUGINS = {
    "dxf": "aecctx.adapters.dxf:DXFPlugin",
    "geometry": "aecctx.adapters.geometry:GeometryPlugin",
    "ifc": "aecctx.adapters.ifc:IFCPlugin",
    "image": "aecctx.adapters.image:ImagePlugin",
    "pdf": "aecctx.adapters.pdf:PDFPlugin",
}
CONFORMANCE_PLUGINS = {
    "_conformance_flood": "aecctx._conformance_plugins:FloodPlugin",
    "_conformance_network": "aecctx._conformance_plugins:NetworkPlugin",
    "_conformance_sleep": "aecctx._conformance_plugins:SleepPlugin",
}


def _deny_network(*args: Any, **kwargs: Any) -> Any:
    raise PermissionError("AECCTX_PLUGIN_NETWORK_DENIED")


def _load(plugin_id: str) -> Any:
    registry = dict(BUILTIN_PLUGINS)
    if os.environ.get("AECCTX_CONFORMANCE") == "1":
        registry.update(CONFORMANCE_PLUGINS)
    target = registry.get(plugin_id)
    if target is None:
        raise LookupError("AECCTX_PLUGIN_NOT_REGISTERED")
    module_name, class_name = target.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)()


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii"), "encoding": "base64"}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def main() -> int:
    socket.socket = _deny_network  # type: ignore[assignment]
    socket.create_connection = _deny_network  # type: ignore[assignment]
    try:
        request = json.loads(sys.stdin.buffer.read())
        plugin = _load(request["plugin_id"])
        action = request["action"]
        if action not in {"describe", "probe", "extract", "finalize", "render"}:
            raise ValueError("AECCTX_PLUGIN_ACTION_UNSUPPORTED")
        payload = request.get("payload", {})
        if action == "probe":
            result = plugin.probe(base64.b64decode(payload["prefix_base64"], validate=True))
        else:
            result = getattr(plugin, action)(**payload)
            if action == "extract":
                result = list(result)
        if action == "extract" and len(result) > int(request["limits"]["max_records"]):
            raise OverflowError("AECCTX_PLUGIN_RECORD_LIMIT_EXCEEDED")
        response = {"ok": True, "result": _json_safe(result)}
    except PermissionError as error:
        response = {"error": {"code": "AECCTX_PLUGIN_NETWORK_DENIED", "message": str(error)}, "ok": False}
    except LookupError as error:
        response = {"error": {"code": "AECCTX_PLUGIN_NOT_REGISTERED", "message": str(error)}, "ok": False}
    except OverflowError as error:
        response = {"error": {"code": "AECCTX_PLUGIN_RECORD_LIMIT_EXCEEDED", "message": str(error)}, "ok": False}
    except Exception as error:
        response = {"error": {"code": "AECCTX_PLUGIN_FAILED", "message": f"{type(error).__name__}: {error}"}, "ok": False}
    sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if response["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

