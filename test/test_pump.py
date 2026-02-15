"""
Unit tests for Pump module

Tests the physical pump model, controller, and diagnostic flags.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.pump import PumpController


@pytest.fixture
def controller():
    """Fixture providing a PumpController instance."""
    return PumpController()


@pytest.fixture
def props():
    """Fixture providing PropsService singleton."""
    return get_props_service()


@pytest.fixture
def nominal_state_in(props):
    """
    Fixture providing nominal state_in (pump inlet).
    
    Saturated liquid at condenser temperature (35°C).
    """
    # Condenser temperature
    T_cond = 308.15  # 35°C
    P_cond = props.Psat_T(T_cond)
    
    # State_in: saturated liquid (x = 0.0)
    state_in = ThermoState()
    state_in.update_from_PX(P_cond, 0.0)
    
    return state_in


class TestPumpNominal:
    """Test nominal pump operation."""
    
    def test_nominal_pumping(self, controller, nominal_state_in, props):
        """
        Test nominal pumping operation.
        
        Saturated liquid at condenser pressure (35°C) compressed to generator pressure (100°C).
        """
        # Generator pressure (100°C)
        T_gen = 373.15  # 100°C
        P_out = props.Psat_T(T_gen)
        
        # Pump parameters
        eta_is = 0.70  # 70% efficiency
        m_dot = 0.035  # kg/s
        
        # Run simulation
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=eta_is,
            m_dot=m_dot,
        )
        
        # Verify pressure rise
        assert result.state_out.P > nominal_state_in.P, "Outlet pressure should be higher than inlet"
        assert abs(result.state_out.P - P_out) < 1.0, "Outlet pressure should match P_out"
        
        # Verify pump work is positive
        assert result.W_pump > 0, "Pump power should be positive"
        
        # Verify enthalpy increase
        assert result.delta_h > 0, "Enthalpy should increase"
        assert result.state_out.h > nominal_state_in.h, "h_out > h_in"
        
        # Verify outlet is compressed liquid (not two-phase)
        assert result.state_out.x is None, "Outlet should be compressed liquid (x=None)"
        
        # Verify no critical errors
        assert not result.flags["invalid_pressure_rise"], "Pressure rise should be valid"
        assert not result.flags["two_phase_inlet"], "Inlet should be liquid"
    
    def test_isentropic_consistency(self, controller, nominal_state_in, props):
        """
        Test that isentropic state is correctly calculated.
        
        Isentropic compression should have same entropy as inlet.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.035,
        )
        
        # Verify isentropic state has same entropy as inlet
        assert abs(result.state_is.s - nominal_state_in.s) < 1.0, "Isentropic state should have same entropy"
        
        # Verify isentropic enthalpy increase is positive
        delta_h_is = result.state_is.h - nominal_state_in.h
        assert delta_h_is > 0, "Isentropic enthalpy increase should be positive"
        
        # Verify real enthalpy increase is larger (due to inefficiency)
        assert result.delta_h > delta_h_is, "Real enthalpy increase should be larger than isentropic"
        
        # Verify efficiency relationship: delta_h = delta_h_is / eta
        expected_delta_h = delta_h_is / 0.70
        assert abs(result.delta_h - expected_delta_h) < 1.0, "Delta_h should match delta_h_is / eta"
    
    def test_power_calculation(self, controller, nominal_state_in, props):
        """
        Test that pump power is correctly calculated: W = m_dot * (h_out - h_in).
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        m_dot = 0.035
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=m_dot,
        )
        
        # Manually compute power
        W_expected = m_dot * (result.state_out.h - nominal_state_in.h)
        
        # Verify
        assert abs(result.W_pump - W_expected) < 1e-6, "W_pump should equal m_dot * delta_h"


class TestPumpFlags:
    """Test diagnostic flags."""
    
    def test_invalid_pressure_rise(self, controller, nominal_state_in, props):
        """
        Test invalid_pressure_rise flag when P_out <= P_in.
        """
        # Set P_out equal to P_in (no pressure rise)
        P_out = nominal_state_in.P
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.035,
        )
        
        # Verify flag is set
        assert result.flags["invalid_pressure_rise"], "invalid_pressure_rise should be True when P_out <= P_in"
    
    def test_invalid_efficiency_zero(self, controller, nominal_state_in, props):
        """
        Test that zero efficiency raises ValueError.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        with pytest.raises(ValueError, match="Isentropic efficiency"):
            controller.solve(
                state_in=nominal_state_in,
                P_out=P_out,
                eta_is=0.0,  # Invalid: zero efficiency
                m_dot=0.035,
            )
    
    def test_invalid_efficiency_negative(self, controller, nominal_state_in, props):
        """
        Test that negative efficiency raises ValueError.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        with pytest.raises(ValueError, match="Isentropic efficiency"):
            controller.solve(
                state_in=nominal_state_in,
                P_out=P_out,
                eta_is=-0.5,  # Invalid: negative
                m_dot=0.035,
            )
    
    def test_invalid_efficiency_above_one(self, controller, nominal_state_in, props):
        """
        Test that efficiency > 1 raises ValueError.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        with pytest.raises(ValueError, match="Isentropic efficiency"):
            controller.solve(
                state_in=nominal_state_in,
                P_out=P_out,
                eta_is=1.2,  # Invalid: > 1
                m_dot=0.035,
            )
    
    def test_cavitation_risk_low_pressure(self, controller, props):
        """
        Test cavitation_risk flag when inlet pressure is very low.
        """
        # Create low-pressure inlet state
        P_in_low = 1000  # 1000 Pa (below 1500 Pa threshold)
        T_in = 280.0  # Low temperature
        
        state_in_low = ThermoState()
        state_in_low.update_from_PT(P_in_low, T_in)
        
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result = controller.solve(
            state_in=state_in_low,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.035,
        )
        
        # Verify cavitation warning
        assert result.flags["cavitation_risk"], "cavitation_risk should be True for low inlet pressure"


