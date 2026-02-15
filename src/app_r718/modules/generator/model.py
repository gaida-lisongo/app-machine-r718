"""
Generator Model - Physical heating/vaporization model

Implements constant-pressure heating from liquid to saturated/superheated vapor.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from dataclasses import dataclass
import numpy as np
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service


@dataclass
class GeneratorResult:
    """
    Result of generator calculation.
    
    Attributes:
        state_out: Outlet thermodynamic state (saturated or superheated vapor)
        P_gen: Generator pressure [Pa]
        Q_mass: Heat input from mass balance [W]
        Q_KA: Heat input from heat exchanger model [W]
        delta_relative: Relative difference between Q_mass and Q_KA [-]
        delta_T_lm: Log-mean temperature difference [K]
        flags: Diagnostic flags dictionary
    """
    state_out: ThermoState
    P_gen: float
    Q_mass: float
    Q_KA: float
    delta_relative: float
    delta_T_lm: float
    flags: dict[str, bool]


class GeneratorModel:
    """
    Physical model of solar/thermal generator.
    
    Models constant-pressure heating and vaporization of liquid refrigerant.
    Heat is supplied by a hot thermal fluid (HTF) like hot water or thermal oil.
    """
    
    def __init__(self):
        """Initialize generator model."""
        self.props = get_props_service()
    
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
        Solve generator heating/vaporization with heat exchanger model.
        
        Args:
            state_in: Inlet thermodynamic state (compressed liquid from pump)
            m_dot: Refrigerant mass flow rate [kg/s]
            T_gen_target: Target generator saturation temperature [K]
            K: Overall heat transfer coefficient [W/m²/K]
            A: Heat exchanger area [m²]
            T_htf_in: Hot thermal fluid inlet temperature [K]
            T_htf_out: Hot thermal fluid outlet temperature [K]
            superheat_K: Superheat above saturation [K] (0 = saturated vapor)
            
        Returns:
            GeneratorResult with outlet state and diagnostic flags
        """
        # Initialize flags
        flags = {
            "insufficient_heating": False,
            "invalid_LMTD": False,
            "negative_heat_input": False,
            "thermal_mismatch": False,
            "two_phase_outlet": False,
        }
        
        # Compute generator pressure from target saturation temperature
        P_gen = self.props.Psat_T(T_gen_target)
        T_sat = T_gen_target
        
        # Construct outlet state
        state_out = ThermoState()
        
        if superheat_K <= 0.0:
            # Saturated vapor (x = 1.0)
            state_out.update_from_PX(P_gen, 1.0)
        else:
            # Superheated vapor
            T_out = T_sat + superheat_K
            state_out.update_from_PT(P_gen, T_out)
        
        # Check if outlet is actually two-phase (shouldn't happen with x=1 or superheat)
        if state_out.x is not None and 0 < state_out.x < 1:
            flags["two_phase_outlet"] = True
        
        # Mass balance: Q = m_dot * (h_out - h_in)
        h_in = state_in.h
        h_out = state_out.h
        
        # Check for negative heat input
        if h_out <= h_in:
            flags["negative_heat_input"] = True
        
        Q_mass = m_dot * (h_out - h_in)
        
        if Q_mass < 0:
            flags["negative_heat_input"] = True
        
        # Heat exchanger model: Q = K * A * ΔT_lm
        # LMTD for constant saturation temperature on refrigerant side
        # HTF cools from T_htf_in to T_htf_out
        # Refrigerant heats from T_in to T_sat (and superheat if any)
        
        # For LMTD calculation, use effective refrigerant temperature = T_sat
        # (simplification: assumes most heat transfer is during phase change)
        delta_T1 = T_htf_in - T_sat
        delta_T2 = T_htf_out - T_sat
        
        # Check for invalid temperature differences
        if delta_T1 <= 0 or delta_T2 <= 0:
            flags["invalid_LMTD"] = True
            # Use fallback LMTD to avoid crash
            delta_T_lm = max(abs(delta_T1), abs(delta_T2), 1.0)
        else:
            # Compute LMTD
            if abs(delta_T1 - delta_T2) < 1e-6:
                # Avoid division by zero if ΔT1 ≈ ΔT2
                delta_T_lm = delta_T1
            else:
                delta_T_lm = (delta_T1 - delta_T2) / np.log(delta_T1 / delta_T2)
        
        # Heat transfer from KA model
        Q_KA = K * A * delta_T_lm
        
        # Compare Q_mass and Q_KA
        eps = 1e-6
        delta_relative = abs(Q_mass - Q_KA) / max(abs(Q_mass), abs(Q_KA), eps)
        
        # Flag thermal mismatch if relative difference > 20%
        if delta_relative > 0.20:
            flags["thermal_mismatch"] = True
        
        # Check if HTF provides sufficient heating
        if Q_KA < 0.5 * Q_mass:
            flags["insufficient_heating"] = True
        
        return GeneratorResult(
            state_out=state_out,
            P_gen=P_gen,
            Q_mass=Q_mass,
            Q_KA=Q_KA,
            delta_relative=delta_relative,
            delta_T_lm=delta_T_lm,
            flags=flags,
        )
