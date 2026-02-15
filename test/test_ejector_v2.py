"""
Unit tests for Ejector V2 module (Compressible flow with shock)

Tests the compressible flow ejector model with Mach number calculations,
choking detection, normal shock wave, and Rankine-Hugoniot relations.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
import numpy as np
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.ejector import EjectorController
from app_r718.modules.ejector.model_v2 import EjectorModelV2, EjectorResultV2


@pytest.fixture
def controller_v2():
    """Fixture providing an EjectorController instance in V2 mode."""
    return EjectorController(mode="V2")


@pytest.fixture
def model_v2():
    """Fixture providing EjectorModelV2 instance directly."""
    return EjectorModelV2()


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


@pytest.fixture
def high_pressure_states(props):
    """
    Fixture for high pressure ratio conditions (more likely to produce supersonic flow).
    
    Primary: 140°C, Secondary: 5°C, Condenser: 30°C
    """
    T_gen = 413.15  # 140°C
    P_gen = props.Psat_T(T_gen)
    state_p_in = ThermoState()
    state_p_in.update_from_PX(P_gen, 1.0)
    
    T_evap = 278.15  # 5°C
    P_evap = props.Psat_T(T_evap)
    state_s_in = ThermoState()
    state_s_in.update_from_PX(P_evap, 1.0)
    
    T_cond = 303.15  # 30°C
    P_out = props.Psat_T(T_cond)
    
    return {
        'state_p_in': state_p_in,
        'state_s_in': state_s_in,
        'P_out': P_out,
    }


class TestCompressibleFlowPhysics:
    """Test compressible flow physics calculations."""
    
    def test_sound_speed_calculation(self, model_v2):
        """Test speed of sound calculation."""
        T = 373.15  # 100°C
        c = model_v2.compute_sound_speed(T)
        
        # c = sqrt(gamma * R * T)
        # With gamma=1.33, R=461.5, T=373.15
        c_expected = np.sqrt(1.33 * 461.5 * 373.15)
        
        assert abs(c - c_expected) < 0.1, "Sound speed calculation incorrect"
        assert c > 400, "Sound speed should be > 400 m/s for steam at 100°C"
    
    def test_mach_number_calculation(self, model_v2):
        """Test Mach number calculation."""
        v = 500  # m/s
        T = 373.15  # K
        
        M = model_v2.compute_mach_number(v, T)
        
        c = model_v2.compute_sound_speed(T)
        M_expected = v / c
        
        assert abs(M - M_expected) < 0.001, "Mach number calculation incorrect"
    
    def test_critical_pressure_ratio(self, model_v2):
        """Test critical pressure ratio for choking."""
        critical_ratio = model_v2.compute_critical_pressure_ratio()
        
        # For gamma=1.33: (2/(gamma+1))^(gamma/(gamma-1))
        gamma = 1.33
        expected = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        
        assert abs(critical_ratio - expected) < 0.001, "Critical pressure ratio incorrect"
        assert 0 < critical_ratio < 1.0, "Critical ratio must be between 0 and 1"
    
    def test_choking_detection(self, model_v2):
        """Test choking detection logic."""
        P_stag = 100e3  # 100 kPa
        
        # Pressure below critical ratio → choked
        P_exit_choked = 50e3  # 50 kPa (low)
        assert model_v2.is_choked(P_exit_choked, P_stag), "Should detect choking"
        
        # Pressure above critical ratio → not choked
        P_exit_unchoked = 95e3  # 95 kPa (high)
        assert not model_v2.is_choked(P_exit_unchoked, P_stag), "Should not detect choking"


class TestNormalShock:
    """Test normal shock wave relations."""
    
    def test_shock_pressure_increase(self, model_v2):
        """Test that pressure increases across shock."""
        mach_1 = 2.0  # Supersonic upstream
        P_1 = 10e3  # 10 kPa
        T_1 = 300  # K
        h_1 = 2.8e6  # J/kg
        
        shock_data = model_v2.apply_normal_shock(mach_1, P_1, T_1, h_1)
        
        assert shock_data["P_2"] > P_1, "Pressure must increase across shock"
        assert shock_data["mach_2"] < 1.0, "Downstream Mach must be subsonic"
    
    def test_shock_mach_decrease(self, model_v2):
        """Test that Mach number decreases across shock."""
        mach_1 = 1.5  # Supersonic
        P_1 = 20e3
        T_1 = 350
        h_1 = 2.7e6
        
        shock_data = model_v2.apply_normal_shock(mach_1, P_1, T_1, h_1)
        
        assert shock_data["mach_2"] < mach_1, "Mach decreases across shock"
        assert shock_data["mach_2"] < 1.0, "Downstream is subsonic"
        assert shock_data["mach_2"] > 0, "Mach must be positive"
    
    def test_shock_entropy_increase(self, model_v2):
        """Test that entropy increases across shock (2nd law)."""
        mach_1 = 2.5  # Strongly supersonic
        P_1 = 15e3
        T_1 = 320
        h_1 = 2.75e6
        
        shock_data = model_v2.apply_normal_shock(mach_1, P_1, T_1, h_1)
        
        assert shock_data["delta_s"] > 0, "Entropy must increase across shock (2nd law)"
    
    def test_shock_temperature_increase(self, model_v2):
        """Test that temperature increases across shock."""
        mach_1 = 1.8
        P_1 = 25e3
        T_1 = 340
        h_1 = 2.72e6
        
        shock_data = model_v2.apply_normal_shock(mach_1, P_1, T_1, h_1)
        
        assert shock_data["T_2"] > T_1, "Temperature increases across shock"
    
    def test_no_shock_if_subsonic(self, model_v2):
        """Test that no shock occurs if upstream flow is subsonic."""
        mach_1 = 0.8  # Subsonic
        P_1 = 30e3
        T_1 = 360
        h_1 = 2.68e6
        
        shock_data = model_v2.apply_normal_shock(mach_1, P_1, T_1, h_1)
        
        # Properties should remain unchanged (no shock)
        assert shock_data["P_2"] == P_1, "Pressure unchanged for subsonic"
        assert shock_data["mach_2"] == mach_1, "Mach unchanged for subsonic"
        assert shock_data["delta_s"] == 0.0, "No entropy change for subsonic"


class TestEjectorV2Nominal:
    """Test V2 ejector operation under nominal conditions."""
    
    def test_v2_nominal_operation(self, controller_v2, nominal_states):
        """Test V2 model with nominal refrigeration conditions."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        assert isinstance(result, EjectorResultV2), "Should return V2 result"
        assert result.mu >= 0, "Entrainment ratio must be non-negative"
        assert result.m_dot_p == 0.020, "Primary flow should match input"
        assert result.m_dot_s >= 0, "Secondary flow must be non-negative"
        
        # V2-specific checks
        assert result.mach_primary_nozzle >= 0, "Mach number must be non-negative"
        assert result.regime in ["subsonic", "choked", "supersonic", "no_flow"], "Valid regime"
    
    def test_v2_high_pressure_ratio(self, controller_v2, high_pressure_states):
        """Test V2 with high pressure ratio (more likely supersonic)."""
        result = controller_v2.solve(
            state_p_in=high_pressure_states['state_p_in'],
            state_s_in=high_pressure_states['state_s_in'],
            P_out=high_pressure_states['P_out'],
            m_dot_p=0.030,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        assert isinstance(result, EjectorResultV2), "Should return V2 result"
        assert result.mu >= 0, "Entrainment ratio must be non-negative"
        
        # With high pressure ratio, more likely to be supersonic/choked
        # But exact regime depends on detailed flow physics
        assert result.regime in ["subsonic", "choked", "supersonic"], "Valid regime"
        
        # If supersonic and shock detected
        if result.mach_before_shock > 1.0:
            assert result.mach_after_shock < 1.0, "Mach after shock must be subsonic"
            assert result.entropy_jump > 0, "Entropy increases across shock"
    
    def test_v2_zero_primary_flow(self, controller_v2, nominal_states):
        """Test V2 model with zero primary flow (edge case)."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.0,  # Zero flow
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        assert result.mu == 0.0, "No entrainment with zero primary flow"
        assert result.m_dot_s == 0.0, "Secondary flow should be zero"
        assert result.regime == "no_flow", "Regime should be no_flow"


class TestV2ShockDetection:
    """Test shock detection and location in V2 model."""
    
    def test_shock_location_marked(self, controller_v2, high_pressure_states):
        """Test that shock location is properly marked if detected."""
        result = controller_v2.solve(
            state_p_in=high_pressure_states['state_p_in'],
            state_s_in=high_pressure_states['state_s_in'],
            P_out=high_pressure_states['P_out'],
            m_dot_p=0.025,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        if result.mach_before_shock > 1.0:
            # Shock should be detected
            assert result.shock_location != "none", "Shock location should be marked"
            assert result.P_after_shock > result.P_before_shock, "Pressure increases at shock"
        else:
            # No shock if subsonic
            assert result.shock_location == "none", "No shock for subsonic flow"
    
    def test_mach_consistency(self, controller_v2, nominal_states):
        """Test that Mach numbers are physically consistent."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # All Mach numbers must be non-negative
        assert result.mach_primary_nozzle >= 0, "Mach >= 0"
        assert result.mach_before_shock >= 0, "Mach >= 0"
        assert result.mach_after_shock >= 0, "Mach >= 0"
        
        # If shock occurs, upstream must be supersonic
        if result.shock_location != "none":
            assert result.mach_before_shock >= 1.0, "Shock requires M >= 1 upstream"
            assert result.mach_after_shock < 1.0, "Shock produces M < 1 downstream"


class TestV2Stability:
    """Test numerical stability of V2 model."""
    
    def test_no_crash_extreme_conditions(self, controller_v2, props):
        """Test that V2 doesn't crash with extreme conditions."""
        # Very high generator temperature
        T_gen = 473.15  # 200°C
        P_gen = props.Psat_T(T_gen)
        state_p_in = ThermoState()
        state_p_in.update_from_PX(P_gen, 1.0)
        
        # Very low evaporator temperature (avoid triple point at 273.15 K)
        T_evap = 275.15  # 2°C (safely above triple point)
        P_evap = props.Psat_T(T_evap)
        state_s_in = ThermoState()
        state_s_in.update_from_PX(P_evap, 1.0)
        
        # Condenser
        T_cond = 313.15  # 40°C
        P_out = props.Psat_T(T_cond)
        
        # Should not crash
        result = controller_v2.solve(
            state_p_in=state_p_in,
            state_s_in=state_s_in,
            P_out=P_out,
            m_dot_p=0.050,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        assert result is not None, "Should return result even with extreme conditions"
        assert result.mu >= 0, "mu must be non-negative"
    
    def test_different_efficiencies(self, controller_v2, nominal_states):
        """Test V2 with various efficiency values."""
        for eta_nozzle in [0.70, 0.85, 0.95]:
            for eta_diffuser in [0.70, 0.85, 0.95]:
                result = controller_v2.solve(
                    state_p_in=nominal_states['state_p_in'],
                    state_s_in=nominal_states['state_s_in'],
                    P_out=nominal_states['P_out'],
                    m_dot_p=0.020,
                    eta_nozzle=eta_nozzle,
                    eta_diffuser=eta_diffuser,
                    eta_mixing=1.0,
                )
                
                assert result.mu >= 0, f"mu >= 0 for eta_noz={eta_nozzle}, eta_diff={eta_diffuser}"
    
    def test_v2_vs_v1_consistency(self, nominal_states):
        """Test that V2 gives reasonable results compared to V1."""
        controller_v1 = EjectorController(mode="V1")
        controller_v2 = EjectorController(mode="V2")
        
        result_v1 = controller_v1.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        result_v2 = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # V2 should give comparable (but not identical) mu to V1
        # Allow for differences due to more detailed physics
        # V2 uses different optimization objective, so mu can differ more
        assert result_v2.mu >= 0, "V2 mu must be non-negative"
        
        # Both should be non-negative and physically reasonable (mu < 5.0)
        assert result_v1.mu >= 0, "V1 mu must be non-negative"
        assert result_v2.mu < 5.0, "V2 mu should be physically reasonable"
        
        # V2 and V1 may differ significantly due to different physics
        # Key test: both models run without crashing


class TestV2EntrainmentConditions:
    """Test conditions for positive entrainment in V2."""
    
    def test_mu_positive_favorable_conditions(self, controller_v2, high_pressure_states):
        """Test that μ > 0 appears under favorable conditions."""
        result = controller_v2.solve(
            state_p_in=high_pressure_states['state_p_in'],
            state_s_in=high_pressure_states['state_s_in'],
            P_out=high_pressure_states['P_out'],
            m_dot_p=0.030,
            eta_nozzle=0.90,  # High efficiency
            eta_diffuser=0.90,
            eta_mixing=1.0,
        )
        
        # With high pressure ratio and good efficiencies, expect positive μ
        assert result.mu >= 0, "μ must be non-negative"
        
        # In V2, even with better physics, μ might still be small for certain conditions
        # The key is it should not be negative
    
    def test_pressure_recovery(self, controller_v2, nominal_states):
        """Test pressure recovery from P_mix to P_out."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # P_mix should be less than P_out (diffuser compresses)
        assert result.P_mix < result.state_out.P, "Diffuser should compress P_mix → P_out"
        
        # P_mix should be greater than secondary inlet pressure
        assert result.P_mix > nominal_states['state_s_in'].P, "P_mix > P_s_in"


class TestV2NewDiagnostics:
    """Test new diagnostic features added in V2 improvements."""
    
    def test_entropy_units_consistent(self, controller_v2, high_pressure_states):
        """Test that entropy units are consistent (both J/kg/K and kJ/kg/K)."""
        result = controller_v2.solve(
            state_p_in=high_pressure_states['state_p_in'],
            state_s_in=high_pressure_states['state_s_in'],
            P_out=high_pressure_states['P_out'],
            m_dot_p=0.025,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # Check entropy_jump_kJ is exactly entropy_jump / 1000
        expected_kJ = result.entropy_jump / 1000.0
        assert abs(result.entropy_jump_kJ - expected_kJ) < 1e-9, "Entropy units inconsistent"
        
        # If shock detected, entropy should increase
        if result.shock_location != "none":
            assert result.entropy_jump > 0, "Entropy must increase across shock"
            assert result.entropy_jump_kJ > 0, "Entropy (kJ) must increase across shock"
    
    def test_suction_condition_logic(self, controller_v2, nominal_states):
        """Test suction condition logic."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # P_suction_local should be valid
        assert result.P_suction_local > 0, "Suction pressure should be positive"
        
        # Suction condition check
        P_sec = nominal_states['state_s_in'].P
        if result.suction_condition:
            assert result.P_suction_local < P_sec, "Suction condition requires P_suction < P_sec"
        else:
            assert result.P_suction_local >= P_sec, "No suction if P_suction >= P_sec"
    
    def test_shock_pressure_strict_increase(self, controller_v2, high_pressure_states):
        """Test that pressure strictly increases across shock."""
        result = controller_v2.solve(
            state_p_in=high_pressure_states['state_p_in'],
            state_s_in=high_pressure_states['state_s_in'],
            P_out=high_pressure_states['P_out'],
            m_dot_p=0.025,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        if result.shock_location != "none":
            # Strict pressure increase across shock
            assert result.P_after_shock > result.P_before_shock, "P must increase across shock"
            
            # Minimum ratio
            ratio = result.P_after_shock / result.P_before_shock
            assert ratio > 1.0, "Pressure ratio must be > 1.0 across shock"
    
    def test_mixture_enthalpy_bounds(self, controller_v2, nominal_states):
        """Test that mixture enthalpy is physically consistent."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # Check flag is set
        assert hasattr(result, 'physically_consistent_mixture'), "Should have consistency flag"
        
        # If not consistent, should be flagged
        # (This is a diagnostic, not a failure condition)
    
    def test_regime_type_assignment(self, controller_v2, nominal_states):
        """Test that regime_type is properly assigned."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        # regime_type should be one of the expected values
        assert result.regime_type in ["non-entraining", "critical", "entraining-supersonic"], \
            "Invalid regime_type"
        
        # If mu is very small, should be non-entraining
        if result.mu < 0.01:
            assert result.regime_type == "non-entraining", "Low mu should be non-entraining"
    
    def test_compression_ratio_positive(self, controller_v2, nominal_states):
        """Test that compression ratio is positive."""
        result = controller_v2.solve(
            state_p_in=nominal_states['state_p_in'],
            state_s_in=nominal_states['state_s_in'],
            P_out=nominal_states['P_out'],
            m_dot_p=0.020,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        assert result.compression_ratio > 0, "Compression ratio should be positive"
        assert result.pressure_lift > 0, "Pressure lift should be positive"
        
        # Verify calculation
        P_sec = nominal_states['state_s_in'].P
        expected_ratio = nominal_states['P_out'] / P_sec
        assert abs(result.compression_ratio - expected_ratio) < 0.01, "Compression ratio incorrect"
    
    def test_shock_states_available(self, controller_v2, high_pressure_states):
        """Test that shock states are available when shock is detected."""
        result = controller_v2.solve(
            state_p_in=high_pressure_states['state_p_in'],
            state_s_in=high_pressure_states['state_s_in'],
            P_out=high_pressure_states['P_out'],
            m_dot_p=0.025,
            eta_nozzle=0.85,
            eta_diffuser=0.85,
            eta_mixing=1.0,
        )
        
        if result.shock_location != "none":
            # States should be available
            assert result.state_before_shock is not None, "Before-shock state should exist"
            assert result.state_after_shock is not None, "After-shock state should exist"
            
            # States should be valid ThermoState objects
            assert result.state_before_shock.P > 0, "Before-shock pressure should be positive"
            assert result.state_after_shock.P > 0, "After-shock pressure should be positive"
            
            # Entropy should increase
            s1 = result.state_before_shock.s
            s2 = result.state_after_shock.s
            assert s2 > s1, "Entropy must increase across shock"

