"""Simple request router for the RPi‑TV Dashboard.
It maps URL paths to handler callables defined in `handlers.py`.
Each handler receives the request instance (`self`), the parsed
query dict (`q`) and the path string.
"""

from typing import Callable, Optional
from handlers import route_table

# route_table is a dict mapping path -> callable

def route(path: str) -> Optional[Callable]:
    """Return the handler for *path* or `None` if not found."""
    return route_table.get(path)
