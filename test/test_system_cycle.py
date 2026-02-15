"""
Unit tests for complete system cycle model

Tests state numbering consistency and thermodynamic coherence.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.modules.system_dashboard.model import SystemCycleModel
from app_r718.core.props_service import get_props_service


class TestSystemCycleStates:
    """Test thermodynamic state numbering and consistency."""
    
    def setup_method(self):
        """Initialize model and Props service for each test."""
        self.model = SystemCycleModel()
        self.props = get_props_service()
    
    def test_state_numbering_complete(self):
        """Test that all states 1-8 are present in result."""
        result = self.model.solve_cycle(
            T_gen=373.15,  # 100°C
            T_evap=283.15,  # 10°C
            T_cond=308.15,  # 35°C
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        # All states must be present
        for state_num in [1, 2, 3, 4, 5, 6, 7, 8]:
            assert state_num in result.states, f"State {state_num} missing from results"
            assert result.states[state_num].is_initialized(), f"State {state_num} not initialized"
    
    def test_state_2_is_two_phase(self):
        """Test that state 2 (expansion valve outlet) is two-phase."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_2 = result.states[2]
        
        # State 2 must be two-phase (0 < x < 1)
        assert state_2.x is not None, "State 2 quality is None (should be two-phase)"
        assert 0.0 < state_2.x < 1.0, f"State 2 quality x={state_2.x} not in (0,1)"
    
    def test_state_3_is_saturated_vapor(self):
        """Test that state 3 (evaporator outlet) is saturated vapor."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_3 = result.states[3]
        
        # State 3 must be saturated vapor (x = 1.0)
        assert state_3.x is not None, "State 3 quality is None"
        assert abs(state_3.x - 1.0) < 1e-6, f"State 3 quality x={state_3.x} not saturated vapor (x=1)"
    
    def test_state_2_enthalpy_equals_state_1(self):
        """Test that h2 = h1 (isenthalpic expansion)."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_1 = result.states[1]
        state_2 = result.states[2]
        
        # Isenthalpic expansion: h2 = h1 (within tolerance)
        h_diff = abs(state_2.h - state_1.h)
        assert h_diff < 100.0, f"h2 != h1: h1={state_1.h:.1f} J/kg, h2={state_2.h:.1f} J/kg, Δh={h_diff:.1f} J/kg"
    
    def test_state_2_pressure_equals_evap_pressure(self):
        """Test that P2 = P_evap."""
        T_evap = 283.15  # 10°C
        P_evap_expected = self.props.Psat_T(T_evap)
        
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=T_evap,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_2 = result.states[2]
        
        # Pressure must match evaporator pressure
        P_diff_rel = abs(state_2.P - P_evap_expected) / P_evap_expected
        assert P_diff_rel < 1e-3, f"P2 != P_evap: P2={state_2.P:.1f} Pa, P_evap={P_evap_expected:.1f} Pa"
    
    def test_state_3_pressure_equals_evap_pressure(self):
        """Test that P3 = P_evap."""
        T_evap = 283.15  # 10°C
        P_evap_expected = self.props.Psat_T(T_evap)
        
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=T_evap,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_3 = result.states[3]
        
        # Pressure must match evaporator pressure
        P_diff_rel = abs(state_3.P - P_evap_expected) / P_evap_expected
        assert P_diff_rel < 1e-3, f"P3 != P_evap: P3={state_3.P:.1f} Pa, P_evap={P_evap_expected:.1f} Pa"
    
    def test_state_3_enthalpy_greater_than_state_2(self):
        """Test that h3 > h2 (energy added by evaporation)."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_3 = result.states[3]
        state_2 = result.states[2]
        
        # Evaporation adds energy: h3 > h2
        assert state_3.h > state_2.h, f"h3 ({state_3.h:.1f}) <= h2 ({state_2.h:.1f}) - evaporation should add energy"
    
    def test_state_1_is_saturated_liquid(self):
        """Test that state 1 (sortie condenseur) is saturated liquid."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_1 = result.states[1]
        
        # State 1 must be saturated liquid (x = 0.0)
        assert state_1.x is not None, "State 1 quality is None"
        assert abs(state_1.x - 0.0) < 1e-6, f"State 1 quality x={state_1.x} not saturated liquid (x=0)"
    
    def test_state_6_is_saturated_liquid(self):
        """Test that state 6 (sortie condenseur) is saturated liquid."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_6 = result.states[6]
        
        # State 6 must be saturated liquid (x = 0.0)
        assert state_6.x is not None, "State 6 quality is None"
        assert abs(state_6.x - 0.0) < 1e-6, f"State 6 quality x={state_6.x} not saturated liquid (x=0)"
    
    def test_state_8_is_saturated_vapor(self):
        """Test that state 8 (sortie chaudière) is saturated vapor."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_8 = result.states[8]
        
        # State 8 must be saturated vapor (x = 1.0)
        assert state_8.x is not None, "State 8 quality is None"
        assert abs(state_8.x - 1.0) < 1e-6, f"State 8 quality x={state_8.x} not saturated vapor (x=1)"
    
    def test_state_7_is_compressed_liquid(self):
        """Test that state 7 (sortie pompe) is compressed liquid."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_7 = result.states[7]
        
        # State 7 should be liquid (x = 0 or None for subcooled liquid)
        # It's compressed liquid, so either x=0 or x=None
        if state_7.x is not None:
            assert state_7.x < 0.01, f"State 7 quality x={state_7.x} should be liquid (x≈0)"
    
    def test_state_6_pressure_equals_cond_pressure(self):
        """Test that P6 = P_cond (sortie condenseur)."""
        T_cond = 308.15  # 35°C
        P_cond_expected = self.props.Psat_T(T_cond)
        
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=T_cond,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_6 = result.states[6]
        
        # Pressure must match condenser pressure
        P_diff_rel = abs(state_6.P - P_cond_expected) / P_cond_expected
        assert P_diff_rel < 0.1, f"P6 != P_cond: P6={state_6.P:.1f} Pa, P_cond={P_cond_expected:.1f} Pa"
    
    def test_state_5_pressure_equals_cond_pressure(self):
        """Test that P5 ≈ P_cond (sortie diffuseur éjecteur)."""
        T_cond = 308.15  # 35°C
        P_cond_expected = self.props.Psat_T(T_cond)
        
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=T_cond,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        state_5 = result.states[5]
        
        # Diffuser outlet pressure should be close to condenser pressure
        P_diff_rel = abs(state_5.P - P_cond_expected) / P_cond_expected
        assert P_diff_rel < 0.1, f"P5 far from P_cond: P5={state_5.P:.1f} Pa, P_cond={P_cond_expected:.1f} Pa"


class TestSystemCycleInverseDimensioning:
    """Test inverse dimensioning mode (Q_evap_target specified)."""
    
    def setup_method(self):
        """Initialize model for each test."""
        self.model = SystemCycleModel()
    
    def test_inverse_dimensioning_converges(self):
        """Test that inverse dimensioning converges to target Q_evap."""
        Q_target = 12.0  # kW
        
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            Q_evap_target=Q_target,  # Inverse mode
            use_ejector_v2=True,
        )
        
        # Check convergence
        assert result.flags.get('success', False), "Inverse dimensioning failed"
        assert not result.flags.get('dimensioning_not_converged', False), "Did not converge"
        
        # Check Q_evap close to target (within 1% tolerance)
        Q_evap_actual = result.metrics['Q_evap']
        error_rel = abs(Q_evap_actual - Q_target) / Q_target
        assert error_rel < 0.01, f"Q_evap={Q_evap_actual:.2f} kW not close to target {Q_target} kW (error: {error_rel*100:.1f}%)"
    
    def test_inverse_dimensioning_states_valid(self):
        """Test that inverse dimensioning produces valid states."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            Q_evap_target=12.0,
            use_ejector_v2=True,
        )
        
        # All states must still be present and valid
        for state_num in [1, 2, 3, 4, 5, 6, 7, 8]:
            assert state_num in result.states, f"State {state_num} missing"
            assert result.states[state_num].is_initialized(), f"State {state_num} not initialized"
        
        # State 6 must still be two-phase
        assert result.states[6].x is not None
        assert 0.0 < result.states[6].x < 1.0
        
        # State 5 must still be saturated vapor
        assert abs(result.states[5].x - 1.0) < 1e-6


