"""
Types partagés démos / clients — sans import vers stores (évite les imports circulaires).
"""

from typing import Literal

DemoStatusSlug = Literal["envoyee", "ouverte", "validee", "expiree"]

MANUAL_DEMO_STATUSES: frozenset[DemoStatusSlug] = frozenset({"validee", "expiree"})
