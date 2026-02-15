"""
ExpansionValve View - Display and reporting functionality

Handles all output formatting for expansion valve results.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from typing import Optional
from app_r718.modules.expansion_valve.model import ExpansionValveResult


class ExpansionValveView:
    """
    View component for expansion valve visualization.
    
    Responsible for formatting and displaying expansion valve results.
    No computation should occur here - only presentation.
    """
    
    @staticmethod
    def display_result(result: ExpansionValveResult, verbose: bool = True) -> None:
        """
        Display expansion valve calculation results.
        
        Args:
            result: Calculation results to display
            verbose: If True, show detailed state information
        """
        print("=" * 60)
        print("EXPANSION VALVE RESULTS")
        print("=" * 60)
        
        # Display inlet/outlet states
        if verbose:
            print("\nOutlet State:")
            print(f"  {result.state2}")
        else:
            print(f"\n  P_out = {result.state2.P:.2e} Pa")
            print(f"  T_out = {result.state2.T:.2f} K ({result.state2.T - 273.15:.2f} °C)")
            print(f"  h_out = {result.state2.h:.2e} J/kg")
        
        # Display mass flow if calculated
        if result.m_dot is not None:
            print(f"\n  Mass flow rate = {result.m_dot:.6f} kg/s")
        
        # Display flags
        print("\nDiagnostic Flags:")
        for flag_name, flag_value in result.flags.items():
            status = "⚠️  ACTIVE" if flag_value else "✓ OK"
            print(f"  {flag_name}: {status}")
        
        print("=" * 60)
    
    @staticmethod
    def display_summary(result: ExpansionValveResult) -> None:
        """
        Display compact summary of results.
        
        Args:
            result: Calculation results to summarize
        """
        print(f"Expansion Valve: P_out={result.state2.P/1e5:.2f} bar, "
              f"T_out={result.state2.T-273.15:.1f}°C", end="")
        
        if result.m_dot is not None:
            print(f", m_dot={result.m_dot:.6f} kg/s", end="")
        
        # Show warnings if any
        active_flags = [k for k, v in result.flags.items() if v]
        if active_flags:
            print(f" [WARNINGS: {', '.join(active_flags)}]")
        else:
            print()
    
    @staticmethod
    def format_report(result: ExpansionValveResult) -> str:
        """
        Generate formatted text report.
        
        Args:
            result: Calculation results
            
        Returns:
            Formatted string report
        """
        lines = []
        lines.append("EXPANSION VALVE REPORT")
        lines.append("-" * 40)
        
        # Outlet conditions
        lines.append(f"Outlet Pressure:    {result.state2.P/1e5:.3f} bar")
        lines.append(f"Outlet Temperature: {result.state2.T:.2f} K ({result.state2.T-273.15:.2f} °C)")
        lines.append(f"Outlet Enthalpy:    {result.state2.h/1e3:.2f} kJ/kg")
        
        if result.state2.x is not None:
            lines.append(f"Outlet Quality:     {result.state2.x:.4f} [-]")
        
        # Mass flow if available
        if result.m_dot is not None:
            lines.append(f"Mass Flow Rate:     {result.m_dot:.6f} kg/s")
        
        # Flags
        lines.append("\nDiagnostic Status:")
        for flag_name, flag_value in result.flags.items():
            status = "ACTIVE" if flag_value else "OK"
            lines.append(f"  {flag_name:20s}: {status}")
        
        return "\n".join(lines)
    
    @staticmethod
    def check_warnings(result: ExpansionValveResult) -> None:
        """
        Display only active warnings.
        
        Args:
            result: Calculation results to check
        """
        active_warnings = {k: v for k, v in result.flags.items() if v}
        
        if not active_warnings:
            print("✓ No warnings detected")
            return
        
        print("⚠️  WARNINGS DETECTED:")
        for flag_name in active_warnings:
            if flag_name == "deep_vacuum_warning":
                print(f"  • {flag_name}: Outlet pressure below 2000 Pa (deep vacuum)")
            elif flag_name == "two_phase_outlet":
                print(f"  • {flag_name}: Outlet is in two-phase region")
            elif flag_name == "invalid_delta_p":
                print(f"  • {flag_name}: Pressure drop is zero or negative")
            else:
                print(f"  • {flag_name}: Active")
