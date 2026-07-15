"""Token de cancelación cooperativa, independiente de cualquier framework de UI."""

from __future__ import annotations

import threading


class CancellationToken:
    """Señal de cancelación segura entre hilos, basada en `threading.Event` (biblioteca estándar).

    Un hilo (p. ej. la UI) llama a `cancel()`; el motor, ejecutándose en
    otro hilo (p. ej. un `QThread` futuro), consulta `is_cancelled()`
    periódicamente. No corrompe `PackingState`: al detectarse la
    cancelación, el bucle de la estrategia simplemente deja de procesar
    instancias nuevas y marca las restantes como `UnpackedUnit`; nunca
    interrumpe una mutación de estado a mitad de camino. `optimization`
    no importa PySide6 ni ningún framework de UI: quien quiera cancelar
    desde Qt conecta una señal a `token.cancel()` desde fuera de este
    paquete.
    """

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()
