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
        """Build metrics cards section (top) - 4 cards with grouped metrics."""
        metrics_frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2)
        metrics_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=10)
        
        # 4 equal columns for cards
        for i in range(4):
            metrics_frame.columnconfigure(i, weight=1)
        
        # Card style
        card_style = {'relief': tk.RAISED, 'borderwidth': 2, 'padding': 10}
        
        # ===== CARTE 1: Performances (COP, Q_evap, Q_gen) =====
        card_perf = ttk.LabelFrame(metrics_frame, text="⚡ Performances", **card_style)
        card_perf.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        # COP
        ttk.Label(card_perf, text="COP:", font=('Arial', 10)).pack()
        self.lbl_cop_value = ttk.Label(card_perf, text="--", font=('Arial', 18, 'bold'), foreground='darkblue')
        self.lbl_cop_value.pack()
        
        # Q_evap
        ttk.Label(card_perf, text="Q_evap:", font=('Arial', 10)).pack(pady=(5,0))
        self.lbl_qevap_value = ttk.Label(card_perf, text="-- kW", font=('Arial', 14, 'bold'), foreground='blue')
        self.lbl_qevap_value.pack()
        
        # Q_gen
        ttk.Label(card_perf, text="Q_gen:", font=('Arial', 10)).pack(pady=(5,0))
        self.lbl_qgen_value = ttk.Label(card_perf, text="-- kW", font=('Arial', 14, 'bold'), foreground='red')
        self.lbl_qgen_value.pack()
        
        # ===== CARTE 2: Énergies (mu, Q_cond, W_pump) =====
        card_energy = ttk.LabelFrame(metrics_frame, text="🔥 Énergies", **card_style)
        card_energy.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        # mu
        ttk.Label(card_energy, text="μ (ṁ_s/ṁ_p):", font=('Arial', 10)).pack()
        self.lbl_mu_value = ttk.Label(card_energy, text="--", font=('Arial', 18, 'bold'), foreground='green')
        self.lbl_mu_value.pack()
        
        # Q_cond
        ttk.Label(card_energy, text="Q_cond:", font=('Arial', 10)).pack(pady=(5,0))
        self.lbl_qcond_value = ttk.Label(card_energy, text="-- kW", font=('Arial', 14, 'bold'), foreground='orange')
        self.lbl_qcond_value.pack()
        
        # W_pump
        ttk.Label(card_energy, text="W_pump:", font=('Arial', 10)).pack(pady=(5,0))
        self.lbl_wpump_value = ttk.Label(card_energy, text="-- kW", font=('Arial', 14, 'bold'), foreground='purple')
        self.lbl_wpump_value.pack()
        
        # ===== CARTE 3: Débits (m_dot_total, m_dot_p, m_dot_s) =====
        card_flow = ttk.LabelFrame(metrics_frame, text="💧 Débits Massiques", **card_style)
        card_flow.grid(row=0, column=2, padx=5, pady=5, sticky='nsew')
        
        # m_dot_total
        ttk.Label(card_flow, text="ṁ_total:", font=('Arial', 10)).pack()
        self.lbl_mdot_total_value = ttk.Label(card_flow, text="-- kg/s", font=('Arial', 16, 'bold'), foreground='black')
        self.lbl_mdot_total_value.pack()
        
        # m_dot_p
        ttk.Label(card_flow, text="ṁ_p (primaire):", font=('Arial', 10)).pack(pady=(5,0))
        self.lbl_mdot_p_value = ttk.Label(card_flow, text="-- kg/s", font=('Arial', 12))
        self.lbl_mdot_p_value.pack()
        
        # m_dot_s
        ttk.Label(card_flow, text="ṁ_s (secondaire):", font=('Arial', 10)).pack(pady=(5,0))
        self.lbl_mdot_s_value = ttk.Label(card_flow, text="-- kg/s", font=('Arial', 12))
        self.lbl_mdot_s_value.pack()
        
        # ===== CARTE 4: État Système & Flags =====
        card_flags = ttk.LabelFrame(metrics_frame, text="🚦 État Système", **card_style)
        card_flags.grid(row=0, column=3, padx=5, pady=5, sticky='nsew')
        
        # État global
        ttk.Label(card_flags, text="État global:", font=('Arial', 10)).pack()
        self.lbl_global_status = ttk.Label(card_flags, text="● En attente", font=('Arial', 12, 'bold'), foreground='gray')
        self.lbl_global_status.pack(pady=(0,10))
        
        # Flags (scrollable text)
        flag_subframe = ttk.Frame(card_flags)
        flag_subframe.pack(fill=tk.BOTH, expand=True)
        self.txt_flags = tk.Text(flag_subframe, height=8, width=25, font=('Courier', 8), wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1)
        self.txt_flags.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_flags = ttk.Scrollbar(flag_subframe, orient=tk.VERTICAL, command=self.txt_flags.yview)
        scrollbar_flags.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_flags.config(yscrollcommand=scrollbar_flags.set)
        self.txt_flags.insert('1.0', 'Aucun diagnostic\n')
        self.txt_flags.config(state=tk.DISABLED)
    
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
        """Build parameters control panel with 2 columns layout."""
        params_container = ttk.LabelFrame(parent, text="🎛️ Contrôle Système", relief=tk.RIDGE, borderwidth=2, padding=10)
        params_container.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # 2 columns layout
        params_container.columnconfigure(0, weight=1)
        params_container.columnconfigure(1, weight=1)
        params_container.rowconfigure(0, weight=1)
        
        # Store parameter widgets
        self.param_widgets = {}
        
        # ===== COLONNE GAUCHE: PARAMÈTRES D'ENTRÉE =====
        frame_inputs = ttk.Frame(params_container, padding=5)
        frame_inputs.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        ttk.Label(frame_inputs, text="📋 PARAMÈTRES D'ENTRÉE", font=('Arial', 10, 'bold'), foreground='darkblue').pack(anchor='w', pady=(0,10))
        
        # Q_evap_target
        ttk.Label(frame_inputs, text="Puiss. Frigorifique Cible:", font=('Arial', 9, 'bold')).pack(anchor='w')
        var_q = tk.DoubleVar(value=12.0)
        self.param_widgets['Q_evap_target'] = var_q
        
        q_display_frame = ttk.Frame(frame_inputs)
        q_display_frame.pack(fill='x', pady=2)
        lbl_q_val = ttk.Label(q_display_frame, textvariable=var_q, font=('Arial', 16, 'bold'), foreground='blue')
        lbl_q_val.pack(side=tk.LEFT)
        ttk.Label(q_display_frame, text=" kW", font=('Arial', 10)).pack(side=tk.LEFT)
        
        slider_q = ttk.Scale(frame_inputs, from_=0, to=120, variable=var_q, orient=tk.HORIZONTAL)
        slider_q.pack(fill='x', pady=2)
        
        q_entry_frame = ttk.Frame(frame_inputs)
        q_entry_frame.pack(fill='x', pady=2)
        ttk.Entry(q_entry_frame, textvariable=var_q, width=8).pack(side=tk.LEFT)
        ttk.Label(q_entry_frame, text=" kW").pack(side=tk.LEFT)
        
        ttk.Separator(frame_inputs, orient=tk.HORIZONTAL).pack(fill='x', pady=8)
        
        # T_evap
        ttk.Label(frame_inputs, text="Temp. Évaporation:", font=('Arial', 9, 'bold')).pack(anchor='w')
        var_tevap = tk.DoubleVar(value=10.0)
        self.param_widgets['T_evap'] = var_tevap
        
        tevap_display_frame = ttk.Frame(frame_inputs)
        tevap_display_frame.pack(fill='x', pady=2)
        lbl_tevap_val = ttk.Label(tevap_display_frame, textvariable=var_tevap, font=('Arial', 14, 'bold'), foreground='cyan')
        lbl_tevap_val.pack(side=tk.LEFT)
        ttk.Label(tevap_display_frame, text=" °C", font=('Arial', 10)).pack(side=tk.LEFT)
        
        slider_tevap = ttk.Scale(frame_inputs, from_=-5, to=20, variable=var_tevap, orient=tk.HORIZONTAL)
        slider_tevap.pack(fill='x', pady=2)
        
        tevap_entry_frame = ttk.Frame(frame_inputs)
        tevap_entry_frame.pack(fill='x', pady=2)
        ttk.Entry(tevap_entry_frame, textvariable=var_tevap, width=8).pack(side=tk.LEFT)
        ttk.Label(tevap_entry_frame, text=" °C").pack(side=tk.LEFT)
        
        ttk.Separator(frame_inputs, orient=tk.HORIZONTAL).pack(fill='x', pady=8)
        
        # T_cond
        ttk.Label(frame_inputs, text="Temp. Condensation:", font=('Arial', 9, 'bold')).pack(anchor='w')
        var_tcond = tk.DoubleVar(value=35.0)
        self.param_widgets['T_cond'] = var_tcond
        
        tcond_frame = ttk.Frame(frame_inputs)
        tcond_frame.pack(fill='x', pady=2)
        ttk.Entry(tcond_frame, textvariable=var_tcond, width=8).pack(side=tk.LEFT)
        ttk.Label(tcond_frame, text=" °C").pack(side=tk.LEFT)
        slider_tcond = ttk.Scale(frame_inputs, from_=25, to=50, variable=var_tcond, orient=tk.HORIZONTAL)
        slider_tcond.pack(fill='x', pady=2)
        
        # T_gen
        ttk.Label(frame_inputs, text="Temp. Générateur:", font=('Arial', 9, 'bold')).pack(anchor='w', pady=(5,0))
        var_tgen = tk.DoubleVar(value=100.0)
        self.param_widgets['T_gen'] = var_tgen
        
        tgen_frame = ttk.Frame(frame_inputs)
        tgen_frame.pack(fill='x', pady=2)
        ttk.Entry(tgen_frame, textvariable=var_tgen, width=8).pack(side=tk.LEFT)
        ttk.Label(tgen_frame, text=" °C").pack(side=tk.LEFT)
        slider_tgen = ttk.Scale(frame_inputs, from_=80, to=160, variable=var_tgen, orient=tk.HORIZONTAL)
        slider_tgen.pack(fill='x', pady=2)
        
        # ===== COLONNE DROITE: OPTIONS & RENDEMENTS =====
        frame_options = ttk.Frame(params_container, padding=5)
        frame_options.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        ttk.Label(frame_options, text="⚙️ OPTIONS", font=('Arial', 10, 'bold'), foreground='darkgreen').pack(anchor='w', pady=(0,10))
        
        # ===== BOUTON PRINCIPAL (EN HAUT) =====
        btn_simulate = ttk.Button(
            frame_options, 
            text="🚀 DIMENSIONNER", 
            command=self._run_simulation
        )
        btn_simulate.pack(fill='x', pady=(0, 15))
        
        ttk.Separator(frame_options, orient=tk.HORIZONTAL).pack(fill='x', pady=5)
        
        # Modèle éjecteur
        ttk.Label(frame_options, text="Modèle Éjecteur:", font=('Arial', 9, 'bold')).pack(anchor='w', pady=(0,3))
        self.var_use_v2 = tk.BooleanVar(value=True)
        chk_v2 = ttk.Checkbutton(
            frame_options, 
            text="☑ V2 Compressible (choc)",
            variable=self.var_use_v2
        )
        chk_v2.pack(anchor='w', pady=2)
        
        ttk.Separator(frame_options, orient=tk.HORIZONTAL).pack(fill='x', pady=8)
        
        # Actions
        ttk.Label(frame_options, text="Actions:", font=('Arial', 9, 'bold')).pack(anchor='w', pady=(0,3))
        
        btn_export = ttk.Button(frame_options, text="💾 Exporter JSON", command=self._export_results)
        btn_export.pack(fill='x', pady=2)
        
        btn_reset = ttk.Button(frame_options, text="🔄 Réinitialiser", command=self._load_default_params)
        btn_reset.pack(fill='x', pady=2)
        
        ttk.Separator(frame_options, orient=tk.HORIZONTAL).pack(fill='x', pady=8)
        
        # Rendements (section repliable)
        ttk.Label(frame_options, text="Rendements (avancé):", font=('Arial', 9, 'bold')).pack(anchor='w', pady=(0,3))
        
        self.advanced_visible = tk.BooleanVar(value=False)
        btn_toggle_eta = ttk.Checkbutton(
            frame_options,
            text="▼ Afficher les rendements",
            variable=self.advanced_visible,
            command=self._toggle_advanced_params
        )
        btn_toggle_eta.pack(anchor='w', pady=2)
        
        # Advanced frame (initially hidden)
        self.advanced_frame = ttk.Frame(frame_options)
        
        # η pompe
        var_eta_pump = tk.DoubleVar(value=0.7)
        self.param_widgets['eta_pump'] = var_eta_pump
        pump_frame = ttk.Frame(self.advanced_frame)
        pump_frame.pack(fill='x', pady=1)
        ttk.Label(pump_frame, text="η pompe:", width=10, anchor='w').pack(side=tk.LEFT)
        ttk.Entry(pump_frame, textvariable=var_eta_pump, width=5).pack(side=tk.LEFT)
        
        # η tuyère
        var_eta_noz = tk.DoubleVar(value=0.85)
        self.param_widgets['eta_nozzle'] = var_eta_noz
        noz_frame = ttk.Frame(self.advanced_frame)
        noz_frame.pack(fill='x', pady=1)
        ttk.Label(noz_frame, text="η tuyère:", width=10, anchor='w').pack(side=tk.LEFT)
        ttk.Entry(noz_frame, textvariable=var_eta_noz, width=5).pack(side=tk.LEFT)
        
        # η diffuseur
        var_eta_diff = tk.DoubleVar(value=0.85)
        self.param_widgets['eta_diffuser'] = var_eta_diff
        diff_frame = ttk.Frame(self.advanced_frame)
        diff_frame.pack(fill='x', pady=1)
        ttk.Label(diff_frame, text="η diffuseur:", width=10, anchor='w').pack(side=tk.LEFT)
        ttk.Entry(diff_frame, textvariable=var_eta_diff, width=5).pack(side=tk.LEFT)
        
        # η mélange
        var_eta_mix = tk.DoubleVar(value=1.0)
        self.param_widgets['eta_mixing'] = var_eta_mix
        mix_frame = ttk.Frame(self.advanced_frame)
        mix_frame.pack(fill='x', pady=1)
        ttk.Label(mix_frame, text="η mélange:", width=10, anchor='w').pack(side=tk.LEFT)
        ttk.Entry(mix_frame, textvariable=var_eta_mix, width=5).pack(side=tk.LEFT)
    
    def _toggle_advanced_params(self):
        """Toggle visibility of advanced efficiency parameters."""
        if self.advanced_visible.get():
            self.advanced_frame.pack(fill='x', pady=5)
        else:
            self.advanced_frame.pack_forget()
    
    def _add_param_block(self, parent, title):
        """Add a parameter block separator."""
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=5)
        lbl = ttk.Label(parent, text=title, font=('Arial', 10, 'bold'), foreground='#00539F')
        lbl.pack(anchor='w', padx=5, pady=2)
    
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
        """
        Draw R718 ejector cycle schematic with OFFICIAL numbering convention.
        
        CONVENTION OFFICIELLE (context.md):
            1→2: Détendeur
            2→3: Évaporateur
            3→4: Chambre de mélange (secondaire)
            4→5: Diffuseur
            5→6: Condenseur
            1→7: Pompe
            7→8: Chaudière
            8→4: Tuyère (primaire)
        """
        self.canvas.delete("all")
        w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 800
        h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 320
        
        components = {
            'condenser': (0.50 * w, 0.15 * h),   # Centre haut
            'pump': (0.15 * w, 0.35 * h),        # Gauche haut
            'generator': (0.15 * w, 0.65 * h),   # Gauche bas (chaudière)
            'ejector': (0.50 * w, 0.50 * h),     # Centre milieu
            'valve': (0.85 * w, 0.35 * h),       # Droite haut (détendeur)
            'evaporator': (0.85 * w, 0.65 * h),  # Droite bas
        }
        
        box_w, box_h = 70, 40
        
        # Condenser (top center - gray)
        x, y = components['condenser']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, 
                                     fill='#e6e6e6', outline='black', width=2, tags='component')
        self.canvas.create_text(x, y, text="Condenseur", font=('Arial', 8, 'bold'))
        
        # Pump (left top - green)
        x, y = components['pump']
        self.canvas.create_oval(x-25, y-25, x+25, y+25, fill='#ccffcc', outline='green', width=2, tags='component')
        self.canvas.create_text(x, y, text="Pompe", font=('Arial', 8, 'bold'))
        
        # Generator/Boiler (left bottom - red/hot)
        x, y = components['generator']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, 
                                     fill='#ffcccc', outline='red', width=2, tags='component')
        self.canvas.create_text(x, y, text="Chaudière", font=('Arial', 8, 'bold'))
        
        # Ejector (center - blue)
        x, y = components['ejector']
        pts = [x-40, y-20, x-10, y, x-40, y+20, x+30, y+15, x+30, y-15]
        self.canvas.create_polygon(pts, fill='#cce5ff', outline='blue', width=2, tags='component')
        self.canvas.create_text(x-5, y, text="Éjecteur", font=('Arial', 8, 'bold'))
        
        # Expansion Valve (right top - orange)
        x, y = components['valve']
        self.canvas.create_polygon(x-15, y-20, x+15, y-20, x+15, y, x-15, y+20, 
                                   fill='#ffe6cc', outline='orange', width=2, tags='component')
        self.canvas.create_text(x, y+28, text="Détendeur", font=('Arial', 7))
        
        # Evaporator (right bottom - cyan/cold)
        x, y = components['evaporator']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, 
                                     fill='#ccffff', outline='cyan', width=2, tags='component')
        self.canvas.create_text(x, y, text="Évaporateur", font=('Arial', 8, 'bold'))
        
        # ===== DRAW PIPES WITH STATE NUMBERS (CONVENTION OFFICIELLE) =====
        
        # State 1: Sortie condenseur (bifurcation)
        x_cond, y_cond = components['condenser']
        x_valve, y_valve = components['valve']
        x_pump, y_pump = components['pump']
        
        # Line from condenser to bifurcation
        bifur_x, bifur_y = x_cond, y_cond + box_h/2 + 20
        self.canvas.create_line(x_cond, y_cond+box_h/2, bifur_x, bifur_y, 
                               fill='black', width=2, tags='pipe')
        
        # État 1: sur le tuyau avant bifurcation
        self.canvas.create_text(bifur_x + 15, bifur_y - 5, text="①", font=('Arial', 10, 'bold'), 
                               fill='darkblue', tags='state_label')
        
        # 1→2: Détendeur (branch to right)
        mid_x_valve = (bifur_x + x_valve) / 2
        self.canvas.create_line(bifur_x, bifur_y, mid_x_valve, bifur_y, 
                               fill='black', width=2, tags='pipe')
        self.canvas.create_line(mid_x_valve, bifur_y, x_valve, y_valve-20, 
                               fill='black', width=2, arrow=tk.LAST, tags='pipe')
        
        # 2→3: Évaporateur
        x_evap, y_evap = components['evaporator']
        self.canvas.create_line(x_valve, y_valve+20, x_evap, y_evap-box_h/2, 
                               fill='orange', width=2, arrow=tk.LAST, tags='pipe')
        
        # État 2: sur le tuyau entre détendeur et évaporateur
        self.canvas.create_text((x_valve + x_evap)/2 + 10, (y_valve+20 + y_evap-box_h/2)/2, 
                               text="②", font=('Arial', 10, 'bold'), 
                               fill='darkorange', tags='state_label')
        
        # 3→4: Aspiration secondaire vers éjecteur
        x_ej, y_ej = components['ejector']
        self.canvas.create_line(x_evap-box_w/2, y_evap, x_ej-40, y_ej+20, 
                               fill='cyan', width=2, arrow=tk.LAST, tags='pipe')
        
        # État 3: sur le tuyau entre évaporateur et éjecteur
        self.canvas.create_text((x_evap-box_w/2 + x_ej-40)/2, (y_evap + y_ej+20)/2 - 10, 
                               text="③", font=('Arial', 10, 'bold'), 
                               fill='darkcyan', tags='state_label')
        
        # 1→7: Pompe (branch to left)
        mid_x_pump = (bifur_x + x_pump + 25) / 2
        self.canvas.create_line(bifur_x, bifur_y, mid_x_pump, bifur_y, 
                               fill='black', width=2, tags='pipe')
        self.canvas.create_line(mid_x_pump, bifur_y, x_pump+25, y_pump, 
                               fill='black', width=2, arrow=tk.LAST, tags='pipe')
        
        # 7→8: Chaudière
        x_gen, y_gen = components['generator']
        self.canvas.create_line(x_pump, y_pump+25, x_gen, y_gen-box_h/2, 
                               fill='green', width=2, arrow=tk.LAST, tags='pipe')
        
        # État 7: sur le tuyau entre pompe et chaudière
        self.canvas.create_text((x_pump + x_gen)/2 - 15, (y_pump+25 + y_gen-box_h/2)/2, 
                               text="⑦", font=('Arial', 10, 'bold'), 
                               fill='darkgreen', tags='state_label')
        
        # 8→4: Tuyère primaire
        self.canvas.create_line(x_gen+box_w/2, y_gen, x_ej-40, y_ej, 
                               fill='red', width=3, arrow=tk.LAST, tags='pipe')
        
        # État 8: sur le tuyau entre chaudière et éjecteur
        self.canvas.create_text((x_gen+box_w/2 + x_ej-40)/2, y_gen - 10, 
                               text="⑧", font=('Arial', 10, 'bold'), 
                               fill='darkred', tags='state_label')
        
        # État 4: Chambre de mélange (inside ejector)
        self.canvas.create_text(x_ej-15, y_ej, text="④", font=('Arial', 10, 'bold'), 
                               fill='blue', tags='state_label')
        
        # 5→6: Condenseur
        self.canvas.create_line(x_ej+30, y_ej, x_cond-box_w/2, y_cond, 
                               fill='purple', width=2, arrow=tk.LAST, tags='pipe')
        
        # État 5: sur le tuyau à la sortie éjecteur
        self.canvas.create_text((x_ej+30 + x_cond-box_w/2)/2 + 10, (y_ej + y_cond)/2 - 10, 
                               text="⑤", font=('Arial', 10, 'bold'), 
                               fill='purple', tags='state_label')
        
        # État 6: sur le tuyau avant entrée condenseur
        self.canvas.create_text(x_cond-box_w/2 - 15, y_cond - 15, 
                               text="⑥", font=('Arial', 10, 'bold'), 
                               fill='darkgray', tags='state_label')
        
        # Add simplified legend (NUMBERS ONLY per user request)
        legend_x, legend_y = 10, h - 40
        self.canvas.create_text(legend_x, legend_y, text="États: 1→2→3→4→5→6, 1→7→8→4", 
                               font=('Arial', 8, 'bold'), anchor='w')
    
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
        # Main parameters
        if 'Q_evap_target' in self.param_widgets:
            self.param_widgets['Q_evap_target'].set(12.0)  # kW
        if 'T_evap' in self.param_widgets:
            self.param_widgets['T_evap'].set(10.0)  # °C
        
        # Advanced parameters
        if 'T_cond' in self.param_widgets:
            self.param_widgets['T_cond'].set(35.0)
        if 'T_gen' in self.param_widgets:
            self.param_widgets['T_gen'].set(100.0)
        if 'eta_nozzle' in self.param_widgets:
            self.param_widgets['eta_nozzle'].set(0.85)
        if 'eta_diffuser' in self.param_widgets:
            self.param_widgets['eta_diffuser'].set(0.85)
        if 'eta_mixing' in self.param_widgets:
            self.param_widgets['eta_mixing'].set(1.0)
        
        self.var_use_v2.set(True)
    
    def _get_params_from_ui(self) -> Dict:
        """Extract parameters from UI widgets for dimensioning mode."""
        params = {}
        
        # Main inputs (user-controlled)
        params['Q_evap_target'] = self.param_widgets['Q_evap_target'].get()  # kW
        params['T_evap'] = self.param_widgets['T_evap'].get() + 273.15  # °C → K
        
        # Advanced parameters
        params['T_cond'] = self.param_widgets.get('T_cond', tk.DoubleVar(value=35.0)).get() + 273.15
        params['T_gen'] = self.param_widgets.get('T_gen', tk.DoubleVar(value=100.0)).get() + 273.15
        params['eta_nozzle'] = self.param_widgets.get('eta_nozzle', tk.DoubleVar(value=0.85)).get()
        params['eta_diffuser'] = self.param_widgets.get('eta_diffuser', tk.DoubleVar(value=0.85)).get()
        params['eta_mixing'] = self.param_widgets.get('eta_mixing', tk.DoubleVar(value=1.0)).get()
        
        # Model selection
        params['use_ejector_v2'] = self.var_use_v2.get()
        
        # Fixed internal parameters (not user-adjustable in dimensioning mode)
        params['m_dot_p'] = 0.020  # Will be calculated by model
        params['K_evap'] = 800.0
        params['A_evap'] = 6.0
        params['K_cond'] = 15.0
        params['A_cond'] = 20.0
        params['K_gen'] = 250.0
        params['A_gen'] = 6.0
        
        return params
    
    def _run_simulation(self):
        """Run cycle dimensioning/simulation and update UI."""
        try:
            # Get parameters
            params = self._get_params_from_ui()
            
            # Update status
            self.lbl_global_status.config(text="● Dimensionnement en cours...", foreground='orange')
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
                self.lbl_global_status.config(text="● ✓ Dimensionnement OK", foreground='green')
            
            # Display summary
            Q_target = params['Q_evap_target']
            Q_actual = result.metrics.get('Q_evap', 0.0)
            mu = result.metrics.get('mu', 0.0)
            cop = result.metrics.get('COP', 0.0)
            
            summary = f"""Dimensionnement terminé!
            
Cible: {Q_target:.1f} kW
Obtenu: {Q_actual:.2f} kW
COP: {cop:.3f}
μ: {mu:.4f}

Lancer l'animation du cycle?"""
            
            if messagebox.askyesno("Dimensionnement réussi", summary):
                self._start_animation()
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec du dimensionnement:\n{str(e)}")
            self.lbl_global_status.config(text="● Erreur", foreground='red')
    
    def _update_metrics(self, result: CycleResult):
        """Update metrics cards with simulation results."""
        metrics = result.metrics
        flags = result.flags
        
        # ===== CARTE 1: Performances =====
        cop = metrics.get('COP', 0.0)
        self.lbl_cop_value.config(text=f"{cop:.3f}")
        
        q_evap = metrics.get('Q_evap', 0.0)
        self.lbl_qevap_value.config(text=f"{q_evap:.2f} kW")
        
        q_gen = metrics.get('Q_gen', 0.0)
        self.lbl_qgen_value.config(text=f"{q_gen:.2f} kW")
        
        # ===== CARTE 2: Énergies =====
        mu = metrics.get('mu', 0.0)
        self.lbl_mu_value.config(text=f"{mu:.4f}")
        
        q_cond = metrics.get('Q_cond', 0.0)
        self.lbl_qcond_value.config(text=f"{q_cond:.2f} kW")
        
        w_pump = metrics.get('W_pump', 0.0)
        self.lbl_wpump_value.config(text=f"{w_pump:.3f} kW")
        
        # ===== CARTE 3: Débits =====
        m_dot_total = metrics.get('m_dot_total', 0.0)
        self.lbl_mdot_total_value.config(text=f"{m_dot_total:.5f} kg/s")
        
        m_dot_p = metrics.get('m_dot_p', 0.0)
        self.lbl_mdot_p_value.config(text=f"{m_dot_p:.5f} kg/s")
        
        m_dot_s = metrics.get('m_dot_s', 0.0)
        self.lbl_mdot_s_value.config(text=f"{m_dot_s:.5f} kg/s")
        
        # ===== CARTE 4: État & Flags =====
        # Global status
        if flags.get('error', False):
            self.lbl_global_status.config(text="● Erreur Critique", foreground='red')
        elif flags.get('dimensioning_not_converged', False):
            self.lbl_global_status.config(text="● Non Convergé", foreground='orange')
        elif flags.get('success', True):
            self.lbl_global_status.config(text="● ✓ OK", foreground='green')
        else:
            self.lbl_global_status.config(text="● Inconnu", foreground='gray')
        
        # Flags text display
        self.txt_flags.config(state=tk.NORMAL)
        self.txt_flags.delete('1.0', tk.END)
        
        flag_text = ""
        if flags.get('success', False):
            flag_text += "✓ SUCCESS\\n"
        if flags.get('error', False):
            flag_text += "✗ ERROR\\n"
        if flags.get('mismatch_active', False):
            flag_text += "⚠ MISMATCH ACTIF\\n"
        if flags.get('dimensioning_not_converged', False):
            flag_text += "⚠ NON CONVERGÉ\\n"
        if flags.get('low_cop', False):
            flag_text += "⚠ COP faible\\n"
        if flags.get('low_entrainment', False):
            flag_text += "⚠ μ faible\\n"
        
        # Ejector flags
        for key, value in flags.items():
            if key.startswith('ejector_') and value:
                flag_name = key.replace('ejector_', '').replace('_', ' ').title()
                flag_text += f"• Ejector: {flag_name}\\n"
        
        if not flag_text:
            flag_text = "Aucun diagnostic particulier\\n"
        
        # Add notes
        if result.notes:
            flag_text += "\\n--- Notes ---\\n"
            flag_text += result.notes
        
        self.txt_flags.insert('1.0', flag_text)
        self.txt_flags.config(state=tk.DISABLED)
    
    def _update_diagrams(self, result: CycleResult):
        """
        Update P-h and T-s diagrams with cycle states.
        
        CONVENTION OFFICIELLE (context.md):
            1→2→3→4→5→6→1 (cycle principal)
            1→7→8→4 (cycle chaud)
        
        AFFICHAGE: UNIQUEMENT LES NUMÉROS (1,2,3,4,5,6,7,8) - PAS DE TEXTE DESCRIPTIF
        """
        states = result.states
        
        if not states:
            return
        
        # ===== PLOT P-h DIAGRAM =====
        self.ax_ph.clear()
        self.ax_ph.set_xlabel('Enthalpie h [kJ/kg]', fontsize=11)
        self.ax_ph.set_ylabel('Pression P [kPa]', fontsize=11)
        self.ax_ph.set_title('Diagramme P-h', fontsize=12, fontweight='bold')
        self.ax_ph.set_yscale('log')
        
        # Draw saturation dome (simplified)
        try:
            self._draw_saturation_dome_ph(self.ax_ph)
        except:
            pass
        
        # Extract state properties
        def get_h(i):
            return states[i].h / 1000.0 if i in states and states[i].h is not None else None
        
        def get_P(i):
            return states[i].P / 1000.0 if i in states and states[i].P is not None else None
        
        # CYCLE PRINCIPAL (bleu): 1→2→3→4→5→6→1
        cycle_main = [1, 2, 3]
        if all(get_h(i) and get_P(i) for i in cycle_main):
            h_main = [get_h(i) for i in cycle_main]
            P_main = [get_P(i) for i in cycle_main]
            self.ax_ph.plot(h_main, P_main, 'b-', linewidth=2.5, zorder=3)
        
        # CYCLE CHAUD (rouge): 1→7→8
        cycle_hot = [1, 7, 8]
        if all(get_h(i) and get_P(i) for i in cycle_hot):
            h_hot = [get_h(i) for i in cycle_hot]
            P_hot = [get_P(i) for i in cycle_hot]
            self.ax_ph.plot(h_hot, P_hot, 'r-', linewidth=2.5, zorder=3)
        
        # ÉJECTEUR: 3→4 (secondaire), 8→4 (primaire), 4→5 (diffuseur)
        # 3→4 (aspiration secondaire)
        if all(get_h(i) and get_P(i) for i in [3, 4]):
            self.ax_ph.plot([get_h(3), get_h(4)], [get_P(3), get_P(4)], 'c--', linewidth=2, alpha=0.6, zorder=2)
        
        # 8→4 (tuyère primaire)
        if all(get_h(i) and get_P(i) for i in [8, 4]):
            self.ax_ph.plot([get_h(8), get_h(4)], [get_P(8), get_P(4)], 'r--', linewidth=2, alpha=0.6, zorder=2)
        
        # 4→5 (diffuseur)
        if all(get_h(i) and get_P(i) for i in [4, 5]):
            self.ax_ph.plot([get_h(4), get_h(5)], [get_P(4), get_P(5)], 'm-', linewidth=2.5, zorder=3)
        
        # 5→6 (condensation)
        if all(get_h(i) and get_P(i) for i in [5, 6]):
            self.ax_ph.plot([get_h(5), get_h(6)], [get_P(5), get_P(6)], 'g-', linewidth=2.5, zorder=3)
        
        # 6→1 (bouclage)
        if all(get_h(i) and get_P(i) for i in [6, 1]):
            self.ax_ph.plot([get_h(6), get_h(1)], [get_P(6), get_P(1)], 'g--', linewidth=1.5, alpha=0.5, zorder=2)
        
        # Annotations: UNIQUEMENT LES NUMÉROS avec offsets intelligents
        offsets_ph = {
            1: (-10, 8),   # Condenseur outlet
            2: (8, -8),    # Détendeur outlet
            3: (8, 8),     # Évaporateur outlet
            4: (0, -12),   # Mélange
            5: (8, 5),     # Diffuseur
            6: (-8, -10),  # Condenseur
            7: (8, -5),    # Pompe
            8: (8, 8),     # Chaudière
        }
        
        for i in [1, 2, 3, 4, 5, 6, 7, 8]:
            h, P = get_h(i), get_P(i)
            if h and P:
                offset = offsets_ph.get(i, (3, 3))
                self.ax_ph.annotate(str(i), (h, P), textcoords="offset points", 
                                   xytext=offset, fontsize=9, color='black', fontweight='bold',
                                   zorder=5)
        
        # Zoomer sur la zone utile
        all_h = [get_h(i) for i in [1, 2, 3, 4, 5, 6, 7, 8] if get_h(i)]
        all_P = [get_P(i) for i in [1, 2, 3, 4, 5, 6, 7, 8] if get_P(i)]
        
        if all_h and all_P:
            h_min, h_max = min(all_h), max(all_h)
            P_min, P_max = min(all_P), max(all_P)
            
            # Ajouter une marge de 15%
            h_margin = (h_max - h_min) * 0.15
            # Pour P en échelle log, utiliser une marge multiplicative
            P_margin_factor = 1.3
            
            self.ax_ph.set_xlim(h_min - h_margin, h_max + h_margin)
            self.ax_ph.set_ylim(P_min / P_margin_factor, P_max * P_margin_factor)
        
        self.ax_ph.grid(True, alpha=0.3, which='both', linestyle='--')
        self.canvas_ph.draw()
        
        # ===== PLOT T-s DIAGRAM =====
        self.ax_ts.clear()
        self.ax_ts.set_xlabel('Entropie s [kJ/kg/K]', fontsize=11)
        self.ax_ts.set_ylabel('Température T [K]', fontsize=11)
        self.ax_ts.set_title('Diagramme T-s', fontsize=12, fontweight='bold')
        
        # Draw saturation dome
        try:
            self._draw_saturation_dome_ts(self.ax_ts)
        except:
            pass
        
        def get_s(i):
            return states[i].s / 1000.0 if i in states and states[i].s is not None else None
        
        def get_T(i):
            return states[i].T if i in states and states[i].T is not None else None
        
        # CYCLE PRINCIPAL (bleu): 1→2→3
        if all(get_s(i) and get_T(i) for i in [1, 2, 3]):
            s_main = [get_s(i) for i in [1, 2, 3]]
            T_main = [get_T(i) for i in [1, 2, 3]]
            self.ax_ts.plot(s_main, T_main, 'b-', linewidth=2.5, zorder=3)
        
        # CYCLE CHAUD (rouge): 1→7→8
        if all(get_s(i) and get_T(i) for i in [1, 7, 8]):
            s_hot = [get_s(i) for i in [1, 7, 8]]
            T_hot = [get_T(i) for i in [1, 7, 8]]
            self.ax_ts.plot(s_hot, T_hot, 'r-', linewidth=2.5, zorder=3)
        
        # ÉJECTEUR: 3→4, 8→4, 4→5
        if all(get_s(i) and get_T(i) for i in [3, 4]):
            self.ax_ts.plot([get_s(3), get_s(4)], [get_T(3), get_T(4)], 'c--', linewidth=2, alpha=0.6, zorder=2)
        
        if all(get_s(i) and get_T(i) for i in [8, 4]):
            self.ax_ts.plot([get_s(8), get_s(4)], [get_T(8), get_T(4)], 'r--', linewidth=2, alpha=0.6, zorder=2)
        
        if all(get_s(i) and get_T(i) for i in [4, 5]):
            self.ax_ts.plot([get_s(4), get_s(5)], [get_T(4), get_T(5)], 'm-', linewidth=2.5, zorder=3)
        
        # 5→6 (condensation)
        if all(get_s(i) and get_T(i) for i in [5, 6]):
            self.ax_ts.plot([get_s(5), get_s(6)], [get_T(5), get_T(6)], 'g-', linewidth=2.5, zorder=3)
        
        # 6→1 (bouclage)
        if all(get_s(i) and get_T(i) for i in [6, 1]):
            self.ax_ts.plot([get_s(6), get_s(1)], [get_T(6), get_T(1)], 'g--', linewidth=1.5, alpha=0.5, zorder=2)
        
        # Annotations: UNIQUEMENT LES NUMÉROS avec offsets intelligents pour éviter superposition
        # Définir des offsets personnalisés pour chaque état basé sur leur position dans le cycle
        offsets = {
            1: (8, -8),   # Condenseur outlet - en bas à droite
            2: (-10, 5),  # Détendeur outlet - à gauche
            3: (8, 5),    # Évaporateur outlet - à droite
            4: (0, -12),  # Mélange - en haut
            5: (10, -5),  # Diffuseur - en haut à droite
            6: (-8, 8),   # Condenseur - en haut à gauche
            7: (5, -10),  # Pompe - en haut à droite
            8: (8, 8),    # Chaudière - en haut à droite
        }
        
        for i in [1, 2, 3, 4, 5, 6, 7, 8]:
            s, T = get_s(i), get_T(i)
            if s and T:
                offset = offsets.get(i, (3, 3))
                self.ax_ts.annotate(str(i), (s, T), textcoords="offset points", 
                                   xytext=offset, fontsize=9, color='black', fontweight='bold',
                                   zorder=5)
        
        # Zoomer sur la zone utile du cycle
        all_s = [get_s(i) for i in [1, 2, 3, 4, 5, 6, 7, 8] if get_s(i)]
        all_T = [get_T(i) for i in [1, 2, 3, 4, 5, 6, 7, 8] if get_T(i)]
        
        if all_s and all_T:
            s_min, s_max = min(all_s), max(all_s)
            T_min, T_max = min(all_T), max(all_T)
            
            # Ajouter une marge de 10%
            s_margin = (s_max - s_min) * 0.15
            T_margin = (T_max - T_min) * 0.15
            
            self.ax_ts.set_xlim(s_min - s_margin, s_max + s_margin)
            self.ax_ts.set_ylim(T_min - T_margin, T_max + T_margin)
        
        self.ax_ts.grid(True, alpha=0.3, linestyle='--')
        self.canvas_ts.draw()
    
    def _draw_saturation_dome_ph(self, ax):
        """Draw saturation dome on P-h diagram."""
        from app_r718.core.props_service import get_props_service
        props = get_props_service()
        
        # Temperature range for saturation dome
        T_range = np.linspace(273.15, 647.0, 50)  # 0°C to near critical point
        
        h_liq, h_vap = [], []
        P_sat = []
        
        for T in T_range:
            try:
                P = props.Psat_T(T)
                h_l = props.h_PX(P, 0.0) / 1000.0  # kJ/kg
                h_v = props.h_PX(P, 1.0) / 1000.0
                
                h_liq.append(h_l)
                h_vap.append(h_v)
                P_sat.append(P / 1000.0)  # kPa
            except:
                continue
        
        if h_liq and h_vap:
            ax.plot(h_liq, P_sat, 'k--', linewidth=1, alpha=0.4, label='Cloche saturation')
            ax.plot(h_vap, P_sat, 'k--', linewidth=1, alpha=0.4)
    
    def _draw_saturation_dome_ts(self, ax):
        """Draw saturation dome on T-s diagram."""
        from app_r718.core.props_service import get_props_service
        props = get_props_service()
        
        # Temperature range
        T_range = np.linspace(273.15, 647.0, 50)
        
        s_liq, s_vap = [], []
        T_sat = []
        
        for T in T_range:
            try:
                P = props.Psat_T(T)
                s_l = props.s_PX(P, 0.0) / 1000.0  # kJ/kg/K
                s_v = props.s_PX(P, 1.0) / 1000.0
                
                s_liq.append(s_l)
                s_vap.append(s_v)
                T_sat.append(T)
            except:
                continue
        
        if s_liq and s_vap:
            ax.plot(s_liq, T_sat, 'k--', linewidth=1, alpha=0.4, label='Cloche saturation')
            ax.plot(s_vap, T_sat, 'k--', linewidth=1, alpha=0.4)
    
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
