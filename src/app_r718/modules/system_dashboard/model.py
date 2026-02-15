"""
System Cycle Model

Orchestrates all components to simulate the complete R718 ejector refrigeration cycle.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import numpy as np

from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.pump import PumpController
from app_r718.modules.generator import GeneratorController
from app_r718.modules.ejector import EjectorController
from app_r718.modules.condenser import CondenserController
from app_r718.modules.expansion_valve import ExpansionValveController
from app_r718.modules.evaporator import EvaporatorController


@dataclass
class CycleResult:
    """
    Complete cycle simulation result.
    
    Attributes:
        states: Dictionary of thermodynamic states at each point (1-8)
        metrics: Key performance indicators (COP, Q_evap, Q_gen, mu, etc.)
        flags: Diagnostic flags (mismatch, errors, warnings)
        notes: Descriptive notes from simulation
        component_results: Individual component results for detailed analysis
    """
    states: Dict[int, ThermoState] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    notes: str = ""
    component_results: Dict[str, any] = field(default_factory=dict)


class SystemCycleModel:
    """
    Complete R718 ejector refrigeration cycle model.
    
    CONVENTION OFFICIELLE (context.md lines 230-237) - NE JAMAIS MODIFIER:
        1: Sortie condenseur (liquide saturé, P_cond, x=0) - POINT DE BIFURCATION
           → flows to expansion valve (1→2) AND to pump (1→7)
        2: Sortie détendeur (diphasique, P_evap, h2=h1, x2<1) - entrée évaporateur
        3: Sortie évaporateur (vapeur saturée, P_evap, x3≈1) - ENTRÉE SECONDAIRE éjecteur
        4: Chambre de mélange éjecteur (état après mélange primaire 8 + secondaire 3)
        5: Sortie diffuseur éjecteur (P_cond après compression) → vers condenseur
        6: Sortie condenseur (liquide saturé, P_cond, x6=0) → retour vers 1
        7: Sortie pompe (liquide comprimé, P_gen) → vers chaudière
        8: Sortie chaudière/entrée tuyère (vapeur saturée, P_gen, x8≈1) - ENTRÉE PRIMAIRE éjecteur
    
    Chemins thermodynamiques:
        Cycle froid (BP): 1 → 2 (détendeur) → 3 (évaporateur) → 4 (éjecteur secondaire)
        Cycle chaud (HP): 1 → 7 (pompe) → 8 (chaudière) → 4 (tuyère éjecteur)
        Éjecteur: 8→4 (tuyère primaire), 3→4 (aspiration secondaire), 4→5 (diffuseur)
        Condensation: 5 → 6 (condenseur) → 1 (bouclage)
    """
    
    def __init__(self):
        """Initialize system model with component controllers."""
        self.props = get_props_service()
        
        # Component controllers
        self.pump_ctrl = PumpController()
        self.generator_ctrl = GeneratorController()
        self.ejector_ctrl = EjectorController(mode="V2")  # Default V2
        self.condenser_ctrl = CondenserController()
        self.expansion_valve_ctrl = ExpansionValveController()
        self.evaporator_ctrl = EvaporatorController()
    
    def solve_cycle(
        self,
        # Operating conditions
        T_gen: float = 373.15,      # Generator temperature [K]
        T_evap: float = 283.15,     # Evaporator temperature [K]
        T_cond: float = 308.15,     # Condenser temperature [K]
        m_dot_p: float = 0.020,     # Primary mass flow [kg/s]
        
        # Dimensioning mode (inverse)
        Q_evap_target: float = None,  # Target cooling power [kW] - if set, calculates m_dot_p
        
        # Efficiencies
        eta_pump: float = 0.7,
        eta_nozzle: float = 0.85,
        eta_diffuser: float = 0.85,
        eta_mixing: float = 1.0,
        
        # Heat exchanger sizing (K = overall heat transfer coefficient)
        K_gen: float = 250.0,       # [W/m²K]
        A_gen: float = 6.0,         # [m²]
        T_htf_in: float = 403.15,   # HTF inlet temperature [K]
        T_htf_out: float = 383.15,  # HTF outlet temperature [K]
        
        K_cond: float = 15.0,       # [W/m²K]
        A_cond: float = 20.0,       # [m²]
        T_air_in: float = 300.15,   # Air inlet temperature [K]
        T_air_out: float = 305.15,  # Air outlet temperature [K]
        
        K_evap: float = 800.0,      # [W/m²K]
        A_evap: float = 6.0,        # [m²]
        T_cold_in: float = 295.15,  # Cold fluid inlet [K]
        T_cold_out: float = 289.15, # Cold fluid outlet [K]
        
        # Options
        use_ejector_v2: bool = True,
        
    ) -> CycleResult:
        """
        Solve complete cycle with given parameters.
        
        If Q_evap_target is provided, performs inverse dimensioning to find m_dot_p.
        
        Returns:
            CycleResult object with states, metrics, flags, and notes
        """
        # If inverse dimensioning mode
        if Q_evap_target is not None and Q_evap_target > 0:
            return self._solve_cycle_inverse(
                Q_evap_target=Q_evap_target,
                T_gen=T_gen,
                T_evap=T_evap,
                T_cond=T_cond,
                eta_pump=eta_pump,
                eta_nozzle=eta_nozzle,
                eta_diffuser=eta_diffuser,
                eta_mixing=eta_mixing,
                use_ejector_v2=use_ejector_v2,
            )
        
        # Direct mode (forward calculation)
        return self._solve_cycle_direct(
            T_gen=T_gen,
            T_evap=T_evap,
            T_cond=T_cond,
            m_dot_p=m_dot_p,
            eta_pump=eta_pump,
            eta_nozzle=eta_nozzle,
            eta_diffuser=eta_diffuser,
            eta_mixing=eta_mixing,
            use_ejector_v2=use_ejector_v2,
        )
    
    def _solve_cycle_inverse(
        self,
        Q_evap_target: float,  # kW
        T_gen: float,
        T_evap: float,
        T_cond: float,
        eta_pump: float,
        eta_nozzle: float,
        eta_diffuser: float,
        eta_mixing: float,
        use_ejector_v2: bool,
    ) -> CycleResult:
        """
        Inverse dimensioning: find m_dot_p to achieve target Q_evap.
        
        Uses iterative method to converge on correct mass flow rate.
        """
        # Convert kW to W
        Q_evap_target_W = Q_evap_target * 1000.0
        
        # Initial guess based on typical enthalpy difference
        # Q_evap = m_dot_s * (h_evap_out - h_evap_in)
        # Estimate: Δh ≈ 2500 kJ/kg for water evaporation at 10°C
        # m_dot_s ≈ Q / Δh ≈ 12000 / 2500000 ≈ 0.005 kg/s
        # With μ ≈ 1.0, m_dot_p ≈ m_dot_s ≈ 0.005
        m_dot_p_guess = Q_evap_target_W / 2500000.0
        
        # Iterative solver
        max_iterations = 20
        tolerance = 0.01  # 1% tolerance on Q_evap
        
        for iteration in range(max_iterations):
            # Solve cycle with current guess
            result = self._solve_cycle_direct(
                T_gen=T_gen,
                T_evap=T_evap,
                T_cond=T_cond,
                m_dot_p=m_dot_p_guess,
                eta_pump=eta_pump,
                eta_nozzle=eta_nozzle,
                eta_diffuser=eta_diffuser,
                eta_mixing=eta_mixing,
                use_ejector_v2=use_ejector_v2,
            )
            
            # Check convergence
            Q_evap_actual_kW = result.metrics.get('Q_evap', 0.0)
            Q_evap_actual_W = Q_evap_actual_kW * 1000.0
            
            error_relative = abs(Q_evap_actual_W - Q_evap_target_W) / Q_evap_target_W
            
            if error_relative < tolerance:
                # Converged!
                result.notes = f"Dimensionnement inverse convergé en {iteration+1} itérations (erreur: {error_relative*100:.2f}%)"
                return result
            
            # Update guess using proportional adjustment
            # m_dot_new = m_dot_old * (Q_target / Q_actual)
            if Q_evap_actual_W > 0:
                m_dot_p_guess = m_dot_p_guess * (Q_evap_target_W / Q_evap_actual_W)
            else:
                # If no cooling power, increase flow
                m_dot_p_guess *= 1.5
            
            # Safety bounds
            m_dot_p_guess = max(0.001, min(0.1, m_dot_p_guess))
        
        # Did not converge
        result.flags['dimensioning_not_converged'] = True
        result.notes = f"Dimensionnement inverse n'a pas convergé après {max_iterations} itérations. Q_evap = {Q_evap_actual_kW:.2f} kW (cible: {Q_evap_target:.2f} kW)"
        return result
    
    def _solve_cycle_direct(
        self,
        T_gen: float,
        T_evap: float,
        T_cond: float,
        m_dot_p: float,
        eta_pump: float,
        eta_nozzle: float,
        eta_diffuser: float,
        eta_mixing: float,
        use_ejector_v2: bool,
    ) -> CycleResult:
        """
        Solve cycle with fixed m_dot_p (direct simulation).
        
        État sequence (CONVENTION OFFICIELLE):
            1 → 2 → 3 → 4 → 5 → 6 → 1 (cycle principal)
            1 → 7 → 8 → 4 (cycle chaud)
        """
        result = CycleResult()
        notes = []
        
        try:
            # Set ejector mode
            if use_ejector_v2:
                self.ejector_ctrl.set_mode("V2")
            else:
                self.ejector_ctrl.set_mode("V1")
            
            # ===== PRESSURES FROM SATURATION =====
            P_gen = self.props.Psat_T(T_gen)
            P_evap = self.props.Psat_T(T_evap)
            P_cond = self.props.Psat_T(T_cond)
            
            # ===== STATE 1: Sortie condenseur (saturated liquid) - BIFURCATION =====
            state_1 = ThermoState()
            state_1.update_from_PX(P_cond, 0.0)  # Liquide saturé
            result.states[1] = state_1
            
            # ===== STATE 2: Sortie détendeur (entrée évaporateur) =====
            # Détente isenthalpique from state 1 to P_evap: 1→2
            valve_result = self.expansion_valve_ctrl.solve(
                state1=state_1,
                P_out=P_evap,
            )
            state_2 = valve_result.state2
            result.states[2] = state_2
            result.component_results['expansion_valve'] = valve_result
            
            # Verify state 2 is two-phase (quality < 1)
            if state_2.x is None or state_2.x >= 1.0:
                notes.append(f"Warning: État 2 not diphasique (x={state_2.x})")
            
            # Verify isenthalpic: h2 = h1
            h_diff = abs(state_2.h - state_1.h)
            if h_diff > 100.0:  # Tolerance 100 J/kg
                notes.append(f"Warning: h2 ({state_2.h:.1f}) != h1 ({state_1.h:.1f}), Δh={h_diff:.1f} J/kg")
            
            # ===== STATE 3: Sortie évaporateur (saturated vapor) =====
            # Évaporation complète to saturated vapor: 2→3
            state_3 = ThermoState()
            state_3.update_from_PX(P_evap, 1.0)  # Vapeur saturée
            result.states[3] = state_3
            
            # ===== STATE 7: Sortie pompe =====
            # Compression du liquide from state 1 to P_gen: 1→7
            pump_result = self.pump_ctrl.solve(
                state_in=state_1,
                P_out=P_gen,
                eta_is=eta_pump,
                m_dot=m_dot_p,
            )
            state_7 = pump_result.state_out
            result.states[7] = state_7
            result.component_results['pump'] = pump_result
            
            # ===== STATE 8: Sortie chaudière/entrée tuyère (saturated vapor) =====
            # Chauffage + vaporisation: 7→8
            # Assume saturated vapor at P_gen
            state_8 = ThermoState()
            state_8.update_from_PX(P_gen, 1.0)  # Vapeur saturée
            result.states[8] = state_8
            
            # Calculate generator heat duty
            Q_gen = m_dot_p * (state_8.h - state_7.h)
            
            # ===== EJECTOR: États 8 (primary), 3 (secondary) → 4 (mix), 5 (diffuser) =====
            ejector_result = self.ejector_ctrl.solve(
                state_p_in=state_8,        # Primary: sortie chaudière
                state_s_in=state_3,        # Secondary: sortie évaporateur
                P_out=P_cond,
                m_dot_p=m_dot_p,
                eta_nozzle=eta_nozzle,
                eta_diffuser=eta_diffuser,
                eta_mixing=eta_mixing,
            )
            
            # Extract ejector states
            # NOTE: ejector_result.state_mix corresponds to état 4 (chambre de mélange)
            # NOTE: ejector_result.state_out corresponds to état 5 (sortie diffuseur)
            
            # État 4: mixing chamber (if available, otherwise skip)
            if hasattr(ejector_result, 'state_mix') and ejector_result.state_mix is not None:
                state_4 = ejector_result.state_mix
                result.states[4] = state_4
            else:
                # If not explicitly available, we'll skip state 4 for now
                # (some ejector models don't expose the mix state explicitly)
                pass
            
            # État 5: diffuser outlet
            state_5 = ejector_result.state_out
            result.states[5] = state_5
            result.component_results['ejector'] = ejector_result
            
            mu = ejector_result.mu
            m_dot_s = ejector_result.m_dot_s
            m_dot_total = m_dot_p + m_dot_s
            
            # ===== STATE 6: Sortie condenseur =====
            # After condensation 5→6, returns to state 1 conditions
            # State 6 is saturated liquid at P_cond (same as state 1)
            state_6 = ThermoState()
            state_6.update_from_PX(P_cond, 0.0)  # Liquide saturé
            result.states[6] = state_6
            
            # ===== CONDENSER HEAT DUTY =====
            # Q_cond = m_dot_total * (h5 - h6)
            Q_cond = m_dot_total * (state_5.h - state_6.h)
            
            # ===== EVAPORATOR HEAT DUTY =====
            # Q_evap = m_dot_s * (h3 - h2)
            Q_evap = m_dot_s * (state_3.h - state_2.h)
            
            # ===== METRICS =====
            # COP = Q_evap / (W_pump + Q_gen)
            W_pump = pump_result.W_pump
            COP = Q_evap / (W_pump + Q_gen) if (W_pump + Q_gen) > 0 else 0.0
            
            result.metrics = {
                'COP': COP,
                'Q_evap': Q_evap / 1000.0,  # kW
                'Q_gen': Q_gen / 1000.0,    # kW
                'Q_cond': Q_cond / 1000.0,  # kW
                'mu': mu,
                'W_pump': W_pump / 1000.0,  # kW
                'm_dot_p': m_dot_p,
                'm_dot_s': m_dot_s,
                'm_dot_total': m_dot_total,
            }
            
            # ===== FLAGS AND DIAGNOSTICS =====
            result.flags['success'] = True
            result.flags['mismatch_active'] = False
            
            # Check for warnings from ejector
            if hasattr(ejector_result, 'flags'):
                for flag_name, flag_value in ejector_result.flags.items():
                    if flag_value:
                        result.flags[f'ejector_{flag_name}'] = True
                        notes.append(f"Ejector: {flag_name}")
            
            # Check COP sanity
            if COP < 0.1:
                result.flags['low_cop'] = True
                notes.append(f"Warning: COP très faible ({COP:.3f})")
            
            if mu < 0.01:
                result.flags['low_entrainment'] = True
                notes.append(f"Warning: Taux d'entraînement faible ({mu:.4f})")
            
            result.notes = "; ".join(notes) if notes else "Cycle converged successfully"
            
        except Exception as e:
            result.flags['error'] = True
            result.notes = f"Cycle solve error: {str(e)}"
            # Fill with dummy metrics to avoid crashes
            result.metrics = {
                'COP': 0.0,
                'Q_evap': 0.0,
                'Q_gen': 0.0,
                'Q_cond': 0.0,
                'mu': 0.0,
                'W_pump': 0.0,
                'm_dot_p': m_dot_p,
                'm_dot_s': 0.0,
                'm_dot_total': m_dot_p,
            }
        
        return result
