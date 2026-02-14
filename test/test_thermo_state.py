"""
Unit tests for ThermoState class

Tests verify thermodynamic consistency, property calculations,
and error handling for the ThermoState class.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-14
"""

import pytest
from src.core.thermo_state import ThermoState
from src.core.props_service import get_props_service


class TestThermoStateInitialization:
    """Test ThermoState initialization and basic properties."""
    
    def test_default_initialization(self):
        """Test default initialization creates empty state."""
        state = ThermoState()
        assert state.fluid == "Water"
        assert state.P is None
        assert state.T is None
        assert state.h is None
        assert state.s is None
        assert state.x is None
        assert state.rho is None
        assert not state.is_initialized()
    
    def test_custom_fluid(self):
        """Test initialization with custom fluid name."""
        state = ThermoState(fluid="CustomFluid")
        assert state.fluid == "CustomFluid"


class TestThermoStateFromPT:
    """Test state updates from pressure and temperature."""
    
    def test_superheated_vapor(self):
        """Test superheated vapor state (P=1 bar, T=150°C)."""
        state = ThermoState()
        P = 1e5  # 1 bar
        T = 150 + 273.15  # 150°C
        
        state.update_from_PT(P, T)
        
        assert state.P == P
        assert state.T == T
        assert state.h is not None
        assert state.s is not None
        assert state.rho is not None
        assert state.x is None  # Superheated, not two-phase
        assert state.is_initialized()
    
    def test_subcooled_liquid(self):
        """Test subcooled liquid state (P=10 bar, T=50°C)."""
        state = ThermoState()
        P = 10e5  # 10 bar
        T = 50 + 273.15  # 50°C
        
        state.update_from_PT(P, T)
        
        assert state.P == P
        assert state.T == T
        assert state.h is not None
        assert state.s is not None
        assert state.rho is not None
        assert state.rho > 900  # Liquid density check
        assert state.is_initialized()
    
    def test_invalid_pressure(self):
        """Test that negative pressure raises error."""
        state = ThermoState()
        with pytest.raises(ValueError, match="Pressure must be positive"):
            state.update_from_PT(-1000, 300)
    
    def test_invalid_temperature(self):
        """Test that negative temperature raises error."""
        state = ThermoState()
        with pytest.raises(ValueError, match="Temperature must be positive"):
            state.update_from_PT(1e5, -10)


class TestThermoStateFromPH:
    """Test state updates from pressure and enthalpy."""
    
    def test_from_ph_liquid(self):
        """Test state calculation from P and h for liquid."""
        state = ThermoState()
        props = get_props_service()
        
        P = 5e5  # 5 bar
        T = 100 + 273.15  # 100°C
        h = props.h_PT(P, T)
        
        state.update_from_PH(P, h)
        
        assert state.P == P
        assert abs(state.T - T) < 0.1  # Within 0.1 K
        assert abs(state.h - h) < 1.0  # Within 1 J/kg
        assert state.is_initialized()
    
    def test_from_ph_vapor(self):
        """Test state calculation from P and h for vapor."""
        state = ThermoState()
        props = get_props_service()
        
        P = 1e5  # 1 bar
        T = 200 + 273.15  # 200°C
        h = props.h_PT(P, T)
        
        state.update_from_PH(P, h)
        
        assert state.P == P
        assert abs(state.T - T) < 0.1  # Within 0.1 K
        assert state.is_initialized()
    
    def test_invalid_pressure_ph(self):
        """Test that invalid pressure raises error."""
        state = ThermoState()
        with pytest.raises(ValueError, match="Pressure must be positive"):
            state.update_from_PH(0, 1e6)


class TestThermoStateFromPS:
    """Test state updates from pressure and entropy."""
    
    def test_from_ps_consistency(self):
        """Test that P,S -> state is consistent with P,T."""
        state_pt = ThermoState()
        state_ps = ThermoState()
        
        P = 2e5  # 2 bar
        T = 150 + 273.15  # 150°C
        
        # Create state from P,T
        state_pt.update_from_PT(P, T)
        
        # Create state from P,s (using entropy from first state)
        state_ps.update_from_PS(P, state_pt.s)
        
        # Both states should be identical
        assert abs(state_ps.T - state_pt.T) < 0.1
        assert abs(state_ps.h - state_pt.h) < 10
        assert abs(state_ps.s - state_pt.s) < 0.1
    
    def test_isentropic_expansion(self):
        """Test isentropic expansion (constant entropy)."""
        state1 = ThermoState()
        state2 = ThermoState()
        
        # High pressure state
        P1 = 10e5  # 10 bar
        T1 = 200 + 273.15  # 200°C
        state1.update_from_PT(P1, T1)
        
        # Isentropic expansion to lower pressure
        P2 = 1e5  # 1 bar
        state2.update_from_PS(P2, state1.s)
        
        assert state2.P == P2
        assert abs(state2.s - state1.s) < 1.0  # Entropy preserved
        assert state2.h < state1.h  # Enthalpy decreases
        assert state2.T < state1.T  # Temperature decreases


