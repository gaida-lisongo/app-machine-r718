# Interface Utilisateur R718 - Guide de Lancement

## 🚀 Lancement de l'application

### Méthode 1 : Via le module Python

```bash
python -m app_r718
```

### Méthode 2 : Via main.py

```bash
python main.py
```

## 📋 Prérequis

Assurez-vous que toutes les dépendances sont installées :

```bash
pip install -r requirements.txt
```

Les packages nécessaires incluent :

- CoolProp (calculs thermodynamiques)
- numpy, scipy (calculs numériques)
- matplotlib (graphiques)
- tkinter (interface graphique, inclus avec Python)

## 🖥️ Utilisation

### Fenêtre principale

Au lancement, vous verrez la fenêtre principale avec les modules disponibles :

- ✅ **Détendeur** (Expansion Valve) - Disponible
- ⏳ Évaporateur, Condenseur, Pompe, Générateur, Éjecteur - À venir

### Module Détendeur

1. **Cliquez sur "Détendeur"** pour ouvrir la fenêtre de simulation

2. **Saisissez les paramètres d'entrée :**
   - Pression entrée P_in [Pa] (défaut: 1 MPa = 10 bar)
   - Température entrée T_in [K] (défaut: 308.15 K = 35°C)
   - Pression sortie P_out [Pa] (défaut: 1227 Pa ≈ 10°C saturation)

3. **Modèle d'orifice (optionnel) :**
   - Cochez "Activer calcul débit orifice"
   - Coefficient de décharge Cd (défaut: 0.8)
   - Aire orifice A [m²] (défaut: 1e-6)

4. **Cliquez sur "▶ Simuler"**

5. **Visualisation des résultats :**
   - **Panneau gauche** : Paramètres d'entrée
   - **Panneau droit** : Résultats détaillés (états 1 et 2, diagnostics)
   - **Panneau bas** : Diagramme P-h montrant la transformation isoenthalpique

### Interprétation du diagramme P-h

- **Point rouge (1)** : État d'entrée
- **Point bleu (2)** : État de sortie
- **Ligne verte** : Processus de détente (1→2)
- **Échelle log** : Axe des pressions pour meilleure lisibilité

## 🧪 Tests (Console uniquement)

L'interface utilisateur n'interfère pas avec les tests unitaires :

```bash
# Tester le module détendeur
pytest test/test_expansion_valve.py -v

# Tester tous les modules
pytest test/ -v

# Avec rapport HTML
pytest test/ -v --html=reports/report.html
```

Les tests s'exécutent **sans ouvrir d'interface graphique**.

## 📁 Structure ajoutée

```
src/app_r718/
├── ui/
│   ├── __init__.py          # Package UI
│   └── app.py               # Fenêtre principale
└── __main__.py              # Point d'entrée module

main.py                       # Point d'entrée racine

src/app_r718/modules/expansion_valve/
└── view.py                   # Vue console + ExpansionValveTkView (Tkinter)
```

## ⚠️ Dépannage

### Erreur "No module named 'tkinter'"

Tkinter est normalement inclus avec Python. Si manquant :

- **Ubuntu/Debian** : `sudo apt-get install python3-tk`
- **Fedora** : `sudo dnf install python3-tkinter`
- **Windows/Mac** : Réinstaller Python avec l'option Tcl/Tk

### Matplotlib backend error

Si erreur de backend Matplotlib, vérifiez que TkAgg est disponible :

```python
import matplotlib
print(matplotlib.get_backend())
```

## 📊 Exemple de simulation

**Conditions nominales** (condenseur 35°C → évaporateur 10°C) :

- P_in = 5628 Pa (35°C saturation R718)
- T_in = 308.15 K
- P_out = 1227 Pa (10°C saturation R718)

**Résultat attendu** :

- Transformation isoenthalpique : h₂ = h₁
- État de sortie : mélange diphasique (x₂ ≈ 0.15-0.25)
- Flag `two_phase_outlet` = True

---

**Documentation projet** : Voir [context.md](context.md) pour détails thermodynamiques
