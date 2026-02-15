"""
Ejector Controller - Orchestration layer

Coordinates ejector model execution and result packaging.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.modules.ejector.model import EjectorModel, EjectorResult


class EjectorController:
    """
    Controller for ejector simulation.
    
    Orchestrates model execution without direct UI dependencies.
    """
    
    def __init__(self):
        """Initialize controller with ejector model."""
        self.model = EjectorModel()
    
    def solve(
        self,
        state_p_in: ThermoState,
        state_s_in: ThermoState,
        P_out: float,
        m_dot_p: float,
        eta_nozzle: float = 0.85,
        eta_diffuser: float = 0.85,
        eta_mixing: float = 1.0,
    ) -> EjectorResult:
        """
        Solve ejector mixing and entrainment.
        
        Args:
            state_p_in: Primary inlet state (generator vapor)
            state_s_in: Secondary inlet state (evaporator vapor)
            P_out: Discharge pressure [Pa]
            m_dot_p: Primary mass flow rate [kg/s]
            eta_nozzle: Nozzle efficiency [-]
            eta_diffuser: Diffuser efficiency [-]
            eta_mixing: Mixing efficiency [-]
            
        Returns:
            EjectorResult with entrainment ratio and states
        """
        return self.model.solve(
            state_p_in=state_p_in,
            state_s_in=state_s_in,
            P_out=P_out,
            m_dot_p=m_dot_p,
            eta_nozzle=eta_nozzle,
            eta_diffuser=eta_diffuser,
            eta_mixing=eta_mixing,
        )
