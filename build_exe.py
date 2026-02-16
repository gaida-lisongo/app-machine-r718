"""
Script de build pour générer l'exécutable Windows de app_r718.

Usage:
    python build_exe.py
"""

import os
import sys
import shutil
import subprocess

def main():
    print("=" * 60)
    print("BUILD APP_R718 - Génération de l'exécutable Windows")
    print("=" * 60)
    
    # Vérifier que pyinstaller est installé
    try:
        import PyInstaller
        print(f"✓ PyInstaller version {PyInstaller.__version__} détecté")
    except ImportError:
        print("⚠ PyInstaller n'est pas installé.")
        print("Installation en cours...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installé")
    
    # Nettoyer les anciens builds
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Nettoyage: {d}/")
            shutil.rmtree(d)
    
    # Supprimer l'ancien .spec si présent
    spec_file = "app_r718.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Suppression: {spec_file}")
    
    print("\n" + "=" * 60)
    print("Génération de l'exécutable...")
    print("=" * 60 + "\n")
    
    # Commande PyInstaller
    cmd = [
        "pyinstaller",
        "--name=App_R718_v1.0",
        "--onefile",                    # Un seul fichier .exe
        "--windowed",                   # Pas de console (interface graphique)
        "--icon=NONE",                  # Pas d'icône personnalisée (à ajouter si vous avez un .ico)
        "--clean",                      # Nettoyer les fichiers temporaires
        "--noconfirm",                  # Pas de confirmation
        # Hidden imports pour les modules qui pourraient ne pas être détectés
        "--hidden-import=CoolProp",
        "--hidden-import=matplotlib",
        "--hidden-import=numpy",
        "--hidden-import=tkinter",
        "--hidden-import=app_r718.core",
        "--hidden-import=app_r718.modules",
        # Point d'entrée
        "main.py"
    ]
    
    print(f"Commande: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("✓ BUILD RÉUSSI!")
        print("=" * 60)
        print(f"\nFichier exécutable généré: dist/App_R718_v1.0.exe")
        print(f"Taille: {os.path.getsize('dist/App_R718_v1.0.exe') / (1024*1024):.1f} MB")
        print("\nVous pouvez maintenant distribuer ce fichier .exe")
        print("Il fonctionne sans installation Python sur d'autres PC Windows.")
    else:
        print("\n⚠ ERREUR lors du build")
        print(f"Code de sortie: {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
