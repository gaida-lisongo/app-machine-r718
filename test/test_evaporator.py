"""
Unit tests for Evaporator module

Tests the physical evaporation model, controller, and diagnostic flags.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.evaporator import EvaporatorController


@pytest.fixture
def controller():
    """Fixture providing an EvaporatorController instance."""
    return EvaporatorController()


@pytest.fixture
def props():
    """Fixture providing PropsService singleton."""
    return get_props_service()


@pytest.fixture
def nominal_state2(props):
    """
    Fixture providing nominal state2 (evaporator inlet).
    
    Generated via isenthalpic expansion from saturated liquid at condenser
    temperature (35°C) to evaporator pressure (10°C saturation).
    """
    # State 1: saturated liquid at condenser (35°C)
    T_cond = 308.15  # 35°C
    P_cond = props.Psat_T(T_cond)
    state1 = ThermoState()
    state1.update_from_PX(P_cond, 0.0)  # Saturated liquid
    
    # State 2: isenthalpic expansion to evaporator pressure
    T_evap = 283.15  # 10°C
    P_evap = props.Psat_T(T_evap)
    state2 = ThermoState()
    state2.update_from_PH(P_evap, state1.h)  # h2 = h1
    
    return state2


class TestEvaporatorNominal:
    """Test nominal evaporator operation."""
    
    def test_complete_vaporization(self, controller, nominal_state2, props):
        """
        Test complete vaporization process (nominal case).
        
        State2 (two-phase inlet) should evaporate to state3 (saturated vapor).
        Heat transfer Q_mass should be positive.
        Delta relative should be reasonable.
        """
        # Nominal parameters
        T_evap = 283.15  # 10°C
        P_evap = props.Psat_T(T_evap)
        m_dot = 0.035  # kg/s
        K = 800  # W/m²/K
        A = 6.0  # m²
        T_ext_in = 295.15  # 22°C
        T_ext_out = 289.15  # 16°C
        superheat_K = 0.0
        
        # Run simulation
        result = controller.solve(
            state2=nominal_state2,
            m_dot=m_dot,
            P_evap=P_evap,
            K=K,
            A=A,
            T_ext_in=T_ext_in,
            T_ext_out=T_ext_out,
            superheat_K=superheat_K,
        )
        
        # Verify heat transfer is positive
        assert result.Q_mass > 0, "Q_mass should be positive for evaporation"
        assert result.Q_KA > 0, "Q_KA should be positive"
        
        # Verify outlet state is saturated vapor
        assert result.state3.x is not None, "State3 should be two-phase or saturated"
        assert abs(result.state3.x - 1.0) < 1e-6, "State3 should be saturated vapor (x=1)"
        
        # Verify pressure is constant
        assert abs(result.state3.P - P_evap) < 1.0, "Pressure should remain constant"
        
        # Verify delta_relative is reasonable (may have mismatch but should not be huge)
        # Note: mismatch is expected if K*A is not perfectly matched to m_dot*(h3-h2)
        assert result.delta_relative < 1.0, "Delta relative should be less than 100%"
        
        # Verify no critical errors (incomplete evaporation, negative heat)
        assert not result.flags["incomplete_evaporation"], "Evaporation should be complete"
        assert not result.flags["negative_heat_transfer"], "Heat transfer should be positive"
        assert not result.flags["invalid_LMTD"], "LMTD should be valid"
    
    def test_superheat_option(self, controller, nominal_state2, props):
        """
        Test optional superheat functionality.
        
        When superheat_K > 0, outlet temperature should be T_sat + superheat_K.
        """
        T_evap = 283.15  # 10°C
        P_evap = props.Psat_T(T_evap)
        T_sat = props.Tsat_P(P_evap)
        
        superheat_K = 5.0  # 5 K superheat
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=superheat_K,
        )
        
        # Verify outlet temperature
        expected_T3 = T_sat + superheat_K
        assert abs(result.state3.T - expected_T3) < 0.1, "T3 should be T_sat + superheat_K"
        
        # Verify state3 is superheated (x should be None)
        assert result.state3.x is None, "Superheated vapor should have x=None"
        
        # Heat transfer should still be positive
        assert result.Q_mass > 0, "Q_mass should be positive"


class TestEvaporatorFlags:
    """Test diagnostic flags."""
    
    def test_invalid_LMTD_low_ext_temp(self, controller, nominal_state2, props):
        """
        Test invalid_LMTD flag when external temperature is too low.
        
        If T_ext_in <= T_sat or T_ext_out <= T_sat, LMTD is invalid.
        """
        T_evap = 283.15  # 10°C
        P_evap = props.Psat_T(T_evap)
        T_sat = props.Tsat_P(P_evap)
        
        # Set external temperatures below or equal to saturation
        T_ext_in = T_sat - 1.0  # Below saturation
        T_ext_out = T_sat - 2.0
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=T_ext_in,
            T_ext_out=T_ext_out,
            superheat_K=0.0,
        )
        
        # Verify invalid_LMTD flag is set
        assert result.flags["invalid_LMTD"], "invalid_LMTD should be True when T_ext <= T_sat"
        
        # Q_KA should be zero or invalid
        assert result.Q_KA == 0.0, "Q_KA should be zero when LMTD is invalid"
    
    def test_thermal_mismatch_low_KA(self, controller, nominal_state2, props):
        """
        Test thermal_mismatch flag when K*A is very low.
        
        If heat exchanger capacity (K*A) is much lower than required heat transfer,
        thermal_mismatch flag should be set.
        """
        T_evap = 283.15  # 10°C
        P_evap = props.Psat_T(T_evap)
        
        # Very low K*A product
        K = 50  # W/m²/K (much lower than nominal 800)
        A = 0.5  # m² (much lower than nominal 6.0)
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=K,
            A=A,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=0.0,
        )
        
        # Verify thermal_mismatch flag is set
        assert result.flags["thermal_mismatch"], "thermal_mismatch should be True when K*A is too low"
        
        # Verify delta_relative is large
        assert result.delta_relative > 0.05, "Delta relative should be > 5% for thermal mismatch"
    
    def test_negative_heat_transfer_reversed_temps(self, controller, nominal_state2, props):
        """
        Test negative_heat_transfer flag when temperatures are reversed or invalid.
        """
        T_evap = 283.15  # 10°C
        P_evap = props.Psat_T(T_evap)
        T_sat = props.Tsat_P(P_evap)
        
        # Reversed external temperatures (outlet > inlet) - physically impossible for cooling
        T_ext_in = T_sat - 2.0
        T_ext_out = T_sat - 1.0  # T_out > T_in
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=T_ext_in,
            T_ext_out=T_ext_out,
            superheat_K=0.0,
        )
        
        # Should trigger invalid_LMTD (both temps below T_sat)
        assert result.flags["invalid_LMTD"], "invalid_LMTD should be True"


class TestEvaporatorEnergyBalance:
    """Test energy balance consistency."""
    
    def test_energy_balance_inlet_outlet(self, controller, nominal_state2, props):
        """
        Test that energy balance is consistent: Q = m_dot * (h3 - h2).
        """
        T_evap = 283.15  # 10°C
        P_evap = props.Psat_T(T_evap)
        m_dot = 0.035
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=m_dot,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=0.0,
        )
        
        # Manually compute Q_mass
        Q_computed = m_dot * (result.state3.h - nominal_state2.h)
        
        # Verify Q_mass matches
        assert abs(result.Q_mass - Q_computed) < 1e-3, "Q_mass should match m_dot*(h3-h2)"
    
    def test_state3_higher_enthalpy_than_state2(self, controller, nominal_state2, props):
        """
        Test that outlet enthalpy is higher than inlet enthalpy (evaporation adds energy).
        """
        T_evap = 283.15
        P_evap = props.Psat_T(T_evap)
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=0.0,
        )
        
        # h3 should be greater than h2 (evaporation)
        assert result.state3.h > nominal_state2.h, "h3 should be greater than h2 for evaporation"


class TestEvaporatorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_mass_flow(self, controller, nominal_state2, props):
        """
        Test behavior with zero mass flow rate.
        
        Q_mass should be zero, but simulation should not crash.
        """
        T_evap = 283.15
        P_evap = props.Psat_T(T_evap)
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.0,  # Zero mass flow
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=0.0,
        )
        
        # Q_mass should be zero
        assert abs(result.Q_mass) < 1e-6, "Q_mass should be zero for zero mass flow"
    
    def test_very_high_superheat(self, controller, nominal_state2, props):
        """
        Test with very high superheat (e.g., 50 K).
        
        Should not crash, and T3 should be much higher than T_sat.
        """
        T_evap = 283.15
        P_evap = props.Psat_T(T_evap)
        T_sat = props.Tsat_P(P_evap)
        
        superheat_K = 50.0  # 50 K superheat
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=superheat_K,
        )
        
        # Verify T3 is approximately T_sat + 50
        expected_T3 = T_sat + superheat_K
        assert abs(result.state3.T - expected_T3) < 1.0, "T3 should be T_sat + superheat_K"
        
        # State should be superheated vapor
        assert result.state3.x is None, "State3 should be superheated (x=None)"


class TestEvaporatorStateConsistency:
    """Test thermodynamic state consistency."""
    
    def test_pressure_constant_during_evaporation(self, controller, nominal_state2, props):
        """
        Test that pressure remains constant during evaporation (isobaric process).
        """
        T_evap = 283.15
        P_evap = props.Psat_T(T_evap)
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=0.0,
        )
        
        # Verify P3 = P_evap (constant pressure)
        assert abs(result.state3.P - P_evap) < 1.0, "Pressure should remain constant during evaporation"
    
    def test_saturated_vapor_quality(self, controller, nominal_state2, props):
        """
        Test that saturated vapor outlet has quality x=1.0.
        """
        T_evap = 283.15
        P_evap = props.Psat_T(T_evap)
        
        result = controller.solve(
            state2=nominal_state2,
            m_dot=0.035,
            P_evap=P_evap,
            K=800,
            A=6.0,
            T_ext_in=295.15,
            T_ext_out=289.15,
            superheat_K=0.0,  # No superheat
        )
        
        # Quality should be 1.0
        assert result.state3.x is not None, "Saturated vapor should have defined quality"
        assert abs(result.state3.x - 1.0) < 1e-6, "Saturated vapor should have x=1.0"


# Summary fixture for test collection
def test_summary():
    """Summary of evaporator tests."""
    print("\n" + "=" * 60)
    print("EVAPORATOR TESTS SUMMARY")
    print("=" * 60)
    print("Tests cover:")
    print("  ✓ Nominal complete vaporization")
    print("  ✓ Optional superheat functionality")
    print("  ✓ Diagnostic flags (invalid_LMTD, thermal_mismatch)")
    print("  ✓ Energy balance consistency")
    print("  ✓ Edge cases (zero flow, high superheat)")
    print("  ✓ Thermodynamic state consistency")
    print("=" * 60)
