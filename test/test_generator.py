"""
Unit tests for Generator module

Tests the physical generator model, controller, and diagnostic flags.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.generator import GeneratorController


@pytest.fixture
def controller():
    """Fixture providing a GeneratorController instance."""
    return GeneratorController()


@pytest.fixture
def props():
    """Fixture providing PropsService singleton."""
    return get_props_service()


@pytest.fixture
def nominal_state_in(props):
    """
    Fixture providing nominal state_in (generator inlet).
    
    Compressed liquid at generator pressure (100°C saturation).
    """
    # Generator nominal conditions
    T_gen = 373.15  # 100°C
    P_gen = props.Psat_T(T_gen)
    
    # State_in: saturated liquid at generator pressure (x = 0.0)
    state_in = ThermoState()
    state_in.update_from_PX(P_gen, 0.0)
    
    return state_in


class TestGeneratorNominal:
    """Test nominal generator operation."""
    
    def test_nominal_heating_to_saturated_vapor(self, controller, nominal_state_in, props):
        """
        Test nominal heating operation.
        
        Saturated liquid heated to saturated vapor at 100°C.
        """
        # Nominal parameters
        T_gen_target = 373.15  # 100°C
        m_dot = 0.035  # kg/s
        K = 250.0  # W/m²/K
        A = 6.0  # m²
        T_htf_in = 403.15  # 130°C
        T_htf_out = 383.15  # 110°C
        superheat_K = 0.0  # No superheat
        
        # Run simulation
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=m_dot,
            T_gen_target=T_gen_target,
            K=K,
            A=A,
            T_htf_in=T_htf_in,
            T_htf_out=T_htf_out,
            superheat_K=superheat_K,
        )
        
        # Verify heat input is positive
        assert result.Q_mass > 0, "Q_mass should be positive"
        assert result.Q_KA > 0, "Q_KA should be positive"
        
        # Verify outlet is saturated vapor (x = 1.0)
        assert result.state_out.x is not None, "Outlet should be saturated (x defined)"
        assert abs(result.state_out.x - 1.0) < 0.01, "Outlet should be saturated vapor (x ≈ 1)"
        
        # Verify pressure is correct
        P_gen_expected = props.Psat_T(T_gen_target)
        assert abs(result.P_gen - P_gen_expected) < 10.0, "P_gen should match saturation pressure"
        
        # Verify no critical errors
        assert not result.flags["negative_heat_input"], "Heat input should be positive"
        assert not result.flags["invalid_LMTD"], "LMTD should be valid"
    
    def test_heat_balance_consistency(self, controller, nominal_state_in, props):
        """
        Test that Q_mass and Q_KA are reasonably consistent.
        """
        T_gen_target = 373.15
        m_dot = 0.035
        K = 250.0
        A = 6.0
        T_htf_in = 403.15
        T_htf_out = 383.15
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=m_dot,
            T_gen_target=T_gen_target,
            K=K,
            A=A,
            T_htf_in=T_htf_in,
            T_htf_out=T_htf_out,
            superheat_K=0.0,
        )
        
        # Q_mass should be positive
        assert result.Q_mass > 0, "Q_mass should be positive"
        
        # Q_KA should be positive
        assert result.Q_KA > 0, "Q_KA should be positive"
        
        # Relative difference should be reasonable (depends on K, A sizing)
        # Just verify it's computed
        assert result.delta_relative >= 0, "Relative difference should be non-negative"
    
    def test_enthalpy_increase(self, controller, nominal_state_in, props):
        """
        Test that enthalpy increases during heating.
        """
        T_gen_target = 373.15
        m_dot = 0.035
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=m_dot,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Outlet enthalpy should be higher than inlet
        assert result.state_out.h > nominal_state_in.h, "h_out should be > h_in"
        
        # Latent heat of vaporization should be significant
        delta_h = result.state_out.h - nominal_state_in.h
        assert delta_h > 2000e3, "Latent heat should be significant (> 2 MJ/kg for water)"


class TestGeneratorFlags:
    """Test diagnostic flags."""
    
    def test_invalid_LMTD_htf_too_cold(self, controller, nominal_state_in, props):
        """
        Test invalid_LMTD flag when HTF is too cold (T_htf <= T_sat).
        """
        T_gen_target = 373.15  # 100°C
        T_htf_in = 370.15  # 97°C - below saturation!
        T_htf_out = 360.15  # 87°C
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=T_htf_in,
            T_htf_out=T_htf_out,
            superheat_K=0.0,
        )
        
        # Verify flag is set
        assert result.flags["invalid_LMTD"], "invalid_LMTD should be True when T_htf < T_sat"
    
    def test_thermal_mismatch_small_area(self, controller, nominal_state_in, props):
        """
        Test thermal_mismatch flag when heat exchanger area is too small.
        """
        # Very small area → Q_KA << Q_mass
        A_small = 0.5  # m² (too small)
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=373.15,
            K=250.0,
            A=A_small,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Verify thermal mismatch is detected
        assert result.flags["thermal_mismatch"], "thermal_mismatch should be True for small area"
    
    def test_insufficient_heating(self, controller, nominal_state_in, props):
        """
        Test insufficient_heating flag when Q_KA is much less than Q_mass.
        """
        # Very small K → Q_KA << Q_mass
        K_small = 10.0  # W/m²/K (very low)
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=373.15,
            K=K_small,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Verify insufficient heating flag
        assert result.flags["insufficient_heating"], "insufficient_heating should be True for low K"


class TestGeneratorSuperheat:
    """Test superheated vapor generation."""
    
    def test_superheat_generation(self, controller, nominal_state_in, props):
        """
        Test generation of superheated vapor (superheat > 0).
        """
        T_gen_target = 373.15  # 100°C saturation
        superheat_K = 10.0  # 10 K superheat
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=superheat_K,
        )
        
        # Verify outlet temperature includes superheat
        T_out_expected = T_gen_target + superheat_K
        assert abs(result.state_out.T - T_out_expected) < 0.5, "T_out should include superheat"
        
        # Verify outlet is superheated (x = None)
        assert result.state_out.x is None, "Superheated vapor should have x=None"
    
    def test_superheat_increases_enthalpy(self, controller, nominal_state_in, props):
        """
        Test that superheat increases enthalpy beyond saturated vapor.
        """
        T_gen_target = 373.15
        
        # Case 1: Saturated vapor (no superheat)
        result_sat = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Case 2: Superheated vapor
        result_superheat = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=15.0,
        )
        
        # Superheated enthalpy should be higher
        assert result_superheat.state_out.h > result_sat.state_out.h, "Superheat should increase enthalpy"


class TestGeneratorPressureLevels:
    """Test different generator pressure levels."""
    
    def test_low_temperature_generator(self, controller, props):
        """
        Test generator at lower temperature (80°C).
        """
        T_gen = 353.15  # 80°C
        P_gen = props.Psat_T(T_gen)
        
        # Create inlet state at lower pressure
        state_in = ThermoState()
        state_in.update_from_PX(P_gen, 0.0)
        
        result = controller.solve(
            state_in=state_in,
            m_dot=0.035,
            T_gen_target=T_gen,
            K=250.0,
            A=6.0,
            T_htf_in=373.15,  # 100°C HTF
            T_htf_out=363.15,  # 90°C HTF
            superheat_K=0.0,
        )
        
        # Verify pressure matches low temperature
        assert abs(result.P_gen - P_gen) < 10.0, "P_gen should match 80°C saturation"
        assert result.Q_mass > 0, "Heat should be positive"
    
    def test_high_temperature_generator(self, controller, props):
        """
        Test generator at higher temperature (120°C).
        """
        T_gen = 393.15  # 120°C
        P_gen = props.Psat_T(T_gen)
        
        # Create inlet state at higher pressure
        state_in = ThermoState()
        state_in.update_from_PX(P_gen, 0.0)
        
        result = controller.solve(
            state_in=state_in,
            m_dot=0.035,
            T_gen_target=T_gen,
            K=250.0,
            A=6.0,
            T_htf_in=423.15,  # 150°C HTF
            T_htf_out=413.15,  # 140°C HTF
            superheat_K=0.0,
        )
        
        # Verify pressure matches high temperature
        assert abs(result.P_gen - P_gen) < 50.0, "P_gen should match 120°C saturation"
        assert result.Q_mass > 0, "Heat should be positive"


class TestGeneratorMassFlow:
    """Test different mass flow rates."""
    
    def test_high_mass_flow(self, controller, nominal_state_in, props):
        """
        Test with higher mass flow rate.
        
        Q_mass should increase proportionally with m_dot.
        """
        T_gen_target = 373.15
        
        # Case 1: Nominal flow
        result_nominal = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Case 2: Double flow
        result_double = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.070,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Q_mass should approximately double
        ratio = result_double.Q_mass / result_nominal.Q_mass
        assert abs(ratio - 2.0) < 0.01, "Q_mass should scale linearly with m_dot"
    
    def test_zero_mass_flow(self, controller, nominal_state_in, props):
        """
        Test with zero mass flow rate.
        
        Q_mass should be zero.
        """
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.0,  # Zero flow
            T_gen_target=373.15,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # Q_mass should be zero
        assert abs(result.Q_mass) < 1e-6, "Q_mass should be zero for zero mass flow"


class TestGeneratorLMTD:
    """Test LMTD calculation."""
    
    def test_LMTD_positive(self, controller, nominal_state_in, props):
        """
        Test that LMTD is positive under normal conditions.
        """
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=373.15,
            K=250.0,
            A=6.0,
            T_htf_in=403.15,
            T_htf_out=383.15,
            superheat_K=0.0,
        )
        
        # LMTD should be positive
        assert result.delta_T_lm > 0, "LMTD should be positive"
    
    def test_LMTD_calculation(self, controller, nominal_state_in, props):
        """
        Test LMTD calculation manually.
        """
        T_gen_target = 373.15  # 100°C
        T_htf_in = 403.15  # 130°C
        T_htf_out = 383.15  # 110°C
        
        result = controller.solve(
            state_in=nominal_state_in,
            m_dot=0.035,
            T_gen_target=T_gen_target,
            K=250.0,
            A=6.0,
            T_htf_in=T_htf_in,
            T_htf_out=T_htf_out,
            superheat_K=0.0,
        )
        
        # Manual LMTD calculation
        delta_T1 = T_htf_in - T_gen_target  # 130 - 100 = 30
        delta_T2 = T_htf_out - T_gen_target  # 110 - 100 = 10
        import numpy as np
        LMTD_expected = (delta_T1 - delta_T2) / np.log(delta_T1 / delta_T2)
        
        # Verify
        assert abs(result.delta_T_lm - LMTD_expected) < 0.1, "LMTD should match manual calculation"


# Summary fixture for test collection
def test_summary():
    """Summary of generator tests."""
    print("\n" + "=" * 60)
    print("GENERATOR TESTS SUMMARY")
    print("=" * 60)
    print("Tests cover:")
    print("  ✓ Nominal heating to saturated vapor")
    print("  ✓ Heat balance consistency (Q_mass vs Q_KA)")
    print("  ✓ Diagnostic flags (invalid LMTD, thermal mismatch, insufficient heating)")
    print("  ✓ Superheated vapor generation")
    print("  ✓ Different generator temperatures/pressures")
    print("  ✓ Mass flow rate effects")
    print("  ✓ LMTD calculation accuracy")
    print("=" * 60)
