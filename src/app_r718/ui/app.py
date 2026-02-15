"""
Main Application Window - R718 Ejector Refrigeration System Simulator

Provides the main window with buttons to access different module simulations.

Author: R718 Ejector Refrigeration Project
Date: 2026-02-15
"""

import tkinter as tk
from tkinter import ttk


class MainWindow:
    """
    Main application window for R718 refrigeration system simulator.
    
    Provides access to individual module simulations through buttons.
    """
    
    def __init__(self):
        """Initialize the main application window."""
        self.root = tk.Tk()
        self.root.title("Simulateur R718 – Machine à éjecteur")
        self.root.geometry("600x400")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface components."""
        # Header
        header = ttk.Label(
            self.root,
            text="Simulateur de Machine Frigorifique à Éjecteur R718",
            font=("Arial", 16, "bold"),
        )
        header.pack(pady=20)
        
        # Description
        desc = ttk.Label(
            self.root,
            text="Système solaire de 12 kW utilisant l'eau (R718) comme fluide frigorigène",
            font=("Arial", 10),
        )
        desc.pack(pady=10)
        
        # Separator
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", pady=20)
        
        # Module buttons frame
        modules_frame = ttk.LabelFrame(
            self.root,
            text="Modules de Simulation",
            padding=20,
        )
        modules_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        # Create buttons for each module
        self._create_module_buttons(modules_frame)
        
        # Footer
        footer = ttk.Label(
            self.root,
            text="R718 Ejector Refrigeration Project - 2026",
            font=("Arial", 8),
            foreground="gray",
        )
        footer.pack(side="bottom", pady=10)
    
    def _create_module_buttons(self, parent):
        """
        Create buttons for each simulation module.
        
        Args:
            parent: Parent frame widget
        """
        button_style = {"width": 25, "padding": 10}
        
        # Expansion Valve (available)
        btn_expansion = ttk.Button(
            parent,
            text="🌡️ Détendeur (Expansion Valve)",
            command=self._open_expansion_valve,
            **button_style,
        )
        btn_expansion.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        # Evaporator (available)
        btn_evaporator = ttk.Button(
            parent,
            text="❄️ Évaporateur (Evaporator)",
            command=self._open_evaporator,
            **button_style,
        )
        btn_evaporator.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # Condenser (available)
        btn_condenser = ttk.Button(
            parent,
            text="♨️ Condenseur (Condenser)",
            command=self._open_condenser,
            **button_style,
        )
        btn_condenser.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # Pump (available)
        btn_pump = ttk.Button(
            parent,
            text="⚙️ Pompe (Pump)",
            command=self._open_pump,
            **button_style,
        )
        btn_pump.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        # Generator (available)
        btn_generator = ttk.Button(
            parent,
            text="🔥 Générateur (Generator)",
            command=self._open_generator,
            **button_style,
        )
        btn_generator.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        # Ejector (available)
        btn_ejector = ttk.Button(
            parent,
            text="🚀 Éjecteur (Ejector)",
            command=self._open_ejector,
            **button_style,
        )
        btn_ejector.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        
        # System Dashboard (available)
        btn_system = ttk.Button(
            parent,
            text="🔄 Système Complet (Dashboard)",
            command=self._open_system_dashboard,
            **button_style,
        )
        btn_system.grid(row=6, column=0, padx=10, pady=5, sticky="ew")
        
        # Configure grid
        parent.columnconfigure(0, weight=1)
    
    def _open_expansion_valve(self):
        """Open the Expansion Valve simulation window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.expansion_valve.view import ExpansionValveTkView
        
        ExpansionValveTkView.open_window(self.root)
    
    def _open_evaporator(self):
        """Open the Evaporator simulation window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.evaporator.view import EvaporatorTkView
        
        EvaporatorTkView.open_window(self.root)
    
    def _open_condenser(self):
        """Open the Condenser simulation window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.condenser.view import CondenserTkView
        
        CondenserTkView.open_window(self.root)
    
    def _open_pump(self):
        """Open the Pump simulation window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.pump.view import PumpTkView
        
        PumpTkView.open_window(self.root)
    
    def _open_generator(self):
        """Open the Generator simulation window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.generator.view import GeneratorTkView
        
        GeneratorTkView.open_window(self.root)
    
    def _open_ejector(self):
        """Open the Ejector simulation window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.ejector.view import EjectorTkView
        
        EjectorTkView.open_window(self.root)
    
    def _open_system_dashboard(self):
        """Open the System Dashboard window."""
        # Import here to avoid circular dependencies and allow headless testing
        from app_r718.modules.system_dashboard.view import open_system_dashboard
        
        open_system_dashboard(self.root)
    
    def run(self):
        """Start the application main loop."""
        self.root.mainloop()


def main():
    """Entry point for the UI application."""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