class TestPumpEfficiencyVariation:
    """Test pump behavior with different efficiencies."""
    
    def test_high_efficiency(self, controller, nominal_state_in, props):
        """
        Test pump with high efficiency (eta = 0.95).
        
        Higher efficiency means lower real enthalpy increase (closer to isentropic).
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result_high = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.95,
            m_dot=0.035,
        )
        
        result_low = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.50,
            m_dot=0.035,
        )
        
        # Higher efficiency should result in lower power consumption
        assert result_high.W_pump < result_low.W_pump, "Higher efficiency should consume less power"
        
        # Higher efficiency should result in lower enthalpy increase
        assert result_high.delta_h < result_low.delta_h, "Higher efficiency should have lower delta_h"
    
    def test_efficiency_edge_case_one(self, controller, nominal_state_in, props):
        """
        Test pump with perfect efficiency (eta = 1.0).
        
        Real state should match isentropic state.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=1.0,
            m_dot=0.035,
        )
        
        # With perfect efficiency, real state should equal isentropic state
        assert abs(result.state_out.h - result.state_is.h) < 1.0, "Perfect efficiency: h_out should equal h_is"
        assert abs(result.delta_h - (result.state_is.h - nominal_state_in.h)) < 1.0


class TestPumpStateConsistency:
    """Test thermodynamic state consistency."""
    
    def test_outlet_is_compressed_liquid(self, controller, nominal_state_in, props):
        """
        Test that outlet state is compressed liquid (not two-phase).
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.035,
        )
        
        # Outlet should be compressed liquid
        assert result.state_out.x is None, "Compressed liquid should have x=None"
    
    def test_temperature_increase(self, controller, nominal_state_in, props):
        """
        Test that compression causes temperature increase.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.035,
        )
        
        # Temperature should increase due to compression
        assert result.state_out.T > nominal_state_in.T, "Temperature should increase during compression"


class TestPumpEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_mass_flow(self, controller, nominal_state_in, props):
        """
        Test behavior with zero mass flow rate.
        
        W_pump should be zero.
        """
        T_gen = 373.15
        P_out = props.Psat_T(T_gen)
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.0,  # Zero mass flow
        )
        
        # Power should be zero
        assert abs(result.W_pump) < 1e-6, "W_pump should be zero for zero mass flow"
    
    def test_small_pressure_rise(self, controller, nominal_state_in, props):
        """
        Test with very small pressure rise.
        
        Should still work, with small delta_h and W_pump.
        """
        # Small pressure increase
        P_out = nominal_state_in.P * 1.01  # 1% increase
        
        result = controller.solve(
            state_in=nominal_state_in,
            P_out=P_out,
            eta_is=0.70,
            m_dot=0.035,
        )
        
        # Power should be small but positive
        assert result.W_pump > 0, "W_pump should be positive"
        assert result.W_pump < 100, "W_pump should be small for small pressure rise"


# Summary fixture for test collection
def test_summary():
    """Summary of pump tests."""
    print("\n" + "=" * 60)
    print("PUMP TESTS SUMMARY")
    print("=" * 60)
    print("Tests cover:")
    print("  ✓ Nominal pumping operation")
    print("  ✓ Isentropic efficiency model")
    print("  ✓ Power calculation")
    print("  ✓ Diagnostic flags (invalid pressure/efficiency, cavitation)")
    print("  ✓ Efficiency variation effects")
    print("  ✓ Thermodynamic state consistency")
    print("  ✓ Edge cases (zero flow, small pressure rise)")
    print("=" * 60)
