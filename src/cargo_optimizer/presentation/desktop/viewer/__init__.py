"""Visor 3D de `presentation/desktop` (fase 6.1).

Representa un `PackingResult` ya calculado — nunca ejecuta
`PackingEngine`, `PackingRequest` ni `RulesEngine` (ver ADR-0011,
`docs/ThreeDViewerDesign.md`). Depende de `cargo_optimizer.domain` (por
debajo de `presentation` en la regla de dependencia) y de terceros
(`pyvista`, `pyvistaqt`), nunca de `cargo_optimizer.optimization`.
"""
