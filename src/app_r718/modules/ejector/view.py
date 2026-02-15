"""
Ejector View - Console and Tkinter UI

Provides both console-based and graphical user interfaces for ejector simulation.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

from app_r718.core.thermo_state import ThermoState
from app_r718.core.props_service import get_props_service
from app_r718.modules.ejector import EjectorController, EjectorResult


class EjectorView:
    """Console-based view for ejector simulation."""
    
    def __init__(self):
        """Initialize view with controller."""
        self.controller = EjectorController()
        self.props = get_props_service()
    
    def run(self):
        """Run console interface (placeholder for future CLI)."""
        print("Ejector Console View - Not yet implemented")
        print("Use EjectorTkView for graphical interface")


class EjectorTkView:
    """
    Tkinter-based graphical user interface for ejector simulation.
    
    Includes input fields, results display, and dual P-h / T-s diagrams.
    """
    
    @staticmethod
    def open_window(parent=None):
        """
        Open a new ejector simulation window.
        
        Args:
            parent: Parent Tkinter window (optional)
        """
        # Import here to allow headless testing
        import tkinter as tk
        from tkinter import ttk, messagebox
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
        
        controller = EjectorController()
        props = get_props_service()
        
        # Create window
        window = tk.Toplevel(parent) if parent else tk.Tk()
        window.title("Éjecteur (Ejector) - R718")
        window.geometry("1400x900")
        
        # Storage for results
        result_data = {
            "state_p_in": None,
            "state_s_in": None,
            "P_out": None,
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
        
        # --- Temperatures for state generation ---
        ttk.Label(left_frame, text="Conditions nominales:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=5
        )
        
        # Generator temperature
        ttk.Label(left_frame, text="T_gen (générateur) [K]:").grid(
            row=1, column=0, sticky="w", pady=2
        )
        var_T_gen = tk.StringVar(value="373.15")  # 100°C
        ttk.Entry(left_frame, textvariable=var_T_gen, width=15).grid(
            row=1, column=1, sticky="w", pady=2
        )
        
        # Evaporator temperature
        ttk.Label(left_frame, text="T_evap (évaporateur) [K]:").grid(
            row=2, column=0, sticky="w", pady=2
        )
        var_T_evap = tk.StringVar(value="283.15")  # 10°C
        ttk.Entry(left_frame, textvariable=var_T_evap, width=15).grid(
            row=2, column=1, sticky="w", pady=2
        )
        
        # Condenser temperature
        ttk.Label(left_frame, text="T_cond (condenseur) [K]:").grid(
            row=3, column=0, sticky="w", pady=2
        )
        var_T_cond = tk.StringVar(value="308.15")  # 35°C
        ttk.Entry(left_frame, textvariable=var_T_cond, width=15).grid(
            row=3, column=1, sticky="w", pady=2
        )
        
        def generate_nominal_states():
            """Generate nominal primary, secondary, and outlet pressure."""
            try:
                T_gen = float(var_T_gen.get())
                T_evap = float(var_T_evap.get())
                T_cond = float(var_T_cond.get())
                
                # Primary: saturated vapor at generator pressure
                P_gen = props.Psat_T(T_gen)
                state_p_in = ThermoState()
                state_p_in.update_from_PX(P_gen, 1.0)  # Saturated vapor
                
                # Secondary: saturated vapor at evaporator pressure
                P_evap = props.Psat_T(T_evap)
                state_s_in = ThermoState()
                state_s_in.update_from_PX(P_evap, 1.0)  # Saturated vapor
                
                # Outlet pressure: condenser pressure
                P_out = props.Psat_T(T_cond)
                
                # Store
                result_data["state_p_in"] = state_p_in
                result_data["state_s_in"] = state_s_in
                result_data["P_out"] = P_out
                
                messagebox.showinfo(
                    "États générés",
                    f"Primaire (générateur):\n"
                    f"  P_p = {P_gen/1e3:.2f} kPa, T = {T_gen-273.15:.1f} °C\n\n"
                    f"Secondaire (évaporateur):\n"
                    f"  P_s = {P_evap/1e3:.2f} kPa, T = {T_evap-273.15:.1f} °C\n\n"
                    f"Sortie (condenseur):\n"
                    f"  P_out = {P_out/1e3:.2f} kPa, T = {T_cond-273.15:.1f} °C"
                )
            except ValueError as e:
                messagebox.showerror("Erreur", f"Erreur génération états:\n{str(e)}")
        
        ttk.Button(
            left_frame,
            text="📥 Générer états nominaux",
            command=generate_nominal_states,
        ).grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        
        # --- Operating Parameters ---
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        ttk.Label(left_frame, text="Paramètres opératoires:", font=("Arial", 10, "bold")).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=5
        )
        
        # Primary mass flow rate
        ttk.Label(left_frame, text="Débit primaire m_dot_p [kg/s]:").grid(
            row=7, column=0, sticky="w", pady=2
        )
        var_m_dot_p = tk.StringVar(value="0.020")
        ttk.Entry(left_frame, textvariable=var_m_dot_p, width=15).grid(
            row=7, column=1, sticky="w", pady=2
        )
        
        # --- Efficiencies ---
        ttk.Separator(left_frame, orient="horizontal").grid(
            row=8, column=0, columnspan=2, sticky="ew", pady=10
        )
        
        ttk.Label(left_frame, text="Rendements:", font=("Arial", 10, "bold")).grid(
            row=9, column=0, columnspan=2, sticky="w", pady=5
        )
        
        # Nozzle efficiency
        ttk.Label(left_frame, text="η_nozzle (tuyère) [-]:").grid(
            row=10, column=0, sticky="w", pady=2
        )
        var_eta_nozzle = tk.StringVar(value="0.85")
        ttk.Entry(left_frame, textvariable=var_eta_nozzle, width=15).grid(
            row=10, column=1, sticky="w", pady=2
        )
        
        # Diffuser efficiency
        ttk.Label(left_frame, text="η_diffuser (diffuseur) [-]:").grid(
            row=11, column=0, sticky="w", pady=2
        )
        var_eta_diffuser = tk.StringVar(value="0.85")
        ttk.Entry(left_frame, textvariable=var_eta_diffuser, width=15).grid(
            row=11, column=1, sticky="w", pady=2
        )
        
        # Mixing efficiency
        ttk.Label(left_frame, text="η_mixing (mélange) [-]:").grid(
            row=12, column=0, sticky="w", pady=2
        )
        var_eta_mixing = tk.StringVar(value="1.0")
        ttk.Entry(left_frame, textvariable=var_eta_mixing, width=15).grid(
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
            text="Éjecteur - Résultats de Simulation",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=10)
        
        def simulate():
            try:
                # Always regenerate states from current temperature values
                # This makes the UI dynamic - user can change temps and simulate directly
                T_gen = float(var_T_gen.get())
                T_evap = float(var_T_evap.get())
                T_cond = float(var_T_cond.get())
                
                # Generate primary state (saturated vapor at generator pressure)
                P_gen = props.Psat_T(T_gen)
                state_p_in = ThermoState()
                state_p_in.update_from_PX(P_gen, 1.0)  # Saturated vapor
                
                # Generate secondary state (saturated vapor at evaporator pressure)
                P_evap = props.Psat_T(T_evap)
                state_s_in = ThermoState()
                state_s_in.update_from_PX(P_evap, 1.0)  # Saturated vapor
                
                # Outlet pressure: condenser pressure
                P_out = props.Psat_T(T_cond)
                
                # Parse operation parameters
                m_dot_p = float(var_m_dot_p.get())
                eta_nozzle = float(var_eta_nozzle.get())
                eta_diffuser = float(var_eta_diffuser.get())
                eta_mixing = float(var_eta_mixing.get())
                
                # Run simulation
                result = controller.solve(
                    state_p_in=state_p_in,
                    state_s_in=state_s_in,
                    P_out=P_out,
                    m_dot_p=m_dot_p,
                    eta_nozzle=eta_nozzle,
                    eta_diffuser=eta_diffuser,
                    eta_mixing=eta_mixing,
                )
                
                # Store results
                result_data["result"] = result
                result_data["state_p_in"] = state_p_in
                result_data["state_s_in"] = state_s_in
                result_data["P_out"] = P_out
                
                # Display results
                display_results(result, state_p_in, state_s_in)
                
                # Plot diagrams
                plot_diagrams(result, state_p_in, state_s_in)
                
            except ValueError as e:
                messagebox.showerror("Erreur", f"Valeur invalide:\n{str(e)}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur simulation:\n{str(e)}")
        
        # Simulate button
        ttk.Button(
            right_frame,
            text="▶ Simuler",
            command=simulate,
            width=25,
        ).grid(row=1, column=0, columnspan=2, pady=10)
        
        # Results text widget
        results_text = tk.Text(right_frame, width=50, height=20, wrap="word")
        results_text.grid(row=2, column=0, sticky="nsew", pady=5)
        
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=results_text.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        results_text.config(yscrollcommand=scrollbar.set)
        
        def display_results(result: EjectorResult, state_p_in: ThermoState, state_s_in: ThermoState):
            """Display simulation results in text widget."""
            results_text.delete("1.0", "end")
            
            output = []
            output.append("=" * 50)
            output.append("RÉSULTATS - ÉJECTEUR")
            output.append("=" * 50)
            output.append("")
            
            # Entrainment ratio (KEY RESULT)
            output.append("🎯 TAUX D'ENTRAÎNEMENT:")
            output.append(f"  μ = {result.mu:.4f}")
            output.append(f"  m_dot_p = {result.m_dot_p:.4f} kg/s (primaire)")
            output.append(f"  m_dot_s = {result.m_dot_s:.4f} kg/s (secondaire)")
            output.append(f"  m_dot_total = {result.m_dot_p + result.m_dot_s:.4f} kg/s")
            output.append("")
            
            # Mixing pressure
            output.append("⚙️ Pression de mélange:")
            output.append(f"  P_mix = {result.P_mix/1e3:.2f} kPa ({result.P_mix/1e5:.3f} bar)")
            output.append("")
            
            # Primary inlet
            output.append("📥 Primaire entrée (générateur):")
            output.append(f"  P = {state_p_in.P/1e3:.2f} kPa")
            output.append(f"  T = {state_p_in.T:.2f} K ({state_p_in.T-273.15:.2f} °C)")
            output.append(f"  h = {state_p_in.h/1e3:.2f} kJ/kg")
            output.append(f"  s = {state_p_in.s/1e3:.4f} kJ/kg/K")
            output.append("")
            
            # Primary after nozzle
            output.append("🌀 Primaire après tuyère:")
            output.append(f"  P = {result.state_p_noz.P/1e3:.2f} kPa")
            output.append(f"  T = {result.state_p_noz.T:.2f} K ({result.state_p_noz.T-273.15:.2f} °C)")
            output.append(f"  h = {result.state_p_noz.h/1e3:.2f} kJ/kg")
            output.append("")
            
            # Secondary inlet
            output.append("❄️ Secondaire entrée (évaporateur):")
            output.append(f"  P = {state_s_in.P/1e3:.2f} kPa")
            output.append(f"  T = {state_s_in.T:.2f} K ({state_s_in.T-273.15:.2f} °C)")
            output.append(f"  h = {state_s_in.h/1e3:.2f} kJ/kg")
            output.append(f"  s = {state_s_in.s/1e3:.4f} kJ/kg/K")
            output.append("")
            
            # Mixed state
            output.append("🔀 État mélangé:")
            output.append(f"  P = {result.state_mix.P/1e3:.2f} kPa")
            output.append(f"  T = {result.state_mix.T:.2f} K ({result.state_mix.T-273.15:.2f} °C)")
            output.append(f"  h = {result.state_mix.h/1e3:.2f} kJ/kg")
            output.append("")
            
            # Outlet
            output.append("📤 Sortie (vers condenseur):")
            output.append(f"  P = {result.state_out.P/1e3:.2f} kPa")
            output.append(f"  T = {result.state_out.T:.2f} K ({result.state_out.T-273.15:.2f} °C)")
            output.append(f"  h = {result.state_out.h/1e3:.2f} kJ/kg")
            if result.state_out.x is not None:
                output.append(f"  x = {result.state_out.x:.4f}")
            output.append("")
            
            # Diagnostic flags
            output.append("🚩 Diagnostics:")
            for flag_name, flag_value in result.flags.items():
                status = "⚠️ OUI" if flag_value else "✅ Non"
                output.append(f"  {flag_name}: {status}")
            output.append("")
            
            # Notes
            if result.notes:
                output.append("📝 Notes:")
                output.append(f"  {result.notes}")
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
            
            hl = []
            hv = []
            sl = []
            sv = []
            Tl = []
            Tv = []
            
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
        
        def plot_diagrams(result: EjectorResult, state_p_in: ThermoState, state_s_in: ThermoState):
            """Plot P-h and T-s diagrams showing ejector process."""
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
            
            # Extract state data (handle potential None values)
            states = {
                'p_in': (state_p_in.h / 1e3, state_p_in.P, state_p_in.s / 1e3, state_p_in.T),
                'p_noz': (result.state_p_noz.h / 1e3, result.state_p_noz.P, result.state_p_noz.s / 1e3, result.state_p_noz.T),
                's_in': (state_s_in.h / 1e3, state_s_in.P, state_s_in.s / 1e3, state_s_in.T),
                'mix': (result.state_mix.h / 1e3, result.state_mix.P, result.state_mix.s / 1e3, result.state_mix.T),
                'out': (result.state_out.h / 1e3, result.state_out.P, result.state_out.s / 1e3, result.state_out.T),
            }
            
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
            ax_ph.plot(states['p_in'][0], states['p_in'][1], 'mo', markersize=10, label='Prim. entrée', zorder=4)
            ax_ph.plot(states['p_noz'][0], states['p_noz'][1], 'cv', markersize=8, label='Prim. tuyère', zorder=4)
            ax_ph.plot(states['s_in'][0], states['s_in'][1], 'bs', markersize=10, label='Sec. entrée', zorder=4)
            ax_ph.plot(states['mix'][0], states['mix'][1], 'go', markersize=10, label='Mélange', zorder=4)
            ax_ph.plot(states['out'][0], states['out'][1], 'r^', markersize=12, label='Sortie', zorder=4)
            
            # Plot process lines
            # Primary nozzle: p_in → p_noz
            ax_ph.plot([states['p_in'][0], states['p_noz'][0]], 
                      [states['p_in'][1], states['p_noz'][1]], 
                      'm--', linewidth=1.5, alpha=0.7, zorder=3)
            
            # Mixing: p_noz, s_in → mix (simplified representation)
            ax_ph.plot([states['p_noz'][0], states['mix'][0]], 
                      [states['p_noz'][1], states['mix'][1]], 
                      'c-', linewidth=1.5, alpha=0.7, zorder=3)
            ax_ph.plot([states['s_in'][0], states['mix'][0]], 
                      [states['s_in'][1], states['mix'][1]], 
                      'b-', linewidth=1.5, alpha=0.7, zorder=3)
            
            # Diffuser: mix → out
            ax_ph.plot([states['mix'][0], states['out'][0]], 
                      [states['mix'][1], states['out'][1]], 
                      'darkred', linewidth=2.5, zorder=3)
            
            # Add arrows
            ax_ph.annotate('', xy=(states['p_noz'][0], states['p_noz'][1]), 
                          xytext=(states['p_in'][0], states['p_in'][1]),
                          arrowprops=dict(arrowstyle='->', color='magenta', lw=1.5))
            ax_ph.annotate('', xy=(states['out'][0], states['out'][1]), 
                          xytext=(states['mix'][0], states['mix'][1]),
                          arrowprops=dict(arrowstyle='->', color='darkred', lw=2))
            
            # Formatting P-h
            ax_ph.set_xlabel('Enthalpie spécifique h [kJ/kg]', fontsize=11, fontweight='bold')
            ax_ph.set_ylabel('Pression P [Pa]', fontsize=11, fontweight='bold')
            ax_ph.set_title('Diagramme Pression-Enthalpie (P-h)', fontsize=12, fontweight='bold')
            ax_ph.set_yscale('log')
            ax_ph.grid(True, alpha=0.3, which='both', linestyle=':')
            ax_ph.legend(loc='best', fontsize=8, framealpha=0.9)
            
            # Set limits
            h_all = [s[0] for s in states.values()]
            h_min = min(min(hl_kJ), min(h_all)) - 50
            h_max = max(max(hv_kJ), max(h_all)) + 50
            ax_ph.set_xlim(h_min, h_max)
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
            ax_ts.plot(states['p_in'][2], states['p_in'][3], 'mo', markersize=10, label='Prim. entrée', zorder=4)
            ax_ts.plot(states['p_noz'][2], states['p_noz'][3], 'cv', markersize=8, label='Prim. tuyère', zorder=4)
            ax_ts.plot(states['s_in'][2], states['s_in'][3], 'bs', markersize=10, label='Sec. entrée', zorder=4)
            ax_ts.plot(states['mix'][2], states['mix'][3], 'go', markersize=10, label='Mélange', zorder=4)
            ax_ts.plot(states['out'][2], states['out'][3], 'r^', markersize=12, label='Sortie', zorder=4)
            
            # Plot process lines
            ax_ts.plot([states['p_in'][2], states['p_noz'][2]], 
                      [states['p_in'][3], states['p_noz'][3]], 
                      'm--', linewidth=1.5, alpha=0.7, zorder=3)
            ax_ts.plot([states['p_noz'][2], states['mix'][2]], 
                      [states['p_noz'][3], states['mix'][3]], 
                      'c-', linewidth=1.5, alpha=0.7, zorder=3)
            ax_ts.plot([states['s_in'][2], states['mix'][2]], 
                      [states['s_in'][3], states['mix'][3]], 
                      'b-', linewidth=1.5, alpha=0.7, zorder=3)
            ax_ts.plot([states['mix'][2], states['out'][2]], 
                      [states['mix'][3], states['out'][3]], 
                      'darkred', linewidth=2.5, zorder=3)
            
            # Add arrows
            ax_ts.annotate('', xy=(states['p_noz'][2], states['p_noz'][3]), 
                          xytext=(states['p_in'][2], states['p_in'][3]),
                          arrowprops=dict(arrowstyle='->', color='magenta', lw=1.5))
            ax_ts.annotate('', xy=(states['out'][2], states['out'][3]), 
                          xytext=(states['mix'][2], states['mix'][3]),
                          arrowprops=dict(arrowstyle='->', color='darkred', lw=2))
            
            # Formatting T-s
            ax_ts.set_xlabel('Entropie spécifique s [kJ/kg/K]', fontsize=11, fontweight='bold')
            ax_ts.set_ylabel('Température T [K]', fontsize=11, fontweight='bold')
            ax_ts.set_title('Diagramme Température-Entropie (T-s)', fontsize=12, fontweight='bold')
            ax_ts.grid(True, alpha=0.3, linestyle=':')
            ax_ts.legend(loc='best', fontsize=8, framealpha=0.9)
            
            # Set limits
            s_all = [s[2] for s in states.values()]
            s_min = min(min(sl_kJ), min(s_all)) - 0.2
            s_max = max(max(sv_kJ), max(s_all)) + 0.2
            ax_ts.set_xlim(s_min, s_max)
            ax_ts.set_ylim(Tl.min() - 10, Tv.max() + 20)
            
            # Redraw canvas
            canvas.draw()
        
        window.mainloop()
