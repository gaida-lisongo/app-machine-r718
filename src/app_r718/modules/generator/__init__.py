"""
Generator Module - Solar/thermal generator for R718 system

Heats compressed liquid from pump to produce saturated or superheated vapor.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.modules.generator.controller import GeneratorController
from app_r718.modules.generator.model import GeneratorModel, GeneratorResult

__all__ = ['GeneratorController', 'GeneratorModel', 'GeneratorResult']
