"""
Pump Controller - Orchestration layer

Coordinates pump model execution and result packaging.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.modules.pump.model import PumpModel, PumpResult


class PumpController:
    """
    Controller for pump simulation.
    
    Orchestrates model execution without direct UI dependencies.
    """
    
    def __init__(self):
        """Initialize controller with pump model."""
        self.model = PumpModel()
    
    def solve(
        self,
        state_in: ThermoState,
        P_out: float,
        eta_is: float,
        m_dot: float,
    ) -> PumpResult:
        """
        Solve pump compression.
        
        Args:
            state_in: Inlet thermodynamic state (liquid)
            P_out: Outlet pressure [Pa]
            eta_is: Isentropic efficiency [-]
            m_dot: Mass flow rate [kg/s]
            
        Returns:
            PumpResult with outlet state and diagnostics
            
        Raises:
            ValueError: If eta_is is invalid (<=0 or >1)
        """
        # Validate isentropic efficiency
        if eta_is <= 0 or eta_is > 1:
            raise ValueError(
                f"Isentropic efficiency must be in (0, 1], got {eta_is}"
            )
        
        return self.model.solve(
            state_in=state_in,
            P_out=P_out,
            eta_is=eta_is,
            m_dot=m_dot,
        )
