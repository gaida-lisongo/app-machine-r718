"""
Condenser Controller - Orchestration layer

Coordinates condenser model execution and result packaging.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.modules.condenser.model import CondenserModel, CondenserResult


class CondenserController:
    """
    Controller for condenser simulation.
    
    Orchestrates model execution without direct UI dependencies.
    """
    
    def __init__(self):
        """Initialize controller with condenser model."""
        self.model = CondenserModel()
    
    def solve(
        self,
        state_in: ThermoState,
        m_dot: float,
        T_cond: float,
        K: float,
        A: float,
        T_air_in: float,
        T_air_out: float,
        subcool_K: float = 0.0,
    ) -> CondenserResult:
        """
        Solve condenser energy balance.
        
        Args:
            state_in: Inlet thermodynamic state (vapor or two-phase)
            m_dot: Mass flow rate [kg/s]
            T_cond: Condensation temperature [K]
            K: Overall heat transfer coefficient [W/m²/K]
            A: Heat exchanger surface area [m²]
            T_air_in: Air inlet temperature [K]
            T_air_out: Air outlet temperature [K]
            subcool_K: Optional subcooling below saturation [K]
            
        Returns:
            CondenserResult with outlet state and diagnostics
        """
        return self.model.solve(
            state_in=state_in,
            m_dot=m_dot,
            T_cond=T_cond,
            K=K,
            A=A,
            T_air_in=T_air_in,
            T_air_out=T_air_out,
            subcool_K=subcool_K,
        )
