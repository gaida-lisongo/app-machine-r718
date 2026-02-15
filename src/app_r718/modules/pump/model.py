"""
Pump Model - Physical pump model for R718

Implements 1D isentropic efficiency model for liquid compression.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from dataclasses import dataclass
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service


@dataclass
class PumpResult:
    """
    Result of pump calculation.
    
    Attributes:
        state_out: Outlet thermodynamic state (compressed liquid)
        state_is: Isentropic outlet state (ideal compression)
        W_pump: Pump power consumption [W]
        delta_h: Enthalpy increase [J/kg]
        flags: Diagnostic flags dictionary
    """
    state_out: ThermoState
    state_is: ThermoState
    W_pump: float
    delta_h: float
    flags: dict[str, bool]


class PumpModel:
    """
    Physical model of feedwater pump.
    
    Models liquid compression with isentropic efficiency.
    Adiabatic process with no heat transfer.
    """
    
    def __init__(self):
        """Initialize pump model."""
        self.props = get_props_service()
    
    def solve(
        self,
        state_in: ThermoState,
        P_out: float,
        eta_is: float,
        m_dot: float,
    ) -> PumpResult:
        """
        Solve pump compression with isentropic efficiency model.
        
        Args:
            state_in: Inlet thermodynamic state (saturated or subcooled liquid)
            P_out: Outlet pressure [Pa]
            eta_is: Isentropic efficiency [-] (0 < eta <= 1)
            m_dot: Mass flow rate [kg/s]
            
        Returns:
            PumpResult with outlet state and diagnostic flags
        """
        # Initialize flags
        flags = {
            "invalid_pressure_rise": False,
            "two_phase_inlet": False,
            "cavitation_risk": False,
            "unphysical_state": False,
        }
        
        # Check pressure rise validity
        if P_out <= state_in.P:
            flags["invalid_pressure_rise"] = True
        
        # Check for two-phase inlet (pump should receive pure liquid)
        if state_in.x is not None and 0 < state_in.x < 1:
            flags["two_phase_inlet"] = True
        
        # Check for cavitation risk (simplified criterion)
        # Cavitation occurs if inlet pressure is too low
        if state_in.P < 1500.0:  # Pa, adjustable threshold
            flags["cavitation_risk"] = True
        
        # Compute isentropic (ideal) outlet state
        state_is = ThermoState()
        s_in = state_in.s
        
        try:
            state_is.update_from_PS(P_out, s_in)
        except Exception:
            flags["unphysical_state"] = True
            # Create a fallback state
            state_is = ThermoState()
            state_is.P = P_out
            state_is.h = state_in.h  # Fallback: assume no enthalpy change
        
        # Compute real outlet enthalpy with isentropic efficiency
        # h_out = h_in + (h_is - h_in) / eta_is
        # Real pump consumes more energy than ideal
        h_in = state_in.h
        h_is = state_is.h
        h_out = h_in + (h_is - h_in) / eta_is
        
        # Construct real outlet state
        state_out = ThermoState()
        try:
            state_out.update_from_PH(P_out, h_out)
        except Exception:
            flags["unphysical_state"] = True
            # Fallback
            state_out = ThermoState()
            state_out.P = P_out
            state_out.h = h_out
        
        # Compute pump power
        delta_h = h_out - h_in
        W_pump = m_dot * delta_h
        
        return PumpResult(
            state_out=state_out,
            state_is=state_is,
            W_pump=W_pump,
            delta_h=delta_h,
            flags=flags,
        )
