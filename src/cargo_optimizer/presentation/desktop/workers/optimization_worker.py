"""`OptimizationWorker`: ejecuta `PackingEngine.optimize` en un `QThread`.

Un `QThread` por ejecución (no un `QThreadPool` compartido): cada
optimización es una operación larga y única, con su propio
`CancellationToken` — no hay nada que ganar reutilizando hilos aquí, y
un `QThread` dedicado hace trivial esperar su finalización limpia al
cancelar o al cerrar la ventana (`QThread.wait`).

Todas las señales pasan objetos de dominio (`PackingProgress`,
`PackingResult`) tal cual, vía `Signal(object)`: Qt las entrega al hilo
de la GUI mediante una conexión en cola automática porque el emisor
(este hilo) y el receptor (`MainWindow`, en el hilo principal)
pertenecen a hilos distintos. Ningún método de este worker toca un
widget directamente — esa es la única prohibición estricta al escribir
código que se ejecuta en `run()`.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from cargo_optimizer.domain.packing_result import PackingResult
from cargo_optimizer.optimization.cancellation import CancellationToken
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest


class OptimizationWorker(QThread):
    """Ejecuta una única `PackingRequest` en un hilo secundario."""

    progress = Signal(object)  # PackingProgress
    optimization_finished = Signal(object)  # PackingResult
    optimization_failed = Signal(str)

    def __init__(self, request: PackingRequest, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._request = request
        self.cancellation_token = CancellationToken()

    def run(self) -> None:
        engine = PackingEngine()
        try:
            result: PackingResult = engine.optimize(
                self._request,
                cancellation_token=self.cancellation_token,
                progress_callback=self.progress.emit,
            )
        except Exception as exc:  # todo error debe llegar a la UI (QMessageBox), nunca perderse
            self.optimization_failed.emit(str(exc))
            return
        self.optimization_finished.emit(result)
