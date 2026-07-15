"""Ejecución del motor de optimización fuera del hilo de interfaz.

`OptimizationWorker` es el único punto de `presentation/desktop` que
invoca `cargo_optimizer.optimization.PackingEngine`. Nunca ejecuta el
motor en el hilo principal de Qt: bloquearía la interfaz durante toda
la duración de la optimización (segundos a minutos, ver
`docs/OptimizerPerformance.md`).
"""
