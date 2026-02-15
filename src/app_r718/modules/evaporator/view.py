"""
Evaporator View - Display and reporting functionality

Handles all output formatting for evaporator results.
Includes both console output and Tkinter GUI with Matplotlib diagrams.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from typing import Optional
from app_r718.modules.evaporator.model import EvaporatorResult


class EvaporatorView:
    """
    View component for evaporator visualization.
    
    Responsible for formatting and displaying evaporator results.
    No computation should occur here - only presentation.
    """
    
    @staticmethod
    def display_result(result: EvaporatorResult, verbose: bool = True) -> None:
        """
        Display evaporator calculation results.
        
        Args:
            result: Calculation results to display
            verbose: If True, show detailed state information
        """
        print("=" * 60)
        print("EVAPORATOR RESULTS")
        print("=" * 60)
        
        # Display outlet state
        if verbose:
            print("\nOutlet State (3):")
            print(f"  {result.state3}")
        else:
            print(f"\n  P_out = {result.state3.P:.2e} Pa")
            print(f"  T_out = {result.state3.T:.2f} K ({result.state3.T - 273.15:.2f} °C)")
            print(f"  h_out = {result.state3.h:.2e} J/kg")
        
        # Display heat transfers
        print(f"\nHeat Transfer:")
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
    def display_summary(result: EvaporatorResult) -> None:
        """
        Display compact summary of results.
        
        Args:
            result: Calculation results to summarize
        """
        print(f"Evaporator: Q={result.Q_mass/1e3:.2f} kW, "
              f"T_out={result.state3.T-273.15:.1f}°C", end="")
        
        # Show warnings if any
        active_flags = [k for k, v in result.flags.items() if v]
        if active_flags:
            print(f" [WARNINGS: {', '.join(active_flags)}]")
        else:
            print()


class EvaporatorTkView:
    """
    Tkinter-based GUI view for evaporator simulation.
    
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
        Open evaporator simulation window.
        
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
        from app_r718.modules.evaporator import EvaporatorController
        
        # Create Toplevel window
        window = tk.Toplevel(parent)
        window.title("Évaporateur (Evaporator) - Simulation")
        window.geometry("1200x750")
        
        # Controller instance
        controller = EvaporatorController()
        props = get_props_service()
        
        # Variables
        var_m_dot = tk.StringVar(value="0.035")
        var_P_evap = tk.StringVar(value=str(props.Psat_T(283.15)))  # 10°C
        var_K = tk.StringVar(value="800")
        var_A = tk.StringVar(value="6.0")
        var_T_ext_in = tk.StringVar(value="295.15")  # 22°C
        var_T_ext_out = tk.StringVar(value="289.15")  # 16°C
        var_superheat_K = tk.StringVar(value="0.0")
        
        # State2 variables (manual input option)
        var_P2 = tk.StringVar(value="")
        var_h2 = tk.StringVar(value="")
        
        # Results storage
        result_data = {"result": None, "state2": None}
        
        # ========== LEFT PANEL: Inputs ==========
        left_frame = ttk.Frame(window, padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Title
        ttk.Label(
            left_frame,
            text="Paramètres d'entrée",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        # State 2 generation section
        ttk.Label(left_frame, text="État 2 (entrée évaporateur):", font=("Arial", 10, "bold")).grid(
            row=1, column=0, columnspan=2, pady=5, sticky="w"
        )
        
        state2_info = tk.Text(left_frame, width=40, height=4, wrap="word")
        state2_info.grid(row=2, column=0, columnspan=2, pady=2)
        state2_info.insert("1.0", "État 2 non généré.\nCliquez sur 'Générer état 2 nominal' ou entrez P2/h2 manuellement.")
        state2_info.config(state="disabled")
        
        def generate_nominal_state2():
            """Generate nominal state2 via isenthalpic expansion."""
            try:
                # State 1: saturated liquid at condenser temperature (35°C)
                T_cond = 308.15  # 35°C
                P_cond = props.Psat_T(T_cond)
                state1 = ThermoState()
                state1.update_from_PX(P_cond, 0.0)  # Saturated liquid
                
                # Get P_evap from input field
                P_evap = float(var_P_evap.get())
                
                # State 2: isenthalpic expansion (h2 = h1)
                state2 = ThermoState()
                state2.update_from_PH(P_evap, state1.h)
                
                # Store state2
                result_data["state2"] = state2
                
                # Update info display
                state2_info.config(state="normal")
                state2_info.delete("1.0", "end")
                info_text = f"État 2 généré (détente isoenthalpique):\n"
                info_text += f"  P₂ = {state2.P:.2e} Pa ({state2.P/1e3:.2f} kPa)\n"
                info_text += f"  T₂ = {state2.T:.2f} K ({state2.T-273.15:.2f} °C)\n"
                info_text += f"  h₂ = {state2.h/1e3:.2f} kJ/kg\n"
                if state2.x is not None:
                    info_text += f"  x₂ = {state2.x:.4f} (diphasique)"
                state2_info.insert("1.0", info_text)
                state2_info.config(state="disabled")
                
                messagebox.showinfo("Succès", "État 2 généré avec succès!")
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la génération de l'état 2:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="🔄 Générer état 2 nominal (via détente)",
            command=generate_nominal_state2,
            width=35,
        ).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Manual state2 input (optional)
        ttk.Label(left_frame, text="Ou entrer manuellement:", font=("Arial", 9)).grid(
            row=4, column=0, columnspan=2, sticky="w"
        )
        
        ttk.Label(left_frame, text="P₂ [Pa]:").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_P2, width=20).grid(row=5, column=1, pady=2)
        
        ttk.Label(left_frame, text="h₂ [J/kg]:").grid(row=6, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_h2, width=20).grid(row=6, column=1, pady=2)
        
        def load_manual_state2():
            """Load state2 from manual input."""
            try:
                P2 = float(var_P2.get())
                h2 = float(var_h2.get())
                
                state2 = ThermoState()
                state2.update_from_PH(P2, h2)
                
                result_data["state2"] = state2
                
                # Update info display
                state2_info.config(state="normal")
                state2_info.delete("1.0", "end")
                info_text = f"État 2 chargé manuellement:\n"
                info_text += f"  P₂ = {state2.P:.2e} Pa\n"
                info_text += f"  h₂ = {state2.h/1e3:.2f} kJ/kg\n"
                info_text += f"  T₂ = {state2.T:.2f} K"
                state2_info.insert("1.0", info_text)
                state2_info.config(state="disabled")
                
                messagebox.showinfo("Succès", "État 2 chargé!")
                
            except ValueError:
                messagebox.showerror("Erreur", "P₂ et h₂ doivent être des nombres valides.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="📥 Charger état 2 manuel",
            command=load_manual_state2,
            width=20,
        ).grid(row=7, column=0, columnspan=2, pady=5)
        
        # Separator
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        # Evaporator parameters
        ttk.Label(left_frame, text="Paramètres évaporateur:", font=("Arial", 10, "bold")).grid(
            row=9, column=0, columnspan=2, pady=5, sticky="w"
        )
        
        ttk.Label(left_frame, text="Débit masse m_dot [kg/s]:").grid(row=10, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_m_dot, width=20).grid(row=10, column=1, pady=2)
        
        ttk.Label(left_frame, text="Pression évaporation P_evap [Pa]:").grid(row=11, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_P_evap, width=20).grid(row=11, column=1, pady=2)
        
        ttk.Label(left_frame, text="Coefficient global K [W/m²/K]:").grid(row=12, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_K, width=20).grid(row=12, column=1, pady=2)
        
        ttk.Label(left_frame, text="Surface échange A [m²]:").grid(row=13, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_A, width=20).grid(row=13, column=1, pady=2)
        
        ttk.Label(left_frame, text="T fluide externe entrée [K]:").grid(row=14, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_T_ext_in, width=20).grid(row=14, column=1, pady=2)
        
        ttk.Label(left_frame, text="T fluide externe sortie [K]:").grid(row=15, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_T_ext_out, width=20).grid(row=15, column=1, pady=2)
        
        ttk.Label(left_frame, text="Surchauffe superheat_K [K]:").grid(row=16, column=0, sticky="w", pady=2)
        ttk.Entry(left_frame, textvariable=var_superheat_K, width=20).grid(row=16, column=1, pady=2)
        
        # Simulate button
        def simulate():
            try:
                # Check if state2 is loaded
                if result_data["state2"] is None:
                    messagebox.showwarning("Attention", "Veuillez d'abord générer ou charger l'état 2!")
                    return
                
                state2 = result_data["state2"]
                
                # Parse parameters
                m_dot = float(var_m_dot.get())
                P_evap = float(var_P_evap.get())
                K = float(var_K.get())
                A = float(var_A.get())
                T_ext_in = float(var_T_ext_in.get())
                T_ext_out = float(var_T_ext_out.get())
                superheat_K = float(var_superheat_K.get())
                
                # Run simulation
                result = controller.solve(
                    state2=state2,
                    m_dot=m_dot,
                    P_evap=P_evap,
                    K=K,
                    A=A,
                    T_ext_in=T_ext_in,
                    T_ext_out=T_ext_out,
                    superheat_K=superheat_K,
                )
                
                # Store results
                result_data["result"] = result
                
                # Display results
                display_results(result, state2)
                
                # Plot diagrams
                plot_diagrams(result, state2)
                
            except ValueError as e:
                messagebox.showerror("Erreur", f"Valeur invalide:\n{str(e)}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur simulation:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="▶ Simuler",
            command=simulate,
            width=20,
        ).grid(row=17, column=0, columnspan=2, pady=20)
        
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
        results_text = tk.Text(right_frame, width=50, height=20, wrap="word")
        results_text.grid(row=1, column=0, sticky="nsew", pady=5)
        
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=results_text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        results_text.config(yscrollcommand=scrollbar.set)
        
        def display_results(result: EvaporatorResult, state2: ThermoState):
            """Display simulation results in text widget."""
            results_text.delete("1.0", "end")
            
            T_sat = props.Tsat_P(float(var_P_evap.get()))
            
            output = []
            output.append("=" * 50)
            output.append("RÉSULTATS - ÉVAPORATEUR")
            output.append("=" * 50)
            output.append("")
            
            # Saturation temperature
            output.append(f"🌡️ Température de saturation:")
            output.append(f"  T_sat = {T_sat:.2f} K ({T_sat-273.15:.2f} °C)")
            output.append("")
            
            # State 2 (inlet)
            output.append("📥 État d'entrée (2):")
            output.append(f"  P₂ = {state2.P/1e3:.2f} kPa")
            output.append(f"  T₂ = {state2.T:.2f} K ({state2.T-273.15:.2f} °C)")
            output.append(f"  h₂ = {state2.h/1e3:.2f} kJ/kg")
            output.append(f"  s₂ = {state2.s/1e3:.4f} kJ/kg/K")
            if state2.x is not None:
                output.append(f"  x₂ = {state2.x:.4f} (titre vapeur)")
            output.append("")
            
            # State 3 (outlet)
            output.append("📤 État de sortie (3):")
            output.append(f"  P₃ = {result.state3.P/1e3:.2f} kPa")
            output.append(f"  T₃ = {result.state3.T:.2f} K ({result.state3.T-273.15:.2f} °C)")
            output.append(f"  h₃ = {result.state3.h/1e3:.2f} kJ/kg")
            output.append(f"  s₃ = {result.state3.s/1e3:.4f} kJ/kg/K")
            if result.state3.x is not None:
                output.append(f"  x₃ = {result.state3.x:.4f} (titre vapeur)")
            else:
                output.append(f"  État: vapeur surchauffée")
            output.append("")
            
            # Heat transfers
            output.append("🔥 Transferts thermiques:")
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
        
        def plot_diagrams(result: EvaporatorResult, state2: ThermoState):
            """Plot P-h and P-s diagrams showing evaporation process with saturation curves."""
            
            # Clear both axes
            ax_ph.clear()
            ax_ps.clear()
            
            # Compute saturation curves
            P_sat, hl, hv, sl, sv = EvaporatorTkView._compute_saturation_curve()
            
            # Convert to kJ/kg and kJ/kg/K
            hl_kJ = hl / 1e3
            hv_kJ = hv / 1e3
            sl_kJ = sl / 1e3
            sv_kJ = sv / 1e3
            
            # Extract state data
            h2 = state2.h / 1e3  # kJ/kg
            P2 = state2.P
            s2 = state2.s / 1e3  # kJ/kg/K
            
            h3 = result.state3.h / 1e3  # kJ/kg
            P3 = result.state3.P
            s3 = result.state3.s / 1e3  # kJ/kg/K
            
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
            ax_ph.plot(h2, P2, 'go', markersize=12, label='État 2 (entrée)', zorder=4)
            ax_ph.plot(h3, P3, 'bs', markersize=12, label='État 3 (sortie)', zorder=4)
            
            # Plot process line (evaporation: horizontal line in P-h at constant P)
            ax_ph.plot([h2, h3], [P2, P3], 'purple', linewidth=2.5, label='Évaporation (2→3)', zorder=3)
            
            # Add arrow
            ax_ph.annotate('', xy=(h3, P3), xytext=(h2, P2),
                          arrowprops=dict(arrowstyle='->', color='purple', lw=2.5))
            
            # Add "Évaporation" annotation
            mid_h = (h2 + h3) / 2
            mid_P = P2  # Constant pressure
            ax_ph.annotate('Évaporation', xy=(mid_h, mid_P), xytext=(mid_h, mid_P * 1.8),
                          fontsize=9, color='purple', fontweight='bold',
                          arrowprops=dict(arrowstyle='->', color='purple', lw=1.5),
                          bbox=dict(boxstyle='round,pad=0.5', facecolor='lavender', alpha=0.8))
            
            # Add state labels
            ax_ph.text(h2, P2 / 1.3, '2', fontsize=13, color='green', fontweight='bold',
                      ha='center', va='top')
            ax_ph.text(h3, P3 / 1.3, '3', fontsize=13, color='blue', fontweight='bold',
                      ha='center', va='top')
            
            # Formatting P-h
            ax_ph.set_xlabel('Enthalpie spécifique h [kJ/kg]', fontsize=11, fontweight='bold')
            ax_ph.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ph.set_title('Diagramme Pression-Enthalpie (P-h)', fontsize=12, fontweight='bold')
            ax_ph.set_yscale('log')
            ax_ph.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ph.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            h_margin = max(50, abs(h3 - h2) * 0.3)
            ax_ph.set_xlim(min(hl_kJ.min(), h2, h3) - h_margin, 
                          max(hv_kJ.max(), h2, h3) + h_margin)
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
            ax_ps.plot(s2, P2, 'go', markersize=12, label='État 2 (entrée)', zorder=4)
            ax_ps.plot(s3, P3, 'bs', markersize=12, label='État 3 (sortie)', zorder=4)
            
            # Plot process line
            ax_ps.plot([s2, s3], [P2, P3], 'purple', linewidth=2.5, label='Évaporation (2→3)', zorder=3)
            
            # Add arrow
            ax_ps.annotate('', xy=(s3, P3), xytext=(s2, P2),
                          arrowprops=dict(arrowstyle='->', color='purple', lw=2.5))
            
            # Add state labels
            ax_ps.text(s2, P2 / 1.3, '2', fontsize=13, color='green', fontweight='bold',
                      ha='center', va='top')
            ax_ps.text(s3, P3 / 1.3, '3', fontsize=13, color='blue', fontweight='bold',
                      ha='center', va='top')
            
            # Formatting P-s
            ax_ps.set_xlabel('Entropie spécifique s [kJ/kg/K]', fontsize=11, fontweight='bold')
            ax_ps.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ps.set_title('Diagramme Pression-Entropie (P-s)', fontsize=12, fontweight='bold')
            ax_ps.set_yscale('log')
            ax_ps.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ps.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            s_margin = max(0.1, abs(s3 - s2) * 0.3)
            ax_ps.set_xlim(min(sl_kJ.min(), s2, s3) - s_margin,
                          max(sv_kJ.max(), s2, s3) + s_margin)
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
