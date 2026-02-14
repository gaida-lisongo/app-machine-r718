"""
ThermoState - Thermodynamic state representation

This module defines the ThermoState class for representing and manipulating
thermodynamic states of water (R718) using CoolProp.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-14
"""

from typing import Optional, Dict, Any
from src.core.props_service import get_props_service


class ThermoState:
    """
    Represents a complete thermodynamic state of water (R718).
    
    All properties are computed using CoolProp via PropsService.
    The state is immutable once set - use update methods to modify.
    
    Attributes:
        fluid (str): Working fluid name (default: "Water")
        P (float): Pressure [Pa]
        T (float): Temperature [K]
        h (float): Specific enthalpy [J/kg]
        s (float): Specific entropy [J/kg/K]
        x (Optional[float]): Quality [-], None if single-phase
        rho (float): Density [kg/m³]
    """
    
    def __init__(self, fluid: str = "Water"):
        """
        Initialize an empty thermodynamic state.
        
        Args:
            fluid: Working fluid name (default: "Water")
        """
        self.fluid: str = fluid
        self.P: Optional[float] = None
        self.T: Optional[float] = None
        self.h: Optional[float] = None
        self.s: Optional[float] = None
        self.x: Optional[float] = None
        self.rho: Optional[float] = None
        self._props = get_props_service()
    
    def _validate_pressure(self, P: float) -> None:
        """
        Validate pressure is physically meaningful.
        
        Args:
            P: Pressure [Pa]
            
        Raises:
            ValueError: If pressure is non-positive
        """
        if P <= 0:
            raise ValueError(f"Pressure must be positive, got P={P:.2e} Pa")
    
    def _validate_temperature(self, T: float) -> None:
        """
        Validate temperature is physically meaningful.
        
        Args:
            T: Temperature [K]
            
        Raises:
            ValueError: If temperature is below absolute zero
        """
        if T <= 0:
            raise ValueError(f"Temperature must be positive, got T={T:.2f} K")
    
    def _validate_quality(self, x: float) -> None:
        """
        Validate quality is in valid range.
        
        Args:
            x: Quality [-]
            
        Raises:
            ValueError: If quality is outside [0, 1]
        """
        if not (0.0 <= x <= 1.0):
            raise ValueError(f"Quality must be in [0, 1], got x={x:.4f}")
    
    def update_from_PT(self, P: float, T: float) -> None:
        """
        Update state from pressure and temperature.
        
        Computes all other properties (h, s, rho) using CoolProp.
        Quality is set to None (assumed single-phase).
        
        Args:
            P: Pressure [Pa]
            T: Temperature [K]
            
        Raises:
            ValueError: If inputs are invalid or state cannot be computed
        """
        self._validate_pressure(P)
        self._validate_temperature(T)
        
        try:
            # Compute properties
            h = self._props.h_PT(P, T)
            s = self._props.s_PT(P, T)
            rho = self._props.rho_PT(P, T)
            
            # Attempt to determine if two-phase (will fail if superheated/subcooled)
            try:
                x = self._props.x_PH(P, h)
                if 0.0 <= x <= 1.0:
                    self.x = x
                else:
                    self.x = None
            except:
                self.x = None
            
            # Update state
            self.P = P
            self.T = T
            self.h = h
            self.s = s
            self.rho = rho
            
        except Exception as e:
            raise ValueError(
                f"Failed to compute state from P={P:.2e} Pa, T={T:.2f} K: {str(e)}"
            ) from e
    
    def update_from_PH(self, P: float, h: float) -> None:
        """
        Update state from pressure and enthalpy.
        
        Computes all other properties (T, s, rho, x) using CoolProp.
        
        Args:
            P: Pressure [Pa]
            h: Specific enthalpy [J/kg]
            
        Raises:
            ValueError: If inputs are invalid or state cannot be computed
        """
        self._validate_pressure(P)
        
        try:
            # Compute properties
            T = self._props.T_PH(P, h)
            s = self._props.s_PH(P, h)
            rho = self._props.rho_PH(P, h)
            
            # Determine quality (if two-phase)
            try:
                x = self._props.x_PH(P, h)
                if 0.0 <= x <= 1.0:
                    self.x = x
                else:
                    self.x = None
            except:
                self.x = None
            
            # Update state
            self.P = P
            self.T = T
            self.h = h
            self.s = s
            self.rho = rho
            
        except Exception as e:
            raise ValueError(
                f"Failed to compute state from P={P:.2e} Pa, h={h:.2e} J/kg: {str(e)}"
            ) from e
    
    def update_from_PS(self, P: float, s: float) -> None:
        """
        Update state from pressure and entropy.
        
        Computes all other properties (T, h, rho, x) using CoolProp.
        
        Args:
            P: Pressure [Pa]
            s: Specific entropy [J/kg/K]
            
        Raises:
            ValueError: If inputs are invalid or state cannot be computed
        """
        self._validate_pressure(P)
        
        try:
            # Compute properties
            T = self._props.T_PS(P, s)
            h = self._props.h_PS(P, s)
            rho = self._props.rho_PH(P, h)
            
            # Determine quality (if two-phase)
            try:
                x = self._props.x_PH(P, h)
                if 0.0 <= x <= 1.0:
                    self.x = x
                else:
                    self.x = None
            except:
                self.x = None
            
            # Update state
            self.P = P
            self.T = T
            self.h = h
            self.s = s
            self.rho = rho
            
        except Exception as e:
            raise ValueError(
                f"Failed to compute state from P={P:.2e} Pa, s={s:.2e} J/kg/K: {str(e)}"
            ) from e
    
    def update_from_PX(self, P: float, x: float) -> None:
        """
        Update state from pressure and quality (two-phase only).
        
        Quality must be in [0, 1]. Computes all saturated properties.
        
        Args:
            P: Pressure [Pa]
            x: Quality [-] (0 = saturated liquid, 1 = saturated vapor)
            
        Raises:
            ValueError: If inputs are invalid or state cannot be computed
        """
        self._validate_pressure(P)
        self._validate_quality(x)
        
        try:
            # Compute properties at saturation
            h = self._props.h_PX(P, x)
            s = self._props.s_PX(P, x)
            T = self._props.Tsat_P(P)
            rho = self._props.rho_PH(P, h)
            
            # Update state
            self.P = P
            self.T = T
            self.h = h
            self.s = s
            self.x = x
            self.rho = rho
            
        except Exception as e:
            raise ValueError(
                f"Failed to compute state from P={P:.2e} Pa, x={x:.4f}: {str(e)}"
            ) from e
    
    def clone(self) -> 'ThermoState':
        """
        Create a deep copy of this thermodynamic state.
        
        Returns:
            New ThermoState instance with identical properties
        """
        new_state = ThermoState(fluid=self.fluid)
        new_state.P = self.P
        new_state.T = self.T
        new_state.h = self.h
        new_state.s = self.s
        new_state.x = self.x
        new_state.rho = self.rho
        return new_state
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert state to dictionary representation.
        
        Useful for serialization, logging, and debugging.
        
        Returns:
            Dictionary containing all state properties
        """
        return {
            'fluid': self.fluid,
            'P': self.P,
            'T': self.T,
            'h': self.h,
            's': self.s,
            'x': self.x,
            'rho': self.rho
        }
    
    def __repr__(self) -> str:
        """
        String representation of thermodynamic state.
        
        Returns:
            Formatted string with key properties
        """
        x_str = f"{self.x:.4f}" if self.x is not None else "None"
        return (
            f"ThermoState({self.fluid}): "
            f"P={self.P:.2e} Pa, T={self.T:.2f} K, "
            f"h={self.h:.2e} J/kg, s={self.s:.2e} J/kg/K, "
            f"x={x_str}, rho={self.rho:.2f} kg/m³"
        )
    
    def is_initialized(self) -> bool:
        """
        Check if state has been initialized with valid properties.
        
        Returns:
            True if P, T, h, s, and rho are all set
        """
        return all([
            self.P is not None,
            self.T is not None,
            self.h is not None,
            self.s is not None,
            self.rho is not None
        ])
