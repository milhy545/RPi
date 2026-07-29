"""Authentication primitives."""

from __future__ import annotations

from enum import IntEnum


class Role(IntEnum):
    BASIC = 0
    EXPERT = 1
    ADMIN = 2

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Role):
            return int(self) >= int(other)
        return NotImplemented
