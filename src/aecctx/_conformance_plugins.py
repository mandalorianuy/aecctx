from __future__ import annotations

import socket
import time


class SleepPlugin:
    def describe(self) -> dict[str, str]:
        time.sleep(5)
        return {"status": "unexpected"}


class NetworkPlugin:
    def describe(self) -> dict[str, str]:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return {"status": "unexpected"}


class FloodPlugin:
    def describe(self) -> dict[str, str]:
        return {"payload": "x" * 100_000}

