"""Computer Use Linux (eski adı NexRemote) — yapay zekâ ajanlarına uzaktan görme + kontrol yeteneği.

Evrensel köprü: her harness'a (MCP'li/MCP'siz), her modele (tool-calling
olan/olmayan), GUI ve terminal (TUI) ortamlarına takılır.
"""
import os

# Yeni ad: CUL_* ortam değişkenleri eski NEXREMOTE_* adlarına aktarılır; eski adlar da geçerli.
for _k, _v in list(os.environ.items()):
    if _k.startswith("CUL_"):
        os.environ.setdefault("NEXREMOTE_" + _k[4:], _v)

from .models import (
    Action, Capability, CommandResult, Element, Role, Screenshot, Window,
)
from .nexremote import NexRemote

__version__ = "0.7.0"
__all__ = [
    "NexRemote", "Element", "Window", "Screenshot", "CommandResult",
    "Capability", "Role", "Action", "__version__",
]
