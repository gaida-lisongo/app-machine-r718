"""
Generator View - Console and Tkinter UI

Provides both console-based and graphical user interfaces for generator simulation.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.generator import GeneratorController, GeneratorResult


class GeneratorView:
    """Console-based view for generator simulation."""
    
    def __init__(self):
        """Initialize view with controller."""
        self.controller = GeneratorController()
        self.props = get_props_service()
    
    def run(self):
        """Run console interface (placeholder for future CLI)."""
        print("Generator Console View - Not yet implemented")
        print("Use GeneratorTkView for graphical interface")


class GeneratorTkView:
    """
    Tkinter-based graphical user interface for generator simulation.
    
    Includes input fields, results display, and dual P-h / T-s diagrams.
    """
    
    @staticmethod
    def open_window(parent=None):
        """
        Open a new generator simulation window.
        
        Args:
            parent: Parent Tkinter window (optional)
        """
        # Import here to allow headless testing
        import tkinter as tk
        from tkinter import ttk, messagebox
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
        
        controller = GeneratorController()
        props = get_props_service()
        
        # Create window
        window = tk.Toplevel(parent) if parent else tk.Tk()
        window.title("Générateur (Generator) - R718")
        window.geometry("1400x900")
        
        # Storage for results
        result_data = {
            "state_in": None,
            "result": None,
        }
        
        # Main container
        main_frame = ttk.Frame(window, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # ========== LEFT PANEL: INPUTS ==========
        left_frame = ttk.LabelFrame(main_frame, text="⚙️ Paramètres d'Entrée", padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=2)
        
        # --- State In Generation ---
        ttk.Label(left_frame, text="État d'entrée:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=5
        )
        
        # Default target temperature for pressure calculation
        var_T_gen_target = tk.StringVar(value="373.15")  # 100°C
        
        def generate_saturated_liquid():
            """Generate inlet state as saturated liquid at generator pressure."""
            try:
                T_gen = float(var_T_gen_target.get())
                P_gen = props.Psat_T(T_gen)
                
                state_in = ThermoState()
                state_in.update_from_PX(P_gen, 0.0)  # Saturated liquid
                
                result_data["state_in"] = state_in
                
                messagebox.showinfo(
                    "État généré",
                    f"Liquide saturé généré:\n"
                    f"P = {P_gen/1e3:.2f} kPa\n"
                    f"T = {state_in.T:.2f} K ({state_in.T-273.15:.2f} °C)\n"
                    f"h = {state_in.h/1e3:.2f} kJ/kg"
                )
            except ValueError as e:
                messagebox.showerror("Erreur", f"Erreur génération état:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="📥 Générer entrée liquide saturé (P_gen)",
            command=generate_saturated_liquid,
        ).grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")
        
        # --- Operating Parameters ---
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        ttk.Label(left_frame, text="Paramètres opératoires:", font=("Arial", 10, "bold")).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=5
        )
        
        # Mass flow rate
        ttk.Label(left_frame, text="Débit massique m_dot [kg/s]:").grid(
            row=4, column=0, sticky="w", pady=2
        )
        var_m_dot = tk.StringVar(value="0.035")
        ttk.Entry(left_frame, textvariable=var_m_dot, width=15).grid(
            row=4, column=1, sticky="w", pady=2
        )
        
        # Target generator temperature
        ttk.Label(left_frame, text="Température générateur T_gen [K]:").grid(
            row=5, column=0, sticky="w", pady=2
        )
        ttk.Entry(left_frame, textvariable=var_T_gen_target, width=15).grid(
            row=5, column=1, sticky="w", pady=2
        )
        
        # Superheat
        ttk.Label(left_frame, text="Surchauffe superheat_K [K]:").grid(
            row=6, column=0, sticky="w", pady=2
        )
        var_superheat = tk.StringVar(value="0.0")
        ttk.Entry(left_frame, textvariable=var_superheat, width=15).grid(
            row=6, column=1, sticky="w", pady=2
        )
        
        # --- Heat Exchanger Parameters ---
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=7, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        ttk.Label(left_frame, text="Échangeur solaire:", font=("Arial", 10, "bold")).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=5
        )
        
        # Heat transfer coefficient
        ttk.Label(left_frame, text="Coefficient K [W/m²/K]:").grid(
            row=9, column=0, sticky="w", pady=2
        )
        var_K = tk.StringVar(value="250.0")
        ttk.Entry(left_frame, textvariable=var_K, width=15).grid(
            row=9, column=1, sticky="w", pady=2
        )
        
        # Heat exchanger area
        ttk.Label(left_frame, text="Surface A [m²]:").grid(
            row=10, column=0, sticky="w", pady=2
        )
        var_A = tk.StringVar(value="6.0")
        ttk.Entry(left_frame, textvariable=var_A, width=15).grid(
            row=10, column=1, sticky="w", pady=2
        )
        
        # HTF inlet temperature
        ttk.Label(left_frame, text="T_htf_in (entrée fluide chaud) [K]:").grid(
            row=11, column=0, sticky="w", pady=2
        )
        var_T_htf_in = tk.StringVar(value="403.15")  # 130°C
        ttk.Entry(left_frame, textvariable=var_T_htf_in, width=15).grid(
            row=11, column=1, sticky="w", pady=2
        )
        
        # HTF outlet temperature
        ttk.Label(left_frame, text="T_htf_out (sortie fluide chaud) [K]:").grid(
            row=12, column=0, sticky="w", pady=2
        )
        var_T_htf_out = tk.StringVar(value="383.15")  # 110°C
        ttk.Entry(left_frame, textvariable=var_T_htf_out, width=15).grid(
            row=12, column=1, sticky="w", pady=2
        )
        
        # ========== RIGHT PANEL: RESULTS ==========
        right_frame = ttk.LabelFrame(main_frame, text="📊 Résultats", padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)
        
        # Title
        ttk.Label(
            right_frame,
            text="Générateur - Résultats de Simulation",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        def simulate():
            try:
                # Check if state_in is loaded
                if result_data["state_in"] is None:
                    messagebox.showwarning("Attention", "Veuillez d'abord générer l'état d'entrée!")
                    return
                
                state_in = result_data["state_in"]
                
                # Parse parameters
                m_dot = float(var_m_dot.get())
                T_gen_target = float(var_T_gen_target.get())
                superheat_K = float(var_superheat.get())
                K = float(var_K.get())
                A = float(var_A.get())
                T_htf_in = float(var_T_htf_in.get())
                T_htf_out = float(var_T_htf_out.get())
                
                # Run simulation
                result = controller.solve(
                    state_in=state_in,
                    m_dot=m_dot,
                    T_gen_target=T_gen_target,
                    K=K,
                    A=A,
                    T_htf_in=T_htf_in,
                    T_htf_out=T_htf_out,
                    superheat_K=superheat_K,
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
        
        def display_results(result: GeneratorResult, state_in: ThermoState):
            """Display simulation results in text widget."""
            results_text.delete("1.0", "end")
            
            output = []
            output.append("=" * 50)
            output.append("RÉSULTATS - GÉNÉRATEUR")
            output.append("=" * 50)
            output.append("")
            
            # Heat input
            output.append("🔥 Chaleur apportée:")
            output.append(f"  Q_mass = {result.Q_mass:.2f} W ({result.Q_mass/1e3:.3f} kW)")
            output.append(f"  Q_KA = {result.Q_KA:.2f} W ({result.Q_KA/1e3:.3f} kW)")
            output.append(f"  Écart relatif = {result.delta_relative*100:.2f} %")
            output.append(f"  ΔT_lm = {result.delta_T_lm:.2f} K")
            output.append("")
            
            # Generator pressure
            output.append("⚙️ Conditions générateur:")
            output.append(f"  P_gen = {result.P_gen/1e3:.2f} kPa ({result.P_gen/1e5:.3f} bar)")
            output.append("")
            
            # State_in (inlet)
            output.append("📥 État d'entrée (liquide comprimé):")
            output.append(f"  P_in = {state_in.P/1e3:.2f} kPa")
            output.append(f"  T_in = {state_in.T:.2f} K ({state_in.T-273.15:.2f} °C)")
            output.append(f"  h_in = {state_in.h/1e3:.2f} kJ/kg")
            output.append(f"  s_in = {state_in.s/1e3:.4f} kJ/kg/K")
            if state_in.x is not None:
                output.append(f"  x_in = {state_in.x:.4f}")
            output.append("")
            
            # State_out (outlet)
            output.append("📤 État de sortie (vapeur):")
            output.append(f"  P_out = {result.state_out.P/1e3:.2f} kPa")
            output.append(f"  T_out = {result.state_out.T:.2f} K ({result.state_out.T-273.15:.2f} °C)")
            output.append(f"  h_out = {result.state_out.h/1e3:.2f} kJ/kg")
            output.append(f"  s_out = {result.state_out.s/1e3:.4f} kJ/kg/K")
            if result.state_out.x is not None:
                output.append(f"  x_out = {result.state_out.x:.4f}")
            else:
                output.append(f"  État: vapeur surchauffée")
            output.append("")
            
            # Diagnostic flags
            output.append("🚩 Diagnostics:")
            for flag_name, flag_value in result.flags.items():
                status = "⚠️ OUI" if flag_value else "✅ Non"
                output.append(f"  {flag_name}: {status}")
            output.append("")
            
            results_text.insert("1.0", "\n".join(output))
        
        # ========== BOTTOM PANEL: DIAGRAMS ==========
        diagram_frame = ttk.LabelFrame(main_frame, text="📈 Diagrammes Thermodynamiques", padding=10)
        diagram_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Matplotlib figure with two subplots
        fig, (ax_ph, ax_ts) = plt.subplots(1, 2, figsize=(12, 5))
        fig.tight_layout(pad=3.0)
        
        canvas = FigureCanvasTkAgg(fig, master=diagram_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        def _compute_saturation_curve():
            """Compute saturation curves for plotting."""
            # Pressure range for saturation dome
            P_min = 500  # 0.5 kPa
            P_max = 200e3  # 200 kPa
            P_sat = np.logspace(np.log10(P_min), np.log10(P_max), 100)
            
            hl = []  # Saturated liquid enthalpy
            hv = []  # Saturated vapor enthalpy
            sl = []  # Saturated liquid entropy
            sv = []  # Saturated vapor entropy
            Tl = []  # Saturated liquid temperature
            Tv = []  # Saturated vapor temperature
            
            for P in P_sat:
                try:
                    T_sat_p = props.Tsat_P(P)
                    
                    h_l = props.h_PX(P, 0.0)
                    h_v = props.h_PX(P, 1.0)
                    s_l = props.s_PX(P, 0.0)
                    s_v = props.s_PX(P, 1.0)
                    
                    hl.append(h_l)
                    hv.append(h_v)
                    sl.append(s_l)
                    sv.append(s_v)
                    Tl.append(T_sat_p)
                    Tv.append(T_sat_p)
                except:
                    continue
            
            return {
                'P_sat': P_sat[:len(hl)],
                'hl': np.array(hl),
                'hv': np.array(hv),
                'sl': np.array(sl),
                'sv': np.array(sv),
                'Tl': np.array(Tl),
                'Tv': np.array(Tv),
            }
        
        def plot_diagrams(result: GeneratorResult, state_in: ThermoState):
            """Plot P-h and T-s diagrams showing heating/vaporization process."""
            # Clear previous plots
            ax_ph.clear()
            ax_ts.clear()
            
            # Compute saturation curves
            sat_data = _compute_saturation_curve()
            P_sat = sat_data['P_sat']
            hl = sat_data['hl']
            hv = sat_data['hv']
            sl = sat_data['sl']
            sv = sat_data['sv']
            Tl = sat_data['Tl']
            Tv = sat_data['Tv']
            
            # Convert to kJ/kg and kJ/kg/K
            hl_kJ = hl / 1e3
            hv_kJ = hv / 1e3
            sl_kJ = sl / 1e3
            sv_kJ = sv / 1e3
            
            # Extract state data
            h_in = state_in.h / 1e3  # kJ/kg
            P_in = state_in.P
            s_in = state_in.s / 1e3  # kJ/kg/K
            T_in = state_in.T
            
            h_out = result.state_out.h / 1e3  # kJ/kg
            P_out = result.state_out.P
            s_out = result.state_out.s / 1e3  # kJ/kg/K
            T_out = result.state_out.T
            
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
            ax_ph.plot(h_in, P_in, 'go', markersize=12, label='État entrée', zorder=4)
            ax_ph.plot(h_out, P_out, 'rs', markersize=12, label='État sortie', zorder=4)
            
            # Plot process line (isobaric heating)
            ax_ph.plot([h_in, h_out], [P_in, P_out], 'darkred', linewidth=2.5, label='Chauffage/Vaporisation', zorder=3)
            
            # Add arrow
            ax_ph.annotate('', xy=(h_out, P_out), xytext=(h_in, P_in),
                          arrowprops=dict(arrowstyle='->', color='darkred', lw=2.5))
            
            # Add "Vaporisation" annotation
            mid_h = (h_in + h_out) / 2
            mid_P = np.sqrt(P_in * P_out)
            ax_ph.annotate('Vaporisation', xy=(mid_h, mid_P), xytext=(mid_h + 50, mid_P * 1.5),
                          fontsize=9, color='darkred', fontweight='bold',
                          arrowprops=dict(arrowstyle='->', color='darkred', lw=1.5),
                          bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
            
            # Add state labels
            ax_ph.text(h_in, P_in / 1.5, 'Entrée', fontsize=10, color='green', fontweight='bold',
                      ha='center', va='top')
            ax_ph.text(h_out, P_out * 1.5, 'Sortie', fontsize=10, color='red', fontweight='bold',
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
            ax_ph.set_xlim(min(hl_kJ.min(), h_in) - h_margin, 
                          max(hv_kJ.max(), h_out) + h_margin)
            ax_ph.set_ylim(P_sat.min() * 0.8, P_sat.max() * 1.2)
            
            # ========== T-s DIAGRAM ==========
            
            # Plot saturation dome
            ax_ts.plot(sl_kJ, Tl, 'b-', linewidth=2, label='Liquide saturé', zorder=2)
            ax_ts.plot(sv_kJ, Tv, 'r-', linewidth=2, label='Vapeur saturée', zorder=2)
            
            # Plot iso-quality lines
            for x in [0.1, 0.3, 0.5, 0.7, 0.9]:
                s_x = sl + x * (sv - sl)
                s_x_kJ = s_x / 1e3
                ax_ts.plot(s_x_kJ, Tl, 'gray', linewidth=0.5, alpha=0.5, linestyle='--', zorder=1)
            
            # Plot process states
            ax_ts.plot(s_in, T_in, 'go', markersize=12, label='État entrée', zorder=4)
            ax_ts.plot(s_out, T_out, 'rs', markersize=12, label='État sortie', zorder=4)
            
            # Plot process line
            ax_ts.plot([s_in, s_out], [T_in, T_out], 'darkred', linewidth=2.5, label='Chauffage/Vaporisation', zorder=3)
            
            # Add arrow
            ax_ts.annotate('', xy=(s_out, T_out), xytext=(s_in, T_in),
                          arrowprops=dict(arrowstyle='->', color='darkred', lw=2.5))
            
            # Add annotation
            mid_s = (s_in + s_out) / 2
            mid_T = (T_in + T_out) / 2
            ax_ts.annotate('Chauffage / Vaporisation', xy=(mid_s, mid_T), xytext=(mid_s + 0.3, mid_T + 10),
                          fontsize=9, color='darkred', fontweight='bold',
                          arrowprops=dict(arrowstyle='->', color='darkred', lw=1.5),
                          bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
            
            # Add state labels
            ax_ts.text(s_in, T_in - 5, 'Entrée', fontsize=10, color='green', fontweight='bold',
                      ha='center', va='top')
            ax_ts.text(s_out, T_out + 5, 'Sortie', fontsize=10, color='red', fontweight='bold',
                      ha='center', va='bottom')
            
            # Formatting T-s
            ax_ts.set_xlabel('Entropie spécifique s [kJ/kg/K]', fontsize=11, fontweight='bold')
            ax_ts.set_ylabel('Température T [K]', fontsize=11, fontweight='bold')
            ax_ts.set_title('Diagramme Température-Entropie (T-s)', fontsize=12, fontweight='bold')
            ax_ts.grid(True, alpha=0.3, linestyle=':')
            ax_ts.legend(loc='best', fontsize=9, framealpha=0.9)
            
            # Set reasonable limits
            s_margin = max(0.3, abs(s_out - s_in) * 0.3)
            ax_ts.set_xlim(min(sl_kJ.min(), s_in) - s_margin,
                          max(sv_kJ.max(), s_out) + s_margin)
            ax_ts.set_ylim(Tl.min() - 10, Tv.max() + 20)
            
            # Redraw canvas
            canvas.draw()
        
        window.mainloop()
