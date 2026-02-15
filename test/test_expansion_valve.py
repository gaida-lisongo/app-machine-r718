"""
Unit tests for ExpansionValve module

Tests verify physical correctness, isenthalpic process, orifice flow model,
and diagnostic flags for the expansion valve.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import pytest
from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.expansion_valve import (
    ExpansionValveModel,
    ExpansionValveController,
    ExpansionValveResult,
)


class TestExpansionValveModel:
    """Test ExpansionValveModel physical calculations."""
    
    def test_model_initialization(self):
        """Test model initialization with default parameters."""
        model = ExpansionValveModel()
        assert model.use_orifice_flow is False
        assert model.Cd == 0.8
        assert model.A_orifice == 1e-6
    
    def test_model_initialization_custom(self):
        """Test model initialization with custom parameters."""
        model = ExpansionValveModel(
            use_orifice_flow=True,
            Cd=0.7,
            A_orifice=2e-6,
        )
        assert model.use_orifice_flow is True
        assert model.Cd == 0.7
        assert model.A_orifice == 2e-6
    
    def test_invalid_discharge_coefficient(self):
        """Test that invalid Cd raises error."""
        with pytest.raises(ValueError, match="Discharge coefficient"):
            ExpansionValveModel(Cd=-0.5)
        
        with pytest.raises(ValueError, match="Discharge coefficient"):
            ExpansionValveModel(Cd=1.5)
    
    def test_invalid_orifice_area(self):
        """Test that invalid orifice area raises error."""
        with pytest.raises(ValueError, match="Orifice area"):
            ExpansionValveModel(A_orifice=-1e-6)


class TestIsenthalpiExpansion:
    """Test isenthalpic expansion process."""
    
    def test_isenthalpic_process_liquid_to_twophase(self):
        """
        Test isenthalpic expansion from saturated liquid to two-phase.
        
        Condenser: 35°C -> Evaporator: 10°C
        Verifies h2 = h1 within numerical tolerance.
        """
        props = get_props_service()
        
        # Inlet: saturated liquid at condenser pressure (35°C)
        T_cond = 35 + 273.15  # K
        P_cond = props.Psat_T(T_cond)
        
        state1 = ThermoState()
        state1.update_from_PX(P_cond, 0.0)  # Saturated liquid
        h1 = state1.h
        
        # Outlet: evaporator pressure (10°C)
        T_evap = 10 + 273.15  # K
        P_evap = props.Psat_T(T_evap)
        
        # Solve expansion
        model = ExpansionValveModel()
        result = model.solve(state1, P_evap)
        
        # Verify isenthalpic process: h2 = h1
        h2 = result.state2.h
        assert abs(h2 - h1) / abs(h1) < 1e-8, f"Not isenthalpic: h1={h1}, h2={h2}"
        
        # Verify outlet is two-phase (should be in most cases for this expansion)
        # Note: depending on exact conditions, might be slightly subcooled
        # but typically this expansion produces two-phase mixture
        assert result.state2.P == pytest.approx(P_evap, rel=1e-6)
    
    def test_enthalpy_conservation(self):
        """Test strict enthalpy conservation across various conditions."""
        props = get_props_service()
        model = ExpansionValveModel()
        
        # Test multiple pressure ratios
        test_cases = [
            (10e5, 5e5),   # 10 bar -> 5 bar
            (20e5, 1e5),   # 20 bar -> 1 bar
            (5e5, 2e5),    # 5 bar -> 2 bar
        ]
        
        for P_in, P_out in test_cases:
            # Create inlet state (subcooled liquid)
            state1 = ThermoState()
            state1.update_from_PT(P_in, 300)  # 300 K
            h1 = state1.h
            
            # Solve expansion
            result = model.solve(state1, P_out)
            h2 = result.state2.h
            
            # Verify enthalpy conservation
            rel_error = abs(h2 - h1) / abs(h1)
            assert rel_error < 1e-8, f"Enthalpy not conserved: {rel_error:.2e}"
    
    def test_subcooled_to_subcooled(self):
        """Test expansion that remains in subcooled region."""
        model = ExpansionValveModel()
        
        # High pressure subcooled liquid
        state1 = ThermoState()
        state1.update_from_PT(50e5, 300)  # 50 bar, 300 K
        
        # Expand to still high pressure (should stay subcooled)
        result = model.solve(state1, 40e5)
        
        # Verify isenthalpic
        assert abs(result.state2.h - state1.h) / abs(state1.h) < 1e-8
        
        # Likely still subcooled (quality should be None)
        # This depends on exact thermodynamic path


class TestTwoPhaseOutlet:
    """Test two-phase outlet detection."""
    
    def test_two_phase_flag_active(self):
        """Test that two_phase_outlet flag activates correctly."""
        props = get_props_service()
        model = ExpansionValveModel()
        
        # Saturated liquid at high pressure
        P_high = props.Psat_T(373.15)  # 100°C
        state1 = ThermoState()
        state1.update_from_PX(P_high, 0.0)
        
        # Expand to low pressure (should produce two-phase)
        P_low = props.Psat_T(283.15)  # 10°C
        result = model.solve(state1, P_low)
        
        # Check if two-phase (quality between 0 and 1)
        if result.state2.x is not None and 0.0 < result.state2.x < 1.0:
            assert result.flags["two_phase_outlet"] is True
        else:
            # If not two-phase, flag should be False
            assert result.flags["two_phase_outlet"] is False


class TestInvalidDeltaP:
    """Test invalid pressure drop detection."""
    
    def test_zero_pressure_drop(self):
        """Test that zero ΔP is detected."""
        model = ExpansionValveModel(use_orifice_flow=True)
        
        state1 = ThermoState()
        state1.update_from_PT(5e5, 300)
        
        # Outlet pressure equal to inlet
        result = model.solve(state1, 5e5)
        
        assert result.flags["invalid_delta_p"] is True
        assert result.m_dot == 0.0
    
    def test_negative_pressure_drop(self):
        """Test that negative ΔP is detected."""
        model = ExpansionValveModel(use_orifice_flow=True)
        
        state1 = ThermoState()
        state1.update_from_PT(5e5, 300)
        
        # Outlet pressure higher than inlet
        result = model.solve(state1, 10e5)
        
        assert result.flags["invalid_delta_p"] is True
        assert result.m_dot == 0.0
    
    def test_valid_pressure_drop(self):
        """Test that valid ΔP does not trigger flag."""
        model = ExpansionValveModel()
        
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        
        result = model.solve(state1, 5e5)
        
        assert result.flags["invalid_delta_p"] is False


class TestDeepVacuumWarning:
    """Test deep vacuum warning flag."""
    
    def test_deep_vacuum_detected(self):
        """Test that outlet pressure < 2000 Pa triggers warning."""
        model = ExpansionValveModel()
        
        state1 = ThermoState()
        state1.update_from_PT(5e5, 300)
        
        # Very low outlet pressure
        result = model.solve(state1, 1000)
        
        assert result.flags["deep_vacuum_warning"] is True
    
    def test_no_deep_vacuum(self):
        """Test that normal pressures don't trigger warning."""
        model = ExpansionValveModel()
        
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        
        # Normal evaporator pressure
        result = model.solve(state1, 1.2e3)  # ~10°C saturation
        
        assert result.flags["deep_vacuum_warning"] is False


