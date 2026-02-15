"""
ExpansionValve View - Display and reporting functionality

Handles all output formatting for expansion valve results.
Includes both console output and Tkinter GUI.

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


class ExpansionValveTkView:
    """
    Tkinter-based GUI view for expansion valve simulation.
    
    Provides interactive interface with input fields, simulation button,
    results display, and P-h/P-s diagram visualization.
    """
    
    @staticmethod
    def _compute_saturation_curve(P_min: float = 500.0, P_max: float = 2e6, n_points: int = 200):
        """
        Compute saturation curves for P-h and P-s diagrams.
        
        Args:
            P_min: Minimum pressure [Pa]
            P_max: Maximum pressure [Pa]
            n_points: Number of points
            
        Returns:
            Tuple of (P_array, hl_array, hv_array, sl_array, sv_array)
        """
        import numpy as np
        from app_r718.core.props_service import get_props_service
        
        props = get_props_service()
        
        # Log-spaced pressure array
        P_sat = np.logspace(np.log10(P_min), np.log10(P_max), n_points)
        
        hl_array = []
        hv_array = []
        sl_array = []
        sv_array = []
        
        for P in P_sat:
            try:
                hl = props.hl_P(P)
                hv = props.hv_P(P)
                sl = props.sl_P(P)
                sv = props.sv_P(P)
                
                hl_array.append(hl)
                hv_array.append(hv)
                sl_array.append(sl)
                sv_array.append(sv)
            except:
                # Skip points where saturation calculation fails
                continue
        
        return P_sat[:len(hl_array)], np.array(hl_array), np.array(hv_array), np.array(sl_array), np.array(sv_array)
    
    @staticmethod
    def open_window(parent):
        """
        Open expansion valve simulation window.
        
        Args:
            parent: Parent Tkinter window
        """
        # Import Tkinter and Matplotlib here to avoid issues in headless environments
        import tkinter as tk
        from tkinter import ttk, messagebox
        import matplotlib
        matplotlib.use('TkAgg')
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
        
        from app_r718.core.thermo_state import ThermoState
        from app_r718.core.props_service import get_props_service
        from app_r718.modules.expansion_valve import ExpansionValveController
        
        # Create Toplevel window
        window = tk.Toplevel(parent)
        window.title("Détendeur (Expansion Valve) - Simulation")
        window.geometry("1000x700")
        
        # Controller instance
        controller = ExpansionValveController()
        
        # Variables
        var_P_in = tk.StringVar(value="1000000")  # 10 bar
        var_T_in = tk.StringVar(value="308.15")   # 35°C
        var_P_out = tk.StringVar(value="1227")    # ~10°C saturation for R718
        var_use_orifice = tk.BooleanVar(value=False)
        var_Cd = tk.StringVar(value="0.8")
        var_A_orifice = tk.StringVar(value="1e-6")
        
        # Results storage
        result_data = {"result": None, "state1": None}
        
        # ========== LEFT PANEL: Inputs ==========
        left_frame = ttk.Frame(window, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Title
        ttk.Label(
            left_frame,
            text="Paramètres d'entrée",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        # Inlet conditions
        ttk.Label(left_frame, text="Conditions d'entrée:", font=("Arial", 10, "bold")).grid(
            row=1, column=0, columnspan=2, pady=5, sticky="w"
        )
        
        ttk.Label(left_frame, text="Pression entrée P_in [Pa]:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_P_in, width=20).grid(row=2, column=1, pady=2)
        
        ttk.Label(left_frame, text="Température entrée T_in [K]:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_T_in, width=20).grid(row=3, column=1, pady=2)
        
        ttk.Label(left_frame, text="Pression sortie P_out [Pa]:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_P_out, width=20).grid(row=4, column=1, pady=2)
        
        # Separator
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        # Orifice model
        ttk.Label(left_frame, text="Modèle d'orifice:", font=("Arial", 10, "bold")).grid(
            row=6, column=0, columnspan=2, pady=5, sticky="w"
        )
        
        ttk.Checkbutton(
            left_frame,
            text="Activer calcul débit orifice",
            variable=var_use_orifice,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=2)
        
        ttk.Label(left_frame, text="Coefficient de décharge Cd [-]:").grid(row=8, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_Cd, width=20).grid(row=8, column=1, pady=2)
        
        ttk.Label(left_frame, text="Aire orifice A [m²]:").grid(row=9, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_A_orifice, width=20).grid(row=9, column=1, pady=2)
        
        # Simulate button
        def simulate():
            try:
                # Parse inputs
                P_in = float(var_P_in.get())
                T_in = float(var_T_in.get())
                P_out = float(var_P_out.get())
                use_orifice = var_use_orifice.get()
                Cd = float(var_Cd.get())
                A_orifice = float(var_A_orifice.get())
                
                # Validate
                if P_in <= 0:
                    raise ValueError("P_in doit être positif")
                if T_in <= 0:
                    raise ValueError("T_in doit être positif")
                if P_out <= 0:
                    raise ValueError("P_out doit être positif")
                
                # Configure controller
                if use_orifice:
                    controller.enable_orifice_flow(Cd=Cd, A_orifice=A_orifice)
                else:
                    controller.disable_orifice_flow()
                
                # Create inlet state
                state1 = ThermoState()
                state1.update_from_PT(P_in, T_in)
                
                # Solve
                result = controller.solve(state1, P_out)
                
                # Store results
                result_data["result"] = result
                result_data["state1"] = state1
                
                # Display results
                display_results(result, state1)
                plot_ph_diagram(result, state1)
                
            except ValueError as e:
                messagebox.showerror("Erreur de saisie", str(e))
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la simulation:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="▶ Simuler",
            command=simulate,
            width=20,
        ).grid(row=10, column=0, columnspan=2, pady=20)
        
        # ========== RIGHT PANEL: Results ==========
        right_frame = ttk.Frame(window, padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Results title
        ttk.Label(
            right_frame,
            text="Résultats de simulation",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, pady=10, sticky="w")
        
        # Results text widget
        results_text = tk.Text(right_frame, width=50, height=15, wrap="word")
        results_text.grid(row=1, column=0, sticky="nsew", pady=5)
        
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=results_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        results_text.config(yscrollcommand=scrollbar.set)
        
        def display_results(result: ExpansionValveResult, state1: ThermoState):
            """Display simulation results in text widget."""
            results_text.delete("1.0", "end")
            
            output = []
            output.append("=" * 50)
            output.append("RÉSULTATS - DÉTENDEUR")
            output.append("=" * 50)
            output.append("")
            
            # State 1 (inlet)
            output.append("📥 État d'entrée (1):")
            output.append(f"  P₁ = {state1.P/1e5:.3f} bar ({state1.P:.2e} Pa)")
            output.append(f"  T₁ = {state1.T:.2f} K ({state1.T-273.15:.2f} °C)")
            output.append(f"  h₁ = {state1.h/1e3:.2f} kJ/kg")
            output.append(f"  s₁ = {state1.s/1e3:.4f} kJ/kg/K")
            output.append(f"  ρ₁ = {state1.rho:.2f} kg/m³")
            if state1.x is not None:
                output.append(f"  x₁ = {state1.x:.4f}")
            output.append("")
            
            # State 2 (outlet)
            output.append("📤 État de sortie (2):")
            output.append(f"  P₂ = {result.state2.P/1e5:.3f} bar ({result.state2.P:.2e} Pa)")
            output.append(f"  T₂ = {result.state2.T:.2f} K ({result.state2.T-273.15:.2f} °C)")
            output.append(f"  h₂ = {result.state2.h/1e3:.2f} kJ/kg")
            output.append(f"  s₂ = {result.state2.s/1e3:.4f} kJ/kg/K")
            output.append(f"  ρ₂ = {result.state2.rho:.2f} kg/m³")
            if result.state2.x is not None:
                output.append(f"  x₂ = {result.state2.x:.4f}")
            output.append("")
            
            # Verification
            delta_h = abs(result.state2.h - state1.h)
            output.append("✓ Vérification isoenthalpique:")
            output.append(f"  Δh = {delta_h:.2f} J/kg (≈ 0)")
            output.append("")
            
            # Mass flow if calculated
            if result.m_dot is not None:
                output.append("💧 Débit massique (orifice):")
                output.append(f"  ṁ = {result.m_dot:.6f} kg/s")
                output.append("")
            
            # Flags
            output.append("⚠️ Diagnostics:")
            for flag_name, flag_value in result.flags.items():
                status = "🔴 ACTIF" if flag_value else "✅ OK"
                output.append(f"  {flag_name}: {status}")
            
            results_text.insert("1.0", "\n".join(output))
        
        # ========== BOTTOM PANEL: Plot ==========
        plot_frame = ttk.LabelFrame(window, text="Diagrammes thermodynamiques P-h et P-s", padding=10)
        plot_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Create matplotlib figure with two subplots
        fig = Figure(figsize=(14, 5), dpi=100)
        ax_ph = fig.add_subplot(121)  # P-h diagram (left)
        ax_ps = fig.add_subplot(122)  # P-s diagram (right)
        
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        def plot_ph_diagram(result: ExpansionValveResult, state1: ThermoState):
            """Plot P-h and P-s diagrams showing expansion process with saturation curves."""
            import numpy as np
            
            # Clear both axes
            ax_ph.clear()
            ax_ps.clear()
            
            # Compute saturation curves
            P_sat, hl, hv, sl, sv = ExpansionValveTkView._compute_saturation_curve()
            
            # Convert to kJ/kg and kJ/kg/K
            hl_kJ = hl / 1e3
            hv_kJ = hv / 1e3
            sl_kJ = sl / 1e3
            sv_kJ = sv / 1e3
            
            # Extract state data
            h1 = state1.h / 1e3  # kJ/kg
            P1 = state1.P
            s1 = state1.s / 1e3  # kJ/kg/K
            
            h2 = result.state2.h / 1e3  # kJ/kg
            P2 = result.state2.P
            s2 = result.state2.s / 1e3  # kJ/kg/K
            
            # ========== P-h DIAGRAM ==========
            
            # Plot saturation dome
            ax_ph.plot(hl_kJ, P_sat, 'b-', linewidth=2, label='Liquide saturé', zorder=2)
            ax_ph.plot(hv_kJ, P_sat, 'r-', linewidth=2, label='Vapeur saturée', zorder=2)
            
            # Plot iso-quality lines
            for x in [0.1, 0.3, 0.5, 0.7, 0.9]:
                h_x = hl + x * (hv - hl)
                h_x_kJ = h_x / 1e3
                ax_ph.plot(h_x_kJ, P_sat, 'gray', linewidth=0.5, alpha=0.5, linestyle='--', zorder=1)
                
                # Add label for x=0.5 only
                if x == 0.5:
                    mid_idx = len(h_x_kJ) // 2
                    ax_ph.text(h_x_kJ[mid_idx], P_sat[mid_idx], f'x={x}', 
                              fontsize=8, color='gray', rotation=75, va='bottom')
            
            # Plot process states
            ax_ph.plot(h1, P1, 'ro', markersize=12, label='État 1 (entrée)', zorder=4)
            ax_ph.plot(h2, P2, 'bs', markersize=12, label='État 2 (sortie)', zorder=4)
            
            # Plot process line (isenthalpic: vertical line in P-h)
            ax_ph.plot([h1, h2], [P1, P2], 'g-', linewidth=2.5, label='Détente isenthalpique', zorder=3)
            
            # Add arrow
            mid_h = (h1 + h2) / 2
            mid_P = np.sqrt(P1 * P2)  # Geometric mean for log scale
            ax_ph.annotate('', xy=(h2, P2), xytext=(h1, P1),
                          arrowprops=dict(arrowstyle='->', color='green', lw=2.5))
            
            # Add "Flash vaporization" annotation
            ax_ph.annotate('Flash vaporization', xy=(mid_h, mid_P), xytext=(mid_h + 100, mid_P * 2),
                          fontsize=9, color='darkgreen', fontweight='bold',
                          arrowprops=dict(arrowstyle='->', color='darkgreen', lw=1.5),
                          bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
            
            # Add state labels
            ax_ph.text(h1, P1 * 1.3, '1', fontsize=13, color='red', fontweight='bold',
                      ha='center', va='bottom')
            ax_ph.text(h2, P2 / 1.3, '2', fontsize=13, color='blue', fontweight='bold',
                      ha='center', va='top')
            
            # Formatting P-h
            ax_ph.set_xlabel('Enthalpie spécifique h [kJ/kg]', fontsize=11, fontweight='bold')
            ax_ph.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ph.set_title('Diagramme Pression-Enthalpie (P-h)', fontsize=12, fontweight='bold')
            ax_ph.set_yscale('log')
            ax_ph.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ph.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            h_margin = max(50, abs(h2 - h1) * 0.3)
            ax_ph.set_xlim(min(hl_kJ.min(), h1, h2) - h_margin, 
                          max(hv_kJ.max(), h1, h2) + h_margin)
            ax_ph.set_ylim(P_sat.min() * 0.8, P_sat.max() * 1.2)
            
            # ========== P-s DIAGRAM ==========
            
            # Plot saturation dome
            ax_ps.plot(sl_kJ, P_sat, 'b-', linewidth=2, label='Liquide saturé', zorder=2)
            ax_ps.plot(sv_kJ, P_sat, 'r-', linewidth=2, label='Vapeur saturée', zorder=2)
            
            # Plot iso-quality lines
            for x in [0.1, 0.3, 0.5, 0.7, 0.9]:
                s_x = sl + x * (sv - sl)
                s_x_kJ = s_x / 1e3
                ax_ps.plot(s_x_kJ, P_sat, 'gray', linewidth=0.5, alpha=0.5, linestyle='--', zorder=1)
            
            # Plot process states
            ax_ps.plot(s1, P1, 'ro', markersize=12, label='État 1 (entrée)', zorder=4)
            ax_ps.plot(s2, P2, 'bs', markersize=12, label='État 2 (sortie)', zorder=4)
            
            # Plot process line
            ax_ps.plot([s1, s2], [P1, P2], 'g-', linewidth=2.5, label='Détente', zorder=3)
            
            # Add arrow
            ax_ps.annotate('', xy=(s2, P2), xytext=(s1, P1),
                          arrowprops=dict(arrowstyle='->', color='green', lw=2.5))
            
            # Add state labels
            ax_ps.text(s1, P1 * 1.3, '1', fontsize=13, color='red', fontweight='bold',
                      ha='center', va='bottom')
            ax_ps.text(s2, P2 / 1.3, '2', fontsize=13, color='blue', fontweight='bold',
                      ha='center', va='top')
            
            # Formatting P-s
            ax_ps.set_xlabel('Entropie spécifique s [kJ/kg/K]', fontsize=11, fontweight='bold')
            ax_ps.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ps.set_title('Diagramme Pression-Entropie (P-s)', fontsize=12, fontweight='bold')
            ax_ps.set_yscale('log')
            ax_ps.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ps.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            s_margin = max(0.1, abs(s2 - s1) * 0.3)
            ax_ps.set_xlim(min(sl_kJ.min(), s1, s2) - s_margin,
                          max(sv_kJ.max(), s1, s2) + s_margin)
            ax_ps.set_ylim(P_sat.min() * 0.8, P_sat.max() * 1.2)
            
            # Tight layout and draw
            fig.tight_layout()
            canvas.draw()
        
        # Configure grid weights
        window.columnconfigure(0, weight=1)
        window.columnconfigure(1, weight=2)
        window.rowconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        
        left_frame.columnconfigure(1, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

