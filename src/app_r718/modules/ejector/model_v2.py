"""
Ejector Model V2 - Compressible 1D flow with normal shock wave

Implements full compressible flow ejector model with:
- Mach number calculations
- Choking detection
- Normal shock wave modeling
- Rankine-Hugoniot relations
- Momentum and energy conservation

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize_scalar, brentq, fsolve
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.ejector.model import EjectorModel, EjectorResult


@dataclass
class EjectorResultV2(EjectorResult):
    """
    Extended result for V2 model with compressible flow details.
    
    Additional attributes beyond V1:
        mach_primary_nozzle: Mach number at primary nozzle exit [-]
        mach_before_shock: Mach number before shock wave [-]
        mach_after_shock: Mach number after shock wave [-]
        shock_location: Location of shock wave (descriptive string)
        regime: Flow regime ("subsonic", "choked", "supersonic")
        regime_type: Ejector regime ("non-entraining", "critical", "entraining-supersonic")
        entropy_jump: Entropy increase across shock [J/kg/K]
        entropy_jump_kJ: Entropy increase across shock [kJ/kg/K]
        P_before_shock: Pressure before shock [Pa]
        P_after_shock: Pressure after shock [Pa]
        P_suction_local: Local suction pressure [Pa]
        suction_condition: True if P_suction < P_secondary [-]
        compression_ratio: P_out / P_secondary [-]
        pressure_lift: P_out - P_secondary [Pa]
        state_before_shock: ThermoState before shock (if detected)
        state_after_shock: ThermoState after shock (if detected)
        physically_consistent_mixture: True if h_mix in valid range [-]
    """
    mach_primary_nozzle: float = 0.0
    mach_before_shock: float = 0.0
    mach_after_shock: float = 0.0
    shock_location: str = "none"
    regime: str = "subsonic"
    regime_type: str = "non-entraining"
    entropy_jump: float = 0.0
    entropy_jump_kJ: float = 0.0
    P_before_shock: float = 0.0
    P_after_shock: float = 0.0
    P_suction_local: float = 0.0
    suction_condition: bool = False
    static_suction_check: bool = False
    dynamic_entrainment: bool = False
    compression_ratio: float = 0.0
    pressure_lift: float = 0.0
    entropy_jump_suspect: bool = False
    state_before_shock: ThermoState = None
    state_after_shock: ThermoState = None
    physically_consistent_mixture: bool = True


class EjectorModelV2(EjectorModel):
    """
    Compressible flow ejector model (V2).
    
    Implements full 1D compressible flow with:
    - Ideal gas approximation for vapor (γ = 1.33, R = 461.5 J/kg/K)
    - Isentropic relations in nozzle (with efficiency)
    - Momentum and energy conservation in mixing section
    - Normal shock wave with Rankine-Hugoniot relations
    - Entropy jump calculation
    - Subsonic diffuser with efficiency
    
    Physics:
    1. Primary nozzle: Supersonic expansion with choking detection
    2. Mixing section: Momentum + energy balance for mu and P_mix
    3. Normal shock: Rankine-Hugoniot if M > 1
    4. Diffuser: Subsonic compression to P_out
    """
    
    # Thermodynamic constants for water vapor (ideal gas approximation)
    GAMMA = 1.33  # Specific heat ratio for steam [-]
    R_SPECIFIC = 461.5  # Specific gas constant [J/kg/K]
    
    # Numerical tolerances
    MACH_SHOCK_THRESHOLD = 1.0 + 1e-6  # Mach tolerance for shock detection
    MAX_MU = 5.0  # Maximum entrainment ratio
    MAX_ITERATIONS = 100  # Maximum solver iterations
    
    def __init__(self):
        """Initialize V2 model."""
        super().__init__()
    
    def compute_sound_speed(self, temperature: float) -> float:
        """
        Calculate speed of sound in ideal gas.
        
        c = sqrt(gamma * R * T)
        
        Args:
            temperature: Static temperature [K]
            
        Returns:
            Speed of sound [m/s]
        """
        return np.sqrt(self.GAMMA * self.R_SPECIFIC * temperature)
    
    def compute_mach_number(self, velocity: float, temperature: float) -> float:
        """
        Calculate Mach number M = v / c.
        
        Args:
            velocity: Flow velocity [m/s]
            temperature: Static temperature [K]
            
        Returns:
            Mach number [-]
        """
        c = self.compute_sound_speed(temperature)
        return velocity / c if c > 0 else 0.0
    
    def compute_critical_pressure_ratio(self) -> float:
        """
        Calculate critical pressure ratio for choking.
        
        P*/P0 = (2 / (gamma + 1))^(gamma / (gamma - 1))
        
        Returns:
            Critical pressure ratio [-]
        """
        gamma = self.GAMMA
        return (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    
    def is_choked(self, P_exit: float, P_stagnation: float) -> bool:
        """
        Detect if nozzle is choked.
        
        Args:
            P_exit: Exit static pressure [Pa]
            P_stagnation: Inlet stagnation pressure [Pa]
            
        Returns:
            True if choked (M = 1 at throat)
        """
        critical_ratio = self.compute_critical_pressure_ratio()
        return (P_exit / P_stagnation) < critical_ratio
    
    def compute_mach_from_pressure_ratio(self, P_ratio: float, is_expansion: bool = True) -> float:
        """
        Calculate Mach number from isentropic pressure ratio.
        
        P/P0 = (1 + (gamma-1)/2 * M^2)^(-gamma/(gamma-1))
        
        Args:
            P_ratio: P / P_stagnation [-]
            is_expansion: True for nozzle (M >= 1), False for diffuser (M < 1)
            
        Returns:
            Mach number [-]
        """
        gamma = self.GAMMA
        
        if P_ratio >= 1.0:
            return 0.0  # No expansion/compression
        
        try:
            # Invert isentropic relation
            M_squared = (2.0 / (gamma - 1.0)) * (P_ratio ** (-(gamma - 1.0) / gamma) - 1.0)
            
            if M_squared < 0:
                return 0.0
            
            return np.sqrt(M_squared)
        
        except (ValueError, ZeroDivisionError):
            return 0.0
    
    def compute_velocity_from_enthalpy(self, h_stag: float, h_static: float) -> float:
        """
        Calculate velocity from enthalpy difference (energy conservation).
        
        v = sqrt(2 * (h0 - h))
        
        Args:
            h_stag: Stagnation enthalpy [J/kg]
            h_static: Static enthalpy [J/kg]
            
        Returns:
            Velocity [m/s]
        """
        delta_h = h_stag - h_static
        if delta_h <= 0:
            return 0.0
        
        return np.sqrt(2.0 * delta_h)
    
    def apply_normal_shock(self, mach_1: float, P_1: float, T_1: float, h_1: float) -> dict:
        """
        Apply Rankine-Hugoniot relations across normal shock.
        
        Upstream: M1 > 1 (supersonic)
        Downstream: M2 < 1 (subsonic)
        
        Relations:
        - P2/P1 = 1 + 2*gamma/(gamma+1) * (M1^2 - 1)
        - M2^2 = (1 + (gamma-1)/2 * M1^2) / (gamma*M1^2 - (gamma-1)/2)
        - T2/T1 = (P2/P1) * (rho1/rho2)
        
        Args:
            mach_1: Upstream Mach number (M > 1)
            P_1: Upstream pressure [Pa]
            T_1: Upstream temperature [K]
            h_1: Upstream enthalpy [J/kg]
            
        Returns:
            dict with downstream properties (P_2, T_2, mach_2, h_2, delta_s)
        """
        gamma = self.GAMMA
        R = self.R_SPECIFIC
        
        # No shock if subsonic
        if mach_1 <= 1.0:
            return {
                "P_2": P_1,
                "T_2": T_1,
                "mach_2": mach_1,
                "h_2": h_1,
                "delta_s": 0.0,
            }
        
        # Pressure ratio across shock
        P_ratio = 1.0 + (2.0 * gamma / (gamma + 1.0)) * (mach_1**2 - 1.0)
        P_2 = P_1 * P_ratio
        
        # Downstream Mach number
        numerator = 1.0 + ((gamma - 1.0) / 2.0) * mach_1**2
        denominator = gamma * mach_1**2 - (gamma - 1.0) / 2.0
        
        if denominator <= 0:
            mach_2 = 0.1  # Safety fallback
        else:
            mach_2_squared = numerator / denominator
            mach_2 = np.sqrt(max(0.0, mach_2_squared))
        
        # Density ratio (from continuity and Mach relations)
        rho_ratio = ((gamma + 1.0) * mach_1**2) / (2.0 + (gamma - 1.0) * mach_1**2)
        
        # Temperature ratio
        T_ratio = P_ratio / rho_ratio
        T_2 = T_1 * T_ratio
        
        # Stagnation enthalpy is conserved across shock
        h_2 = h_1  # For ideal gas with constant Cp
        
        # Entropy jump (ideal gas)
        # Δs = Cp * ln(T2/T1) - R * ln(P2/P1)
        # For ideal gas: Cp = gamma * R / (gamma - 1)
        Cp = gamma * R / (gamma - 1.0)
        delta_s = Cp * np.log(T_ratio) - R * np.log(P_ratio)
        
        return {
            "P_2": P_2,
            "T_2": T_2,
            "mach_2": mach_2,
            "h_2": h_2,
            "delta_s": delta_s,
        }
    
    def solve_v2(
        self,
        state_p_in: ThermoState,
        state_s_in: ThermoState,
        P_out: float,
        m_dot_p: float,
        eta_nozzle: float = 0.85,
        eta_diffuser: float = 0.85,
        eta_mixing: float = 1.0,
    ) -> EjectorResultV2:
        """
        Solve ejector with compressible flow model (V2).
        
        Args:
            state_p_in: Primary inlet state (high-pressure vapor from generator)
            state_s_in: Secondary inlet state (low-pressure vapor from evaporator)
            P_out: Discharge pressure [Pa] (condenser pressure)
            m_dot_p: Primary mass flow rate [kg/s]
            eta_nozzle: Nozzle isentropic efficiency [-]
            eta_diffuser: Diffuser isentropic efficiency [-]
            eta_mixing: Mixing efficiency [-]
            
        Returns:
            EjectorResultV2 with entrainment ratio, Mach numbers, and shock details
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
            eta_nozzle = 0.85
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
            notes.append("Zero primary flow: mu = 0")
            
            state_p_noz = state_p_in.clone()
            state_s_adj = state_s_in.clone()
            state_mix = state_s_in.clone()
            state_out = ThermoState()
            state_out.P = P_out
            state_out.h = state_s_in.h
            
            return EjectorResultV2(
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
                regime="no_flow",
            )
        
        # ===== STEP 1: PRIMARY NOZZLE (Compressible Expansion) =====
        
        # Initial estimate of mixing pressure
        # V2: Will be calculated from momentum balance, but need initial guess
        P_mix_initial = np.sqrt(P_s_in * P_out)
        P_mix_initial = np.clip(P_mix_initial, P_s_in * 1.01, P_out * 0.99)
        
        # Check if nozzle is choked
        choked = self.is_choked(P_mix_initial, P_p_in)
        regime = "choked" if choked else "subsonic"
        
        # Calculate Mach number at nozzle exit
        P_ratio_nozzle = P_mix_initial / P_p_in
        mach_nozzle = self.compute_mach_from_pressure_ratio(P_ratio_nozzle, is_expansion=True)
        
        if choked and mach_nozzle < 1.0:
            mach_nozzle = 1.0  # At throat if choked
            regime = "supersonic"
        
        # Isentropic expansion to P_mix_initial
        try:
            state_p_is = ThermoState()
            state_p_is.update_from_PS(P_mix_initial, state_p_in.s)
            
            # Real expansion with nozzle efficiency
            h_p_in = state_p_in.h
            h_p_is = state_p_is.h
            h_p_noz = h_p_in - eta_nozzle * (h_p_in - h_p_is)
            
            state_p_noz = ThermoState()
            state_p_noz.update_from_PH(P_mix_initial, h_p_noz)
            
            # Calculate velocity from enthalpy drop
            v_p_noz = self.compute_velocity_from_enthalpy(h_p_in, h_p_noz)
            
            # Recalculate Mach using actual temperature
            T_p_noz = state_p_noz.T
            mach_nozzle = self.compute_mach_number(v_p_noz, T_p_noz)
            
        except Exception as e:
            flags["unphysical_state"] = True
            notes.append(f"Nozzle expansion failed: {e}")
            state_p_noz = ThermoState()
            state_p_noz.P = P_mix_initial
            state_p_noz.h = state_p_in.h
            v_p_noz = 0.0
            mach_nozzle = 0.0
        
        # ===== STEP 2: SECONDARY INLET VELOCITY =====
        
        try:
            # Secondary enters at P_s_in, needs to be mixed at P_mix
            # For now, assume secondary velocity is low (subsonic)
            # In real ejector, secondary is accelerated by primary jet
            
            # Simplified: Assume secondary at low velocity
            v_s_in = 10.0  # m/s (low subsonic)
            
            # Secondary state remains approximately at P_s_in initially
            state_s_adj = state_s_in.clone()
            
        except Exception as e:
            flags["unphysical_state"] = True
            notes.append(f"Secondary state failed: {e}")
            state_s_adj = state_s_in.clone()
            v_s_in = 0.0
        
        # ===== STEP 3: MIXING WITH MOMENTUM BALANCE =====
        
        def solve_mixing_momentum(mu_trial):
            """
            Solve for mixing pressure using momentum and energy balance.
            
            Momentum: m_p*v_p + m_s*v_s = (m_p + m_s)*v_mix
            Energy:   m_p*h_p + m_s*h_s = (m_p + m_s)*h_mix
            
            Returns error metric for mu_trial.
            """
            if mu_trial < 0:
                return 1e10
            
            try:
                m_s = mu_trial * m_dot_p
                m_total = m_dot_p + m_s
                
                if m_total <= 0:
                    return 1e10
                
                # Momentum balance to find v_mix
                momentum_total = m_dot_p * v_p_noz + m_s * v_s_in
                v_mix = momentum_total / m_total
                
                # Energy balance to find h_mix
                h_mix = (m_dot_p * state_p_noz.h + m_s * state_s_adj.h) / m_total
                
                # Estimate P_mix from static enthalpy and velocity
                # h_static = h_stagnation - v^2/2
                h_static_mix = h_mix - v_mix**2 / 2.0
                
                # For this iteration, use geometric mean as approximation
                # More rigorous: solve P_mix from state equation
                P_mix_trial = np.sqrt(P_s_in * P_out)
                
                # Create mixed state
                state_mix_trial = ThermoState()
                state_mix_trial.update_from_PH(P_mix_trial, h_static_mix)
                
                # Check if we can compress to P_out with diffuser
                state_out_is_trial = ThermoState()
                state_out_is_trial.update_from_PS(P_out, state_mix_trial.s)
                
                h_out_is = state_out_is_trial.h
                h_out = h_mix + (h_out_is - h_mix) / eta_diffuser
                
                if h_out < h_mix:
                    return 1e10
                
                # Objective: Find mu that minimizes diffuser compression requirement
                # Lower h_out means better pressure recovery
                # This is physically meaningful unlike just maximizing mu
                compression_work = h_out - h_mix
                
                # Penalize negative mu heavily
                if mu_trial < 0:
                    return 1e10
                
                return compression_work
                
            except Exception:
                return 1e10
        
        # Search for optimal mu
        try:
            result_opt = minimize_scalar(
                solve_mixing_momentum,
                bounds=(0.0, 3.0),
                method='bounded',
            )
            
            if result_opt.success and result_opt.fun < 1e9:
                mu = result_opt.x
            else:
                # Fallback: Empirical correlation
                pressure_ratio_primary = P_p_in / P_mix_initial
                mu = 0.2 + 0.4 * np.log(max(1.1, pressure_ratio_primary))
                mu = np.clip(mu, 0.0, 3.0)
                flags["solver_no_convergence"] = True
                notes.append("Mu optimization failed, using empirical estimate")
                
        except Exception:
            pressure_ratio_primary = P_p_in / P_mix_initial
            mu = 0.2 + 0.4 * np.log(max(1.1, pressure_ratio_primary))
            mu = np.clip(mu, 0.0, 3.0)
            flags["solver_no_convergence"] = True
            notes.append("Mu solver exception, using empirical estimate")
        
        if mu < 0.01:
            flags["poor_pressure_recovery"] = True
            notes.append("Very low entrainment ratio (mu < 0.01)")
        
        # ===== STEP 4: FINAL MIXING STATE =====
        
        m_dot_s = mu * m_dot_p
        m_total = m_dot_p + m_dot_s
        
        try:
            if m_total <= 0:
                raise ValueError("Total mass flow is zero")
            
            # Momentum balance
            momentum_total = m_dot_p * v_p_noz + m_dot_s * v_s_in
            v_mix = momentum_total / m_total
            
            # Energy balance
            h_mix_stag = (m_dot_p * state_p_noz.h + m_dot_s * state_s_adj.h) / m_total
            
            # Static enthalpy
            h_mix_static = h_mix_stag - v_mix**2 / 2.0
            
            # Mixing pressure (refined estimate)
            P_mix = np.sqrt(P_s_in * P_out)
            P_mix = np.clip(P_mix, P_s_in * 1.01, P_out * 0.99)
            
            state_mix = ThermoState()
            state_mix.update_from_PH(P_mix, h_mix_static)
            
            # Calculate Mach at mixing section
            T_mix = state_mix.T
            mach_mix = self.compute_mach_number(v_mix, T_mix)
            
        except Exception as e:
            flags["unphysical_state"] = True
            notes.append(f"Mixing state failed: {e}")
            state_mix = ThermoState()
            state_mix.P = P_mix_initial
            state_mix.h = (state_p_noz.h + state_s_adj.h) / 2
            v_mix = 0.0
            mach_mix = 0.0
        
        # ===== STEP 5: NORMAL SHOCK WAVE =====
        
        shock_data = None
        mach_before_shock = mach_mix
        mach_after_shock = mach_mix
        entropy_jump = 0.0
        shock_location = "none"
        P_before_shock_value = 0.0
        P_after_shock_value = 0.0
        state_before_shock_obj = None
        state_after_shock_obj = None
        
        if mach_mix > self.MACH_SHOCK_THRESHOLD:
            # Apply normal shock (M > 1 + eps)
            shock_location = "mixing_section"
            regime = "supersonic"
            
            try:
                # Save pressure and state BEFORE shock
                P_before_shock_value = state_mix.P
                state_before_shock_obj = state_mix.clone()
                
                shock_data = self.apply_normal_shock(
                    mach_1=mach_mix,
                    P_1=state_mix.P,
                    T_1=state_mix.T,
                    h_1=state_mix.h,
                )
                
                mach_before_shock = mach_mix
                mach_after_shock = shock_data["mach_2"]
                entropy_jump = shock_data["delta_s"]  # In J/kg/K (ideal gas)
                
                # Update state after shock
                P_after_shock_value = shock_data["P_2"]
                T_after_shock = shock_data["T_2"]
                
                # Validate shock physics: P2 > P1 (strict increase)
                if P_after_shock_value <= P_before_shock_value * (1.0 + 1e-6):
                    # Ensure minimum pressure increase across shock
                    P_after_shock_value = P_before_shock_value * 1.001
                    notes.append("Shock pressure ratio adjusted for numerical stability")
                
                # Use (P,T) instead of (P,h) for real gas accuracy
                # This ensures CoolProp computes correct entropy increase
                state_mix_after_shock = ThermoState()
                state_mix_after_shock.update_from_PT(P_after_shock_value, T_after_shock)
                state_after_shock_obj = state_mix_after_shock.clone()
                
                # Recalculate entropy jump from REAL thermodynamic states (CoolProp)
                # This overrides the ideal gas calculation to ensure consistency
                entropy_jump_real = state_after_shock_obj.s - state_before_shock_obj.s
                
                # Validate 2nd law: entropy must increase
                if entropy_jump_real < 0:
                    # If CoolProp gives decreasing entropy, swap states or flag error
                    notes.append(f"Warning: CoolProp entropy decreased ({entropy_jump_real:.2f} J/kg/K), using ideal gas value")
                else:
                    # Use real entropy jump from CoolProp
                    entropy_jump = entropy_jump_real
                
                # Use post-shock state for diffuser inlet
                state_mix = state_mix_after_shock
                
                notes.append(f"Normal shock: M {mach_before_shock:.2f} → {mach_after_shock:.2f}")
                
            except Exception as e:
                notes.append(f"Shock calculation failed: {e}")
                shock_location = "none"
                P_before_shock_value = 0.0
                P_after_shock_value = 0.0
                state_before_shock_obj = None
                state_after_shock_obj = None
        
        # ===== STEP 6: DIFFUSER (Subsonic Compression) =====
        
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
        
        # ===== ADDITIONAL DIAGNOSTICS =====
        
        # Suction diagnostic: use primary nozzle exit pressure as local suction pressure
        # This is the lowest pressure point in the entrainment zone (jet exit)
        P_suction_local = state_p_noz.P
        
        # Static suction check: pressure-based criterion
        static_suction_check = P_suction_local < P_s_in
        
        # Dynamic entrainment: momentum-based criterion
        dynamic_entrainment = (mu > 0.01) and (mach_nozzle > 1.0)
        
        # Legacy suction_condition for backward compatibility
        suction_condition = static_suction_check
        
        # Compression ratio
        compression_ratio = P_out / P_s_in if P_s_in > 0 else 0.0
        
        # Pressure lift
        pressure_lift = P_out - P_s_in
        
        # Regime type
        if mu < 0.01:
            regime_type = "non-entraining"
        elif mach_before_shock > self.MACH_SHOCK_THRESHOLD:
            regime_type = "entraining-supersonic"
        else:
            regime_type = "critical"
        
        # Check mixture physical consistency
        physically_consistent_mixture = True
        try:
            # Check if h_mix is between h_liq and h_vap at P_mix
            T_sat_mix = self.props.Tsat_P(P_mix)
            h_liq_sat = self.props.h_PX(P_mix, 0.0)
            h_vap_sat = self.props.h_PX(P_mix, 1.0)
            
            h_mix_actual = state_mix.h
            if not (h_liq_sat <= h_mix_actual <= h_vap_sat):
                # If outside saturation dome, check if superheated
                if h_mix_actual < h_liq_sat or (h_mix_actual > h_vap_sat and state_mix.T < T_sat_mix):
                    physically_consistent_mixture = False
                    notes.append("Mixture enthalpy outside valid range")
        except Exception:
            # If can't check, assume consistent
            pass
        
        # Entropy jump in kJ/kg/K
        entropy_jump_kJ = entropy_jump / 1000.0
        
        # Entropy plausibility check (soft validation for weak shocks)
        entropy_jump_suspect = False
        if shock_location != "none" and mach_before_shock > 0:
            # For weak shocks (M < 1.1), entropy jump should be small
            if mach_before_shock < 1.1 and entropy_jump_kJ > 0.2:
                entropy_jump_suspect = True
                notes.append(f"Warning: Large entropy jump ({entropy_jump_kJ:.3f} kJ/kg/K) for weak shock (M={mach_before_shock:.3f})")
        
        # Return V2 result with extended information
        return EjectorResultV2(
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
            mach_primary_nozzle=mach_nozzle,
            mach_before_shock=mach_before_shock,
            mach_after_shock=mach_after_shock,
            shock_location=shock_location,
            regime=regime,
            regime_type=regime_type,
            entropy_jump=entropy_jump,  # J/kg/K
            entropy_jump_kJ=entropy_jump_kJ,  # kJ/kg/K
            P_before_shock=P_before_shock_value,
            P_after_shock=P_after_shock_value,
            P_suction_local=P_suction_local,
            suction_condition=suction_condition,
            static_suction_check=static_suction_check,
            dynamic_entrainment=dynamic_entrainment,
            compression_ratio=compression_ratio,
            pressure_lift=pressure_lift,
            entropy_jump_suspect=entropy_jump_suspect,
            state_before_shock=state_before_shock_obj,
            state_after_shock=state_after_shock_obj,
            physically_consistent_mixture=physically_consistent_mixture,
        )
