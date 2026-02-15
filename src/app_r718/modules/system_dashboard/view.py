"""
System Dashboard View

Tkinter UI for complete R718 cycle simulation with:
- Metrics cards display
- Cycle schematic with animation
- Parameter controls
- P-h and T-s diagrams
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional
import numpy as np

# Matplotlib integration
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .controller import SystemCycleController
from .model import CycleResult


class SystemDashboardView:
    """Complete system dashboard UI (Toplevel window)."""
    
    def __init__(self, parent):
        """
        Initialize dashboard window.
        
        Args:
            parent: Parent Tk window
        """
        self.parent = parent
        self.controller = SystemCycleController()
        
        # Create Toplevel window
        self.window = tk.Toplevel(parent)
        self.window.title("Système Complet - Dashboard R718")
        self.window.geometry("1400x900")
        
        # Animation state
        self.animation_running = False
        self.animation_position = 0
        self.animation_particles = []
        
        # Build UI
        self._build_ui()
        
        # Load default parameters
        self._load_default_params()
    
    def _build_ui(self):
        """Build complete UI with 3 sections."""
        # Main container with scrollbar support
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for responsiveness
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)  # Metrics (fixed height)
        main_frame.rowconfigure(1, weight=1)  # Canvas + Params (expandable)
        main_frame.rowconfigure(2, weight=1)  # Diagrams (expandable)
        
        # ===== SECTION 1: METRICS CARDS =====
        self._build_metrics_section(main_frame)
        
        # ===== SECTION 2: CANVAS + PARAMETERS =====
        self._build_middle_section(main_frame)
        
        # ===== SECTION 3: DIAGRAMS =====
        self._build_diagrams_section(main_frame)
    
    def _build_metrics_section(self, parent):
        """Build metrics cards section (top)."""
        metrics_frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2)
        metrics_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        
        # 4 equal columns for cards
        for i in range(4):
            metrics_frame.columnconfigure(i, weight=1)
        
        # Card style
        card_style = {'relief': tk.RAISED, 'borderwidth': 2, 'padding': 10}
        
        # Card 1: COP
        card_cop = ttk.LabelFrame(metrics_frame, text="COP Système", **card_style)
        card_cop.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        self.lbl_cop_value = ttk.Label(card_cop, text="--", font=('Arial', 24, 'bold'))
        self.lbl_cop_value.pack()
        self.lbl_cop_status = ttk.Label(card_cop, text="En attente", foreground='gray')
        self.lbl_cop_status.pack()
        
        # Card 2: Q_evap
        card_qevap = ttk.LabelFrame(metrics_frame, text="Puissance Frigorifique", **card_style)
        card_qevap.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        self.lbl_qevap_value = ttk.Label(card_qevap, text="-- kW", font=('Arial', 24, 'bold'))
        self.lbl_qevap_value.pack()
        self.lbl_qevap_status = ttk.Label(card_qevap, text="Q_evap", foreground='blue')
        self.lbl_qevap_status.pack()
        
        # Card 3: Q_gen
        card_qgen = ttk.LabelFrame(metrics_frame, text="Puissance Thermique", **card_style)
        card_qgen.grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        self.lbl_qgen_value = ttk.Label(card_qgen, text="-- kW", font=('Arial', 24, 'bold'))
        self.lbl_qgen_value.pack()
        self.lbl_qgen_status = ttk.Label(card_qgen, text="Q_gen", foreground='red')
        self.lbl_qgen_status.pack()
        
        # Card 4: mu
        card_mu = ttk.LabelFrame(metrics_frame, text="Taux Entraînement", **card_style)
        card_mu.grid(row=0, column=3, padx=5, pady=5, sticky='nsew')
        self.lbl_mu_value = ttk.Label(card_mu, text="--", font=('Arial', 24, 'bold'))
        self.lbl_mu_value.pack()
        self.lbl_mu_status = ttk.Label(card_mu, text="μ = ṁ_s / ṁ_p", foreground='green')
        self.lbl_mu_status.pack()
        
        # Global status badge
        status_frame = ttk.Frame(metrics_frame)
        status_frame.grid(row=1, column=0, columnspan=4, pady=(5, 0))
        ttk.Label(status_frame, text="État global:").pack(side=tk.LEFT, padx=5)
        self.lbl_global_status = ttk.Label(status_frame, text="● En attente", foreground='gray', font=('Arial', 10, 'bold'))
        self.lbl_global_status.pack(side=tk.LEFT)
    
    def _build_middle_section(self, parent):
        """Build canvas + parameters section (middle)."""
        middle_frame = ttk.Frame(parent)
        middle_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)
        
        # 2 columns: canvas (3/5) and params (2/5)
        middle_frame.columnconfigure(0, weight=3)
        middle_frame.columnconfigure(1, weight=2)
        middle_frame.rowconfigure(0, weight=1)
        
        # ===== LEFT: CANVAS ANIMATION =====
        canvas_frame = ttk.LabelFrame(middle_frame, text="Schéma du Cycle", relief=tk.RIDGE, borderwidth=2)
        canvas_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        self.canvas = tk.Canvas(canvas_frame, bg='white', height=320)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Animation controls
        anim_controls = ttk.Frame(canvas_frame)
        anim_controls.pack(fill=tk.X, padx=5, pady=5)
        self.btn_start_anim = ttk.Button(anim_controls, text="▶ Démarrer Animation", command=self._start_animation)
        self.btn_start_anim.pack(side=tk.LEFT, padx=2)
        self.btn_stop_anim = ttk.Button(anim_controls, text="⏸ Arrêter", command=self._stop_animation, state=tk.DISABLED)
        self.btn_stop_anim.pack(side=tk.LEFT, padx=2)
        
        # Draw initial schematic
        self._draw_cycle_schematic()
        
        # ===== RIGHT: PARAMETERS =====
        self._build_parameters_panel(middle_frame)
    
    def _build_parameters_panel(self, parent):
        """Build parameters control panel (right side of middle section)."""
        params_frame = ttk.LabelFrame(parent, text="Paramètres de Simulation", relief=tk.RIDGE, borderwidth=2)
        params_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Scrollable container
        canvas_scroll = tk.Canvas(params_frame, borderwidth=0, background='#f0f0f0')
        scrollbar = ttk.Scrollbar(params_frame, orient="vertical", command=canvas_scroll.yview)
        scroll_frame = ttk.Frame(canvas_scroll)
        
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )
        
        canvas_scroll.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        
        canvas_scroll.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store parameter widgets
        self.param_widgets = {}
        
        # ===== BLOC A: Operating Conditions =====
        self._add_param_block(scroll_frame, "A - Conditions Nominales")
        self._add_slider_entry(scroll_frame, "T_gen", "T générateur [°C]", 80, 160, 100)
        self._add_slider_entry(scroll_frame, "T_evap", "T évaporateur [°C]", 0, 20, 10)
        self._add_slider_entry(scroll_frame, "T_cond", "T condenseur [°C]", 25, 50, 35)
        
        # ===== BLOC B: Flow Rates =====
        self._add_param_block(scroll_frame, "B - Débits")
        self._add_slider_entry(scroll_frame, "m_dot_p", "ṁ primaire [kg/s]", 0.005, 0.05, 0.020, resolution=0.001)
        
        # ===== BLOC C: Efficiencies =====
        self._add_param_block(scroll_frame, "C - Rendements")
        self._add_slider_entry(scroll_frame, "eta_nozzle", "η tuyère", 0.5, 1.0, 0.85, resolution=0.01)
        self._add_slider_entry(scroll_frame, "eta_diffuser", "η diffuseur", 0.5, 1.0, 0.85, resolution=0.01)
        self._add_slider_entry(scroll_frame, "eta_mixing", "η mélange", 0.8, 1.0, 1.0, resolution=0.01)
        
        # ===== BLOC D: Heat Exchangers =====
        self._add_param_block(scroll_frame, "D - Échangeurs (K, A)")
        
        ttk.Label(scroll_frame, text="Évaporateur:", font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5,2))
        self._add_slider_entry(scroll_frame, "K_evap", "  K_evap [W/m²K]", 100, 1500, 800, resolution=10)
        self._add_slider_entry(scroll_frame, "A_evap", "  A_evap [m²]", 1, 20, 6, resolution=0.5)
        
        ttk.Label(scroll_frame, text="Condenseur:", font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5,2))
        self._add_slider_entry(scroll_frame, "K_cond", "  K_cond [W/m²K]", 5, 50, 15, resolution=1)
        self._add_slider_entry(scroll_frame, "A_cond", "  A_cond [m²]", 5, 50, 20, resolution=1)
        
        ttk.Label(scroll_frame, text="Générateur:", font=('Arial', 9, 'bold')).pack(anchor='w', padx=10, pady=(5,2))
        self._add_slider_entry(scroll_frame, "K_gen", "  K_gen [W/m²K]", 50, 500, 250, resolution=10)
        self._add_slider_entry(scroll_frame, "A_gen", "  A_gen [m²]", 1, 20, 6, resolution=0.5)
        
        # ===== BLOC E: Options =====
        self._add_param_block(scroll_frame, "E - Options")
        
        self.var_use_v2 = tk.BooleanVar(value=True)
        chk_v2 = ttk.Checkbutton(scroll_frame, text="Utiliser Éjecteur V2 (compressible)", variable=self.var_use_v2)
        chk_v2.pack(anchor='w', padx=15, pady=2)
        
        btn_reset = ttk.Button(scroll_frame, text="🔄 Reset Nominal", command=self._load_default_params)
        btn_reset.pack(anchor='w', padx=15, pady=5)
        
        # ===== ACTION BUTTONS =====
        ttk.Separator(scroll_frame, orient='horizontal').pack(fill='x', pady=10)
        
        btn_simulate = ttk.Button(scroll_frame, text="🚀 SIMULER", command=self._run_simulation, style='Accent.TButton')
        btn_simulate.pack(fill='x', padx=10, pady=5)
        
        btn_export = ttk.Button(scroll_frame, text="💾 Exporter Résultats", command=self._export_results)
        btn_export.pack(fill='x', padx=10, pady=2)
    
    def _add_param_block(self, parent, title):
        """Add a parameter block separator."""
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=5)
        lbl = ttk.Label(parent, text=title, font=('Arial', 10, 'bold'), foreground='#00539F')
        lbl.pack(anchor='w', padx=5, pady=2)
    
    def _add_slider_entry(self, parent, key, label, min_val, max_val, default, resolution=1):
        """Add a slider + entry combo for a parameter."""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=10, pady=2)
        
        # Label
        ttk.Label(frame, text=label, width=20, anchor='w').pack(side=tk.LEFT)
        
        # Variable
        var = tk.DoubleVar(value=default)
        self.param_widgets[key] = var
        
        # Entry
        entry = ttk.Entry(frame, textvariable=var, width=8)
        entry.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Slider
        slider = ttk.Scale(frame, from_=min_val, to=max_val, variable=var, orient=tk.HORIZONTAL)
        slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)
    
    def _build_diagrams_section(self, parent):
        """Build P-h and T-s diagrams section (bottom)."""
        diagrams_frame = ttk.Frame(parent)
        diagrams_frame.grid(row=2, column=0, sticky='nsew', padx=10, pady=5)
        
        diagrams_frame.columnconfigure(0, weight=1)
        diagrams_frame.columnconfigure(1, weight=1)
        diagrams_frame.rowconfigure(0, weight=1)
        
        # ===== LEFT: P-h Diagram =====
        ph_frame = ttk.LabelFrame(diagrams_frame, text="Diagramme P-h", relief=tk.RIDGE, borderwidth=2)
        ph_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        self.fig_ph = Figure(figsize=(6, 4), dpi=80)
        self.ax_ph = self.fig_ph.add_subplot(111)
        self.canvas_ph = FigureCanvasTkAgg(self.fig_ph, master=ph_frame)
        self.canvas_ph.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # ===== RIGHT: T-s Diagram =====
        ts_frame = ttk.LabelFrame(diagrams_frame, text="Diagramme T-s", relief=tk.RIDGE, borderwidth=2)
        ts_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        self.fig_ts = Figure(figsize=(6, 4), dpi=80)
        self.ax_ts = self.fig_ts.add_subplot(111)
        self.canvas_ts = FigureCanvasTkAgg(self.fig_ts, master=ts_frame)
        self.canvas_ts.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Initialize empty diagrams
        self._plot_empty_diagrams()
    
    def _draw_cycle_schematic(self):
        """Draw cycle schematic on canvas."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 800
        h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 320
        
        # Component positions (relative)
        components = {
            'generator': (0.15 * w, 0.25 * h),
            'ejector': (0.5 * w, 0.25 * h),
            'condenser': (0.75 * w, 0.25 * h),
            'pump': (0.15 * w, 0.75 * h),
            'valve': (0.50 * w, 0.75 * h),
            'evaporator': (0.75 * w, 0.75 * h),
        }
        
        # Draw components as rectangles
        box_w, box_h = 80, 50
        
        # Generator (red - hot)
        x, y = components['generator']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, fill='#ffcccc', outline='red', width=2, tags='component')
        self.canvas.create_text(x, y, text="Générateur", font=('Arial', 9, 'bold'))
        
        # Ejector (blue - component)
        x, y = components['ejector']
        self.canvas.create_polygon(x-box_w/2, y-box_h/2, x+box_w/2, y, x-box_w/2, y+box_h/2, fill='#cce5ff', outline='blue', width=2, tags='component')
        self.canvas.create_text(x-15, y, text="Éjecteur", font=('Arial', 9, 'bold'))
        
        # Condenser (gray - ambient)
        x, y = components['condenser']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, fill='#e6e6e6', outline='black', width=2, tags='component')
        self.canvas.create_text(x, y, text="Condenseur", font=('Arial', 9, 'bold'))
        
        # Pump (green - work input)
        x, y = components['pump']
        self.canvas.create_oval(x-30, y-30, x+30, y+30, fill='#ccffcc', outline='green', width=2, tags='component')
        self.canvas.create_text(x, y, text="Pompe", font=('Arial', 9, 'bold'))
        
        # Expansion Valve (orange)
        x, y = components['valve']
        self.canvas.create_polygon(x-20, y-25, x+20, y-25, x+20, y, x-20, y+25, fill='#ffe6cc', outline='orange', width=2, tags='component')
        self.canvas.create_text(x, y+15, text="Détendeur", font=('Arial', 8))
        
        # Evaporator (cyan - cold)
        x, y = components['evaporator']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, fill='#ccffff', outline='cyan', width=2, tags='component')
        self.canvas.create_text(x, y, text="Évaporateur", font=('Arial', 9, 'bold'))
        
        # Draw connections (pipes)
        # Pump -> Generator
        self._draw_pipe(components['pump'], components['generator'], 'green')
        
        # Generator -> Ejector (primary)
        self._draw_pipe(components['generator'], components['ejector'], 'red')
        
        # Ejector -> Condenser
        self._draw_pipe(components['ejector'], components['condenser'], 'blue')
        
        # Condenser -> Pump (close loop top)
        x1, y1 = components['condenser']
        x2, y2 = components['pump']
        self.canvas.create_line(x1, y1+25, x1, y1+60, x2+40, y1+60, x2+40, y2-30, fill='black', width=2, arrow=tk.LAST, tags='pipe')
        
        # Condenser -> Valve
        x1, y1 = components['condenser']
        x2, y2 = components['valve']
        self.canvas.create_line(x1, y1+25, x1, (y1+y2)/2, x2, (y1+y2)/2, x2, y2-25, fill='black', width=2, arrow=tk.LAST, tags='pipe')
        
        # Valve -> Evaporator
        self._draw_pipe(components['valve'], components['evaporator'], 'orange')
        
        # Evaporator -> Ejector (secondary)
        x1, y1 = components['evaporator']
        x2, y2 = components['ejector']
        self.canvas.create_line(x1, y1-25, x1, y1-60, x2+40, y1-60, x2+40, y2+25, fill='cyan', width=2, arrow=tk.LAST, tags='pipe')
    
    def _draw_pipe(self, pos1, pos2, color='black'):
        """Draw a simple pipe between two positions."""
        x1, y1 = pos1
        x2, y2 = pos2
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2, arrow=tk.LAST, tags='pipe')
    
    def _plot_empty_diagrams(self):
        """Plot empty P-h and T-s diagrams with placeholder text."""
        # P-h diagram
        self.ax_ph.clear()
        self.ax_ph.set_xlabel('Enthalpie h [kJ/kg]')
        self.ax_ph.set_ylabel('Pression P [kPa]')
        self.ax_ph.set_title('Diagramme P-h')
        self.ax_ph.text(0.5, 0.5, 'Exécutez la simulation', 
                       transform=self.ax_ph.transAxes, ha='center', va='center',
                       fontsize=14, color='gray')
        self.ax_ph.grid(True, alpha=0.3)
        self.canvas_ph.draw()
        
        # T-s diagram
        self.ax_ts.clear()
        self.ax_ts.set_xlabel('Entropie s [kJ/kg/K]')
        self.ax_ts.set_ylabel('Température T [K]')
        self.ax_ts.set_title('Diagramme T-s')
        self.ax_ts.text(0.5, 0.5, 'Exécutez la simulation', 
                       transform=self.ax_ts.transAxes, ha='center', va='center',
                       fontsize=14, color='gray')
        self.ax_ts.grid(True, alpha=0.3)
        self.canvas_ts.draw()
    
    def _load_default_params(self):
        """Load default parameters into UI widgets."""
        defaults = self.controller.get_default_params()
        
        for key, value in defaults.items():
            if key in self.param_widgets:
                self.param_widgets[key].set(value)
        
        self.var_use_v2.set(defaults.get('use_ejector_v2', True))
    
    def _get_params_from_ui(self) -> Dict:
        """Extract parameters from UI widgets."""
        params = {}
        
        # Temperature conversions (°C -> K)
        params['T_gen'] = self.param_widgets['T_gen'].get() + 273.15
        params['T_evap'] = self.param_widgets['T_evap'].get() + 273.15
        params['T_cond'] = self.param_widgets['T_cond'].get() + 273.15
        
        # Direct values
        params['m_dot_p'] = self.param_widgets['m_dot_p'].get()
        params['eta_nozzle'] = self.param_widgets['eta_nozzle'].get()
        params['eta_diffuser'] = self.param_widgets['eta_diffuser'].get()
        params['eta_mixing'] = self.param_widgets['eta_mixing'].get()
        
        # Heat exchangers
        params['K_evap'] = self.param_widgets['K_evap'].get()
        params['A_evap'] = self.param_widgets['A_evap'].get()
        params['K_cond'] = self.param_widgets['K_cond'].get()
        params['A_cond'] = self.param_widgets['A_cond'].get()
        params['K_gen'] = self.param_widgets['K_gen'].get()
        params['A_gen'] = self.param_widgets['A_gen'].get()
        
        # Options
        params['use_ejector_v2'] = self.var_use_v2.get()
        
        return params
    
    def _run_simulation(self):
        """Run cycle simulation and update UI."""
        try:
            # Get parameters
            params = self._get_params_from_ui()
            
            # Update status
            self.lbl_global_status.config(text="● Simulation en cours...", foreground='orange')
            self.window.update()
            
            # Solve cycle
            result = self.controller.solve(params)
            
            # Update UI with results
            self._update_metrics(result)
            self._update_diagrams(result)
            
            # Update global status
            if result.flags.get('error', False):
                self.lbl_global_status.config(text="● Erreur", foreground='red')
                messagebox.showerror("Erreur", result.notes)
            elif result.flags.get('mismatch_active', False):
                self.lbl_global_status.config(text="● Mismatch actif", foreground='orange')
            else:
                self.lbl_global_status.config(text="● OK", foreground='green')
            
            # Ask to start animation
            if messagebox.askyesno("Animation", "Simulation réussie! Lancer l'animation?"):
                self._start_animation()
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de la simulation:\n{str(e)}")
            self.lbl_global_status.config(text="● Erreur", foreground='red')
    
    def _update_metrics(self, result: CycleResult):
        """Update metrics cards with simulation results."""
        metrics = result.metrics
        
        # COP
        cop = metrics.get('COP', 0.0)
        self.lbl_cop_value.config(text=f"{cop:.3f}")
        if cop > 0.5:
            self.lbl_cop_status.config(text="Nominal", foreground='green')
        elif cop > 0.2:
            self.lbl_cop_status.config(text="Faible", foreground='orange')
        else:
            self.lbl_cop_status.config(text="Très faible", foreground='red')
        
        # Q_evap
        q_evap = metrics.get('Q_evap', 0.0)
        self.lbl_qevap_value.config(text=f"{q_evap:.2f} kW")
        self.lbl_qevap_status.config(text=f"Q_evap", foreground='blue')
        
        # Q_gen
        q_gen = metrics.get('Q_gen', 0.0)
        self.lbl_qgen_value.config(text=f"{q_gen:.2f} kW")
        self.lbl_qgen_status.config(text=f"Q_gen", foreground='red')
        
        # mu
        mu = metrics.get('mu', 0.0)
        self.lbl_mu_value.config(text=f"{mu:.4f}")
        if mu > 0.3:
            self.lbl_mu_status.config(text="Bon entraînement", foreground='green')
        elif mu > 0.1:
            self.lbl_mu_status.config(text="Entraînement moyen", foreground='orange')
        else:
            self.lbl_mu_status.config(text="Faible", foreground='red')
    
    def _update_diagrams(self, result: CycleResult):
        """Update P-h and T-s diagrams with cycle states."""
        states = result.states
        
        if not states:
            return
        
        # Extract cycle points
        h_vals = [states[i].h / 1000.0 for i in sorted(states.keys()) if states[i].h is not None]  # kJ/kg
        P_vals = [states[i].P / 1000.0 for i in sorted(states.keys()) if states[i].P is not None]  # kPa
        s_vals = [states[i].s / 1000.0 for i in sorted(states.keys()) if states[i].s is not None]  # kJ/kg/K
        T_vals = [states[i].T for i in sorted(states.keys()) if states[i].T is not None]  # K
        
        # P-h diagram
        self.ax_ph.clear()
        self.ax_ph.set_xlabel('Enthalpie h [kJ/kg]')
        self.ax_ph.set_ylabel('Pression P [kPa]')
        self.ax_ph.set_title('Diagramme P-h - Cycle R718')
        self.ax_ph.set_yscale('log')
        
        # Plot cycle
        if h_vals and P_vals:
            self.ax_ph.plot(h_vals, P_vals, 'ro-', linewidth=2, markersize=8, label='Cycle')
            # Add state numbers
            for i, (h, P) in enumerate(zip(h_vals, P_vals), start=1):
                self.ax_ph.annotate(str(i), (h, P), textcoords="offset points", xytext=(5,5), fontsize=10, color='blue')
        
        self.ax_ph.grid(True, alpha=0.3)
        self.ax_ph.legend()
        self.canvas_ph.draw()
        
        # T-s diagram
        self.ax_ts.clear()
        self.ax_ts.set_xlabel('Entropie s [kJ/kg/K]')
        self.ax_ts.set_ylabel('Température T [K]')
        self.ax_ts.set_title('Diagramme T-s - Cycle R718')
        
        # Plot cycle
        if s_vals and T_vals:
            self.ax_ts.plot(s_vals, T_vals, 'go-', linewidth=2, markersize=8, label='Cycle')
            # Add state numbers
            for i, (s, T) in enumerate(zip(s_vals, T_vals), start=1):
                self.ax_ts.annotate(str(i), (s, T), textcoords="offset points", xytext=(5,5), fontsize=10, color='red')
        
        self.ax_ts.grid(True, alpha=0.3)
        self.ax_ts.legend()
        self.canvas_ts.draw()
    
    def _start_animation(self):
        """Start cycle flow animation."""
        self.animation_running = True
        self.animation_position = 0
        self.btn_start_anim.config(state=tk.DISABLED)
        self.btn_stop_anim.config(state=tk.NORMAL)
        self._animate_step()
    
    def _stop_animation(self):
        """Stop cycle flow animation."""
        self.animation_running = False
        self.btn_start_anim.config(state=tk.NORMAL)
        self.btn_stop_anim.config(state=tk.DISABLED)
        # Clear animation particles
        self.canvas.delete("particle")
    
    def _animate_step(self):
        """Single animation step (recursive via after)."""
        if not self.animation_running:
            return
        
        # Clear old particles
        self.canvas.delete("particle")
        
        # Draw moving particle (simple circle along path)
        # For now, just a simple rotating particle
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        
        # Calculate position along circuit (simplified)
        angle = (self.animation_position % 360) * np.pi / 180
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 3
        
        x = cx + radius * np.cos(angle)
        y = cy + radius * np.sin(angle)
        
        # Draw particle
        self.canvas.create_oval(x-5, y-5, x+5, y+5, fill='red', outline='darkred', tags='particle')
        
        # Increment position
        self.animation_position += 10
        
        # Schedule next frame
        self.window.after(30, self._animate_step)
    
    def _export_results(self):
        """Export simulation results to file."""
        result = self.controller.get_last_result()
        if not result:
            messagebox.showwarning("Attention", "Aucun résultat à exporter. Lancez d'abord une simulation.")
            return
        
        try:
            import json
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                export_data = {
                    'metrics': result.metrics,
                    'flags': result.flags,
                    'notes': result.notes,
                    'states': {
                        i: {
                            'P': state.P,
                            'T': state.T,
                            'h': state.h,
                            's': state.s,
                            'x': state.x,
                        } for i, state in result.states.items()
                    }
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Succès", f"Résultats exportés vers:\n{filename}")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'export:\n{str(e)}")


def open_system_dashboard(parent):
    """Open system dashboard window."""
    dashboard = SystemDashboardView(parent)
    return dashboard
