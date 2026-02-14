# CONTEXT – Master Research Project
## Numerical Modeling of a 12 kW Water (R718) Solar Ejector Refrigeration System

---

# 1. PROJECT OVERVIEW

This project implements a numerical simulation of a 12 kW solar-driven ejector refrigeration machine using water (R718) as refrigerant.

The objective is to:

- Develop a modular object-oriented simulation tool in Python
- Implement each physical component as an independent MVC module
- Validate each module with unit tests
- Couple all modules into a global refrigeration system
- Compute system performance (COP, mass flow rates, pressures)
- Enable future extensions (exergy, optimization)

The simulation must be scientifically consistent with thermodynamic laws and compressible flow theory.

---

# 2. THERMODYNAMIC SPECIFICATIONS

## Working Fluid:
- Water (R718)
- Properties must be obtained using CoolProp

## Nominal Conditions:
- Cooling capacity: 12 kW
- Generator temperature: 100 °C
- Condenser temperature: 35 °C
- Evaporator temperature: 10 °C
- Ambient pressure: 1.013 bar

## Assumptions:
- Steady state
- 1D models
- Adiabatic ejector
- Isenthalpic expansion valve
- No heat losses outside exchangers
- Real fluid properties (CoolProp mandatory)

---

# 3. NOTATION CONVENTIONS (MANDATORY)

Velocity must be written as:
    c

Global heat transfer coefficient:
    K

Mass flow rates:
    m_dot_pri  (primary)
    m_dot_sec  (secondary)

Enthalpy:
    h

Entropy:
    s

Pressure:
    P

Temperature:
    T

Quality:
    x

---

# 4. SOFTWARE ARCHITECTURE (MANDATORY)

The project MUST follow MVC architecture and OOP principles.

Each physical component must be implemented as:

    ComponentModule/
        model.py
        controller.py
        view.py

Modules:

1. PumpModule
2. GeneratorModule
3. EjectorModule
4. CondenserModule
5. ExpansionValveModule
6. EvaporatorModule
7. SystemModule (global coupling)

Each module must:

- Be testable independently
- Not depend directly on other modules
- Communicate only via ThermoState objects

---

# 5. CORE CLASS – ThermoState

All modules must exchange thermodynamic states using a unified class:

Attributes:
- P
- T
- h
- s
- x
- rho

Properties must be updated via CoolProp.

No module should manually approximate thermodynamic properties.

---

# 6. PHYSICAL MODEL REQUIREMENTS PER MODULE

## Pump:
- Isentropic efficiency model
- NPSH calculation
- Cavitation warning

## Generator:
- Direct heating of working fluid
- Solar input Gb
- Optical efficiency
- Thermal losses (convective + radiative)

## Expansion Valve:
- Isenthalpic process
- Optional orifice mass flow model

## Evaporator:
- Film evaporation
- Energy balance:
    Q_evap = m_dot_sec (h3 - h2)
- Optional heat exchanger model:
    Q = K A ΔT_lm

## Condenser:
- Film condensation (Nusselt correlation)
- Natural convection on air side
- Global heat transfer:
    1/K = 1/h_cond + wall + 1/h_air

## Ejector:
- 1D compressible flow
- Nozzle efficiency
- Mixing section (mass + momentum + energy)
- Normal shock (Rankine-Hugoniot relations)
- Diffuser efficiency
- Entrainment ratio:
    mu = m_dot_sec / m_dot_pri
- Must detect critical and subcritical regimes

---

# 7. NUMERICAL STRATEGY

Development must proceed in stages:

Stage 1:
- Fix condenser and evaporator pressures from saturation temperatures

Stage 2:
- Introduce heat exchanger coupling

Stage 3:
- Activate full ejector shock model

Global convergence criteria:
- Residual < 1e-6
- Physical consistency (P>0, 0<=x<=1 if two-phase)

---

# 8. SYSTEM COUPLING STRATEGY

Global system must:

1. Initialize P_cond and P_evap
2. Solve Pump
3. Solve Generator
4. Solve Valve
5. Solve Evaporator
6. Solve Ejector
7. Solve Condenser
8. Iterate until convergence

COP definition:

    COP = Q_evap / Q_gen

Where:

    Q_evap = m_dot_sec (h3 - h2)
    Q_gen  = m_dot_pri (h5 - h4)

---

# 9. SCIENTIFIC PRIORITIES

- Physical consistency is more important than code simplicity
- Avoid hidden approximations
- Explicitly compute all balances
- Log convergence steps
- Provide diagnostic flags in each module

---

# 10. FUTURE EXTENSION

Architecture must allow future addition of:

- Exergy analysis
- Parametric study
- Optimization routines
- Sensitivity analysis

---

END OF CONTEXT
