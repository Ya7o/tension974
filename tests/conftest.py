"""Rend le package importable depuis les tests sans installation.

Remplace les sys.path.insert répétés dans chaque fichier de test.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
