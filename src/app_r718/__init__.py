"""
app_r718 - R718 Ejector Refrigeration System

A modular simulation framework for solar-driven ejector refrigeration machines
using water (R718) as the working fluid.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

__version__ = "0.1.0"
__author__ = "LISONGO SEMETE"

from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import PropsService, get_props_service

__all__ = [
    "ThermoState",
    "PropsService",
    "get_props_service",
]
