"""
System Cycle Controller

Orchestrates interaction between UI and system cycle model.
"""

from typing import Dict, Optional
from .model import SystemCycleModel, CycleResult


class SystemCycleController:
    """Controller for complete system cycle simulation."""
    
    def __init__(self):
        """Initialize controller with model."""
        self.model = SystemCycleModel()
        self.last_result: Optional[CycleResult] = None
    
    def solve(self, params: Dict) -> CycleResult:
        """
        Solve cycle with given parameters from UI.
        
        Args:
            params: Dictionary of simulation parameters
            
        Returns:
            CycleResult object
        """
        # Extract parameters with defaults
        result = self.model.solve_cycle(
            T_gen=params.get('T_gen', 373.15),
            T_evap=params.get('T_evap', 283.15),
            T_cond=params.get('T_cond', 308.15),
            m_dot_p=params.get('m_dot_p', 0.020),
            Q_evap_target=params.get('Q_evap_target', None),  # If set, inverse dimensioning
            eta_pump=params.get('eta_pump', 0.7),
            eta_nozzle=params.get('eta_nozzle', 0.85),
            eta_diffuser=params.get('eta_diffuser', 0.85),
            eta_mixing=params.get('eta_mixing', 1.0),
            K_gen=params.get('K_gen', 250.0),
            A_gen=params.get('A_gen', 6.0),
            T_htf_in=params.get('T_htf_in', 403.15),
            T_htf_out=params.get('T_htf_out', 383.15),
            K_cond=params.get('K_cond', 15.0),
            A_cond=params.get('A_cond', 20.0),
            T_air_in=params.get('T_air_in', 300.15),
            T_air_out=params.get('T_air_out', 305.15),
            K_evap=params.get('K_evap', 800.0),
            A_evap=params.get('A_evap', 6.0),
            T_cold_in=params.get('T_cold_in', 295.15),
            T_cold_out=params.get('T_cold_out', 289.15),
            use_ejector_v2=params.get('use_ejector_v2', True),
        )
        
        self.last_result = result
        return result
    
    def get_last_result(self) -> Optional[CycleResult]:
        """Get last simulation result."""
        return self.last_result
    
    def get_default_params(self) -> Dict:
        """Get default parameter set for UI initialization."""
        return {
            'T_gen': 100.0,     # °C
            'T_evap': 10.0,     # °C
            'T_cond': 35.0,     # °C
            'm_dot_p': 0.020,   # kg/s
            'eta_pump': 0.7,
            'eta_nozzle': 0.85,
            'eta_diffuser': 0.85,
            'eta_mixing': 1.0,
            'K_gen': 250.0,     # W/m²K
            'A_gen': 6.0,       # m²
            'T_htf_in': 130.0,  # °C
            'T_htf_out': 110.0, # °C
            'K_cond': 15.0,     # W/m²K
            'A_cond': 20.0,     # m²
            'T_air_in': 27.0,   # °C
            'T_air_out': 32.0,  # °C
            'K_evap': 800.0,    # W/m²K
            'A_evap': 6.0,      # m²
            'T_cold_in': 22.0,  # °C
            'T_cold_out': 16.0, # °C
            'use_ejector_v2': True,
        }
