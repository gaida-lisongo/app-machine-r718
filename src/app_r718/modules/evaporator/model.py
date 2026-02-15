"""
Evaporator Model - Physical evaporation model for R718

Implements 1D energy balance model for film evaporator.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from dataclasses import dataclass
import math
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service


@dataclass
class EvaporatorResult:
    """
    Result of evaporator calculation.
    
    Attributes:
        state3: Outlet thermodynamic state (saturated or superheated vapor)
        Q_mass: Heat transfer computed from mass flow energy balance [W]
        Q_KA: Heat transfer computed from heat exchanger equation [W]
        delta_relative: Relative difference between Q_mass and Q_KA [-]
        flags: Diagnostic flags dictionary
    """
    state3: ThermoState
    Q_mass: float
    Q_KA: float
    delta_relative: float
    flags: dict[str, bool]


class EvaporatorModel:
    """
    Physical model of film evaporator.
    
    Models evaporation process from two-phase inlet to saturated/superheated vapor outlet.
    Computes heat transfer using both mass flow energy balance and heat exchanger equation.
    """
    
    def __init__(self):
        """Initialize evaporator model."""
        self.props = get_props_service()
    
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
        Solve evaporator energy balance and heat transfer.
        
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
            EvaporatorResult with outlet state and diagnostic flags
        """
        # Initialize flags
        flags = {
            "incomplete_evaporation": False,
            "negative_heat_transfer": False,
            "invalid_LMTD": False,
            "thermal_mismatch": False,
        }
        
        # Get saturation temperature
        T_sat = self.props.Tsat_P(P_evap)
        
        # Compute outlet state (state3)
        state3 = ThermoState()
        
        if superheat_K > 0.0:
            # Superheated vapor
            T3 = T_sat + superheat_K
            state3.update_from_PT(P_evap, T3)
        else:
            # Saturated vapor (x = 1.0)
            state3.update_from_PX(P_evap, 1.0)
        
        # Check for incomplete evaporation
        if state3.h <= state2.h:
            flags["incomplete_evaporation"] = True
        
        # Compute heat transfer from mass flow energy balance
        Q_mass = m_dot * (state3.h - state2.h)
        
        if Q_mass <= 0:
            flags["negative_heat_transfer"] = True
        
        # Compute LMTD for heat exchanger
        delta_T1 = T_ext_in - T_sat
        delta_T2 = T_ext_out - T_sat
        
        # Check validity of LMTD
        if delta_T1 <= 0 or delta_T2 <= 0:
            flags["invalid_LMTD"] = True
            Q_KA = 0.0
            delta_relative = 1.0  # 100% mismatch
        else:
            # Compute LMTD
            if abs(delta_T1 - delta_T2) < 1e-6:
                # Avoid division by zero for equal temperatures
                delta_Tlm = delta_T1
            else:
                delta_Tlm = (delta_T1 - delta_T2) / math.log(delta_T1 / delta_T2)
            
            # Compute heat transfer from heat exchanger equation
            Q_KA = K * A * delta_Tlm
            
            if Q_KA <= 0:
                flags["negative_heat_transfer"] = True
            
            # Compute relative difference
            epsilon = 1.0  # Small value to avoid division by zero
            delta_relative = abs(Q_mass - Q_KA) / max(abs(Q_mass), epsilon)
            
            # Check for thermal mismatch
            if delta_relative > 0.05:
                flags["thermal_mismatch"] = True
        
        return EvaporatorResult(
            state3=state3,
            Q_mass=Q_mass,
            Q_KA=Q_KA,
            delta_relative=delta_relative,
            flags=flags,
        )
