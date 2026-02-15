"""
Condenser Module - Natural convection condenser for R718 refrigeration system

Architecture: MVC (Model-View-Controller)

Components:
- model.py: Physical condensation model (energy balance, heat exchanger)
- controller.py: Orchestration and result packaging
- view.py: Console output and Tkinter GUI with Matplotlib

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.modules.condenser.model import CondenserModel, CondenserResult
from app_r718.modules.condenser.controller import CondenserController
from app_r718.modules.condenser.view import CondenserView

__all__ = [
    "CondenserModel",
    "CondenserResult",
    "CondenserController",
    "CondenserView",
]
