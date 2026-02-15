"""
Unit tests for Condenser module

Tests the physical condensation model, controller, and diagnostic flags.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.condenser import CondenserController


@pytest.fixture
def controller():
    """Fixture providing a CondenserController instance."""
    return CondenserController()


@pytest.fixture
def props():
    """Fixture providing PropsService singleton."""
    return get_props_service()


@pytest.fixture
def nominal_state_in(props):
    """
    Fixture providing nominal state_in (condenser inlet).
    
    Saturated vapor at condenser temperature (35°C).
    """
    # Condenser temperature
    T_cond = 308.15  # 35°C
    P_cond = props.Psat_T(T_cond)
    
    # State_in: saturated vapor (x = 1.0)
    state_in = ThermoState()
    state_in.update_from_PX(P_cond, 1.0)
    
    return state_in


class TestCondenserNominal:
    """Test nominal condenser operation."""
    
    def test_complete_condensation(self, controller, nominal_state_in, props):
        """
        Test complete condensation process (nominal case).
        
        State_in (saturated vapor) should condense to state_out (saturated liquid).
        Heat rejection Q_mass should be positive.
        """
        # Nominal parameters
        T_cond = 308.15  # 35°C
        m_dot = 0.035  # kg/s
        K = 15  # W/m²/K (natural convection)
        A = 20.0  # m²
        T_air_in = 300.15  # 27°C
        T_air_out = 305.15  # 32°C
        subcool_K = 0.0
        
        # Run simulation
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=m_dot,
            T_cond=T_cond,
            K=K,
            A=A,
            T_air_in=T_air_in,
            T_air_out=T_air_out,
            subcool_K=subcool_K,
        )
        
        # Verify heat rejection is positive
        assert result.Q_mass > 0, "Q_mass should be positive for condensation"
        assert result.Q_KA > 0, "Q_KA should be positive"
        
        # Verify outlet state is saturated liquid
        assert result.state_out.x is not None, "State_out should be two-phase or saturated"
        assert abs(result.state_out.x - 0.0) < 1e-6, "State_out should be saturated liquid (x=0)"
        
        # Verify pressure is approximately constant
        assert abs(result.state_out.P - result.P_cond) < 1.0, "Pressure should remain approximately constant"
        
        # Verify no critical errors
        assert not result.flags["incomplete_condensation"], "Condensation should be complete"
        assert not result.flags["negative_heat_rejection"], "Heat rejection should be positive"
        assert not result.flags["invalid_LMTD"], "LMTD should be valid"
    
    def test_subcooling_option(self, controller, nominal_state_in, props):
        """
        Test optional subcooling functionality.
        
        When subcool_K > 0, outlet temperature should be T_sat - subcool_K.
        """
        T_cond = 308.15  # 35°C
        P_cond = props.Psat_T(T_cond)
        T_sat = props.Tsat_P(P_cond)
        
        subcool_K = 5.0  # 5 K subcooling
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=subcool_K,
        )
        
        # Verify outlet temperature
        expected_T_out = T_sat - subcool_K
        assert abs(result.state_out.T - expected_T_out) < 0.1, "T_out should be T_sat - subcool_K"
        
        # Verify state_out is subcooled (x should be None)
        assert result.state_out.x is None, "Subcooled liquid should have x=None"
        
        # Heat rejection should be higher with subcooling
        assert result.Q_mass > 0, "Q_mass should be positive"
    
    def test_pressure_consistency(self, controller, nominal_state_in, props):
        """
        Test that P_cond is correctly calculated from T_cond.
        """
        T_cond = 308.15
        P_cond_expected = props.Psat_T(T_cond)
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # Verify P_cond matches
        assert abs(result.P_cond - P_cond_expected) < 1.0, "P_cond should match Psat_T(T_cond)"


class TestCondenserFlags:
    """Test diagnostic flags."""
    
    def test_invalid_LMTD_high_air_temp(self, controller, nominal_state_in, props):
        """
        Test invalid_LMTD flag when air temperature is too high.
        
        If T_air_in >= T_sat or T_air_out >= T_sat, LMTD is invalid.
        """
        T_cond = 308.15  # 35°C
        P_cond = props.Psat_T(T_cond)
        T_sat = props.Tsat_P(P_cond)
        
        # Set air temperatures above or equal to saturation
        T_air_in = T_sat + 1.0  # Above saturation
        T_air_out = T_sat + 2.0
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=T_air_in,
            T_air_out=T_air_out,
            subcool_K=0.0,
        )
        
        # Verify invalid_LMTD flag is set
        assert result.flags["invalid_LMTD"], "invalid_LMTD should be True when T_air >= T_sat"
        
        # Q_KA should be zero or invalid
        assert result.Q_KA == 0.0, "Q_KA should be zero when LMTD is invalid"
    
    def test_thermal_mismatch_low_KA(self, controller, nominal_state_in, props):
        """
        Test thermal_mismatch flag when K*A is very low.
        
        If heat exchanger capacity (K*A) is much lower than required heat transfer,
        thermal_mismatch flag should be set.
        """
        T_cond = 308.15  # 35°C
        
        # Very low K*A product
        K = 5  # W/m²/K (much lower than nominal 15)
        A = 1.0  # m² (much lower than nominal 20)
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=K,
            A=A,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # Verify thermal_mismatch flag is set
        assert result.flags["thermal_mismatch"], "thermal_mismatch should be True when K*A is too low"
        
        # Verify delta_relative is large
        assert result.delta_relative > 0.05, "Delta relative should be > 5% for thermal mismatch"


class TestCondenserEnergyBalance:
    """Test energy balance consistency."""
    
    def test_energy_balance_inlet_outlet(self, controller, nominal_state_in, props):
        """
        Test that energy balance is consistent: Q = m_dot * (h_in - h_out).
        """
        T_cond = 308.15
        m_dot = 0.035
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=m_dot,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # Manually compute Q_mass
        Q_computed = m_dot * (nominal_state_in.h - result.state_out.h)
        
        # Verify Q_mass matches
        assert abs(result.Q_mass - Q_computed) < 1e-3, "Q_mass should match m_dot*(h_in-h_out)"
    
    def test_state_out_lower_enthalpy_than_state_in(self, controller, nominal_state_in, props):
        """
        Test that outlet enthalpy is lower than inlet enthalpy (condensation removes energy).
        """
        T_cond = 308.15
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # h_out should be less than h_in (condensation)
        assert result.state_out.h < nominal_state_in.h, "h_out should be less than h_in for condensation"
    
    def test_subcooling_increases_heat_rejection(self, controller, nominal_state_in, props):
        """
        Test that subcooling increases heat rejection compared to saturated liquid outlet.
        """
        T_cond = 308.15
        
        # Case 1: No subcooling
        result_no_subcool = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # Case 2: With subcooling
        result_with_subcool = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=5.0,
        )
        
        # Q_mass should be higher with subcooling
        assert result_with_subcool.Q_mass > result_no_subcool.Q_mass, "Subcooling should increase heat rejection"


class TestCondenserEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_mass_flow(self, controller, nominal_state_in, props):
        """
        Test behavior with zero mass flow rate.
        
        Q_mass should be zero, but simulation should not crash.
        """
        T_cond = 308.15
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.0,  # Zero mass flow
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # Q_mass should be zero
        assert abs(result.Q_mass) < 1e-6, "Q_mass should be zero for zero mass flow"
    
    def test_high_subcooling(self, controller, nominal_state_in, props):
        """
        Test with high subcooling (e.g., 20 K).
        
        Should not crash, and T_out should be much lower than T_sat.
        """
        T_cond = 308.15
        P_cond = props.Psat_T(T_cond)
        T_sat = props.Tsat_P(P_cond)
        
        subcool_K = 20.0  # 20 K subcooling
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=subcool_K,
        )
        
        # Verify T_out is approximately T_sat - 20
        expected_T_out = T_sat - subcool_K
        assert abs(result.state_out.T - expected_T_out) < 1.0, "T_out should be T_sat - subcool_K"
        
        # State should be subcooled liquid
        assert result.state_out.x is None, "State_out should be subcooled (x=None)"


class TestCondenserStateConsistency:
    """Test thermodynamic state consistency."""
    
    def test_pressure_constant_during_condensation(self, controller, nominal_state_in, props):
        """
        Test that pressure remains approximately constant during condensation (isobaric process).
        """
        T_cond = 308.15
        P_cond = props.Psat_T(T_cond)
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,
        )
        
        # Verify P_out ≈ P_cond (constant pressure)
        assert abs(result.state_out.P - P_cond) < 1.0, "Pressure should remain approximately constant during condensation"
    
    def test_saturated_liquid_quality(self, controller, nominal_state_in, props):
        """
        Test that saturated liquid outlet has quality x=0.0.
        """
        T_cond = 308.15
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_cond=T_cond,
            K=15,
            A=20.0,
            T_air_in=300.15,
            T_air_out=305.15,
            subcool_K=0.0,  # No subcooling
        )
        
        # Quality should be 0.0
        assert result.state_out.x is not None, "Saturated liquid should have defined quality"
        assert abs(result.state_out.x - 0.0) < 1e-6, "Saturated liquid should have x=0.0"


# Summary fixture for test collection
def test_summary():
    """Summary of condenser tests."""
    print("\n" + "=" * 60)
    print("CONDENSER TESTS SUMMARY")
    print("=" * 60)
    print("Tests cover:")
    print("  ✓ Nominal complete condensation")
    print("  ✓ Optional subcooling functionality")
    print("  ✓ Diagnostic flags (invalid_LMTD, thermal_mismatch)")
    print("  ✓ Energy balance consistency")
    print("  ✓ Edge cases (zero flow, high subcooling)")
    print("  ✓ Thermodynamic state consistency")
    print("=" * 60)
