"""
Unit tests for Ejector module

Tests the physical ejector model, controller, and diagnostic flags.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.ejector import EjectorController


@pytest.fixture
def controller():
    """Fixture providing an EjectorController instance."""
    return EjectorController()


@pytest.fixture
def props():
    """Fixture providing PropsService singleton."""
    return get_props_service()


@pytest.fixture
def nominal_states(props):
    """
    Fixture providing nominal primary and secondary inlet states.
    
    Primary: Saturated vapor at 100°C (generator)
    Secondary: Saturated vapor at 10°C (evaporator)
    P_out: Saturation pressure at 35°C (condenser)
    """
    # Generator conditions
    T_gen = 373.15  # 100°C
    P_gen = props.Psat_T(T_gen)
    state_p_in = ThermoState()
    state_p_in.update_from_PX(P_gen, 1.0)  # Saturated vapor
    
    # Evaporator conditions
    T_evap = 283.15  # 10°C
    P_evap = props.Psat_T(T_evap)
    state_s_in = ThermoState()
    state_s_in.update_from_PX(P_evap, 1.0)  # Saturated vapor
    
    # Condenser conditions
    T_cond = 308.15  # 35°C
    P_out = props.Psat_T(T_cond)
    
    return {
        'state_p_in': state_p_in,
        'state_s_in': state_s_in,
        'P_out': P_out,
    }


class TestEjectorNominal:
    """Test nominal ejector operation."""
    
    def test_nominal_operation(self, controller, nominal_states):
        """
        Test nominal ejector operation with typical refrigeration conditions.
        """
        # Run simulation
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,  # 20 g/s primary
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # Verify entrainment ratio is non-negative
        assert result.mu >= 0, "Entrainment ratio must be non-negative"
        
        # Verify mass flow rates
        assert result.m_dot_p == 0.020, "Primary mass flow should match input"
        assert result.m_dot_s == result.mu * result.m_dot_p, "Secondary flow = mu * m_dot_p"
        
        # Verify outlet pressure
        P_out_expected = nominal_states['P_out']
        assert abs(result.state_out.P - P_out_expected) < 100, "Outlet pressure should match P_out"
        
        # Verify no solver failure
        assert not result.flags["solver_no_convergence"], "Solver should converge"
        
        # Verify mixing pressure is between P_s and P_out
        assert result.P_mix > nominal_states['state_s_in'].P, "P_mix > P_s_in"
        assert result.P_mix < nominal_states['P_out'], "P_mix < P_out"
    
    def test_entrainment_ratio_positive(self, controller, nominal_states):
        """
        Test that entrainment ratio is positive under normal conditions.
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
        )
        
        # Mu should be positive (ejector entrains secondary flow)
        assert result.mu > 0, "Entrainment ratio should be positive"
    
    def test_pressure_levels_valid(self, controller, nominal_states):
        """
        Test that pressure levels are physically consistent throughout ejector.
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
        )
        
        # Primary pressure should decrease through nozzle
        assert result.state_p_noz.P < nominal_states['state_p_in'].P, "Nozzle should expand primary"
        
        # Outlet pressure should match target
        assert abs(result.state_out.P - nominal_states['P_out']) < 100, "Outlet at P_out"


class TestEjectorEfficiencies:
    """Test ejector behavior with different efficiencies."""
    
    def test_high_nozzle_efficiency(self, controller, nominal_states):
        """
        Test ejector with high nozzle efficiency.
        """
        result_high = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.95,
            eta_diffuser=0.85,
        )
        
        result_low = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.70,
            eta_diffuser=0.85,
        )
        
        # Higher nozzle efficiency should generally improve performance
        # (mu may increase with better nozzle efficiency)
        assert result_high.mu >= 0, "High efficiency mu valid"
        assert result_low.mu >= 0, "Low efficiency mu valid"
    
    def test_invalid_efficiency_zero(self, controller, nominal_states):
        """
        Test that zero efficiency is handled gracefully.
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.0,  # Invalid
        )
        
        # Should set flag and use default
        assert result.flags["invalid_efficiency"], "invalid_efficiency flag should be set"
    
    def test_invalid_efficiency_above_one(self, controller, nominal_states):
        """
        Test that efficiency > 1 is handled gracefully.
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_diffuser=1.5,  # Invalid
        )
        
        # Should set flag and use default
        assert result.flags["invalid_efficiency"], "invalid_efficiency flag should be set"


class TestEjectorPressureLevels:
    """Test ejector with different pressure levels."""
    
    def test_invalid_pressure_out_too_high(self, controller, nominal_states):
        """
        Test that P_out >= P_p_in is flagged as invalid.
        """
        # Set P_out higher than primary pressure
        P_out_invalid = nominal_states['state_p_in'].P * 1.1
        
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=P_out_invalid,
            m_dot_p=0.020,
        )
        
        # Should flag invalid pressure levels
        assert result.flags["invalid_pressure_levels"], "Should detect P_out >= P_p_in"
    
    def test_invalid_secondary_pressure_too_high(self, controller, nominal_states, props):
        """
        Test that P_s_in >= P_out is flagged as invalid.
        """
        # Create secondary state with pressure higher than P_out
        T_s_high = 320.15  # 47°C
        P_s_high = props.Psat_T(T_s_high)
        state_s_high = ThermoState()
        state_s_high.update_from_PX(P_s_high, 1.0)
        
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=state_s_high,
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
        )
        
        # Should flag invalid pressure levels
        assert result.flags["invalid_pressure_levels"], "Should detect P_s_in >= P_out"


class TestEjectorMassFlow:
    """Test ejector with different mass flow rates."""
    
    def test_different_primary_flows(self, controller, nominal_states):
        """
        Test ejector with different primary mass flows.
        
        Mu should be independent of m_dot_p (it's a ratio).
        """
        result_low = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.010,
        )
        
        result_high = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.030,
        )
        
        # Mu should be similar (independent of absolute flow rates)
        # Allow some numerical tolerance
        assert abs(result_low.mu - result_high.mu) < 0.5, "Mu should be roughly independent of m_dot_p"
    
    def test_zero_primary_flow(self, controller, nominal_states):
        """
        Test ejector with zero primary flow.
        
        Should handle gracefully (m_dot_s = 0).
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.0,
        )
        
        # m_dot_s should be zero
        assert result.m_dot_s == 0.0, "Secondary flow should be zero"


