"""
Condenser View - Display and reporting functionality

Handles all output formatting for condenser results.
Includes both console output and Tkinter GUI with Matplotlib diagrams.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from typing import Optional
from app_r718.modules.condenser.model import CondenserResult


class CondenserView:
    """
    View component for condenser visualization.
    
    Responsible for formatting and displaying condenser results.
    No computation should occur here - only presentation.
    """
    
    @staticmethod
    def display_result(result: CondenserResult, verbose: bool = True) -> None:
        """
        Display condenser calculation results.
        
        Args:
            result: Calculation results to display
            verbose: If True, show detailed state information
        """
        print("=" * 60)
        print("CONDENSER RESULTS")
        print("=" * 60)
        
        # Display condensation conditions
        print(f"\nCondensation Pressure: {result.P_cond/1e3:.2f} kPa")
        print(f"Saturation Temperature: {result.T_sat:.2f} K ({result.T_sat-273.15:.2f} °C)")
        
        # Display outlet state
        if verbose:
            print("\nOutlet State:")
            print(f"  {result.state_out}")
        else:
            print(f"\n  P_out = {result.state_out.P:.2e} Pa")
            print(f"  T_out = {result.state_out.T:.2f} K ({result.state_out.T - 273.15:.2f} °C)")
            print(f"  h_out = {result.state_out.h:.2e} J/kg")
        
        # Display heat transfers
        print(f"\nHeat Rejection:")
        print(f"  Q_mass = {result.Q_mass/1e3:.3f} kW (from energy balance)")
        print(f"  Q_KA   = {result.Q_KA/1e3:.3f} kW (from heat exchanger)")
        print(f"  Relative difference = {result.delta_relative*100:.2f} %")
        
        # Display flags
        print("\nDiagnostic Flags:")
        for flag_name, flag_value in result.flags.items():
            status = "⚠️  ACTIVE" if flag_value else "✓ OK"
            print(f"  {flag_name}: {status}")
        
        print("=" * 60)
    
    @staticmethod
    def display_summary(result: CondenserResult) -> None:
        """
        Display compact summary of results.
        
        Args:
            result: Calculation results to summarize
        """
        print(f"Condenser: Q={result.Q_mass/1e3:.2f} kW, "
              f"T_out={result.state_out.T-273.15:.1f}°C", end="")
        
        # Show warnings if any
        active_flags = [k for k, v in result.flags.items() if v]
        if active_flags:
            print(f" [WARNINGS: {', '.join(active_flags)}]")
        else:
            print()


class CondenserTkView:
    """
    Tkinter-based GUI view for condenser simulation.
    
    Provides interactive interface with input fields, state generation,
    simulation button, results display, and P-h/P-s diagram visualization.
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
        Open condenser simulation window.
        
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
        from app_r718.modules.condenser import CondenserController
        
        # Create Toplevel window
        window = tk.Toplevel(parent)
        window.title("Condenseur (Condenser) - Simulation")
        window.geometry("1200x750")
        
        # Controller instance
        controller = CondenserController()
        props = get_props_service()
        
        # Variables
        var_m_dot = tk.StringVar(value="0.035")
        var_T_cond = tk.StringVar(value="308.15")  # 35°C
        var_K = tk.StringVar(value="15")  # Low K for natural convection
        var_A = tk.StringVar(value="20.0")  # Large area to compensate
        var_T_air_in = tk.StringVar(value="300.15")  # 27°C
        var_T_air_out = tk.StringVar(value="305.15")  # 32°C
        var_subcool_K = tk.StringVar(value="0.0")
        
        # State_in variables (manual input option)
        var_P_in = tk.StringVar(value="")
        var_h_in = tk.StringVar(value="")
        
        # Results storage
        result_data = {"result": None, "state_in": None}
        
        # ========== LEFT PANEL: Inputs ==========
        left_frame = ttk.Frame(window, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Title
        ttk.Label(
            left_frame,
            text="Paramètres d'entrée",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        # State_in generation section
        ttk.Label(left_frame, text="État d'entrée (vapeur):", font=("Arial", 10, "bold")).grid(
            row=1, column=0, columnspan=2, pady=5, sticky="w"
        )
        
        state_in_info = tk.Text(left_frame, width=40, height=4, wrap="word")
        state_in_info.grid(row=2, column=0, columnspan=2, pady=2)
        state_in_info.insert("1.0", "État d'entrée non généré.\nCliquez sur 'Générer vapeur saturée' ou entrez P/h manuellement.")
        state_in_info.config(state="disabled")
        
        def generate_saturated_vapor():
            """Generate saturated vapor at P_cond."""
            try:
                # Get T_cond from input field
                T_cond = float(var_T_cond.get())
                P_cond = props.Psat_T(T_cond)
                
                # State_in: saturated vapor (x=1.0)
                state_in = ThermoState()
                state_in.update_from_PX(P_cond, 1.0)
                
                # Store state_in
                result_data["state_in"] = state_in
                
                # Update info display
                state_in_info.config(state="normal")
                state_in_info.delete("1.0", "end")
                info_text = f"État d'entrée (vapeur saturée):\n"
                info_text += f"  P_in = {state_in.P:.2e} Pa ({state_in.P/1e3:.2f} kPa)\n"
                info_text += f"  T_in = {state_in.T:.2f} K ({state_in.T-273.15:.2f} °C)\n"
                info_text += f"  h_in = {state_in.h/1e3:.2f} kJ/kg\n"
                info_text += f"  x_in = 1.0 (vapeur saturée)"
                state_in_info.insert("1.0", info_text)
                state_in_info.config(state="disabled")
                
                messagebox.showinfo("Succès", "État d'entrée généré (vapeur saturée)!")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la génération:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="🔄 Générer vapeur saturée",
            command=generate_saturated_vapor,
            width=35,
        ).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Manual state_in input (optional)
        ttk.Label(left_frame, text="Ou entrer manuellement:", font=("Arial", 9)).grid(
            row=4, column=0, columnspan=2, sticky="w"
        )
        
        ttk.Label(left_frame, text="P_in [Pa]:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_P_in, width=20).grid(row=5, column=1, pady=2)
        
        ttk.Label(left_frame, text="h_in [J/kg]:").grid(row=6, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_h_in, width=20).grid(row=6, column=1, pady=2)
        
        def load_manual_state_in():
            """Load state_in from manual input."""
            try:
                P_in = float(var_P_in.get())
                h_in = float(var_h_in.get())
                
                state_in = ThermoState()
                state_in.update_from_PH(P_in, h_in)
                
                result_data["state_in"] = state_in
                
                # Update info display
                state_in_info.config(state="normal")
                state_in_info.delete("1.0", "end")
                info_text = f"État d'entrée chargé manuellement:\n"
                info_text += f"  P_in = {state_in.P:.2e} Pa\n"
                info_text += f"  h_in = {state_in.h/1e3:.2f} kJ/kg\n"
                info_text += f"  T_in = {state_in.T:.2f} K"
                state_in_info.insert("1.0", info_text)
                state_in_info.config(state="disabled")
                
                messagebox.showinfo("Succès", "État d'entrée chargé!")
                
            except ValueError:
                messagebox.showerror("Erreur", "P_in et h_in doivent être des nombres valides.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="📥 Charger état manuel",
            command=load_manual_state_in,
            width=20,
        ).grid(row=7, column=0, columnspan=2, pady=5)
        
        # Separator
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        # Condenser parameters
        ttk.Label(left_frame, text="Paramètres condenseur:", font=("Arial", 10, "bold")).grid(
            row=9, column=0, columnspan=2, pady=5, sticky="w"
        )
        
        ttk.Label(left_frame, text="Débit masse m_dot [kg/s]:").grid(row=10, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_m_dot, width=20).grid(row=10, column=1, pady=2)
        
        ttk.Label(left_frame, text="Température condensation T_cond [K]:").grid(row=11, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_T_cond, width=20).grid(row=11, column=1, pady=2)
        
        ttk.Label(left_frame, text="Coefficient global K [W/m²/K]:").grid(row=12, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_K, width=20).grid(row=12, column=1, pady=2)
        
        ttk.Label(left_frame, text="Surface échange A [m²]:").grid(row=13, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_A, width=20).grid(row=13, column=1, pady=2)
        
        ttk.Label(left_frame, text="T air entrée [K]:").grid(row=14, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_T_air_in, width=20).grid(row=14, column=1, pady=2)
        
        ttk.Label(left_frame, text="T air sortie [K]:").grid(row=15, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_T_air_out, width=20).grid(row=15, column=1, pady=2)
        
        ttk.Label(left_frame, text="Sous-refroidissement subcool_K [K]:").grid(row=16, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_subcool_K, width=20).grid(row=16, column=1, pady=2)
        
        # ========== RIGHT PANEL: Results ==========
        right_frame = ttk.Frame(window, padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Results title
        ttk.Label(
            right_frame,
            text="Résultats de simulation",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=10, sticky="w")
        
        # Simulate button - Define first so it can be used in the function
        def simulate():
            try:
                # Check if state_in is loaded
                if result_data["state_in"] is None:
                    messagebox.showwarning("Attention", "Veuillez d'abord générer ou charger l'état d'entrée!")
                    return
                
                state_in = result_data["state_in"]
                
                # Parse parameters
                m_dot = float(var_m_dot.get())
                T_cond = float(var_T_cond.get())
                K = float(var_K.get())
                A = float(var_A.get())
                T_air_in = float(var_T_air_in.get())
                T_air_out = float(var_T_air_out.get())
                subcool_K = float(var_subcool_K.get())
                
                # Run simulation
                result = controller.solve(
                    state_in=state_in,
                    m_dot=m_dot,
                    T_cond=T_cond,
                    K=K,
                    A=A,
                    T_air_in=T_air_in,
                    T_air_out=T_air_out,
                    subcool_K=subcool_K,
                )
                
                # Store results
                result_data["result"] = result
                
                # Display results
                display_results(result, state_in)
                
                # Plot diagrams
                plot_diagrams(result, state_in)
                
            except ValueError as e:
                messagebox.showerror("Erreur", f"Valeur invalide:\n{str(e)}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur simulation:\n{str(e)}")
        
        # Simulate button (prominent placement)
        ttk.Button(
            right_frame,
            text="▶ Simuler",
            command=simulate,
            width=25,
        ).grid(row=1, column=0, columnspan=2, pady=10)
        
        # Results text widget
        results_text = tk.Text(right_frame, width=50, height=18, wrap="word")
        results_text.grid(row=2, column=0, sticky="nsew", pady=5)
        
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=results_text.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        results_text.config(yscrollcommand=scrollbar.set)
        
        def display_results(result: CondenserResult, state_in: ThermoState):
            """Display simulation results in text widget."""
            results_text.delete("1.0", "end")
            
            output = []
            output.append("=" * 50)
            output.append("RÉSULTATS - CONDENSEUR")
            output.append("=" * 50)
            output.append("")
            
            # Condensation conditions
            output.append(f"🌡️ Conditions de condensation:")
            output.append(f"  P_cond = {result.P_cond/1e3:.2f} kPa")
            output.append(f"  T_sat = {result.T_sat:.2f} K ({result.T_sat-273.15:.2f} °C)")
            output.append("")
            
            # State_in (inlet)
            output.append("📥 État d'entrée:")
            output.append(f"  P_in = {state_in.P/1e3:.2f} kPa")
            output.append(f"  T_in = {state_in.T:.2f} K ({state_in.T-273.15:.2f} °C)")
            output.append(f"  h_in = {state_in.h/1e3:.2f} kJ/kg")
            output.append(f"  s_in = {state_in.s/1e3:.4f} kJ/kg/K")
            if state_in.x is not None:
                output.append(f"  x_in = {state_in.x:.4f} (titre vapeur)")
            output.append("")
            
            # State_out (outlet)
            output.append("📤 État de sortie:")
            output.append(f"  P_out = {result.state_out.P/1e3:.2f} kPa")
            output.append(f"  T_out = {result.state_out.T:.2f} K ({result.state_out.T-273.15:.2f} °C)")
            output.append(f"  h_out = {result.state_out.h/1e3:.2f} kJ/kg")
            output.append(f"  s_out = {result.state_out.s/1e3:.4f} kJ/kg/K")
            if result.state_out.x is not None:
                output.append(f"  x_out = {result.state_out.x:.4f} (liquide saturé)")
            else:
                output.append(f"  État: liquide sous-refroidi")
            output.append("")
            
            # Heat rejection
            output.append("🔥 Rejet thermique:")
            output.append(f"  Q_mass = {result.Q_mass/1e3:.3f} kW (bilan massique)")
            output.append(f"  Q_KA   = {result.Q_KA/1e3:.3f} kW (échangeur)")
            output.append(f"  Écart relatif = {result.delta_relative*100:.2f} %")
            output.append("")
            
            # Diagnostic flags
            output.append("⚙️ Diagnostics:")
            for flag_name, flag_value in result.flags.items():
                status = "⚠️ ACTIF" if flag_value else "✓ OK"
                output.append(f"  {flag_name}: {status}")
            
            output.append("=" * 50)
            
            results_text.insert("1.0", "\n".join(output))
        
        # ========== BOTTOM PANEL: Plots ==========
        plot_frame = ttk.LabelFrame(window, text="Diagrammes thermodynamiques P-h et P-s", padding=10)
        plot_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Create matplotlib figure with two subplots
        fig = Figure(figsize=(14, 5), dpi=100)
        ax_ph = fig.add_subplot(121)  # P-h diagram (left)
        ax_ps = fig.add_subplot(122)  # P-s diagram (right)
        
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        def plot_diagrams(result: CondenserResult, state_in: ThermoState):
            """Plot P-h and P-s diagrams showing condensation process with saturation curves."""
            
            # Clear both axes
            ax_ph.clear()
            ax_ps.clear()
            
            # Compute saturation curves
            P_sat, hl, hv, sl, sv = CondenserTkView._compute_saturation_curve()
            
            # Convert to kJ/kg and kJ/kg/K
            hl_kJ = hl / 1e3
            hv_kJ = hv / 1e3
            sl_kJ = sl / 1e3
            sv_kJ = sv / 1e3
            
            # Extract state data
            h_in = state_in.h / 1e3  # kJ/kg
            P_in = state_in.P
            s_in = state_in.s / 1e3  # kJ/kg/K
            
            h_out = result.state_out.h / 1e3  # kJ/kg
            P_out = result.state_out.P
            s_out = result.state_out.s / 1e3  # kJ/kg/K
            
            # ========== P-h DIAGRAM ==========
            
            # Plot saturation dome
            ax_ph.plot(hl_kJ, P_sat, 'b-', linewidth=2, label='Liquide saturé', zorder=2)
            ax_ph.plot(hv_kJ, P_sat, 'r-', linewidth=2, label='Vapeur saturée', zorder=2)
            
            # Plot iso-quality lines
            for x in [0.1, 0.3, 0.5, 0.7, 0.9]:
                h_x = hl + x * (hv - hl)
                h_x_kJ = h_x / 1e3
                ax_ph.plot(h_x_kJ, P_sat, 'gray', linewidth=0.5, alpha=0.5, linestyle='--', zorder=1)
            
            # Plot process states
            ax_ph.plot(h_in, P_in, 'ro', markersize=12, label='État entrée', zorder=4)
            ax_ph.plot(h_out, P_out, 'bs', markersize=12, label='État sortie', zorder=4)
            
            # Plot process line (condensation)
            ax_ph.plot([h_in, h_out], [P_in, P_out], 'darkgreen', linewidth=2.5, label='Condensation', zorder=3)
            
            # Add arrow
            ax_ph.annotate('', xy=(h_out, P_out), xytext=(h_in, P_in),
                          arrowprops=dict(arrowstyle='->', color='darkgreen', lw=2.5))
            
            # Add "Condensation" annotation
            mid_h = (h_in + h_out) / 2
            mid_P = P_in  # Approximately constant pressure
            ax_ph.annotate('Condensation', xy=(mid_h, mid_P), xytext=(mid_h - 200, mid_P * 1.5),
                          fontsize=9, color='darkgreen', fontweight='bold',
                          arrowprops=dict(arrowstyle='->', color='darkgreen', lw=1.5),
                          bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.8))
            
            # Add state labels
            ax_ph.text(h_in, P_in * 1.3, 'in', fontsize=13, color='red', fontweight='bold',
                      ha='center', va='bottom')
            ax_ph.text(h_out, P_out * 1.3, 'out', fontsize=13, color='blue', fontweight='bold',
                      ha='center', va='bottom')
            
            # Formatting P-h
            ax_ph.set_xlabel('Enthalpie spécifique h [kJ/kg]', fontsize=11, fontweight='bold')
            ax_ph.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ph.set_title('Diagramme Pression-Enthalpie (P-h)', fontsize=12, fontweight='bold')
            ax_ph.set_yscale('log')
            ax_ph.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ph.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            h_margin = max(50, abs(h_out - h_in) * 0.3)
            ax_ph.set_xlim(min(hl_kJ.min(), h_in, h_out) - h_margin, 
                          max(hv_kJ.max(), h_in, h_out) + h_margin)
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
            ax_ps.plot(s_in, P_in, 'ro', markersize=12, label='État entrée', zorder=4)
            ax_ps.plot(s_out, P_out, 'bs', markersize=12, label='État sortie', zorder=4)
            
            # Plot process line
            ax_ps.plot([s_in, s_out], [P_in, P_out], 'darkgreen', linewidth=2.5, label='Condensation', zorder=3)
            
            # Add arrow
            ax_ps.annotate('', xy=(s_out, P_out), xytext=(s_in, P_in),
                          arrowprops=dict(arrowstyle='->', color='darkgreen', lw=2.5))
            
            # Add state labels
            ax_ps.text(s_in, P_in * 1.3, 'in', fontsize=13, color='red', fontweight='bold',
                      ha='center', va='bottom')
            ax_ps.text(s_out, P_out * 1.3, 'out', fontsize=13, color='blue', fontweight='bold',
                      ha='center', va='bottom')
            
            # Formatting P-s
            ax_ps.set_xlabel('Entropie spécifique s [kJ/kg/K]', fontsize=11, fontweight='bold')
            ax_ps.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ps.set_title('Diagramme Pression-Entropie (P-s)', fontsize=12, fontweight='bold')
            ax_ps.set_yscale('log')
            ax_ps.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ps.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            s_margin = max(0.1, abs(s_out - s_in) * 0.3)
            ax_ps.set_xlim(min(sl_kJ.min(), s_in, s_out) - s_margin,
                          max(sv_kJ.max(), s_in, s_out) + s_margin)
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
        right_frame.rowconfigure(2, weight=1)
