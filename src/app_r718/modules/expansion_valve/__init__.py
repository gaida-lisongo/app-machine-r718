"""
ExpansionValve Module - MVC implementation

This module implements an expansion valve (détendeur) for the R718 
refrigeration system using Model-View-Controller architecture.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.modules.expansion_valve.model import (
    ExpansionValveModel,
    ExpansionValveResult,
)
from app_r718.modules.expansion_valve.controller import ExpansionValveController
from app_r718.modules.expansion_valve.view import ExpansionValveView

__all__ = [
    "ExpansionValveModel",
    "ExpansionValveResult",
    "ExpansionValveController",
    "ExpansionValveView",
]
