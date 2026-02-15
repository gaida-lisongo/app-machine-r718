"""
Condenser Model - Physical condensation model for R718

Implements 1D energy balance model for natural convection air-cooled condenser.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from dataclasses import dataclass
import math
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service


@dataclass
class CondenserResult:
    """
    Result of condenser calculation.
    
    Attributes:
        state_out: Outlet thermodynamic state (saturated or subcooled liquid)
        P_cond: Condensation pressure [Pa]
        T_sat: Saturation temperature at P_cond [K]
        Q_mass: Heat transfer from mass flow energy balance [W]
        Q_KA: Heat transfer from heat exchanger equation [W]
        delta_relative: Relative difference between Q_mass and Q_KA [-]
        flags: Diagnostic flags dictionary
    """
    state_out: ThermoState
    P_cond: float
    T_sat: float
    Q_mass: float
    Q_KA: float
    delta_relative: float
    flags: dict[str, bool]


class CondenserModel:
    """
    Physical model of natural convection air-cooled condenser.
    
    Models condensation process from vapor/two-phase inlet to saturated/subcooled liquid outlet.
    Heat rejection to ambient air via natural convection.
    """
    
    def __init__(self):
        """Initialize condenser model."""
        self.props = get_props_service()
    
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
        Solve condenser energy balance and heat transfer.
        
        Args:
            state_in: Inlet thermodynamic state (vapor or two-phase from ejector)
            m_dot: Mass flow rate [kg/s]
            T_cond: Condensation temperature [K]
            K: Overall heat transfer coefficient [W/m²/K]
            A: Heat exchanger surface area [m²]
            T_air_in: Air inlet temperature [K]
            T_air_out: Air outlet temperature [K]
            subcool_K: Optional subcooling below saturation [K]
            
        Returns:
            CondenserResult with outlet state and diagnostic flags
        """
        # Initialize flags
        flags = {
            "incomplete_condensation": False,
            "negative_heat_rejection": False,
            "invalid_LMTD": False,
            "thermal_mismatch": False,
        }
        
        # Calculate condensation pressure
        P_cond = self.props.Psat_T(T_cond)
        T_sat = self.props.Tsat_P(P_cond)  # Verify consistency
        
        # Construct outlet state
        state_out = ThermoState()
        
        if subcool_K > 0.0:
            # Subcooled liquid
            T_out = T_sat - subcool_K
            state_out.update_from_PT(P_cond, T_out)
        else:
            # Saturated liquid (x = 0.0)
            state_out.update_from_PX(P_cond, 0.0)
        
        # Check for incomplete condensation
        if state_in.h <= state_out.h:
            flags["incomplete_condensation"] = True
        
        # Compute heat transfer from mass flow energy balance
        # Condensation: heat rejected = m_dot * (h_in - h_out)
        Q_mass = m_dot * (state_in.h - state_out.h)
        
        if Q_mass <= 0:
            flags["negative_heat_rejection"] = True
        
        # Compute LMTD for heat exchanger
        # Heat flows from refrigerant (T_sat) to air (T_air_in -> T_air_out)
        delta_T1 = T_sat - T_air_in
        delta_T2 = T_sat - T_air_out
        
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
                flags["negative_heat_rejection"] = True
            
            # Compute relative difference
            epsilon = 1.0  # Small value to avoid division by zero
            delta_relative = abs(Q_mass - Q_KA) / max(abs(Q_mass), epsilon)
            
            # Check for thermal mismatch
            if delta_relative > 0.05:
                flags["thermal_mismatch"] = True
        
        return CondenserResult(
            state_out=state_out,
            P_cond=P_cond,
            T_sat=T_sat,
            Q_mass=Q_mass,
            Q_KA=Q_KA,
            delta_relative=delta_relative,
            flags=flags,
        )