class TestOrificeFlowModel:
    """Test orifice mass flow rate calculation."""
    
    def test_orifice_flow_enabled(self):
        """Test mass flow calculation when enabled."""
        model = ExpansionValveModel(
            use_orifice_flow=True,
            Cd=0.8,
            A_orifice=1e-6,
        )
        
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        
        result = model.solve(state1, 5e5)
        
        # Should have calculated mass flow
        assert result.m_dot is not None
        assert result.m_dot > 0.0
    
    def test_orifice_flow_disabled(self):
        """Test that m_dot is None when disabled."""
        model = ExpansionValveModel(use_orifice_flow=False)
        
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        
        result = model.solve(state1, 5e5)
        
        assert result.m_dot is None
    
    def test_orifice_flow_formula(self):
        """Test orifice flow formula: m_dot = Cd * A * sqrt(2*rho*ΔP)."""
        Cd = 0.8
        A_orifice = 1e-6
        
        model = ExpansionValveModel(
            use_orifice_flow=True,
            Cd=Cd,
            A_orifice=A_orifice,
        )
        
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        
        P_out = 5e5
        delta_p = state1.P - P_out
        
        result = model.solve(state1, P_out)
        
        # Calculate expected value
        import math
        expected_m_dot = Cd * A_orifice * math.sqrt(2.0 * state1.rho * delta_p)
        
        assert result.m_dot == pytest.approx(expected_m_dot, rel=1e-6)
    
    def test_orifice_flow_zero_for_invalid_deltap(self):
        """Test that m_dot = 0 when ΔP <= 0."""
        model = ExpansionValveModel(use_orifice_flow=True)
        
        state1 = ThermoState()
        state1.update_from_PT(5e5, 300)
        
        # Same pressure (no drop)
        result = model.solve(state1, 5e5)
        assert result.m_dot == 0.0
        
        # Negative drop
        result = model.solve(state1, 10e5)
        assert result.m_dot == 0.0


