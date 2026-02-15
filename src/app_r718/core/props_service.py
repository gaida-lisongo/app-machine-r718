"""
PropsService - Singleton wrapper for CoolProp

This service centralizes all thermodynamic property calculations using CoolProp.
Implements singleton pattern to ensure single instance across application.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-14
"""

import logging
from typing import Optional
from CoolProp.CoolProp import PropsSI


class PropsService:
    """
    Singleton service for thermodynamic property calculations via CoolProp.
    
    All property calculations must go through this service to ensure:
    - Consistent error handling
    - Centralized logging
    - Single point of thermodynamic computation
    
    Properties are calculated for water (R718) by default.
    """
    
    _instance: Optional['PropsService'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'PropsService':
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(PropsService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger only once."""
        if not PropsService._initialized:
            self.logger = logging.getLogger(__name__)
            self.fluid = "Water"
            PropsService._initialized = True
    
    def _safe_call(self, output: str, input1_name: str, input1_val: float,
                   input2_name: str, input2_val: float) -> float:
        """
        Safe wrapper for CoolProp PropsSI calls with error handling.
        
        Args:
            output: Output property name (e.g., 'H', 'S', 'D')
            input1_name: First input property name (e.g., 'P', 'T')
            input1_val: First input value
            input2_name: Second input property name
            input2_val: Second input value
            
        Returns:
            Calculated property value
            
        Raises:
            ValueError: If CoolProp calculation fails or inputs are invalid
        """
        try:
            result = PropsSI(output, input1_name, input1_val,
                           input2_name, input2_val, self.fluid)
            return result
        except Exception as e:
            error_msg = (
                f"CoolProp error: {output} | "
                f"{input1_name}={input1_val:.2e}, {input2_name}={input2_val:.2e} | "
                f"Error: {str(e)}"
            )
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    # ========== Enthalpy calculations ==========
    
    def h_PT(self, P: float, T: float) -> float:
        """
        Calculate specific enthalpy from pressure and temperature.
        
        Args:
            P: Pressure [Pa]
            T: Temperature [K]
            
        Returns:
            Specific enthalpy [J/kg]
        """
        return self._safe_call('H', 'P', P, 'T', T)
    
    def h_PS(self, P: float, s: float) -> float:
        """
        Calculate specific enthalpy from pressure and entropy.
        
        Args:
            P: Pressure [Pa]
            s: Specific entropy [J/kg/K]
            
        Returns:
            Specific enthalpy [J/kg]
        """
        return self._safe_call('H', 'P', P, 'S', s)
    
    def h_PX(self, P: float, x: float) -> float:
        """
        Calculate specific enthalpy from pressure and quality.
        
        Args:
            P: Pressure [Pa]
            x: Quality [-] (0 = saturated liquid, 1 = saturated vapor)
            
        Returns:
            Specific enthalpy [J/kg]
        """
        return self._safe_call('H', 'P', P, 'Q', x)
    
    # ========== Entropy calculations ==========
    
    def s_PT(self, P: float, T: float) -> float:
        """
        Calculate specific entropy from pressure and temperature.
        
        Args:
            P: Pressure [Pa]
            T: Temperature [K]
            
        Returns:
            Specific entropy [J/kg/K]
        """
        return self._safe_call('S', 'P', P, 'T', T)
    
    def s_PH(self, P: float, h: float) -> float:
        """
        Calculate specific entropy from pressure and enthalpy.
        
        Args:
            P: Pressure [Pa]
            h: Specific enthalpy [J/kg]
            
        Returns:
            Specific entropy [J/kg/K]
        """
        return self._safe_call('S', 'P', P, 'H', h)
    
    def s_PX(self, P: float, x: float) -> float:
        """
        Calculate specific entropy from pressure and quality.
        
        Args:
            P: Pressure [Pa]
            x: Quality [-]
            
        Returns:
            Specific entropy [J/kg/K]
        """
        return self._safe_call('S', 'P', P, 'Q', x)
    
    # ========== Density calculations ==========
    
    def rho_PT(self, P: float, T: float) -> float:
        """
        Calculate density from pressure and temperature.
        
        Args:
            P: Pressure [Pa]
            T: Temperature [K]
            
        Returns:
            Density [kg/m³]
        """
        return self._safe_call('D', 'P', P, 'T', T)
    
    def rho_PH(self, P: float, h: float) -> float:
        """
        Calculate density from pressure and enthalpy.
        
        Args:
            P: Pressure [Pa]
            h: Specific enthalpy [J/kg]
            
        Returns:
            Density [kg/m³]
        """
        return self._safe_call('D', 'P', P, 'H', h)
    
    # ========== Temperature calculations ==========
    
    def T_PH(self, P: float, h: float) -> float:
        """
        Calculate temperature from pressure and enthalpy.
        
        Args:
            P: Pressure [Pa]
            h: Specific enthalpy [J/kg]
            
        Returns:
            Temperature [K]
        """
        return self._safe_call('T', 'P', P, 'H', h)
    
    def T_PS(self, P: float, s: float) -> float:
        """
        Calculate temperature from pressure and entropy.
        
        Args:
            P: Pressure [Pa]
            s: Specific entropy [J/kg/K]
            
        Returns:
            Temperature [K]
        """
        return self._safe_call('T', 'P', P, 'S', s)
    
    # ========== Saturation properties ==========
    
    def Tsat_P(self, P: float) -> float:
        """
        Calculate saturation temperature at given pressure.
        
        Args:
            P: Pressure [Pa]
            
        Returns:
            Saturation temperature [K]
        """
        return self._safe_call('T', 'P', P, 'Q', 0)
    
    def Psat_T(self, T: float) -> float:
        """
        Calculate saturation pressure at given temperature.
        
        Args:
            T: Temperature [K]
            
        Returns:
            Saturation pressure [Pa]
        """
        try:
            result = PropsSI('P', 'T', T, 'Q', 0, self.fluid)
            return result
        except Exception as e:
            error_msg = f"CoolProp error: Psat(T={T:.2f}K) | Error: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def hl_P(self, P: float) -> float:
        """
        Calculate saturated liquid enthalpy at given pressure.
        
        Args:
            P: Pressure [Pa]
            
        Returns:
            Saturated liquid enthalpy [J/kg]
        """
        return self._safe_call('H', 'P', P, 'Q', 0)
    
    def hv_P(self, P: float) -> float:
        """
        Calculate saturated vapor enthalpy at given pressure.
        
        Args:
            P: Pressure [Pa]
            
        Returns:
            Saturated vapor enthalpy [J/kg]
        """
        return self._safe_call('H', 'P', P, 'Q', 1)
    
    def sl_P(self, P: float) -> float:
        """
        Calculate saturated liquid entropy at given pressure.
        
        Args:
            P: Pressure [Pa]
            
        Returns:
            Saturated liquid entropy [J/kg/K]
        """
        return self._safe_call('S', 'P', P, 'Q', 0)
    
    def sv_P(self, P: float) -> float:
        """
        Calculate saturated vapor entropy at given pressure.
        
        Args:
            P: Pressure [Pa]
            
        Returns:
            Saturated vapor entropy [J/kg/K]
        """
        return self._safe_call('S', 'P', P, 'Q', 1)
    
    # ========== Quality calculation ==========
    
    def x_PH(self, P: float, h: float) -> float:
        """
        Calculate quality from pressure and enthalpy.
        
        Args:
            P: Pressure [Pa]
            h: Specific enthalpy [J/kg]
            
        Returns:
            Quality [-] (only valid in two-phase region)
        """
        return self._safe_call('Q', 'P', P, 'H', h)


# Global singleton instance accessor
def get_props_service() -> PropsService:
    """
    Get the global PropsService singleton instance.
    
    Returns:
        PropsService singleton instance
    """
    return PropsService()
