# ADR-0001: Arquitectura en capas (domain / application / infrastructure / presentation)

## Estado

Aceptada — 2026-07-14

## Contexto

La infraestructura inicial del proyecto (fase 1) agrupaba toda la
lógica de negocio futura en un único paquete, `core`, frente a `ui`
(presentación). Esto era suficiente para un "Hola Mundo", pero el
proyecto va a incorporar en fases sucesivas un motor geométrico, un
motor de restricciones, un motor de optimización, persistencia
(SQLite), exportación (Excel, PDF) y visualización 3D (VTK). Sin una
separación más fina, todo ese código caería dentro de `core` sin
ningún límite estructural, y el acoplamiento entre reglas de negocio,
orquestación de casos de uso y detalles técnicos (bases de datos,
formatos de fichero, bibliotecas gráficas) se volvería cada vez más
caro de deshacer.

El objetivo del producto es que el mismo motor pueda exponerse como
aplicación de escritorio, API REST, SDK embebido en un ERP, servicio o
aplicación web, sin reescribirse.

## Decisión

Se adopta una arquitectura por capas inspirada en Clean
Architecture / Arquitectura Hexagonal, con una regla de dependencia
estricta: las capas externas dependen de las internas, nunca al
revés.

```
presentation  →  infrastructure  →  application  →  domain
  (externa)                                        (interna)
```

- **`domain`**: entidades y reglas de negocio puras (`LoadingSpace`,
  `LoadUnit`, invariantes). No depende de nada.
- **`application`**: casos de uso y orquestación. Define los puertos
  (interfaces) que `infrastructure` implementará. Depende solo de
  `domain`.
- **`infrastructure`**: adaptadores concretos (SQLAlchemy, openpyxl,
  ReportLab, VTK) que implementan los puertos de `application`.
  Depende de `application` y `domain`.
- **`presentation`**: mecanismos de entrega (aplicación de escritorio
  PySide6 hoy, API REST y web en el futuro). Depende de `application`.

`core` y `ui` se renombran a `domain` y `presentation` respectivamente;
`application` e `infrastructure` se crean vacíos, con la responsabilidad
documentada, a la espera de las fases correspondientes.

Explícitamente **no** se crean todavía `geometry`, `rules` ni
`optimization` como paquetes propios: su diseño depende de decisiones
que aún no se han tomado (fases 2, 3 y 4). Ver ADR futuro cuando se
diseñe cada motor, y `docs/Roadmap.md` para la regla de cuándo se
crean.

## Consecuencias

**Beneficios:**
- El motor de negocio (`domain` + `application`) puede consumirse desde
  cualquier mecanismo de entrega sin cambios.
- Los adaptadores de infraestructura son sustituibles (p. ej. cambiar
  de SQLite a otro motor) sin tocar `domain` ni `application`.
- La regla de dependencia es verificable automáticamente (ver
  ADR-0004), no solo una convención documentada.

**Costes / riesgos aceptados:**
- Más paquetes que gestionar desde el principio, aunque la mayoría
  estén vacíos hasta sus fases correspondientes.
- Exige disciplina: cualquier importación que viole la dirección de
  dependencia debe rechazarse en revisión, no solo detectarse por la
  herramienta.
