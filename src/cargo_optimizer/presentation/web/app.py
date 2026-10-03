"""CargoOptimizer3D — aplicación web con Trame + PyVista.

Acceso: http://localhost:8080
Un solo usuario, red local.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from dataclasses import replace
from uuid import uuid4

import pyvista as pv
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html
from trame.widgets import vuetify3 as v3

from cargo_optimizer.infrastructure.database import CatalogService
from cargo_optimizer.optimization.engine import PackingEngine
from cargo_optimizer.optimization.models import PackingRequest
from cargo_optimizer.presentation.desktop.viewer.scene_builder import SceneBuilder
from cargo_optimizer.presentation.desktop.viewer.scene_controller import SceneController



# ── Helpers ────────────────────────────────────────────────────────────────

def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _kg(value: float) -> str:
    return f"{value:,.0f} kg".replace(",", ".")


# ── App ────────────────────────────────────────────────────────────────────

def run(port: int = 8080) -> None:
    server = get_server("cargo3d", client_type="vue3")
    state, ctrl = server.state, server.controller

    # ── Datos del catálogo ────────────────────────────────────────────────
    catalog_service = CatalogService.create_default()
    _profiles = sorted(catalog_service.profiles.list_active(), key=lambda p: p.name)
    _products = sorted(catalog_service.products.list_active(), key=lambda p: p.sku)

    _profile_by_id: dict[str, object] = {p.id.hex: p for p in _profiles}
    _product_by_sku: dict[str, object] = {p.sku: p for p in _products}

    # ── Estado inicial ────────────────────────────────────────────────────
    state.profile_options = [
        {"title": p.name, "value": p.id.hex} for p in _profiles
    ]
    state.selected_profile = _profiles[0].id.hex if _profiles else None

    state.product_options = [
        {"title": f"{p.sku}  –  {p.name}", "value": p.sku}
        for p in _products
    ]
    state.selected_sku = None
    state.add_qty = 100

    state.load_list = []   # [{sku, name, qty, color}]

    state.running = False
    state.status_msg = "Listo para optimizar."
    state.error_msg = ""

    state.has_result = False
    state.utilization_pct = "—"
    state.packed_label = "—"
    state.weight_label = "—"
    state.time_label = "—"
    state.unpacked_count = 0

    # ── Visor PyVista ─────────────────────────────────────────────────────
    pl = pv.Plotter(off_screen=True)
    _scene_builder = SceneBuilder()
    _scene_ctrl = SceneController(pl)

    # ── Controladores ─────────────────────────────────────────────────────

    @ctrl.add("add_to_load")
    def add_to_load(sku: str = "", qty_str: str = "", **_):
        # sku y qty vienen como parámetros desde el botón (click con args)
        sku = sku or state.selected_sku
        try:
            qty = int(qty_str) if qty_str else int(state.add_qty or 0)
        except (TypeError, ValueError):
            qty = 0
        if not sku or qty <= 0:
            state.error_msg = "Selecciona un producto y una cantidad > 0."
            return
        product = _product_by_sku.get(sku)
        if product is None:
            state.error_msg = f"SKU {sku} no encontrado."
            return

        existing = {i["sku"]: i for i in state.load_list}
        existing[sku] = {
            "sku": sku,
            "name": product.name,
            "qty": qty,
            "color": getattr(product, "color_hex", "#888888"),
        }
        state.load_list = list(existing.values())
        state.error_msg = ""
        state.selected_sku = None
        state.add_qty = 100

    @ctrl.add("remove_from_load")
    def remove_from_load(sku: str = "", **_):
        state.load_list = [i for i in state.load_list if i["sku"] != sku]

    @ctrl.add("clear_load")
    def clear_load(**_):
        state.load_list = []
        state.has_result = False
        _scene_ctrl.clear_scene()
        try:
            ctrl.view_update()
        except Exception:
            pass

    _executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="cargo_opt")

    async def _run_optimization_async(profile_id: str, load_snapshot: list) -> None:
        """Corre la optimización en un executor (sin bloquear el event loop).

        El trabajo VTK posterior ocurre en el event loop — thread-safe para VTK/OpenGL.
        Al final se llama state.flush() para propagar los cambios al cliente.
        """
        def _pure_optimize():
            profile = _profile_by_id.get(profile_id)
            if profile is None:
                return {"error": "Perfil no encontrado."}

            loading_space = replace(profile, id=uuid4())
            load_units = []
            for item in load_snapshot:
                product = _product_by_sku.get(item["sku"])
                if product is None:
                    continue
                unit = CatalogService.copy_to_project(product)
                unit = replace(unit, quantity=int(item["qty"]))
                load_units.append(unit)

            if not load_units:
                return {"error": "Ningún producto válido en la lista."}

            request = PackingRequest(
                loading_space=loading_space,
                load_units=tuple(load_units),
                time_limit_seconds=30.0,
            )
            result = PackingEngine().optimize(request)

            dims = loading_space.internal_dimensions
            total_vol = dims.length_cm * dims.width_cm * dims.height_cm
            util = result.used_volume_cm3 / total_vol * 100 if total_vol else 0.0
            units_by_id = {u.id: u for u in load_units}
            scene = _scene_builder.build(result, units_by_id)
            return {
                "scene": scene,
                "stats": {
                    "util": _pct(util),
                    "packed": f"{result.packed_count} / {result.requested_count}",
                    "weight": _kg(result.used_weight_kg),
                    "time": f"{result.execution_time_seconds:.1f} s",
                    "unpacked": len(result.unpacked_units),
                    "status": (
                        f"Listo: {result.packed_count}/{result.requested_count} unidades"
                        f"  |  {_pct(util)} utilización"
                    ),
                },
            }

        try:
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(_executor, _pure_optimize)
        except Exception as exc:  # noqa: BLE001
            data = {"error": str(exc)}

        # De vuelta en el event loop → VTK thread-safe
        if "error" in data:
            state.error_msg = data["error"]
            state.status_msg = "Error durante la optimización."
        else:
            _scene_ctrl.load_scene(data["scene"])
            s = data["stats"]
            state.utilization_pct = s["util"]
            state.packed_label = s["packed"]
            state.weight_label = s["weight"]
            state.time_label = s["time"]
            state.unpacked_count = s["unpacked"]
            state.has_result = True
            state.status_msg = s["status"]
            try:
                ctrl.view_update()
                ctrl.view_reset_camera()
            except Exception:
                pass

        state.running = False
        state.flush()

    @ctrl.add("run_optimization")
    def run_optimization(**_):
        if state.running:
            return
        if not state.load_list:
            state.error_msg = "Agrega al menos un producto a la lista de carga."
            return
        if not state.selected_profile:
            state.error_msg = "Selecciona un espacio de carga."
            return

        state.running = True
        state.status_msg = "Optimizando…"
        state.error_msg = ""

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run_optimization_async(state.selected_profile, list(state.load_list)))
        except RuntimeError:
            state.error_msg = "Error interno: event loop no disponible."
            state.running = False

    # ── Layout ────────────────────────────────────────────────────────────
    with SinglePageLayout(server) as layout:
        layout.title.set_text("CargoOptimizer3D")

        # Toolbar
        with layout.toolbar as tb:
            tb.density = "compact"
            with html.Div(classes="d-flex align-center", style="gap:16px; flex:1"):
                html.Span(
                    "CargoOptimizer3D",
                    classes="text-h6 font-weight-bold",
                    style="color:#EF5350",
                )
                v3.VDivider(vertical=True, inset=True)
                html.Span(
                    "{{ status_msg }}",
                    classes="text-body-2 text-medium-emphasis",
                )
            v3.VSpacer()
            with v3.VBtn(
                icon=True,
                color="red",
                variant="tonal",
                click=ctrl.run_optimization,
                loading=("running",),
                disabled=("running || load_list.length === 0",),
                title="Ejecutar optimización (F5)",
            ):
                v3.VIcon("mdi-play")

        # Contenido principal
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-0 fill-height", style="overflow:hidden"):
                with html.Div(
                    classes="d-flex fill-height",
                    style="height:100%; overflow:hidden",
                ):
                    # ── Panel izquierdo ───────────────────────────────────
                    with html.Div(
                        style=(
                            "width:300px; min-width:300px; height:100%;"
                            "overflow-y:auto; border-right:1px solid rgba(255,255,255,0.12);"
                            "padding:12px; display:flex; flex-direction:column; gap:12px"
                        )
                    ):
                        # Espacio de carga
                        with v3.VCard(variant="tonal", classes="pa-3"):
                            v3.VCardSubtitle("ESPACIO DE CARGA", classes="pa-0 mb-2")
                            v3.VSelect(
                                v_model=("selected_profile",),
                                items=("profile_options",),
                                item_title="title",
                                item_value="value",
                                label="Contenedor / perfil",
                                density="compact",
                                hide_details=True,
                                variant="outlined",
                            )

                        # Agregar productos
                        with v3.VCard(variant="tonal", classes="pa-3"):
                            v3.VCardSubtitle("AGREGAR PRODUCTO", classes="pa-0 mb-2")
                            v3.VSelect(
                                v_model=("selected_sku",),
                                items=("product_options",),
                                item_title="title",
                                item_value="value",
                                label="Producto (SKU / nombre)",
                                density="compact",
                                hide_details=True,
                                variant="outlined",
                                classes="mb-2",
                                clearable=True,
                            )
                            with html.Div(classes="d-flex align-center", style="gap:8px"):
                                v3.VTextField(
                                    v_model=("add_qty",),
                                    label="Cantidad",
                                    type="number",
                                    min=1,
                                    density="compact",
                                    hide_details=True,
                                    variant="outlined",
                                    style="flex:1",
                                )
                                v3.VBtn(
                                    "Agregar",
                                    color="primary",
                                    density="compact",
                                    variant="tonal",
                                    click=(
                                        ctrl.add_to_load,
                                        "[selected_sku, String(add_qty)]",
                                    ),
                                )

                        # Lista de carga
                        with v3.VCard(variant="tonal", classes="pa-3", style="flex:1"):
                            with html.Div(
                                classes="d-flex align-center justify-space-between mb-2"
                            ):
                                v3.VCardSubtitle(
                                    "LISTA DE CARGA ({{ load_list.length }})",
                                    classes="pa-0",
                                )
                                with v3.VBtn(
                                    icon=True,
                                    size="x-small",
                                    variant="text",
                                    click=ctrl.clear_load,
                                    v_if="load_list.length > 0",
                                    title="Limpiar lista",
                                ):
                                    v3.VIcon("mdi-trash-can-outline", size="small")

                            # Tabla de carga
                            with v3.VTable(density="compact", v_if="load_list.length > 0"):
                                with html.Template(v_slot_default=True):
                                    with html.Thead():
                                        with html.Tr():
                                            html.Th("SKU", style="font-size:11px")
                                            html.Th("Nombre", style="font-size:11px")
                                            html.Th("QTY", style="font-size:11px; width:50px")
                                            html.Th("", style="width:32px")
                                    with html.Tbody():
                                        with html.Template(
                                            v_for="(item, i) in load_list",
                                            key="item.sku",
                                        ):
                                            with html.Tr():
                                                html.Td(
                                                    "{{ item.sku }}",
                                                    style="font-size:11px; white-space:nowrap",
                                                )
                                                html.Td(
                                                    "{{ item.name }}",
                                                    style="font-size:11px",
                                                )
                                                html.Td(
                                                    "{{ item.qty }}",
                                                    style=(
                                                        "font-size:11px; text-align:right;"
                                                        "padding-right:8px"
                                                    ),
                                                )
                                                with html.Td():
                                                    with v3.VBtn(
                                                        icon=True,
                                                        size="x-small",
                                                        variant="text",
                                                        click=(
                                                            ctrl.remove_from_load,
                                                            "[item.sku]",
                                                        ),
                                                    ):
                                                        v3.VIcon(
                                                            "mdi-close",
                                                            size="x-small",
                                                        )

                            with html.Div(
                                classes="text-caption text-medium-emphasis text-center pa-4",
                                v_if="load_list.length === 0",
                            ):
                                html.Span(
                                    "Agrega productos del catálogo para optimizar."
                                )

                        # Error
                        with v3.VAlert(
                            type="error",
                            density="compact",
                            variant="tonal",
                            v_if="error_msg",
                            classes="text-caption",
                        ):
                            html.Span("{{ error_msg }}")

                    # ── Panel derecho: visor + resultados ─────────────────
                    with html.Div(
                        style="flex:1; display:flex; flex-direction:column; height:100%; min-width:0"
                    ):
                        # Barra de resultados
                        with html.Div(
                            v_if="has_result",
                            classes="d-flex align-center pa-2",
                            style=(
                                "background:rgba(239,83,80,0.08);"
                                "border-bottom:1px solid rgba(239,83,80,0.2);"
                                "gap:12px; flex-shrink:0"
                            ),
                        ):
                            with html.Div(classes="d-flex align-center", style="gap:4px"):
                                v3.VIcon(
                                    "mdi-package-variant-closed",
                                    size="small",
                                    color="red",
                                )
                                html.Span(
                                    "{{ packed_label }}",
                                    classes="text-body-2 font-weight-medium",
                                )
                                html.Span(
                                    "uds. cargadas",
                                    classes="text-caption text-medium-emphasis",
                                )
                            v3.VDivider(vertical=True, inset=True)
                            with html.Div(classes="d-flex align-center", style="gap:4px"):
                                v3.VIcon(
                                    "mdi-cube-outline",
                                    size="small",
                                    color="primary",
                                )
                                html.Span(
                                    "{{ utilization_pct }}",
                                    classes="text-body-2 font-weight-medium",
                                )
                                html.Span(
                                    "volumen",
                                    classes="text-caption text-medium-emphasis",
                                )
                            v3.VDivider(vertical=True, inset=True)
                            with html.Div(classes="d-flex align-center", style="gap:4px"):
                                v3.VIcon(
                                    "mdi-weight-kilogram",
                                    size="small",
                                    color="secondary",
                                )
                                html.Span(
                                    "{{ weight_label }}",
                                    classes="text-body-2 font-weight-medium",
                                )
                            v3.VDivider(vertical=True, inset=True)
                            with html.Div(classes="d-flex align-center", style="gap:4px"):
                                v3.VIcon("mdi-timer-outline", size="small")
                                html.Span(
                                    "{{ time_label }}",
                                    classes="text-caption text-medium-emphasis",
                                )
                            with v3.VChip(
                                v_if="unpacked_count > 0",
                                color="orange",
                                size="small",
                                label=True,
                            ):
                                html.Span("{{ unpacked_count }} sin cargar")

                        # Visor 3D (VtkRemoteView — renderizado server-side)
                        with html.Div(style="flex:1; min-height:0; position:relative; min-width:400px"):
                            from trame_vtk.widgets.vtk import VtkRemoteView

                            view = VtkRemoteView(
                                pl.ren_win,
                                ref="view",
                                style="width:100%; height:100%; display:block",
                            )
                            ctrl.view_update = view.update
                            ctrl.view_reset_camera = view.reset_camera

    server.start(exec_mode="main", port=port, open_browser=True)
