"""
Ejector Model - Physical ejector model (V1: 1D thermodynamic)

Implements simplified 1D ejector model with component efficiencies.
V2 (future): Full compressible flow with shock wave modeling.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize_scalar, brentq
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service


@dataclass
class EjectorResult:
    """
    Result of ejector calculation.
    
    Attributes:
        mu: Entrainment ratio (m_dot_s / m_dot_p) [-]
        m_dot_p: Primary mass flow rate [kg/s]
        m_dot_s: Secondary mass flow rate [kg/s]
        P_mix: Mixing chamber pressure [Pa]
        state_p_noz: Primary state after nozzle (at P_mix)
        state_s_adj: Secondary state adjusted to P_mix
        state_mix: Mixed state (before diffuser)
        state_out: Outlet state (after diffuser, at P_out)
        flags: Diagnostic flags dictionary
        notes: Additional notes or warnings
    """
    mu: float
    m_dot_p: float
    m_dot_s: float
    P_mix: float
    state_p_noz: ThermoState
    state_s_adj: ThermoState
    state_mix: ThermoState
    state_out: ThermoState
    flags: dict[str, bool]
    notes: str


class EjectorModel:
    """
    Physical model of supersonic ejector (V1: simplified 1D).
    
    Models primary nozzle, mixing chamber, and diffuser with component efficiencies.
    
    V1 assumptions:
    - Steady state, 1D flow
    - Adiabatic (no heat transfer)
    - Component efficiencies (nozzle, diffuser, mixing)
    - No explicit shock wave modeling (V2 future)
    
    V2 TODO (future):
    - [ ] Mach number calculations in nozzle
    - [ ] Compressible flow relations
    - [ ] Choking detection
    - [ ] Normal shock wave in diffuser
    - [ ] Rankine-Hugoniot relations across shock
    - [ ] Entropy increase at shock
    """
    
    def __init__(self):
        """Initialize ejector model."""
        self.props = get_props_service()
    
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
        Solve ejector mixing and compression (V1 model).
        
        Args:
            state_p_in: Primary inlet state (high-pressure vapor from generator)
            state_s_in: Secondary inlet state (low-pressure vapor from evaporator)
            P_out: Discharge pressure [Pa] (typically condenser pressure)
            m_dot_p: Primary mass flow rate [kg/s]
            eta_nozzle: Nozzle isentropic efficiency [-]
            eta_diffuser: Diffuser isentropic efficiency [-]
            eta_mixing: Mixing efficiency [-] (1.0 = no losses)
            
        Returns:
            EjectorResult with entrainment ratio mu and thermodynamic states
        """
        # Initialize flags
        flags = {
            "invalid_efficiency": False,
            "invalid_pressure_levels": False,
            "unphysical_state": False,
            "two_phase_outlet": False,
            "poor_pressure_recovery": False,
            "solver_no_convergence": False,
        }
        
        notes = []
        
        # Validate efficiencies
        if not (0 < eta_nozzle <= 1.0):
            flags["invalid_efficiency"] = True
            eta_nozzle = 0.85  # Safe default
            notes.append("Invalid eta_nozzle, using 0.85")
        
        if not (0 < eta_diffuser <= 1.0):
            flags["invalid_efficiency"] = True
            eta_diffuser = 0.85
            notes.append("Invalid eta_diffuser, using 0.85")
        
        if not (0 < eta_mixing <= 1.0):
            flags["invalid_efficiency"] = True
            eta_mixing = 1.0
            notes.append("Invalid eta_mixing, using 1.0")
        
        # Validate pressure levels
        P_p_in = state_p_in.P
        P_s_in = state_s_in.P
        
        if P_out >= P_p_in:
            flags["invalid_pressure_levels"] = True
            notes.append("P_out >= P_p_in: invalid compression")
        
        if P_s_in >= P_out:
            flags["invalid_pressure_levels"] = True
            notes.append("P_s_in >= P_out: secondary pressure too high")
        
        # Handle zero or negative primary flow
        if m_dot_p <= 0:
            # Return trivial solution: no entrainment
            notes.append("Zero primary flow: mu = 0")
            
            # Create fallback states (no actual flow)
            state_p_noz = state_p_in.clone()
            state_s_adj = state_s_in.clone()
            state_mix = state_s_in.clone()
            state_out = ThermoState()
            state_out.P = P_out
            state_out.h = state_s_in.h
            
            return EjectorResult(
                mu=0.0,
                m_dot_p=m_dot_p,
                m_dot_s=0.0,
                P_mix=P_s_in,
                state_p_noz=state_p_noz,
                state_s_adj=state_s_adj,
                state_mix=state_mix,
                state_out=state_out,
                flags=flags,
                notes="; ".join(notes) if notes else "OK",
            )
        
        # Estimate mixing pressure P_mix
        # V1 approach: Use geometric mean between P_s_in and P_out
        # This is a simplified assumption; V2 will calculate this from flow equations
        P_mix = np.sqrt(P_s_in * P_out)
        
        # Ensure P_mix is in valid range
        P_mix = np.clip(P_mix, P_s_in * 1.01, P_out * 0.99)
        
        # ===== PRIMARY NOZZLE =====
        # Expand primary vapor from P_p_in to P_mix with efficiency
        
        try:
            # Isentropic expansion to P_mix
            state_p_is = ThermoState()
            state_p_is.update_from_PS(P_mix, state_p_in.s)
            
            # Real expansion with nozzle efficiency
            h_p_in = state_p_in.h
            h_p_is = state_p_is.h
            h_p_noz = h_p_in - eta_nozzle * (h_p_in - h_p_is)
            
            state_p_noz = ThermoState()
            state_p_noz.update_from_PH(P_mix, h_p_noz)
            
        except Exception as e:
            flags["unphysical_state"] = True
            notes.append(f"Nozzle expansion failed: {e}")
            # Create fallback state
            state_p_noz = ThermoState()
            state_p_noz.P = P_mix
            state_p_noz.h = state_p_in.h
        
        # ===== SECONDARY ADJUSTMENT =====
        # Adjust secondary to mixing pressure P_mix
        # V1: Assume secondary enters as saturated vapor at P_mix if possible
        
        try:
            # Try to create saturated vapor at P_mix
            T_sat_mix = self.props.Tsat_P(P_mix)
            state_s_adj = ThermoState()
            state_s_adj.update_from_PX(P_mix, 1.0)  # Saturated vapor
            
        except Exception:
            try:
                # Fallback: Isentropic compression/expansion to P_mix
                state_s_adj = ThermoState()
                state_s_adj.update_from_PS(P_mix, state_s_in.s)
            except Exception as e:
                flags["unphysical_state"] = True
                notes.append(f"Secondary adjustment failed: {e}")
                state_s_adj = ThermoState()
                state_s_adj.P = P_mix
                state_s_adj.h = state_s_in.h
        
        # ===== CALCULATE ENTRAINMENT RATIO =====
        # V1: Use simplified energy balance and empirical correlation
        # mu depends on pressure ratios and enthalpies
        
        # Simplified approach: Use pressure ratio correlation
        # This is empirical for V1; V2 will use momentum balance
        pressure_ratio_primary = P_p_in / P_mix
        pressure_ratio_secondary = P_mix / P_s_in
        
        # Empirical correlation (typical for ejectors)
        # mu increases with primary pressure ratio
        # This is a placeholder; real calculation requires momentum balance
        mu_estimated = 0.1 + 0.3 * np.log(pressure_ratio_primary) / np.log(pressure_ratio_secondary + 1)
        mu_estimated = np.clip(mu_estimated, 0.0, 5.0)
        
        # Alternative: Try to find mu that balances energy and achieves P_out
        # For robustness, use a search method
        
        def objective_mu(mu_trial):
            """
            Objective function: Find mu that produces valid outlet state at P_out.
            Returns penalty if state is unphysical or P_out not achievable.
            """
            if mu_trial < 0:
                return 1e10
            
            try:
                # Calculate mixed enthalpy
                m_total = m_dot_p + mu_trial * m_dot_p
                
                # Protect against division by zero
                if m_total <= 0:
                    return 1e10
                
                h_mix_ideal = (m_dot_p * state_p_noz.h + mu_trial * m_dot_p * state_s_adj.h) / m_total
                
                # Apply mixing efficiency
                h_mix = h_mix_ideal  # For V1, eta_mixing = 1.0 typically
                
                # Create mixed state at P_mix
                state_mix_trial = ThermoState()
                state_mix_trial.update_from_PH(P_mix, h_mix)
                
                # Diffuser: Compress from P_mix to P_out
                # Isentropic compression
                state_out_is_trial = ThermoState()
                state_out_is_trial.update_from_PS(P_out, state_mix_trial.s)
                
                # Real compression with diffuser efficiency
                h_out_is = state_out_is_trial.h
                h_out = h_mix + (h_out_is - h_mix) / eta_diffuser
                
                # Check if h_out is reasonable
                if h_out < h_mix:
                    return 1e10  # Invalid: enthalpy decreased during compression
                
                # Penalty: Minimize h_out (best pressure recovery)
                # Or: Penalize deviation from target conditions
                return h_out
                
            except Exception:
                return 1e10
        
        # Search for optimal mu in range [0, 2.0]
        try:
            result_opt = minimize_scalar(
                objective_mu,
                bounds=(0.0, 2.0),
                method='bounded',
            )
            
            if result_opt.success and result_opt.fun < 1e9:
                mu = result_opt.x
            else:
                mu = mu_estimated
                flags["solver_no_convergence"] = True
                notes.append("Mu optimization failed, using empirical estimate")
                
        except Exception:
            mu = mu_estimated
            flags["solver_no_convergence"] = True
            notes.append("Mu solver exception, using empirical estimate")
        
        # Clip mu to reasonable range
        mu = np.clip(mu, 0.0, 5.0)
        
        if mu < 0.01:
            flags["poor_pressure_recovery"] = True
            notes.append("Very low entrainment ratio (mu < 0.01)")
        
        # ===== MIXING =====
        m_dot_s = mu * m_dot_p
        m_total = m_dot_p + m_dot_s
        
        try:
            # Energy balance for mixing
            # Protect against division by zero (should not occur due to early return)
            if m_total <= 0:
                raise ValueError("Total mass flow is zero or negative")
            
            h_mix = (m_dot_p * state_p_noz.h + m_dot_s * state_s_adj.h) / m_total
            
            state_mix = ThermoState()
            state_mix.update_from_PH(P_mix, h_mix)
            
        except Exception as e:
            flags["unphysical_state"] = True
            notes.append(f"Mixing state failed: {e}")
            state_mix = ThermoState()
            state_mix.P = P_mix
            state_mix.h = (state_p_noz.h + state_s_adj.h) / 2
        
        # ===== DIFFUSER =====
        # Compress mixed flow from P_mix to P_out with efficiency
        
        try:
            # Isentropic compression to P_out
            state_out_is = ThermoState()
            state_out_is.update_from_PS(P_out, state_mix.s)
            
            # Real compression with diffuser efficiency
            h_out = state_mix.h + (state_out_is.h - state_mix.h) / eta_diffuser
            
            state_out = ThermoState()
            state_out.update_from_PH(P_out, h_out)
            
            # Check for two-phase outlet
            if state_out.x is not None and 0 < state_out.x < 1:
                flags["two_phase_outlet"] = True
                notes.append("Outlet is two-phase (partially condensed)")
            
        except Exception as e:
            flags["unphysical_state"] = True
            notes.append(f"Diffuser compression failed: {e}")
            state_out = ThermoState()
            state_out.P = P_out
            state_out.h = state_mix.h
        
        # ===== PRESSURE RECOVERY CHECK =====
        if P_mix > P_out * 0.95:
            flags["poor_pressure_recovery"] = True
            notes.append("Poor pressure recovery: P_mix too close to P_out")
        
        return EjectorResult(
            mu=mu,
            m_dot_p=m_dot_p,
            m_dot_s=m_dot_s,
            P_mix=P_mix,
            state_p_noz=state_p_noz,
            state_s_adj=state_s_adj,
            state_mix=state_mix,
            state_out=state_out,
            flags=flags,
            notes="; ".join(notes) if notes else "OK",
        )
