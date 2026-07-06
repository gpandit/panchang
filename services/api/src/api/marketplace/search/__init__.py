"""Discovery & Search — Architecture v1.2 §1, module 14.

Filter/sort/rank pandits (service, festival, mode, date+muhurat,
location/distance, language, tradition, price, rating, badges); explainable
"recommended" ranking (finalised in D3).

F4 ships only the package + a stub :data:`router` (module skeleton). Real
endpoints land in WS-B (B1).
"""

from __future__ import annotations
