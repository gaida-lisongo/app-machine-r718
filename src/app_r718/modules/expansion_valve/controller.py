"""
ExpansionValve Controller - Orchestrates expansion valve operations

Provides high-level interface for expansion valve calculations.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from typing import Optional
from app_r718.core.thermo_state import ThermoState
from app_r718.modules.expansion_valve.model import (
    ExpansionValveModel,
    ExpansionValveResult,
)


class ExpansionValveController:
    """
    Controller for expansion valve operations.
    
    Orchestrates the expansion valve model and provides a clean interface
    for performing expansion calculations.
    
    Attributes:
        model: Underlying physical model
    """
    
    def __init__(
        self,
        use_orifice_flow: bool = False,
        Cd: float = 0.8,
        A_orifice: float = 1e-6,
    ):
        """
        Initialize expansion valve controller.
        
        Args:
            use_orifice_flow: Enable mass flow rate calculation
            Cd: Discharge coefficient [-]
            A_orifice: Orifice area [m²]
        """
        self.model = ExpansionValveModel(
            use_orifice_flow=use_orifice_flow,
            Cd=Cd,
            A_orifice=A_orifice,
        )
    
    def solve(
        self,
        state1: ThermoState,
        P_out: float,
    ) -> ExpansionValveResult:
        """
        Solve expansion valve process.
        
        Args:
            state1: Inlet thermodynamic state
            P_out: Outlet pressure [Pa]
            
        Returns:
            ExpansionValveResult containing outlet state and diagnostics
            
        Raises:
            ValueError: If inputs are invalid
        """
        return self.model.solve(state1, P_out)
    
    def enable_orifice_flow(self, Cd: float = 0.8, A_orifice: float = 1e-6) -> None:
        """
        Enable orifice flow calculation with specified parameters.
        
        Args:
            Cd: Discharge coefficient [-]
            A_orifice: Orifice area [m²]
        """
        self.model.use_orifice_flow = True
        self.model.set_orifice_parameters(Cd, A_orifice)
    
    def disable_orifice_flow(self) -> None:
        """Disable orifice flow calculation."""
        self.model.use_orifice_flow = False
    
    def get_configuration(self) -> dict:
        """
        Get current configuration of the expansion valve.
        
        Returns:
            Dictionary with configuration parameters
        """
        return {
            "use_orifice_flow": self.model.use_orifice_flow,
            "Cd": self.model.Cd,
            "A_orifice": self.model.A_orifice,
        }