class TestThermoStateFromPX:
    """Test state updates from pressure and quality (saturation)."""
    
    def test_saturated_liquid(self):
        """Test saturated liquid state (x=0)."""
        state = ThermoState()
        props = get_props_service()
        
        P = 1e5  # 1 bar
        x = 0.0  # Saturated liquid
        
        state.update_from_PX(P, x)
        
        assert state.P == P
        assert state.x == x
        assert abs(state.T - props.Tsat_P(P)) < 0.01
        assert abs(state.h - props.hl_P(P)) < 1.0
        assert abs(state.s - props.sl_P(P)) < 0.1
    
    def test_saturated_vapor(self):
        """Test saturated vapor state (x=1)."""
        state = ThermoState()
        props = get_props_service()
        
        P = 5e5  # 5 bar
        x = 1.0  # Saturated vapor
        
        state.update_from_PX(P, x)
        
        assert state.P == P
        assert state.x == x
        assert abs(state.T - props.Tsat_P(P)) < 0.01
        assert abs(state.h - props.hv_P(P)) < 1.0
        assert abs(state.s - props.sv_P(P)) < 0.1
    
    def test_two_phase_mixture(self):
        """Test two-phase mixture state (0 < x < 1)."""
        state = ThermoState()
        props = get_props_service()
        
        P = 2e5  # 2 bar
        x = 0.5  # 50% vapor
        
        state.update_from_PX(P, x)
        
        assert state.P == P
        assert state.x == x
        assert abs(state.T - props.Tsat_P(P)) < 0.01
        
        # Check enthalpy is between saturated liquid and vapor
        hl = props.hl_P(P)
        hv = props.hv_P(P)
        assert hl < state.h < hv
    
    def test_invalid_quality_negative(self):
        """Test that negative quality raises error."""
        state = ThermoState()
        with pytest.raises(ValueError, match="Quality must be in"):
            state.update_from_PX(1e5, -0.1)
    
    def test_invalid_quality_above_one(self):
        """Test that quality > 1 raises error."""
        state = ThermoState()
        with pytest.raises(ValueError, match="Quality must be in"):
            state.update_from_PX(1e5, 1.5)


class TestThermoStateUtilities:
    """Test utility methods (clone, to_dict, repr)."""
    
    def test_clone(self):
        """Test state cloning creates independent copy."""
        state1 = ThermoState()
        state1.update_from_PT(5e5, 373.15)
        
        state2 = state1.clone()
        
        # States should be equal
        assert state2.P == state1.P
        assert state2.T == state1.T
        assert state2.h == state1.h
        assert state2.s == state1.s
        assert state2.rho == state1.rho
        
        # But independent (modifying one doesn't affect other)
        state2.update_from_PT(1e5, 300)
        assert state2.P != state1.P
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = ThermoState()
        state.update_from_PT(1e5, 373.15)
        
        state_dict = state.to_dict()
        
        assert state_dict['fluid'] == "Water"
        assert state_dict['P'] == state.P
        assert state_dict['T'] == state.T
        assert state_dict['h'] == state.h
        assert state_dict['s'] == state.s
        assert state_dict['rho'] == state.rho
    
    def test_repr(self):
        """Test string representation."""
        state = ThermoState()
        state.update_from_PT(1e5, 373.15)
        
        repr_str = repr(state)
        
        assert "ThermoState" in repr_str
        assert "Water" in repr_str
        assert "Pa" in repr_str
        assert "K" in repr_str


class TestThermodynamicConsistency:
    """Test overall thermodynamic consistency."""
    
    def test_pt_ph_consistency(self):
        """Test that P,T and P,h give same state."""
        state_pt = ThermoState()
        state_ph = ThermoState()
        
        P = 3e5
        T = 200 + 273.15
        
        state_pt.update_from_PT(P, T)
        state_ph.update_from_PH(P, state_pt.h)
        
        assert abs(state_ph.T - state_pt.T) < 0.01
        assert abs(state_ph.s - state_pt.s) < 0.1
        assert abs(state_ph.rho - state_pt.rho) < 0.1
    
    def test_saturation_consistency(self):
        """Test saturation properties are consistent."""
        props = get_props_service()
        
        P = 2e5  # 2 bar
        Tsat = props.Tsat_P(P)
        
        # Check that saturation pressure at Tsat equals P
        Psat = props.Psat_T(Tsat)
        assert abs(Psat - P) / P < 0.001  # Within 0.1%
    
    def test_enthalpy_entropy_relation(self):
        """Test Maxwell relations hold approximately."""
        # For single phase: dh = T*ds at constant P
        state1 = ThermoState()
        state2 = ThermoState()
        
        P = 5e5
        T1 = 100 + 273.15
        T2 = 110 + 273.15
        
        state1.update_from_PT(P, T1)
        state2.update_from_PT(P, T2)
        
        # Approximate check: Δh ≈ T_avg * Δs
        T_avg = (state1.T + state2.T) / 2
        dh = state2.h - state1.h
        ds = state2.s - state1.s
        
        # Should be reasonably close for small changes
        assert abs(dh - T_avg * ds) / dh < 0.1  # Within 10%
