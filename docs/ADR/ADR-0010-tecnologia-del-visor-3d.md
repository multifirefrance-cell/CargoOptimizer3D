# ADR-0010: Tecnología del visor 3D (PyVista + PyVistaQt)

## Estado

Aceptada — 2026-07-15

## Contexto

La fase 6 introduce un visor tridimensional que representa un
`PackingResult` dentro de `presentation/desktop`. Esta sesión (6.0) es
de diseño puro (ver `docs/ThreeDViewerDesign.md`); no se instala
ninguna dependencia todavía. Se evaluaron formalmente cuatro
alternativas de tecnología de renderizado 3D integrable en PySide6:
PyVista + PyVistaQt, VTK integrado directamente, `QOpenGLWidget` con
OpenGL propio, y VisPy — comparadas en integración con PySide6, soporte
Windows, mantenimiento, picking, cámara, transparencia, rendimiento con
miles de cajas, exportación de imágenes, facilidad de pruebas,
empaquetado, peso de dependencias, documentación y riesgo de
incompatibilidad futura (tabla completa en
`docs/ThreeDViewerDesign.md`, sección 2).

## Decisión

Se adopta **PyVista + PyVistaQt** como tecnología de renderizado del
visor 3D, a partir de la fase 6.1.

Las otras tres alternativas se descartan con razones concretas, no por
descarte automático de la recomendación inicial:

- **VTK directo**: tiene exactamente el mismo coste de dependencias y
  empaquetado que PyVista (PyVista es una capa delgada sobre el mismo
  VTK), sin ninguna de sus utilidades de alto nivel (picking, cámara,
  mallas combinadas) — elegirlo renuncia a las ventajas de PyVista sin
  ahorrar nada real.
- **`QOpenGLWidget` propio**: la única alternativa sin dependencias
  nuevas, pero exige construir y mantener indefinidamente un motor de
  renderizado completo (shaders, cámara, transparencia, picking, texto)
  para un problema — cajas ortoédricas en un espacio rectangular — que
  no lo justifica. Para software que debe mantenerse diez años
  (`CLAUDE.md`), asumir ese pasivo de ingeniería es un riesgo mayor que
  el peso de una dependencia madura.
- **VisPy**: más liviana que VTK y con buen rendimiento en instancing,
  pero su integración con Qt, su picking y su comunidad son
  sensiblemente menos maduros que los de VTK/PyVista para este caso
  concreto (escena tipo CAD con selección y cámaras predefinidas). No
  se cierra la puerta a reconsiderarla si el peso de VTK resultara
  inaceptable en empaquetado.

## Consecuencias

**Beneficios:**

- Picking, cámara (órbita/zoom/pan de fábrica, encuadre automático) y
  transparencia llegan resueltos por una biblioteca madura, sin
  reinventar un motor gráfico propio.
- Rutas de escalado conocidas (`MultiBlock`, mallas combinadas con
  datos por celda, `glyph()`/instancing) disponibles para cuando el
  volumen de cajas lo requiera (fase 6.3), sin cambiar de tecnología.
- Modo `off_screen=True` de primera clase, útil para pruebas y para una
  futura captura de imágenes en servidor.
- Documentación extensa y comunidad activa, relevante para un producto
  de vida larga con equipo pequeño.

**Costes / riesgos aceptados:**

- **Peso de empaquetado**: las wheels de VTK son sustancialmente más
  pesadas que el resto de dependencias actuales del proyecto. Se acepta
  porque ninguna alternativa evaluada lo evita sin asumir un coste de
  ingeniería mayor (ver `QOpenGLWidget` arriba); el detalle de riesgo de
  empaquetado se documenta en `docs/ThreeDViewerDesign.md`, sección 21,
  para no sorprender en la fase de distribución.
- **Renderizado offscreen no garantizado en todo entorno**: VTK
  necesita un contexto OpenGL real incluso en modo `off_screen`; un
  entorno de CI totalmente headless sin ningún driver puede no
  conseguirlo. Se acepta con un diseño de pruebas que detecta este caso
  y se salta limpiamente (`docs/ThreeDViewerDesign.md`, sección 22) en
  vez de asumir que siempre funciona.
- **Compatibilidad de versiones por confirmar**: la compatibilidad
  exacta de PyVista + PyVistaQt + VTK con Python 3.12 y PySide6 6.7+
  debe verificarse al implementar (fase 6.1), no se da por hecha en
  esta fase de diseño.
- **No es una garantía de rendimiento**: ninguna cifra de rendimiento
  de esta decisión está medida todavía; las expectativas documentadas
  en `docs/ThreeDViewerDesign.md` son razonadas a partir del
  comportamiento público y conocido de VTK, no mediciones propias.
