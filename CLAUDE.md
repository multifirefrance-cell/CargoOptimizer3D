# CLAUDE.md — Instrucciones permanentes para CargoOptimizer3D

Este archivo contiene las reglas que rigen el proyecto en todas las
sesiones futuras. No son sugerencias: son restricciones de arquitectura
y de producto que deben respetarse salvo decisión explícita en
contrario del arquitecto del proyecto.

## Qué es este software

CargoOptimizer3D es un producto **comercial**, no un prototipo. Se
diseña para mantenerse durante al menos diez años. Prioriza siempre
arquitectura sobre velocidad de entrega. No se acepta una solución
inferior solo por ser más rápida de escribir.

## Vocabulario de dominio (obligatorio)

El sistema es universal, no está orientado a contenedores marítimos
específicamente.

- **Loading Space**: cualquier espacio de carga (contenedor marítimo,
  camión, furgón, van, semirremolque, bodega, plataforma, vagón,
  avión o espacio definido por el usuario). Nunca usar "contenedor"
  como concepto genérico en el código, la API o el dominio.
- **Load Unit**: cualquier unidad a cargar (caja, pallet, cilindro,
  tambor, bobina, tubo, maquinaria, carga irregular, grupo de cajas).
  Nunca usar "producto" como concepto genérico en el código, la API o
  el dominio.

Esta terminología se aplica a nombres de clases, módulos, tablas de
base de datos, endpoints de API y textos de interfaz.

## Regla de arquitectura no negociable

**La interfaz no contiene lógica.** Toda la lógica de negocio vive en
el núcleo (`cargo_optimizer.core`), que debe ser utilizable sin
ninguna dependencia de interfaz gráfica desde:

- la aplicación de escritorio (PySide6)
- una futura API REST
- un ERP
- una futura aplicación web o móvil

En consecuencia: `cargo_optimizer.core` **nunca** importa nada de
`cargo_optimizer.ui` ni de PySide6/Qt. `cargo_optimizer.ui` solo
contiene presentación; delega todo cálculo y toda regla de negocio al
núcleo.

## Stack tecnológico

- Python 3.12+, tipado obligatorio (type hints en todo el código
  nuevo).
- PySide6 para la interfaz de escritorio.
- VTK para visualización 3D (fase 5, aún no implementada).
- SQLite + SQLAlchemy para persistencia (fase 7, aún no implementada).
- openpyxl para Excel y ReportLab para PDF (fase 8, aún no
  implementadas).
- Ruff para lint (incluye orden de imports). Black para formateo. No
  usar el formateador de Ruff para evitar conflictos con Black.
- Mypy en modo estricto (`strict = true`).
- Pytest para pruebas.

## Estructura del repositorio

```
src/cargo_optimizer/
├── core/     # SDK: dominio, motor geométrico, restricciones, optimización, persistencia
└── ui/       # Aplicación de escritorio PySide6. Solo presentación.
tests/        # Pruebas, en espejo de la estructura de src/
docs/         # Documentación de arquitectura y diseño
```

## Comandos de referencia

```powershell
.\.venv\Scripts\python.exe -m cargo_optimizer   # ejecutar la app
.\.venv\Scripts\python.exe -m ruff check .      # lint
.\.venv\Scripts\python.exe -m black .           # formateo
.\.venv\Scripts\python.exe -m mypy src          # tipado
.\.venv\Scripts\python.exe -m pytest            # tests
```

## Fases del proyecto

0. Diseño completo — 1. Arquitectura — 2. Motor geométrico — 3. Motor
   de restricciones — 4. Motor de optimización — 5. Visualización 3D —
   6. Interfaz — 7. Persistencia — 8. Reportes — 9. Integración ERP —
   10. Versión comercial.

Estado actual: **infraestructura base completada** (fin de fase 1,
sin motor geométrico ni de optimización todavía). No implementar
packing 3D, reglas de restricciones, visualización 3D, SQLite, Excel,
PDF ni optimización hasta que se indique explícitamente.

## Reglas de trabajo con el asistente

- Antes de escribir código en una fase nueva: diseñar, documentar,
  proponer alternativas y justificar decisiones técnicas.
- Si una decisión del usuario implica una mala decisión de
  arquitectura, decirlo explícitamente y explicar por qué, antes de
  implementarla.
- No sobrearquitecturar: preferir una base pequeña, limpia y
  totalmente funcional sobre abstracciones especulativas.
- Nunca dejar archivos incompletos, imports rotos ni pseudocódigo.