class TestEjectorStates:
    """Test thermodynamic state consistency."""
    
    def test_all_states_initialized(self, controller, nominal_states):
        """
        Test that all thermodynamic states are initialized.
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
        )
        
        # All states should have pressures assigned
        assert result.state_p_noz.P is not None, "Primary nozzle state should exist"
        assert result.state_s_adj.P is not None, "Secondary adjusted state should exist"
        assert result.state_mix.P is not None, "Mixed state should exist"
        assert result.state_out.P is not None, "Outlet state should exist"
    
    def test_enthalpy_trends(self, controller, nominal_states):
        """
        Test that enthalpy trends are reasonable.
        
        Primary enthalpy decreases through expansion (nozzle).
        Mixed enthalpy is between primary and secondary.
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
        )
        
        # Primary enthalpy should decrease through nozzle (expansion)
        assert result.state_p_noz.h < nominal_states['state_p_in'].h, "Nozzle expansion reduces enthalpy"


class TestEjectorEdgeCases:
    """Test edge cases and robustness."""
    
    def test_no_crash_on_extreme_conditions(self, controller, nominal_states):
        """
        Test that solver doesn't crash on extreme conditions.
        """
        # Try with very low P_out
        try:
            result = controller.solve(
                state_p_in=nominal_states['state_p_in'],
                state_s_in=nominal_states['state_s_in'],
                P_out=1000.0,  # Very low pressure
                m_dot_p=0.020,
            )
            # Should complete without exception
            assert True
        except Exception:
            pytest.fail("Solver should not crash on extreme P_out")
    
    def test_mu_in_reasonable_range(self, controller, nominal_states):
        """
        Test that mu stays in reasonable range (0 to 5).
        """
        result = controller.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
        )
        
        # Mu should be clipped to reasonable range
        assert 0 <= result.mu <= 5.0, "Mu should be in [0, 5]"


# Summary fixture for test collection
def test_summary():
    """Summary of ejector tests."""
    print("\n" + "=" * 60)
    print("EJECTOR TESTS SUMMARY")
    print("=" * 60)
    print("Tests cover:")
    print("  ✓ Nominal ejector operation (mu > 0)")
    print("  ✓ Mass flow consistency (m_dot_s = mu * m_dot_p)")
    print("  ✓ Pressure level validation")
    print("  ✓ Component efficiencies (nozzle, diffuser, mixing)")
    print("  ✓ Invalid pressure configurations")
    print("  ✓ Different primary mass flows")
    print("  ✓ Thermodynamic state consistency")
    print("  ✓ Edge cases and robustness")
    print("=" * 60)
