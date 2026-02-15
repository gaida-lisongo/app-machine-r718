"""
ExpansionValve Model - Physical and thermodynamic calculations

Implements isenthalpic expansion process with optional orifice flow model.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Dict
from app_r718.core.thermo_state import ThermoState


@dataclass
class ExpansionValveResult:
    """
    Result of expansion valve calculation.
    
    Attributes:
        state2: Output thermodynamic state after expansion
        m_dot: Mass flow rate [kg/s], None if orifice model not used
        flags: Dictionary of diagnostic flags
    """
    state2: ThermoState
    m_dot: Optional[float] = None
    flags: Dict[str, bool] = field(default_factory=dict)


class ExpansionValveModel:
    """
    Physical model for expansion valve (détendeur).
    
    Implements:
    - Isenthalpic expansion (h2 = h1)
    - Optional orifice flow model: m_dot = Cd * A * sqrt(2 * rho * ΔP)
    
    Attributes:
        use_orifice_flow: Whether to calculate mass flow rate
        Cd: Discharge coefficient [-] (default: 0.8)
        A_orifice: Orifice area [m²] (default: 1e-6)
    """
    
    def __init__(
        self,
        use_orifice_flow: bool = False,
        Cd: float = 0.8,
        A_orifice: float = 1e-6,
    ):
        """
        Initialize expansion valve model.
        
        Args:
            use_orifice_flow: Enable mass flow rate calculation
            Cd: Discharge coefficient [-]
            A_orifice: Orifice area [m²]
            
        Raises:
            ValueError: If parameters are invalid
        """
        if Cd <= 0 or Cd > 1:
            raise ValueError(f"Discharge coefficient must be in (0, 1], got {Cd}")
        if A_orifice <= 0:
            raise ValueError(f"Orifice area must be positive, got {A_orifice}")
        
        self.use_orifice_flow = use_orifice_flow
        self.Cd = Cd
        self.A_orifice = A_orifice
    
    def solve(
        self,
        state1: ThermoState,
        P_out: float,
    ) -> ExpansionValveResult:
        """
        Solve expansion valve process.
        
        Performs isenthalpic expansion from inlet state to outlet pressure.
        Optionally calculates mass flow rate through orifice.
        
        Args:
            state1: Inlet thermodynamic state
            P_out: Outlet pressure [Pa]
            
        Returns:
            ExpansionValveResult with outlet state, mass flow, and diagnostic flags
            
        Raises:
            ValueError: If inlet state is not initialized
        """
        # Validate input
        if not state1.is_initialized():
            raise ValueError("Inlet state must be initialized")
        
        # Initialize flags
        flags: Dict[str, bool] = {
            "deep_vacuum_warning": False,
            "two_phase_outlet": False,
            "invalid_delta_p": False,
        }
        
        # Check for deep vacuum (below typical evaporator pressures for R718)
        if P_out < 1100.0:
            flags["deep_vacuum_warning"] = True
        
        # Check for invalid pressure drop
        delta_p = state1.P - P_out
        if delta_p <= 0:
            flags["invalid_delta_p"] = True
        
        # Perform isenthalpic expansion: h2 = h1
        state2 = ThermoState(fluid=state1.fluid)
        state2.update_from_PH(P_out, state1.h)
        
        # Check if outlet is two-phase
        if state2.x is not None:
            flags["two_phase_outlet"] = True
        
        # Calculate mass flow rate if orifice model is enabled
        m_dot: Optional[float] = None
        if self.use_orifice_flow:
            m_dot = self._calculate_orifice_flow(state1, P_out, delta_p)
        
        return ExpansionValveResult(
            state2=state2,
            m_dot=m_dot,
            flags=flags,
        )
    
    def _calculate_orifice_flow(
        self,
        state1: ThermoState,
        P_out: float,
        delta_p: float,
    ) -> float:
        """
        Calculate mass flow rate through orifice.
        
        Uses simplified orifice equation:
        m_dot = Cd * A * sqrt(2 * rho_in * ΔP)
        
        Args:
            state1: Inlet state
            P_out: Outlet pressure [Pa]
            delta_p: Pressure difference [Pa]
            
        Returns:
            Mass flow rate [kg/s]
        """
        # If no pressure drop, no flow
        if delta_p <= 0:
            return 0.0
        
        # Orifice flow equation
        # m_dot = Cd * A * sqrt(2 * rho * ΔP)
        try:
            m_dot = self.Cd * self.A_orifice * math.sqrt(2.0 * state1.rho * delta_p)
            return m_dot
        except (ValueError, ArithmeticError):
            # In case of numerical issues
            return 0.0
    
    def set_orifice_parameters(self, Cd: float, A_orifice: float) -> None:
        """
        Update orifice parameters.
        
        Args:
            Cd: Discharge coefficient [-]
            A_orifice: Orifice area [m²]
            
        Raises:
            ValueError: If parameters are invalid
        """
        if Cd <= 0 or Cd > 1:
            raise ValueError(f"Discharge coefficient must be in (0, 1], got {Cd}")
        if A_orifice <= 0:
            raise ValueError(f"Orifice area must be positive, got {A_orifice}")
        
        self.Cd = Cd
        self.A_orifice = A_orifice
