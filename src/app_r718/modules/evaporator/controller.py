"""
Evaporator Controller - Orchestration layer

Coordinates evaporator model execution and result packaging.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.modules.evaporator.model import EvaporatorModel, EvaporatorResult


class EvaporatorController:
    """
    Controller for evaporator simulation.
    
    Orchestrates model execution without direct UI dependencies.
    """
    
    def __init__(self):
        """Initialize controller with evaporator model."""
        self.model = EvaporatorModel()
    
    def solve(
        self,
        state2: ThermoState,
        m_dot: float,
        P_evap: float,
        K: float,
        A: float,
        T_ext_in: float,
        T_ext_out: float,
        superheat_K: float = 0.0,
    ) -> EvaporatorResult:
        """
        Solve evaporator energy balance.
        
        Args:
            state2: Inlet thermodynamic state (from expansion valve)
            m_dot: Mass flow rate [kg/s]
            P_evap: Evaporation pressure [Pa]
            K: Overall heat transfer coefficient [W/m²/K]
            A: Heat exchanger surface area [m²]
            T_ext_in: External fluid inlet temperature [K]
            T_ext_out: External fluid outlet temperature [K]
            superheat_K: Optional superheat above saturation [K]
            
        Returns:
            EvaporatorResult with outlet state and diagnostics
        """
        return self.model.solve(
            state2=state2,
            m_dot=m_dot,
            P_evap=P_evap,
            K=K,
            A=A,
            T_ext_in=T_ext_in,
            T_ext_out=T_ext_out,
            superheat_K=superheat_K,
        )
