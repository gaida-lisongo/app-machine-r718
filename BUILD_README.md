# Guide de Build - App R718

## Génération du fichier .exe

### Méthode Automatique (Recommandée)

```bash
python build_exe.py
```

Le script va :

1. Installer PyInstaller si nécessaire
2. Nettoyer les anciens builds
3. Générer `dist/App_R718_v1.0.exe`

### Méthode Manuelle

#### 1. Installer PyInstaller

```bash
pip install pyinstaller
```

#### 2. Générer l'exécutable

**Option A - Un seul fichier .exe (recommandé):**

```bash
pyinstaller --name=App_R718_v1.0 ^
            --onefile ^
            --windowed ^
            --clean ^
            --hidden-import=CoolProp ^
            --hidden-import=matplotlib ^
            --hidden-import=numpy ^
            main.py
```

**Option B - Dossier avec .exe + dépendances:**

```bash
pyinstaller --name=App_R718_v1.0 ^
            --windowed ^
            --clean ^
            --hidden-import=CoolProp ^
            --hidden-import=matplotlib ^
            main.py
```

#### 3. Tester l'exécutable

```bash
dist\App_R718_v1.0.exe
```

## Options PyInstaller

| Option                   | Description                                                      |
| ------------------------ | ---------------------------------------------------------------- |
| `--onefile`              | Un seul fichier .exe (plus lent au démarrage mais plus pratique) |
| `--windowed`             | Pas de console noire (pour interfaces graphiques)                |
| `--console`              | Affiche la console (utile pour debug)                            |
| `--icon=icon.ico`        | Ajouter une icône personnalisée                                  |
| `--clean`                | Nettoyer les fichiers temporaires                                |
| `--hidden-import=module` | Forcer l'inclusion d'un module                                   |

## Ajout d'une icône personnalisée

1. Créer ou télécharger un fichier `icon.ico` (format Windows)
2. Placer le fichier à la racine du projet
3. Modifier la commande :

```bash
pyinstaller --name=App_R718_v1.0 ^
            --onefile ^
            --windowed ^
            --icon=icon.ico ^
            main.py
```

## Fichiers générés

```
app_r718/
├── build/              # Fichiers temporaires (peut être supprimé)
├── dist/               # Exécutable final
│   └── App_R718_v1.0.exe
└── App_R718_v1.0.spec  # Configuration PyInstaller (peut être réutilisé)
```

## Taille du fichier

- **Mode --onefile** : ~80-150 MB (incluant Python, CoolProp, Matplotlib, etc.)
- **Mode --onedir** : ~200-300 MB répartis dans un dossier

## Réduire la taille (optionnel)

### Utiliser UPX (compresseur)

```bash
# Installer UPX (https://upx.github.io/)
# Puis :
pyinstaller --onefile --windowed --upx-dir=C:\chemin\vers\upx main.py
```

### Exclure des modules non utilisés

```bash
pyinstaller --onefile ^
            --windowed ^
            --exclude-module=PIL ^
            --exclude-module=scipy ^
            main.py
```

## Problèmes courants

### 1. "Module not found" à l'exécution

**Solution:** Ajouter `--hidden-import=nom_module`

```bash
pyinstaller --onefile --hidden-import=CoolProp main.py
```

### 2. L'exe est trop lent au démarrage

**Solution:** Utiliser `--onedir` au lieu de `--onefile`

### 3. Antivirus bloque l'exécutable

**Solution:**

- Signer le .exe avec un certificat
- Ajouter une exception dans l'antivirus
- Exclure `--onefile` lors du build

## Distribution

Pour distribuer l'application :

1. **Mode --onefile** : Distribuer uniquement `dist/App_R718_v1.0.exe`
2. **Mode --onedir** : Compresser tout le dossier `dist/` en ZIP

## Signature de code (optionnel)

Pour éviter les alertes Windows SmartScreen :

1. Obtenir un certificat de signature de code
2. Signer l'exécutable avec `signtool.exe`

```bash
signtool sign /f certificat.pfx /p mot_de_passe dist/App_R718_v1.0.exe
```

## Remarques

- Le premier lancement peut être lent (extraction en mémoire)
- L'exe fonctionne sans installation Python
- Compatible Windows 7, 8, 10, 11
- Taille finale dépend des bibliothèques incluses