class TestSystemCycleMetrics:
    """Test performance metrics calculation."""
    
    def setup_method(self):
        """Initialize model for each test."""
        self.model = SystemCycleModel()
    
    def test_cop_positive(self):
        """Test that COP is positive."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        COP = result.metrics['COP']
        assert COP > 0, f"COP={COP} should be positive"
        assert COP < 10, f"COP={COP} unrealistically high"
    
    def test_entrainment_ratio_positive(self):
        """Test that entrainment ratio mu is positive."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        mu = result.metrics['mu']
        assert mu > 0, f"Entrainment ratio mu={mu} should be positive"
        assert mu < 5, f"Entrainment ratio mu={mu} unrealistically high"
    
    def test_mass_flow_consistency(self):
        """Test that m_dot_total = m_dot_p + m_dot_s."""
        result = self.model.solve_cycle(
            T_gen=373.15,
            T_evap=283.15,
            T_cond=308.15,
            m_dot_p=0.02,
            use_ejector_v2=True,
        )
        
        m_dot_p = result.metrics['m_dot_p']
        m_dot_s = result.metrics['m_dot_s']
        m_dot_total = result.metrics['m_dot_total']
        
        m_dot_sum = m_dot_p + m_dot_s
        diff = abs(m_dot_total - m_dot_sum)
        assert diff < 1e-9, f"Mass flow inconsistency: m_total={m_dot_total}, m_p+m_s={m_dot_sum}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
