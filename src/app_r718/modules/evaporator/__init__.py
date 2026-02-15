"""
Evaporator Module - Film evaporator for R718 refrigeration system

Architecture: MVC (Model-View-Controller)

Components:
- model.py: Physical evaporation model (energy balance, heat exchanger)
- controller.py: Orchestration and result packaging
- view.py: Console output and Tkinter GUI with Matplotlib

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.modules.evaporator.model import EvaporatorModel, EvaporatorResult
from app_r718.modules.evaporator.controller import EvaporatorController
from app_r718.modules.evaporator.view import EvaporatorView

__all__ = [
    "EvaporatorModel",
    "EvaporatorResult",
    "EvaporatorController",
    "EvaporatorView",
]