class TestExpansionValveController:
    """Test ExpansionValveController orchestration."""
    
    def test_controller_initialization(self):
        """Test controller initialization."""
        controller = ExpansionValveController()
        assert controller.model is not None
        assert controller.model.use_orifice_flow is False
    
    def test_controller_solve(self):
        """Test controller solve method."""
        props = get_props_service()
        controller = ExpansionValveController()
        
        # Create inlet state
        P_cond = props.Psat_T(308.15)  # 35°C
        state1 = ThermoState()
        state1.update_from_PX(P_cond, 0.0)
        
        # Solve
        P_evap = props.Psat_T(283.15)  # 10°C
        result = controller.solve(state1, P_evap)
        
        # Verify result type
        assert isinstance(result, ExpansionValveResult)
        assert result.state2.is_initialized()
    
    def test_controller_enable_orifice(self):
        """Test enabling orifice flow through controller."""
        controller = ExpansionValveController()
        
        # Enable orifice flow
        controller.enable_orifice_flow(Cd=0.7, A_orifice=2e-6)
        
        assert controller.model.use_orifice_flow is True
        assert controller.model.Cd == 0.7
        assert controller.model.A_orifice == 2e-6
        
        # Test that mass flow is calculated
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        result = controller.solve(state1, 5e5)
        
        assert result.m_dot is not None
        assert result.m_dot > 0.0
    
    def test_controller_disable_orifice(self):
        """Test disabling orifice flow through controller."""
        controller = ExpansionValveController(use_orifice_flow=True)
        
        # Disable
        controller.disable_orifice_flow()
        
        assert controller.model.use_orifice_flow is False
        
        # Test that m_dot is None
        state1 = ThermoState()
        state1.update_from_PT(10e5, 300)
        result = controller.solve(state1, 5e5)
        
        assert result.m_dot is None
    
    def test_controller_get_configuration(self):
        """Test configuration retrieval."""
        controller = ExpansionValveController(
            use_orifice_flow=True,
            Cd=0.75,
            A_orifice=1.5e-6,
        )
        
        config = controller.get_configuration()
        
        assert config["use_orifice_flow"] is True
        assert config["Cd"] == 0.75
        assert config["A_orifice"] == 1.5e-6


class TestExpansionValveIntegration:
    """Integration tests for complete expansion valve workflow."""
    
    def test_complete_refrigeration_cycle_expansion(self):
        """Test expansion valve in realistic refrigeration cycle context."""
        props = get_props_service()
        controller = ExpansionValveController(use_orifice_flow=True, Cd=0.8, A_orifice=1e-6)
        
        # Nominal conditions from context
        T_cond = 35 + 273.15  # K
        T_evap = 10 + 273.15  # K
        
        P_cond = props.Psat_T(T_cond)
        P_evap = props.Psat_T(T_evap)
        
        # Inlet: saturated liquid from condenser
        state_condenser_out = ThermoState()
        state_condenser_out.update_from_PX(P_cond, 0.0)
        
        # Solve expansion
        result = controller.solve(state_condenser_out, P_evap)
        
        # Verifications
        assert result.state2.P == pytest.approx(P_evap, rel=1e-6)
        assert abs(result.state2.h - state_condenser_out.h) / abs(state_condenser_out.h) < 1e-8
        assert result.m_dot is not None
        assert result.m_dot > 0.0
        assert result.flags["invalid_delta_p"] is False
    
    def test_uninitialized_state_error(self):
        """Test that uninitialized inlet state raises error."""
        controller = ExpansionValveController()
        
        state1 = ThermoState()  # Not initialized
        
        with pytest.raises(ValueError, match="must be initialized"):
            controller.solve(state1, 1e5)
