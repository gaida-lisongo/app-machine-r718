"""
System Dashboard Module

Provides a complete cycle simulation dashboard with:
- Real-time metrics display
- Cycle animation
- Thermodynamic diagrams (P-h and T-s)
"""

from .controller import SystemCycleController
from .model import SystemCycleModel, CycleResult

__all__ = ["SystemCycleController", "SystemCycleModel", "CycleResult"]
