"""Ventana principal de la aplicación."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from cargo_optimizer import __version__


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(f"CargoOptimizer3D v{__version__}")
        self.resize(800, 600)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        label = QLabel("CargoOptimizer3D — infraestructura base operativa.")
        layout.addWidget(label)
        self.setCentralWidget(central)
