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
    
    Cycle numbering:
        1: Condenser outlet (liquid, low P)
        2: Pump outlet (liquid, high P)
        3: Generator outlet (vapor, high P, high T)
        4: Ejector primary nozzle exit
        5: Evaporator outlet (vapor, low P)
        6: Ejector secondary inlet
        7: Ejector mixing/shock zone
        8: Ejector outlet / Condenser inlet
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
        
        Returns:
            CycleResult object with states, metrics, flags, and notes
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
            
            # ===== STATE 1: Condenser outlet (saturated liquid) =====
            state_1 = ThermoState()
            state_1.update_from_PX(P_cond, 0.0)  # Saturated liquid
            result.states[1] = state_1
            
            # ===== STATE 2: Pump outlet =====
            pump_result = self.pump_ctrl.solve(
                state_in=state_1,
                P_out=P_gen,
                eta_is=eta_pump,
                m_dot=m_dot_p,
            )
            state_2 = pump_result.state_out
            result.states[2] = state_2
            result.component_results['pump'] = pump_result
            
            # ===== STATE 3: Generator outlet (saturated vapor) =====
            # For now, assume saturated vapor at P_gen
            # TODO: Use generator model with K, A, m_dot_htf
            state_3 = ThermoState()
            state_3.update_from_PX(P_gen, 1.0)  # Saturated vapor
            result.states[3] = state_3
            
            # Calculate generator heat duty
            Q_gen = m_dot_p * (state_3.h - state_2.h)
            
            # ===== STATE 5: Evaporator outlet (saturated vapor) =====
            state_5 = ThermoState()
            state_5.update_from_PX(P_evap, 1.0)  # Saturated vapor
            result.states[5] = state_5
            
            # ===== EJECTOR: States 3,5 → 8 =====
            ejector_result = self.ejector_ctrl.solve(
                state_p_in=state_3,
                state_s_in=state_5,
                P_out=P_cond,
                m_dot_p=m_dot_p,
                eta_nozzle=eta_nozzle,
                eta_diffuser=eta_diffuser,
                eta_mixing=eta_mixing,
            )
            
            state_4 = ejector_result.state_p_noz  # Primary nozzle exit
            state_6 = ejector_result.state_s_adj  # Secondary adjusted
            state_7 = ejector_result.state_mix    # Mixing zone
            state_8 = ejector_result.state_out    # Ejector outlet
            
            result.states[4] = state_4
            result.states[6] = state_6
            result.states[7] = state_7
            result.states[8] = state_8
            result.component_results['ejector'] = ejector_result
            
            mu = ejector_result.mu
            m_dot_s = ejector_result.m_dot_s
            m_dot_total = m_dot_p + m_dot_s
            
            # ===== CONDENSER HEAT DUTY =====
            Q_cond = m_dot_total * (state_8.h - state_1.h)
            
            # ===== EVAPORATOR HEAT DUTY =====
            # State before evaporator: expansion valve from state_1
            # Assume isenthalpic expansion
            h_before_evap = state_1.h
            Q_evap = m_dot_s * (state_5.h - h_before_evap)
            
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
            result.flags['mismatch_active'] = False  # TODO: check thermal mismatch
            
            # Check for warnings from ejector
            if hasattr(ejector_result, 'flags'):
                for flag_name, flag_value in ejector_result.flags.items():
                    if flag_value:
                        result.flags[f'ejector_{flag_name}'] = True
                        notes.append(f"Ejector: {flag_name}")
            
            # Check COP sanity
            if COP < 0.1:
                result.flags['low_cop'] = True
                notes.append(f"Warning: Very low COP ({COP:.3f})")
            
            if mu < 0.01:
                result.flags['low_entrainment'] = True
                notes.append(f"Warning: Low entrainment ratio ({mu:.4f})")
            
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
