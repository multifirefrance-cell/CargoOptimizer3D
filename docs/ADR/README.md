# Architecture Decision Records

Registro de decisiones de arquitectura significativas de
CargoOptimizer3D, en el formato estándar de ADR (contexto, decisión,
consecuencias). No se reescriben ni se eliminan cuando una decisión
cambia: se marcan como `Reemplazada por ADR-XXXX` y se añade una nueva.

| ADR | Título | Estado |
|---|---|---|
| [ADR-0001](ADR-0001-arquitectura-en-capas.md) | Arquitectura en capas (domain / application / infrastructure / presentation) | Aceptada |
| [ADR-0002](ADR-0002-vocabulario-loading-space-load-unit.md) | Vocabulario de dominio: Loading Space y Load Unit | Aceptada |
| [ADR-0003](ADR-0003-nucleo-como-sdk-independiente.md) | El núcleo (domain + application) es un SDK sin dependencia de UI | Aceptada |
| [ADR-0004](ADR-0004-enforcement-de-capas-con-import-linter.md) | Verificación automática de la regla de dependencia con import-linter | Aceptada |
| [ADR-0005](ADR-0005-inmutabilidad-y-enums-estables.md) | Dataclasses inmutables y enums con valores string estables en el dominio | Aceptada |
| [ADR-0006](ADR-0006-motor-geometrico-tolerancia-y-contacto.md) | Motor geométrico separado del dominio, tolerancia y semántica de contacto | Aceptada |
| [ADR-0007](ADR-0007-motor-de-reglas.md) | Motor de reglas separado del dominio y del optimizador, reglas de extintores, política de acumulación de violaciones | Aceptada |
| [ADR-0008](ADR-0008-arquitectura-del-motor-de-optimizacion.md) | Arquitectura del motor de optimización: paquete separado, `PackingStrategy` como Protocol, determinismo | Aceptada |
| [ADR-0009](ADR-0009-estrategia-greedy-y-separacion-objetivos.md) | Extreme-point greedy como primera estrategia; separación entre restricciones duras y objetivos | Aceptada |
