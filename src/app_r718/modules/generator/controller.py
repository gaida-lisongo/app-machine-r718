"""
Generator Controller - Orchestration layer

Coordinates generator model execution and result packaging.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.modules.generator.model import GeneratorModel, GeneratorResult


class GeneratorController:
    """
    Controller for generator simulation.
    
    Orchestrates model execution without direct UI dependencies.
    """
    
    def __init__(self):
        """Initialize controller with generator model."""
        self.model = GeneratorModel()
    
    def solve(
        self,
        state_in: ThermoState,
        m_dot: float,
        T_gen_target: float,
        K: float,
        A: float,
        T_htf_in: float,
        T_htf_out: float,
        superheat_K: float = 0.0,
    ) -> GeneratorResult:
        """
        Solve generator heating/vaporization.
        
        Args:
            state_in: Inlet thermodynamic state (compressed liquid)
            m_dot: Mass flow rate [kg/s]
            T_gen_target: Target saturation temperature [K]
            K: Overall heat transfer coefficient [W/m²/K]
            A: Heat exchanger area [m²]
            T_htf_in: Hot thermal fluid inlet temperature [K]
            T_htf_out: Hot thermal fluid outlet temperature [K]
            superheat_K: Superheat above saturation [K]
            
        Returns:
            GeneratorResult with outlet state and diagnostics
        """
        return self.model.solve(
            state_in=state_in,
            m_dot=m_dot,
            T_gen_target=T_gen_target,
            K=K,
            A=A,
            T_htf_in=T_htf_in,
            T_htf_out=T_htf_out,
            superheat_K=superheat_K,
        )
