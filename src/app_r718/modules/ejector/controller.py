"""
Ejector Controller - Orchestration layer

Coordinates ejector model execution and result packaging.
Supports both V1 (simplified) and V2 (compressible) models.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.modules.ejector.model import EjectorModel, EjectorResult
from app_r718.modules.ejector.model_v2 import EjectorModelV2, EjectorResultV2


class EjectorController:
    """
    Controller for ejector simulation.
    
    Orchestrates model execution without direct UI dependencies.
    Supports V1 (simplified 1D) and V2 (compressible with shock) models.
    """
    
    def __init__(self, mode: str = "V1"):
        """
        Initialize controller with ejector model.
        
        Args:
            mode: Model version - "V1" (simplified) or "V2" (compressible)
        """
        self.mode = mode
        
        if mode == "V2":
            self.model = EjectorModelV2()
        else:
            self.model = EjectorModel()
    
    def set_mode(self, mode: str):
        """
        Switch between V1 and V2 models.
        
        Args:
            mode: "V1" or "V2"
        """
        if mode != self.mode:
            self.mode = mode
            if mode == "V2":
                self.model = EjectorModelV2()
            else:
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
        
        Uses V1 or V2 model depending on current mode.
        
        Args:
            state_p_in: Primary inlet state (generator vapor)
            state_s_in: Secondary inlet state (evaporator vapor)
            P_out: Discharge pressure [Pa]
            m_dot_p: Primary mass flow rate [kg/s]
            eta_nozzle: Nozzle efficiency [-]
            eta_diffuser: Diffuser efficiency [-]
            eta_mixing: Mixing efficiency [-]
            
        Returns:
            EjectorResult (or EjectorResultV2) with entrainment ratio and states
        """
        if self.mode == "V2":
            return self.model.solve_v2(
                state_p_in=state_p_in,
                state_s_in=state_s_in,
                P_out=P_out,
                m_dot_p=m_dot_p,
                eta_nozzle=eta_nozzle,
                eta_diffuser=eta_diffuser,
                eta_mixing=eta_mixing,
            )
        else:
            return self.model.solve(
                state_p_in=state_p_in,
                state_s_in=state_s_in,
                P_out=P_out,
                m_dot_p=m_dot_p,
                eta_nozzle=eta_nozzle,
                eta_diffuser=eta_diffuser,
                eta_mixing=eta_mixing,
            )
