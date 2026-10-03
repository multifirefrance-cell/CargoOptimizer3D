"""Lanzador de la versión web de CargoOptimizer3D.

Uso:
    python run_web.py          # puerto 8080 por defecto
    python run_web.py 9090     # puerto personalizado
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegura que el paquete sea importable desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cargo_optimizer.presentation.web.app import run

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f"\n  CargoOptimizer3D Web  →  http://localhost:{port}\n")
    run(port=port)
