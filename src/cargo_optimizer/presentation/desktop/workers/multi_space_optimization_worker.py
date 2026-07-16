"""`MultiSpaceOptimizationWorker`: ejecuta `MultiSpaceAssignmentEngine` en un `QThread`.

Mismo patrón que `OptimizationWorker` (ver ese módulo): un `QThread`
dedicado por ejecución, cancelación cooperativa vía `CancellationToken`,
señales que pasan objetos de dominio/aplicación tal cual
(`MultiSpaceProgress`, `MultiSpaceAssignmentResult`) para que Qt las
entregue al hilo de la GUI mediante una conexión en cola automática.
No se introduce un segundo sistema de threading: es el mismo patrón,
aplicado al caso de uso multi-espacio de `application`.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from cargo_optimizer.application.models import MultiSpaceAssignmentRequest
from cargo_optimizer.application.multi_space_assignment import MultiSpaceAssignmentEngine
from cargo_optimizer.optimization.cancellation import CancellationToken


class MultiSpaceOptimizationWorker(QThread):
    """Ejecuta una única `MultiSpaceAssignmentRequest` en un hilo secundario."""

    progress = Signal(object)  # MultiSpaceProgress
    optimization_finished = Signal(object)  # MultiSpaceAssignmentResult
    optimization_failed = Signal(str)

    def __init__(self, request: MultiSpaceAssignmentRequest, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._request = request
        self.cancellation_token = CancellationToken()

    def run(self) -> None:
        engine = MultiSpaceAssignmentEngine()
        try:
            result = engine.assign(
                self._request,
                cancellation_token=self.cancellation_token,
                progress_callback=self.progress.emit,
            )
        except Exception as exc:  # todo error debe llegar a la UI (QMessageBox), nunca perderse
            self.optimization_failed.emit(str(exc))
            return
        self.optimization_finished.emit(result)
