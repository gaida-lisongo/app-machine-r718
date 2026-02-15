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
        """Build simplified parameters control panel (right side of middle section)."""
        params_frame = ttk.LabelFrame(parent, text="Dimensionnement Système", relief=tk.RIDGE, borderwidth=2)
        params_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Main container (no scroll needed with simplified UI)
        main_container = ttk.Frame(params_frame, padding=10)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Store parameter widgets
        self.param_widgets = {}
        
        # ===== TITLE =====
        title_lbl = ttk.Label(
            main_container, 
            text="🎛 PARAMÈTRES UTILISATEUR", 
            font=('Arial', 11, 'bold'),
            foreground='#00539F'
        )
        title_lbl.pack(pady=(0, 10))
        
        # ===== ENTRÉE 1: Puissance frigorifique cible =====
        self._add_param_block(main_container, "Dimensionnement")
        
        frame_q = ttk.LabelFrame(main_container, text="Puissance Frigorifique Cible", padding=10)
        frame_q.pack(fill='x', pady=5)
        
        var_q = tk.DoubleVar(value=12.0)
        self.param_widgets['Q_evap_target'] = var_q
        
        # Value display
        lbl_q_val = ttk.Label(frame_q, textvariable=var_q, font=('Arial', 20, 'bold'), foreground='blue')
        lbl_q_val.pack()
        ttk.Label(frame_q, text="kW", font=('Arial', 10)).pack()
        
        # Slider
        slider_q = ttk.Scale(frame_q, from_=0, to=120, variable=var_q, orient=tk.HORIZONTAL)
        slider_q.pack(fill='x', pady=5)
        
        # Entry
        entry_frame = ttk.Frame(frame_q)
        entry_frame.pack()
        ttk.Label(entry_frame, text="Valeur exacte:").pack(side=tk.LEFT, padx=(0, 5))
        entry_q = ttk.Entry(entry_frame, textvariable=var_q, width=10)
        entry_q.pack(side=tk.LEFT)
        ttk.Label(entry_frame, text="kW").pack(side=tk.LEFT, padx=(5, 0))
        
        # ===== ENTRÉE 2: Température évaporation =====
        frame_tevap = ttk.LabelFrame(main_container, text="Température Évaporation", padding=10)
        frame_tevap.pack(fill='x', pady=5)
        
        var_tevap = tk.DoubleVar(value=10.0)
        self.param_widgets['T_evap'] = var_tevap
        
        # Value display
        lbl_tevap_val = ttk.Label(frame_tevap, textvariable=var_tevap, font=('Arial', 20, 'bold'), foreground='cyan')
        lbl_tevap_val.pack()
        ttk.Label(frame_tevap, text="°C", font=('Arial', 10)).pack()
        
        # Slider
        slider_tevap = ttk.Scale(frame_tevap, from_=-5, to=20, variable=var_tevap, orient=tk.HORIZONTAL)
        slider_tevap.pack(fill='x', pady=5)
        
        # Entry
        entry_frame2 = ttk.Frame(frame_tevap)
        entry_frame2.pack()
        ttk.Label(entry_frame2, text="Valeur exacte:").pack(side=tk.LEFT, padx=(0, 5))
        entry_tevap = ttk.Entry(entry_frame2, textvariable=var_tevap, width=10)
        entry_tevap.pack(side=tk.LEFT)
        ttk.Label(entry_frame2, text="°C").pack(side=tk.LEFT, padx=(5, 0))
        
        # ===== BOUTON PRINCIPAL =====
        ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=15)
        
        btn_simulate = ttk.Button(
            main_container, 
            text="🚀 DIMENSIONNER / SIMULER", 
            command=self._run_simulation,
            style='Accent.TButton'
        )
        btn_simulate.pack(fill='x', pady=5)
        
        # ===== PARAMÈTRES AVANCÉS (REPLIABLE) =====
        ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=15)
        
        # Expander for advanced parameters
        self.advanced_visible = tk.BooleanVar(value=False)
        
        btn_advanced = ttk.Checkbutton(
            main_container,
            text="▼ Paramètres avancés",
            variable=self.advanced_visible,
            command=self._toggle_advanced_params
        )
        btn_advanced.pack(anchor='w')
        
        # Advanced frame (initially hidden)
        self.advanced_frame = ttk.Frame(main_container)
        
        # T_cond
        self._add_simple_param(self.advanced_frame, "T_cond", "T condenseur [°C]", 25, 50, 35)
        
        # T_gen
        self._add_simple_param(self.advanced_frame, "T_gen", "T générateur [°C]", 80, 160, 100)
        
        # Efficiencies
        ttk.Label(self.advanced_frame, text="Rendements:", font=('Arial', 9, 'bold')).pack(anchor='w', pady=(10,2))
        self._add_simple_param(self.advanced_frame, "eta_nozzle", "  η tuyère", 0.5, 1.0, 0.85, resolution=0.01)
        self._add_simple_param(self.advanced_frame, "eta_diffuser", "  η diffuseur", 0.5, 1.0, 0.85, resolution=0.01)
        self._add_simple_param(self.advanced_frame, "eta_mixing", "  η mélange", 0.8, 1.0, 1.0, resolution=0.01)
        
        # Model selection
        ttk.Label(self.advanced_frame, text="Modèle:", font=('Arial', 9, 'bold')).pack(anchor='w', pady=(10,2))
        self.var_use_v2 = tk.BooleanVar(value=True)
        chk_v2 = ttk.Checkbutton(
            self.advanced_frame, 
            text="☑ Utiliser Éjecteur V2 (compressible avec choc)",
            variable=self.var_use_v2
        )
        chk_v2.pack(anchor='w', padx=10, pady=2)
        
        # Reset button
        btn_reset = ttk.Button(self.advanced_frame, text="🔄 Réinitialiser", command=self._load_default_params)
        btn_reset.pack(anchor='w', padx=10, pady=10)
        
        # ===== EXPORT =====
        ttk.Separator(main_container, orient='horizontal').pack(fill='x', pady=10)
        btn_export = ttk.Button(main_container, text="💾 Exporter Résultats", command=self._export_results)
        btn_export.pack(fill='x', pady=2)
    
    def _toggle_advanced_params(self):
        """Toggle visibility of advanced parameters."""
        if self.advanced_visible.get():
            self.advanced_frame.pack(fill='x', pady=5)
        else:
            self.advanced_frame.pack_forget()
    
    def _add_simple_param(self, parent, key, label, min_val, max_val, default, resolution=1):
        """Add a compact parameter control."""
        frame = ttk.Frame(parent)
        frame.pack(fill='x', padx=5, pady=2)
        
        ttk.Label(frame, text=label, width=18, anchor='w').pack(side=tk.LEFT)
        
        var = tk.DoubleVar(value=default)
        self.param_widgets[key] = var
        
        entry = ttk.Entry(frame, textvariable=var, width=8)
        entry.pack(side=tk.RIGHT)
        
        slider = ttk.Scale(frame, from_=min_val, to=max_val, variable=var, orient=tk.HORIZONTAL, length=100)
        slider.pack(side=tk.RIGHT, padx=5)
    
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
        """Draw cycle schematic on canvas with thermodynamic state numbering."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 800
        h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 320
        
        # Component positions (relative)
        components = {
            'condenser': (0.75 * w, 0.20 * h),
            'pump': (0.15 * w, 0.50 * h),
            'generator': (0.15 * w, 0.80 * h),
            'ejector': (0.50 * w, 0.50 * h),
            'valve': (0.75 * w, 0.50 * h),
            'evaporator': (0.75 * w, 0.80 * h),
        }
        
        # Draw components as shapes
        box_w, box_h = 70, 40
        
        # Condenser (top right - gray)
        x, y = components['condenser']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, 
                                     fill='#e6e6e6', outline='black', width=2, tags='component')
        self.canvas.create_text(x, y-10, text="Condenseur", font=('Arial', 8, 'bold'))
        self.canvas.create_text(x, y+10, text="(8→1)", font=('Arial', 7), fill='gray')
        
        # Pump (left middle - green)
        x, y = components['pump']
        self.canvas.create_oval(x-25, y-25, x+25, y+25, fill='#ccffcc', outline='green', width=2, tags='component')
        self.canvas.create_text(x, y-5, text="Pompe", font=('Arial', 8, 'bold'))
        self.canvas.create_text(x, y+8, text="(1→2)", font=('Arial', 7), fill='darkgreen')
        
        # Generator (left bottom - red/hot)
        x, y = components['generator']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, 
                                     fill='#ffcccc', outline='red', width=2, tags='component')
        self.canvas.create_text(x, y-10, text="Générateur", font=('Arial', 8, 'bold'))
        self.canvas.create_text(x, y+10, text="(2→3)", font=('Arial', 7), fill='darkred')
        
        # Ejector (center - blue)
        x, y = components['ejector']
        # Draw ejector as convergent-divergent nozzle shape
        pts = [x-40, y-20, x-10, y, x-40, y+20, x+30, y+15, x+30, y-15]
        self.canvas.create_polygon(pts, fill='#cce5ff', outline='blue', width=2, tags='component')
        self.canvas.create_text(x, y-5, text="Éjecteur", font=('Arial', 8, 'bold'))
        self.canvas.create_text(x, y+10, text="(3,5→8)", font=('Arial', 7), fill='darkblue')
        
        # Expansion Valve (right middle - orange)
        x, y = components['valve']
        self.canvas.create_polygon(x-15, y-20, x+15, y-20, x+15, y, x-15, y+20, 
                                   fill='#ffe6cc', outline='orange', width=2, tags='component')
        self.canvas.create_text(x, y+28, text="Détendeur", font=('Arial', 7))
        self.canvas.create_text(x, y-28, text="(1→6)", font=('Arial', 7), fill='darkorange')
        
        # Evaporator (right bottom - cyan/cold)
        x, y = components['evaporator']
        self.canvas.create_rectangle(x-box_w/2, y-box_h/2, x+box_w/2, y+box_h/2, 
                                     fill='#ccffff', outline='cyan', width=2, tags='component')
        self.canvas.create_text(x, y-10, text="Évaporateur", font=('Arial', 8, 'bold'))
        self.canvas.create_text(x, y+10, text="(6→5)", font=('Arial', 7), fill='darkcyan')
        
        # ===== DRAW PIPES WITH STATE NUMBERS =====
        
        # Condenser → Pump (1)
        x1, y1 = components['condenser']
        x2, y2 = components['pump']
        mid_y = y1 + box_h/2
        # Vertical down from condenser
        self.canvas.create_line(x1, y1+box_h/2, x1, mid_y+30, fill='black', width=2, tags='pipe')
        # Horizontal to pump
        self.canvas.create_line(x1, mid_y+30, x2+25, mid_y+30, fill='black', width=2, tags='pipe')
        # Down to pump
        self.canvas.create_line(x2+25, mid_y+30, x2+25, y2, fill='black', width=2, arrow=tk.LAST, tags='pipe')
        # State label 1
        self.canvas.create_text(x1+15, mid_y+20, text="①", font=('Arial', 12, 'bold'), 
                               fill='white', tags='state_label')
        self.canvas.create_oval(x1+8, mid_y+13, x1+22, mid_y+27, fill='blue', outline='darkblue', width=2, tags='state_marker')
        self.canvas.create_text(x1+15, mid_y+20, text="①", font=('Arial', 12, 'bold'), 
                               fill='white', tags='state_label')
        
        # Pump → Generator (2)
        x1, y1 = components['pump']
        x2, y2 = components['generator']
        self.canvas.create_line(x1, y1+25, x1, y2-box_h/2, fill='green', width=2, arrow=tk.LAST, tags='pipe')
        # State label 2
        self.canvas.create_oval(x1-7, (y1+y2)/2-7, x1+7, (y1+y2)/2+7, fill='green', outline='darkgreen', width=2, tags='state_marker')
        self.canvas.create_text(x1, (y1+y2)/2, text="②", font=('Arial', 12, 'bold'), 
                               fill='white', tags='state_label')
        
        # Generator → Ejector primary (3)
        x1, y1 = components['generator']
        x2, y2 = components['ejector']
        # Horizontal from generator
        self.canvas.create_line(x1+box_w/2, y1, x2-40, y2, fill='red', width=3, arrow=tk.LAST, tags='pipe')
        # State label 3
        self.canvas.create_oval((x1+x2)/2-10-7, y1-7, (x1+x2)/2-10+7, y1+7, fill='red', outline='darkred', width=2, tags='state_marker')
        self.canvas.create_text((x1+x2)/2-10, y1, text="③", font=('Arial', 12, 'bold'), 
                               fill='white', tags='state_label')
        
        # Evaporator → Ejector secondary (5)
        x1, y1 = components['evaporator']
        x2, y2 = components['ejector']
        # Up from evaporator
        self.canvas.create_line(x1-box_w/2, y1, x2-40, y2+20, fill='cyan', width=3, arrow=tk.LAST, tags='pipe')
        # State label 5
        self.canvas.create_oval(x1-box_w/2-15-7, (y1+y2)/2+10-7, x1-box_w/2-15+7, (y1+y2)/2+10+7, 
                               fill='cyan', outline='darkcyan', width=2, tags='state_marker')
        self.canvas.create_text(x1-box_w/2-15, (y1+y2)/2+10, text="⑤", font=('Arial', 12, 'bold'), 
                               fill='black', tags='state_label')
        
        # Ejector → Condenser (8)
        x1, y1 = components['ejector']
        x2, y2 = components['condenser']
        self.canvas.create_line(x1+30, y1, x2-box_w/2, y2, fill='purple', width=3, arrow=tk.LAST, tags='pipe')
        # State label 8
        self.canvas.create_oval((x1+x2)/2-7, y1-7, (x1+x2)/2+7, y1+7, fill='purple', outline='indigo', width=2, tags='state_marker')
        self.canvas.create_text((x1+x2)/2, y1, text="⑧", font=('Arial', 12, 'bold'), 
                               fill='white', tags='state_label')
        
        # Condenser → Valve (1→6 branch)
        x1, y1 = components['condenser']
        x2, y2 = components['valve']
        self.canvas.create_line(x1, y1+box_h/2, x2, y2-20, fill='black', width=2, arrow=tk.LAST, tags='pipe')
        # State label 6
        self.canvas.create_oval(x2-7, y2-35-7, x2+7, y2-35+7, fill='orange', outline='darkorange', width=2, tags='state_marker')
        self.canvas.create_text(x2, y2-35, text="⑥", font=('Arial', 12, 'bold'), 
                               fill='white', tags='state_label')
        
        # Valve → Evaporator (6→5)
        x1, y1 = components['valve']
        x2, y2 = components['evaporator']
        self.canvas.create_line(x1, y1+20, x2, y2-box_h/2, fill='orange', width=2, arrow=tk.LAST, tags='pipe')
        
        # Add legend
        legend_x, legend_y = 10, h - 60
        self.canvas.create_text(legend_x, legend_y, text="États thermodynamiques:", 
                               font=('Arial', 8, 'bold'), anchor='w')
        self.canvas.create_text(legend_x, legend_y+15, 
                               text="① Sortie cond. | ② Sortie pompe | ③ Sortie gén.", 
                               font=('Arial', 7), anchor='w')
        self.canvas.create_text(legend_x, legend_y+30, 
                               text="⑤ Sortie évap. | ⑥ Après détente | ⑧ Sortie éjecteur", 
                               font=('Arial', 7), anchor='w')
    
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
        
        # ===== PLOT P-h DIAGRAM =====
        self.ax_ph.clear()
        self.ax_ph.set_xlabel('Enthalpie h [kJ/kg]', fontsize=11)
        self.ax_ph.set_ylabel('Pression P [kPa]', fontsize=11)
        self.ax_ph.set_title('Diagramme P-h - Cycle R718 à Éjecteur', fontsize=12, fontweight='bold')
        self.ax_ph.set_yscale('log')
        
        # Draw saturation dome (simplified)
        try:
            self._draw_saturation_dome_ph(self.ax_ph)
        except:
            pass  # Skip if saturation dome fails
        
        # Extract state properties
        def get_h(i):
            return states[i].h / 1000.0 if i in states and states[i].h is not None else None
        
        def get_P(i):
            return states[i].P / 1000.0 if i in states and states[i].P is not None else None
        
        # CYCLE MOTEUR (HP - rouge): 1 → 2 → 3 → 4
        if all(get_h(i) and get_P(i) for i in [1, 2, 3, 4]):
            h_hp = [get_h(i) for i in [1, 2, 3, 4]]
            P_hp = [get_P(i) for i in [1, 2, 3, 4]]
            self.ax_ph.plot(h_hp, P_hp, 'r-', linewidth=2.5, label='Cycle Moteur (HP)', zorder=3)
            self.ax_ph.plot(h_hp, P_hp, 'ro', markersize=8, zorder=4)
        
        # CYCLE FRIGORIFIQUE (BP - bleu): 1 → détente → 5 (et 6 identique à 5)
        if all(get_h(i) and get_P(i) for i in [1, 5]):
            # Détente isenthalpique: h constant
            h_lp = [get_h(1), get_h(1), get_h(5)]
            P_lp = [get_P(1), get_P(5), get_P(5)]
            self.ax_ph.plot(h_lp, P_lp, 'b-', linewidth=2.5, label='Cycle Frigorifique (BP)', zorder=3)
            self.ax_ph.plot([get_h(5)], [get_P(5)], 'bo', markersize=8, zorder=4)
        
        # ÉJECTEUR MÉLANGE (violet): 4 + 6 → 7 → 8
        if all(get_h(i) and get_P(i) for i in [4, 7, 8]):
            # Primaire 4 vers mélange 7
            self.ax_ph.plot([get_h(4), get_h(7)], [get_P(4), get_P(7)], 'm--', linewidth=2, alpha=0.7, zorder=2)
            # Secondaire 6 vers mélange 7 (6 identique à 5)
            if get_h(6) and get_P(6):
                self.ax_ph.plot([get_h(6), get_h(7)], [get_P(6), get_P(7)], 'm--', linewidth=2, alpha=0.7, zorder=2)
            # Diffuseur 7 → 8
            self.ax_ph.plot([get_h(7), get_h(8)], [get_P(7), get_P(8)], 'm-', linewidth=2.5, label='Éjecteur', zorder=3)
            self.ax_ph.plot([get_h(7), get_h(8)], [get_P(7), get_P(8)], 'mo', markersize=8, zorder=4)
        
        # CONDENSATION (vert): 8 → 1
        if all(get_h(i) and get_P(i) for i in [8, 1]):
            self.ax_ph.plot([get_h(8), get_h(1)], [get_P(8), get_P(1)], 'g-', linewidth=2.5, label='Condensation', zorder=3)
        
        # Add state labels
        labels = {
            1: '1-Cond.out', 2: '2-Pompe', 3: '3-Gén.', 4: '4-Ejec.P',
            5: '5-Evap.', 6: '6-Ejec.S', 7: '7-Mix', 8: '8-Diff.'
        }
        for i, label in labels.items():
            h, P = get_h(i), get_P(i)
            if h and P:
                self.ax_ph.annotate(label, (h, P), textcoords="offset points", 
                                   xytext=(8, 8), fontsize=9, color='black',
                                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                                   zorder=5)
        
        self.ax_ph.grid(True, alpha=0.3, which='both', linestyle='--')
        self.ax_ph.legend(loc='best', fontsize=9)
        self.canvas_ph.draw()
        
        # ===== PLOT T-s DIAGRAM =====
        self.ax_ts.clear()
        self.ax_ts.set_xlabel('Entropie s [kJ/kg/K]', fontsize=11)
        self.ax_ts.set_ylabel('Température T [K]', fontsize=11)
        self.ax_ts.set_title('Diagramme T-s - Cycle R718 à Éjecteur', fontsize=12, fontweight='bold')
        
        # Draw saturation dome
        try:
            self._draw_saturation_dome_ts(self.ax_ts)
        except:
            pass
        
        def get_s(i):
            return states[i].s / 1000.0 if i in states and states[i].s is not None else None
        
        def get_T(i):
            return states[i].T if i in states and states[i].T is not None else None
        
        # CYCLE MOTEUR (HP - rouge): 1 → 2 → 3 → 4
        if all(get_s(i) and get_T(i) for i in [1, 2, 3, 4]):
            s_hp = [get_s(i) for i in [1, 2, 3, 4]]
            T_hp = [get_T(i) for i in [1, 2, 3, 4]]
            self.ax_ts.plot(s_hp, T_hp, 'r-', linewidth=2.5, label='Cycle Moteur (HP)', zorder=3)
            self.ax_ts.plot(s_hp, T_hp, 'ro', markersize=8, zorder=4)
        
        # CYCLE FRIGORIFIQUE (BP - bleu): 1 → détente → 5
        if all(get_s(i) and get_T(i) for i in [1, 5]):
            # Détente isenthalpique: augmentation entropie
            s_lp = [get_s(1), get_s(1), get_s(5)]
            T_lp = [get_T(1), get_T(5), get_T(5)]
            self.ax_ts.plot(s_lp, T_lp, 'b-', linewidth=2.5, label='Cycle Frigorifique (BP)', zorder=3)
            self.ax_ts.plot([get_s(5)], [get_T(5)], 'bo', markersize=8, zorder=4)
        
        # ÉJECTEUR (violet): 4 + 6 → 7 → 8
        if all(get_s(i) and get_T(i) for i in [4, 7, 8]):
            # Primaire 4 vers mélange 7
            self.ax_ts.plot([get_s(4), get_s(7)], [get_T(4), get_T(7)], 'm--', linewidth=2, alpha=0.7, zorder=2)
            # Secondaire 6 vers mélange 7
            if get_s(6) and get_T(6):
                self.ax_ts.plot([get_s(6), get_s(7)], [get_T(6), get_T(7)], 'm--', linewidth=2, alpha=0.7, zorder=2)
            # Diffuseur 7 → 8
            self.ax_ts.plot([get_s(7), get_s(8)], [get_T(7), get_T(8)], 'm-', linewidth=2.5, label='Éjecteur', zorder=3)
            self.ax_ts.plot([get_s(7), get_s(8)], [get_T(7), get_T(8)], 'mo', markersize=8, zorder=4)
        
        # CONDENSATION (vert): 8 → 1
        if all(get_s(i) and get_T(i) for i in [8, 1]):
            self.ax_ts.plot([get_s(8), get_s(1)], [get_T(8), get_T(1)], 'g-', linewidth=2.5, label='Condensation', zorder=3)
        
        # Add state labels
        for i, label in labels.items():
            s, T = get_s(i), get_T(i)
            if s and T:
                self.ax_ts.annotate(label, (s, T), textcoords="offset points", 
                                   xytext=(8, 8), fontsize=9, color='black',
                                   bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
                                   zorder=5)
        
        self.ax_ts.grid(True, alpha=0.3, linestyle='--')
        self.ax_ts.legend(loc='best', fontsize=9)
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
