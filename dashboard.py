import asyncio
import flet as ft
import math
import os
import random
from datetime import datetime, timezone
from pymongo import MongoClient
from neo4j import GraphDatabase

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "ecodrones_db"
COLLECTION_TELEMETRIA = "telemetria"
COLLECTION_ALERTAS = "alertas_disparadas"
DRONES = ["DRON_ALPHA", "DRON_BETA", "DRON_GAMMA"]
mongo_client = MongoClient(MONGO_URI)
col_telemetria = mongo_client[DB_NAME][COLLECTION_TELEMETRIA]
col_alertas = mongo_client[DB_NAME][COLLECTION_ALERTAS]

# Neo4j para la pestaña de Análisis de Propagación
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Límites para Capilla del Monte
GEO_LON_MIN, GEO_LON_MAX = -64.5400, -64.5050
GEO_LAT_MIN, GEO_LAT_MAX = -30.8750, -30.8500

lat_capilla, lon_capilla = -30.8625, -64.5234
mapa_sat_url = f"https://static-maps.yandex.ru/1.x/?ll={lon_capilla},{lat_capilla}&z=13&l=sat&size=650,450"

def format_timestamp(ts):
    if not ts:
        return "-"
    if isinstance(ts, str):
        return ts.replace("T", " ")[:19]
    return str(ts)


def co2_color(co2):
    if co2 < 600:
        return "#2ecc71"
    if co2 < 1000:
        return "#f1c40f"
    if co2 < 1500:
        return "#e67e22"
    return "#e74c3c"


def co2_status(co2):
    if co2 < 600:
        return "Normal"
    if co2 < 1000:
        return "Moderado"
    if co2 < 1500:
        return "Alto"
    return "Muy alto"


def sensor_box(title, value, unit, color, status=None):
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=10, color="#aaaaaa", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            ft.Row([
                ft.Text(str(value), size=20, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(unit, size=12, color="#cccccc"),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            ft.Text(status or "", size=10, color=color, text_align=ft.TextAlign.CENTER),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#141426",
        border=ft.border.Border.all(1, "#333"),
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        expand=True,
    )


def alert_sensor_box(title, value, unit, color):
    """Versión legible del sensor_box para la lista de alertas"""
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=13, color="#aaaaaa", weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Text(str(value), size=34, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(unit, size=16, color="#cccccc"),
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=2), # Espaciador
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#101020",
        border=ft.border.Border.all(1, "#333"),
        border_radius=8,
        padding=8,
        expand=True,
    )


def build_drone_card(doc):
    drone_id = doc.get("drone_id", "?")
    zona = doc.get("cod_zona", "?")
    coords = doc.get("posicion_geografica", {}).get("coordinates", [None, None])
    lon = coords[0] if len(coords) > 0 else None
    lat = coords[1] if len(coords) > 1 else None
    lec = doc.get("lecturas_sensores", {})
    temp = lec.get("temperatura_c", 0)
    co2 = lec.get("co2_ppm", 0)
    hum = lec.get("humedad_relativa_porcentaje", 0)
    viento = lec.get("viento_velocidad_kmh", 0)
    vdir = lec.get("viento_direccion_grados", 0)
    bat = doc.get("estado_bateria_porcentaje", 0)

    if temp > 45:
        temp_color = "#e74c3c"
        level = "INCENDIO"
    elif temp > 35:
        temp_color = "#e67e22"
        level = "ELEVADO"
    else:
        temp_color = "#2ecc71"
        level = "Normal"

    co2_level = co2_status(co2)
    co2_color_value = co2_color(co2)

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text(f"{drone_id}", size=18, weight=ft.FontWeight.BOLD, color="white"),
                ft.Container(expand=True),
                ft.Text(format_timestamp(doc.get("timestamp", "")), size=11, color="#888"),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Container(width=10, height=10, bgcolor="#2ecc71", border_radius=5),
                ft.Text("ONLINE", size=10, color="#2ecc71"),
                ft.Container(expand=True),
                ft.Text(doc.get("modelo_hardware", ""), size=9, color="#666"),
            ], spacing=8),
            ft.Text(f"Zona: {zona}", size=12, color="#99bbff"),
            ft.Text(f"Posición: {lon if lon is not None else '-'} , {lat if lat is not None else '-'}", size=11, color="#cccccc"),
            ft.Divider(color="#2a2a3a"),
            ft.Row([
                sensor_box("TEMPERATURA", f"{temp}°C", "", temp_color, level),
                sensor_box("CO2", f"{co2}", "ppm", co2_color_value, co2_level),
                sensor_box("HUMEDAD", f"{hum}", "%", "#4fc3f7", None),
                sensor_box("VIENTO", f"{viento}", "km/h", "#9b59b6", f"Dir {vdir}°"),
            ], spacing=10),
            # Sensores adicionales (solo si existen en el documento — esquema flexible)
            ft.Row([
                sensor_box("UV", f"{lec.get('radiacion_uv_indice', '-')}", "idx", "#ff7043", None) if lec.get("radiacion_uv_indice") else ft.Container(),
                sensor_box("PRESIÓN", f"{lec.get('presion_atmosferica_hpa', '-')}", "hPa", "#42a5f5", None) if lec.get("presion_atmosferica_hpa") else ft.Container(),
                sensor_box("LUZ", f"{lec.get('luminosidad_lux', '-')}", "lux", "#ffca28", None) if lec.get("luminosidad_lux") else ft.Container(),
                sensor_box("PM2.5", f"{lec.get('particulas_pm25_ugm3', '-')}", "μg/m³", "#ab47bc", None) if lec.get("particulas_pm25_ugm3") else ft.Container(),
            ], spacing=10) if any(lec.get(k) for k in ("radiacion_uv_indice", "presion_atmosferica_hpa", "luminosidad_lux", "particulas_pm25_ugm3")) else ft.Container(),
            ft.Row([
                ft.Text(f"Batería: {bat}%", size=11, color="#bbbbbb"),
                ft.Container(expand=True),
                ft.Text("Datos en vivo desde MongoDB", size=11, color="#888"),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=12),
        bgcolor="#181832",
        border=ft.border.Border.all(1, "#333"),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=18, vertical=18),
        expand=True,
    )


def build_history_card(drone_id, docs):
    rows = [
        ft.Row([
            ft.Text("Hora", size=10, color="#777", width=150),
            ft.Text("Longitud", size=10, color="#777", width=120),
            ft.Text("Latitud", size=10, color="#777", width=120),
            ft.Text("Zona", size=10, color="#777", width=100),
        ], spacing=10),
        ft.Divider(color="#2a2a3a"),
    ]

    if not docs:
        rows.append(ft.Text("No hay registros recientes para este dron.", size=11, color="#999"))
    else:
        for doc in docs:
            coords = doc.get("posicion_geografica", {}).get("coordinates", [None, None])
            lon = coords[0] if len(coords) > 0 else None
            lat = coords[1] if len(coords) > 1 else None
            rows.append(
                ft.Row([
                    ft.Text(format_timestamp(doc.get("timestamp", "")), size=10, color="#ccc", width=150),
                    ft.Text(f"{lon:.6f}" if lon is not None else "-", size=10, color="#ccc", width=120),
                    ft.Text(f"{lat:.6f}" if lat is not None else "-", size=10, color="#ccc", width=120),
                    ft.Text(doc.get("cod_zona", "-"), size=10, color="#99bbff", width=100),
                ], spacing=10)
            )

    return ft.Container(
        content=ft.Column([
            ft.Text(f"Recorrido de {drone_id}", size=14, weight=ft.FontWeight.BOLD, color="white"),
            *rows,
        ], spacing=8),
        bgcolor="#181832",
        border=ft.border.Border.all(1, "#333"),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=16, vertical=16),
        expand=True,
    )


def build_route_map(alpha_docs, beta_docs, gamma_docs=[]):
    W, H = 940, 340
    padding = 40
    grid_color = "#1f2840"

    def get_latest_point(docs):
        for doc in reversed(docs):
            geo = doc.get("posicion_geografica", {}).get("coordinates", [None, None])
            if len(geo) >= 2 and geo[0] is not None and geo[1] is not None:
                temp = doc.get("lecturas_sensores", {}).get("temperatura_c", 0)
                co2 = doc.get("lecturas_sensores", {}).get("co2_ppm", 0)
                return {
                    "lon": geo[0],
                    "lat": geo[1],
                    "temp": temp,
                    "co2": co2,
                }
        return None

    alpha_point = get_latest_point(alpha_docs)
    beta_point = get_latest_point(beta_docs)
    gamma_point = get_latest_point(gamma_docs)

    if not alpha_point and not beta_point and not gamma_point:
        return ft.Container(
            content=ft.Text("Esperando puntos de latitud/longitud...", color="#999", size=12),
            bgcolor="#181832",
            border=ft.border.Border.all(1, "#333"),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=16),
            expand=True,
            height=H + 2 * padding,
        )

    def project(lon, lat):
        x = padding + (lon - GEO_LON_MIN) / (GEO_LON_MAX - GEO_LON_MIN) * (W - 2 * padding)
        y = padding + (GEO_LAT_MAX - lat) / (GEO_LAT_MAX - GEO_LAT_MIN) * (H - 2 * padding)
        return x, y

    def temp_color(temp):
        red = min(255, max(0, int((temp - 20) / 40 * 255)))
        green = min(255, max(0, int((60 - temp) / 40 * 255)))
        return f"#{red:02x}{green:02x}00"

    def co2_ring_size(co2):
        normalized = min(1.0, max(0.0, (co2 - 400) / 800.0))
        return int(24 + normalized * 36)

    def co2_color(co2):
        if co2 < 600:
            return "#2ecc71"
        if co2 < 1000:
            return "#f1c40f"
        if co2 < 1500:
            return "#e67e22"
        return "#e74c3c"

    def separate_points(p1, p2):
        if not p1 or not p2:
            return
        x1, y1 = project(p1["lon"], p1["lat"])
        x2, y2 = project(p2["lon"], p2["lat"])
        if abs(x1 - x2) < 30 and abs(y1 - y2) < 30:
            p1["dx"], p1["dy"] = -14, 0
            p2["dx"], p2["dy"] = 14, 0
        else:
            p1["dx"], p1["dy"] = 0, 0
            p2["dx"], p2["dy"] = 0, 0

    separate_points(alpha_point, beta_point)

    def draw_grid():
        controls = []
        for i in range(1, 6):
            x = padding + i * (W - 2 * padding) / 6
            y = padding + i * (H - 2 * padding) / 6
            controls.append(ft.Container(left=x, top=padding, width=1, height=H - 2 * padding, bgcolor=grid_color))
            controls.append(ft.Container(left=padding, top=y, width=W - 2 * padding, height=1, bgcolor=grid_color))
        return controls

    controls = [
        ft.Container(width=W, height=H, bgcolor="#0c1224", border=ft.border.Border.all(1, "#222"), border_radius=16),
        *draw_grid(),
    ]

    def add_route_point(point, accent_color, label):
        x, y = project(point["lon"], point["lat"])
        x += point.get("dx", 0)
        y += point.get("dy", 0)
        color = temp_color(point["temp"])
        ring_size = co2_ring_size(point["co2"])
        ring_color = co2_color(point["co2"])
        controls.append(ft.Container(
            left=x - ring_size / 2,
            top=y - ring_size / 2,
            width=ring_size,
            height=ring_size,
            border_radius=ring_size / 2,
            border=ft.border.Border.all(2, ring_color),
        ))
        controls.append(ft.Container(
            left=x - 8,
            top=y - 8,
            width=16,
            height=16,
            border_radius=8,
            bgcolor=color,
            border=ft.border.Border.all(2, accent_color),
        ))
        controls.append(ft.Container(
            left=x - 30,
            top=y - ring_size / 2 - 24,
            width=60,
            height=20,
            content=ft.Text(label, size=10, color="white", text_align=ft.TextAlign.CENTER),
            alignment=ft.Alignment(0, 0),
        ))

    if alpha_point:
        add_route_point(alpha_point, "#4cd964", "DRON_ALPHA")
    if beta_point:
        add_route_point(beta_point, "#ff9500", "DRON_BETA")
    if gamma_point:
        add_route_point(gamma_point, "#3498db", "DRON_GAMMA")

    return ft.Container(
        content=ft.Stack(controls, width=W, height=H),
        bgcolor="#181832",
        border=ft.border.Border.all(1, "#333"),
        border_radius=16,
        padding=ft.Padding.all(12),
        expand=True,
    )


def build_route_legend():
    return ft.Container(
        content=ft.Column([
            ft.Text("Leyenda", size=12, weight=ft.FontWeight.BOLD, color="white"),
            ft.Row([
                ft.Row([
                    ft.Container(width=12, height=12, bgcolor="#ffffff", border_radius=6),
                    ft.Text("Color del punto = temperatura (verde frío, rojo caliente)", size=10, color="#ccc"),
                ], spacing=8),
                ft.Row([
                    ft.Container(width=20, height=20, border=ft.border.Border.all(2, "#77a0ff"), border_radius=10),
                    ft.Text("Tamaño del anillo = CO₂ (verde normal, rojo alto)", size=10, color="#ccc"),
                ], spacing=8),
            ], spacing=18),
        ], spacing=10),
        bgcolor="#13172f",
        border=ft.border.Border.all(1, "#222"),
        border_radius=14,
        padding=ft.Padding.symmetric(horizontal=14, vertical=14),
        expand=True,
    )


def build_route_tab(alpha_docs, beta_docs, gamma_docs=[]):
    return ft.Column([
        ft.Row([
            ft.Text("Recorrido de drones desde MongoDB", size=16, weight=ft.FontWeight.BOLD, color="white"),
            ft.Container(expand=True),
            ft.Row([
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor="#2ecc71", border_radius=5),
                    ft.Text(" DRON_ALPHA online", size=11, color="#ccc"),
                ], spacing=4),
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor="#2ecc71", border_radius=5),
                    ft.Text(" DRON_BETA online", size=11, color="#ccc"),
                ], spacing=4),
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor="#2ecc71", border_radius=5),
                    ft.Text(" DRON_GAMMA online", size=11, color="#ccc"),
                ], spacing=4),
            ], spacing=10),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ft.Text("Cada punto es un registro de latitud/longitud desde MongoDB.", size=11, color="#aaa"),
        ft.Divider(color="#2a2a3a"),
        build_route_map(alpha_docs, beta_docs),
        build_route_legend(),
    ], spacing=12, expand=True)

def query_propagacion_neo4j(cod_zona, direccion_viento):
    """Consulta Neo4j para obtener fauna en riesgo y zonas de propagación."""
    query = """
    MATCH (z:Zona {cod_zona: $zona})
    OPTIONAL MATCH (especie:Especie)-[h:HABITA_EN]->(z)
    WITH z, collect(DISTINCT {comun: especie.nombre_comun, cientifico: especie.nombre_cientifico, iucn: especie.categoria_iucn, densidad: h.densidad_estimada_por_ha}) AS fauna_local

    OPTIONAL MATCH (z)-[r1:LIMITA_CON {direccion: $dir_viento}]->(z1:Zona)
    OPTIONAL MATCH (e1:Especie)-[h1:HABITA_EN]->(z1)
    WITH z, fauna_local, z1, r1, collect(DISTINCT {comun: e1.nombre_comun, cientifico: e1.nombre_cientifico, iucn: e1.categoria_iucn, densidad: h1.densidad_estimada_por_ha}) AS fauna1

    OPTIONAL MATCH (z1)-[r2:LIMITA_CON {direccion: $dir_viento}]->(z2:Zona)
    OPTIONAL MATCH (e2:Especie)-[h2:HABITA_EN]->(z2)
    WITH z, fauna_local, z1, r1, fauna1, z2, r2, collect(DISTINCT {comun: e2.nombre_comun, cientifico: e2.nombre_cientifico, iucn: e2.categoria_iucn, densidad: h2.densidad_estimada_por_ha}) AS fauna2

    RETURN
      z.nombre AS zona_origen_nombre,
      z.tipo_bioma AS zona_origen_bioma,
      z.superficie_hectareas AS zona_origen_sup,
      fauna_local,
      z1.cod_zona AS salto1_cod,
      z1.nombre AS salto1_nombre,
      z1.tipo_bioma AS salto1_bioma,
      r1.distancia_km AS salto1_dist,
      r1.probabilidad_propagacion AS salto1_prob,
      fauna1 AS salto1_fauna,
      z2.cod_zona AS salto2_cod,
      z2.nombre AS salto2_nombre,
      z2.tipo_bioma AS salto2_bioma,
      r2.distancia_km AS salto2_dist,
      r2.probabilidad_propagacion AS salto2_prob,
      fauna2 AS salto2_fauna
    """
    try:
        with neo4j_driver.session() as session:
            result = session.run(query, zona=cod_zona, dir_viento=direccion_viento)
            return result.single()
    except Exception as e:
        print(f"Error Neo4j propagación: {e}")
        return None


def calcular_rumbo_desde_grados(grados):
    """Traduce grados del sensor a dirección cardinal de propagación."""
    if 45 <= grados <= 135:
        return "Oeste"
    elif 225 <= grados <= 315:
        return "Este"
    elif 135 < grados < 225:
        return "Norte"
    else:
        return "Sur"


def main(page: ft.Page):
    page.title = "EcoDrones — Monitoreo Táctico"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f1225"
    page.window_width = 1250
    page.window_height = 850
    page.padding = 16

    status_dot = ft.Container(width=10, height=10, bgcolor="#2ecc71", border_radius=5)
    status_text = ft.Text("Sistema Operativo", size=12, color="#bbbbbb")

    drone_cards = ft.Row([], spacing=16, expand=True)

    def open_neo4j(e):
        import webbrowser
        webbrowser.open("http://localhost:7474")

    header = ft.Row([
        ft.Column([
            ft.Text("EcoDrones", size=24, weight=ft.FontWeight.BOLD, color="white"),
            ft.Text("Monitoreo Táctico: Área Capilla del Monte / Cerro Uritorco", size=12, color="#aaaaaa"),
        ]),
        ft.Container(expand=True),
        ft.ElevatedButton(
            "Neo4j Browser",
            icon=ft.Icons.HUB,
            on_click=open_neo4j,
            bgcolor="#1565c0",
            color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
        ),
        ft.Row([status_dot, status_text], spacing=8),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

    route_container = ft.Container(
        content=ft.Column([ft.Text("Cargando mapa de recorrido...", size=12, color="#999")]),
        bgcolor="#181832", border=ft.border.Border.all(1, "#333"), border_radius=16, padding=16, expand=True,
    )

    main_tab = ft.Container(
        content=ft.Column([
            ft.Container(content=drone_cards, bgcolor="#13172f", border=ft.border.Border.all(1, "#222"), border_radius=18, padding=16, expand=True),
        ], spacing=12, expand=True),
        expand=True,
    )

    alerts_list_column = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    alerts_tab = ft.Container(
        content=ft.Column([
            ft.Text("LISTADO DE ALERTAS", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(color="#2a2a3a"),
            ft.Container(content=alerts_list_column, bgcolor="#181832", border=ft.border.Border.all(1, "#333"), border_radius=12, padding=15, expand=True),
        ], spacing=10, expand=True),
        expand=True,
    )

    zones_list = [
        {"id": "ZONA_001", "nombre": "Los Terrones", "color": "#e67e22", "bioma": "Sierras", "desc": "Formaciones rocosas."},
        {"id": "ZONA_004", "nombre": "Dique El Cajón", "color": "#3498db", "bioma": "Embalse", "desc": "Reserva de agua."},
        {"id": "ZONA_002", "nombre": "Centro Capilla", "color": "#1abc9c", "bioma": "Urbano", "desc": "Área residencial."},
        {"id": "ZONA_005", "nombre": "Paso del Indio", "color": "#9b59b6", "bioma": "Cañadón", "desc": "Acceso difícil."},
        {"id": "ZONA_003", "nombre": "Base Uritorco", "color": "#f1c40f", "bioma": "Monte", "desc": "Acceso principal."},
        {"id": "ZONA_006", "nombre": "Cerro Uritorco", "color": "#27ae60", "bioma": "Cumbre", "desc": "Punto más alto."},
    ]

    zone_rects = []
    zone_descriptions = []
    fire_icons_topology = {}

    for z in zones_list:
        f_icon = ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="orange", size=25, visible=False)
        fire_icons_topology[z["id"]] = f_icon
        zone_rects.append(
            ft.Container(
                content=ft.Column([
                    f_icon, 
                    ft.Text(z["id"].replace("ZONA_00", "Zona "), weight="bold", color="white", size=14),
                    ft.Text(z.get("bioma", ""), size=9, color="white70"),
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=z["color"], opacity=0.6, expand=True, border=ft.border.Border.all(1, "white24")
            )
        )
        zone_descriptions.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(width=12, height=12, bgcolor=z["color"], border_radius=3), 
                    ft.Column([
                        ft.Text(f"{z['id'].replace('ZONA_00', 'Zona ')} - {z['nombre']}", weight="bold", size=13),
                        ft.Text(z.get("desc", ""), size=11, color="#aaaaaa"),
                    ], spacing=2, expand=True)
                ], vertical_alignment=ft.CrossAxisAlignment.START),
                padding=12, bgcolor="#141426", border_radius=10, border=ft.border.Border.all(1, "#333")
            )
        )

    quadrants = [
        ft.Container(content=ft.Column([zone_rects[0], zone_rects[1]], spacing=0), expand=True, border=ft.border.Border(right=ft.border.BorderSide(2, "white54"))),
        ft.Container(content=ft.Column([zone_rects[2], zone_rects[3]], spacing=0), expand=True, border=ft.border.Border(right=ft.border.BorderSide(2, "white54"))),
        ft.Container(content=ft.Column([zone_rects[4], zone_rects[5]], spacing=0), expand=True),
    ]

    zones_tab = ft.Container(
        content=ft.Row([
            ft.Column([ft.Text("TOPOLOGÍA TÁCTICA (GRILLA 3x2)", size=12), ft.Container(content=ft.Row(quadrants, spacing=0), height=350, border_radius=16, clip_behavior=ft.ClipBehavior.ANTI_ALIAS)], expand=3),
            ft.Column([ft.Text("DETALLE BIOMAS", size=12), ft.Column(zone_descriptions, scroll=ft.ScrollMode.ADAPTIVE, spacing=10)], expand=2),
        ], spacing=20, expand=True), expand=True
    )

    dron_alpha_sat = ft.Container(animate_position=1000)
    dron_beta_sat = ft.Container(animate_position=1000)
    dron_gamma_sat = ft.Container(animate_position=1000)

    # Capa de destello rojo para emergencias en Zona 3
    flash_zona_3 = ft.Container(bgcolor="red", opacity=0.0, expand=True, animate_opacity=300)

    # Contenedores dinámicos para múltiples fuegos y humos en Zona 3
    fuegos_z3_container = ft.Stack(width=150, height=100, left=490, top=50)
    humos_z3_container = ft.Stack(width=150, height=100, left=485, top=30)
    
    # Los demás iconos se mantienen individuales por si acaso, pero Z3 es un Stack
    fire_icons_sat = {
        "ZONA_001": ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=30, left=60, top=80, visible=False),
        "ZONA_004": ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=30, left=60, top=300, visible=False),
        "ZONA_002": ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=30, left=280, top=80, visible=False),
        "ZONA_005": ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=30, left=280, top=300, visible=False),
        "ZONA_003": fuegos_z3_container, # Ahora es un Stack dinámico
        "ZONA_006": ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=30, left=480, top=300, visible=False),
    }

    smoke_icons_sat = {
        "ZONA_003": humos_z3_container # Ahora el humo también es un contenedor dinámico
    }

    # Etiquetas de Nombres de Zona sobre el mapa satelital (Coordenadas proyectadas)
    etiquetas_zonas = [
        # Columna Izquierda (Oeste - Agua)
        ft.Text("Zona 1 - Terrones", color="white60", size=11, weight="bold", left=80, top=100),
        ft.Text("Zona 4 - Dique", color="white60", size=11, weight="bold", left=80, top=320),
        # Columna Centro (Casco Urbano)
        ft.Text("Zona 2 - Centro", color="white60", size=11, weight="bold", left=300, top=100),
        ft.Text("Zona 5 - Indio", color="white60", size=11, weight="bold", left=300, top=320),
        # Columna Derecha (Este - Montañas)
        ft.Text("Zona 3 - Base", color="white60", size=11, weight="bold", left=530, top=100),
        ft.Text("Zona 6 - Cerro", color="white60", size=11, weight="bold", left=500, top=320),
    ]

    divisores_sat = [
        ft.Container(left=216, top=0, width=1, height=450, bgcolor="white24"),
        ft.Container(left=433, top=0, width=1, height=450, bgcolor="white24"),
        ft.Container(left=0, top=225, width=650, height=1, bgcolor="white24"),
    ]

    # Leyenda Operativa para el Mapa
    leyenda_mapa = ft.Container(
        content=ft.Column([
            ft.Text("LEYENDA TÁCTICA", size=11, weight="bold", color="#555577"),
            ft.Row([ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=16), ft.Text("Incendio Activo", size=10)]),
            ft.Row([ft.Icon(ft.Icons.CLOUD, color="#555555", size=16), ft.Text("Pluma de Humo", size=10)]),
            ft.Row([
                ft.Container(width=14, height=14, border=ft.border.Border.all(2, "#4b0082"), border_radius=7),
                ft.Text("CO2 Muy Alto (Violeta)", size=10)
            ]),
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.ADD, size=8, color="white"),
                    width=14, height=14, border=ft.border.Border.all(1, "white54"), border_radius=7
                ),
                ft.Text("Aro: Nivel de CO2", size=10)
            ]),
        ], spacing=5),
        padding=10,
        bgcolor="#12122b",
        border_radius=10,
    )

    simulacion_sat_tab = ft.Container(
        content=ft.Column([
            ft.Text("MAPA OPERATIVO TÁCTICO", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.Container(
                    content=ft.Stack([
                        ft.Image(src=mapa_sat_url, fit="cover", width=650, height=450),
                        flash_zona_3,
                        *divisores_sat,
                        *etiquetas_zonas,
                        *smoke_icons_sat.values(),
                        *[v for k,v in fire_icons_sat.items() if k != "ZONA_003"],
                        fuegos_z3_container,
                        dron_alpha_sat,
                        dron_beta_sat,
                        dron_gamma_sat
                    ]),
                    width=650,
                    height=450,
                    border_radius=15,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    border=ft.border.Border.all(1, "#333355"),
                ),
                ft.Column([
                    ft.Text("ESTADO DE MISIÓN", size=12, weight="bold", color="#555577"),
                    ft.Row([ft.Container(width=10, height=10, bgcolor="#4cd964", border_radius=5), ft.Text("ALPHA: Patrullando", size=12)]),
                    ft.Row([ft.Container(width=10, height=10, bgcolor="#ff9500", border_radius=5), ft.Text("BETA: Respaldo", size=12)]),
                    ft.Row([ft.Container(width=10, height=10, bgcolor="#3498db", border_radius=5), ft.Text("GAMMA: Patrullando", size=12)]),
                    ft.Divider(color="#2a2a3a"),
                    leyenda_mapa,
                ], spacing=10, width=200)
            ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=10, expand=True),
        bgcolor="#0f1225",
        padding=20,
        expand=True,
    )

    # ══════ PESTAÑA DE ANÁLISIS DE PROPAGACIÓN (Neo4j en tiempo real) ══════
    propagacion_content = ft.Column(spacing=12, scroll=ft.ScrollMode.ADAPTIVE, expand=True)

    # Mini-grilla visual de zonas con indicador de riesgo en tiempo real
    zona_grid_cells = {}
    zona_grid_labels = {}
    zonas_info_grid = [
        ("ZONA_001", "Z1\nTerrones"), ("ZONA_002", "Z2\nCentro"), ("ZONA_003", "Z3\nUritorco"),
        ("ZONA_004", "Z4\nDique"), ("ZONA_005", "Z5\nIndio"), ("ZONA_006", "Z6\nCerro"),
    ]
    for zid, zlabel in zonas_info_grid:
        zona_grid_labels[zid] = ft.Text(zlabel, size=10, color="white", text_align=ft.TextAlign.CENTER, weight="bold")
        zona_grid_cells[zid] = ft.Container(
            content=ft.Column([
                zona_grid_labels[zid],
            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e3a1e",
            border=ft.border.Border.all(1, "#333"),
            border_radius=6,
            width=110, height=60,
            alignment=ft.Alignment(0, 0),
        )

    grilla_visual = ft.Container(
        content=ft.Column([
            ft.Text("MAPA DE RIESGO EN TIEMPO REAL (Neo4j)", size=11, weight="bold", color="#77aaff"),
            ft.Row([
                zona_grid_cells["ZONA_001"], zona_grid_cells["ZONA_002"], zona_grid_cells["ZONA_003"],
            ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                zona_grid_cells["ZONA_004"], zona_grid_cells["ZONA_005"], zona_grid_cells["ZONA_006"],
            ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                ft.Container(width=12, height=12, bgcolor="#2e7d32", border_radius=3),
                ft.Text("Normal", size=9, color="#aaa"),
                ft.Container(width=12, height=12, bgcolor="#f9a825", border_radius=3),
                ft.Text("Elevado", size=9, color="#aaa"),
                ft.Container(width=12, height=12, bgcolor="#e65100", border_radius=3),
                ft.Text("Propagación", size=9, color="#aaa"),
                ft.Container(width=12, height=12, bgcolor="#b71c1c", border_radius=3),
                ft.Text("Incendio", size=9, color="#aaa"),
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor="#0d1520",
        border=ft.border.Border.all(1, "#2a3a4a"),
        border_radius=10,
        padding=12,
    )

    propagacion_tab = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.WHATSHOT, color="#ff6b35", size=28),
                ft.Text("ANÁLISIS DE PROPAGACIÓN", size=18, weight=ft.FontWeight.BOLD, color="white"),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text("DATOS EN VIVO DESDE NEO4J", size=10, color="#66bb6a", weight="bold"),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border=ft.border.Border.all(1, "#66bb6a"),
                    border_radius=12,
                ),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(
                content=ft.Column([
                    grilla_visual,
                    ft.Divider(color="#2a2a3a"),
                    propagacion_content,
                ], spacing=10),
                bgcolor="#181832",
                border=ft.border.Border.all(1, "#333"),
                border_radius=12,
                padding=15,
                expand=True,
            ),
        ], spacing=10, expand=True, scroll=ft.ScrollMode.ADAPTIVE),
        expand=True,
    )

    # Versión de pestañas con máxima compatibilidad para Flet
    tabs = ft.Tabs(
        length=4,
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Monitoreo"),
                        ft.Tab(label="Alertas"),
                        ft.Tab(label="Mapa Operativo"),
                        ft.Tab(label="🔥 Propagación"),
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        main_tab,
                        alerts_tab,
                        simulacion_sat_tab,
                        propagacion_tab,
                    ],
                ),
            ],
        ),
    )

    page.add(
        ft.Column([
            header,
            ft.Divider(color="#252a42"),
            tabs,
        ], spacing=18, expand=True),
    )

    # --- ESTADO DE SESIÓN ---
    app_start_time = datetime.now(timezone.utc)
    zonas_descubiertas = set() # Memoria persistente de incendios detectados
    flicker_state = [True] # Estado para la animación de parpadeo
    cantidad_fuegos_z3 = [1] # Contador interno para el crecimiento del fuego
    ultimo_incendio_data = [None] # Estado persistente del último incendio para la pestaña de propagación

    def refresh_dashboard(latest):
        # Función interna para proyectar GPS a los 650x450 px del mapa satelital
        def project_to_sat(lon, lat):
            width, height = 650, 450
            
            x = (lon - GEO_LON_MIN) / (GEO_LON_MAX - GEO_LON_MIN) * width
            y = (GEO_LAT_MAX - lat) / (GEO_LAT_MAX - GEO_LAT_MIN) * height
            return x, y

        drone_cards.controls.clear()
        for drone_id in DRONES:
            doc = latest.get(drone_id)
            
            # Actualizar posición en el Mapa Satelital si hay coordenadas
            if doc:
                coords = doc.get("posicion_geografica", {}).get("coordinates", [None, None])
                if coords[0] is not None and coords[1] is not None:
                    x, y = project_to_sat(coords[0], coords[1])
                    
                    # Obtener datos de sensores para replicar el estilo de la pestaña Recorrido
                    lec = doc.get("lecturas_sensores", {})
                    temp = lec.get("temperatura_c", 20)
                    co2 = lec.get("co2_ppm", 400)
                    
                    # Cálculo de colores (Lógica de la pestaña Recorrido)
                    r_val = min(255, max(0, int((temp - 20) / 40 * 255)))
                    g_val = min(255, max(0, int((60 - temp) / 40 * 255)))
                    t_color = f"#{r_val:02x}{g_val:02x}00"
                    
                    if co2 < 600: c_color = "#2ecc71"
                    elif co2 < 1000: c_color = "#f1c40f"
                    elif co2 < 1500: c_color = "#e67e22"
                    else: c_color = "#4b0082" # Violeta Oscuro para CO2 Crítico
                    
                    accent = "#4cd964" if drone_id == "DRON_ALPHA" else "#ff9500"
                    
                    # --- LÓGICA DE ARO DINÁMICO SEGÚN CO2 ---
                    # El tamaño base es 30, y crece hasta 70 si el CO2 es muy alto
                    c_size = 30 + (min(co2, 2000) - 400) / 1600 * 40
                    
                    # Marcadores dinámicos sobre el dron según lectura actual
                    fuego_dron = ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=20, top=-20, left=c_size/2-10) if temp > 45 else ft.Container()
                    humo_dron = ft.Icon(ft.Icons.CLOUD, color="#555555", size=22, top=-25, left=c_size/2+5) if co2 > 800 else ft.Container()

                    # Actualizar el contenido visual del marcador
                    new_marker = ft.Stack([
                        ft.Container(width=c_size, height=c_size, border_radius=c_size/2, border=ft.border.Border.all(2, c_color), animate=500),
                        ft.Container(width=12, height=12, border_radius=6, bgcolor=t_color, border=ft.border.Border.all(2, accent), left=c_size/2-6, top=c_size/2-6),
                        ft.Text(drone_id.split("_")[1], size=10, weight="bold", color="white", top=-15, left=c_size/2-15),
                        fuego_dron,
                        humo_dron
                    ])

                    if drone_id == "DRON_ALPHA":
                        dron_alpha_sat.left, dron_alpha_sat.top = x - c_size/2, y - c_size/2
                        dron_alpha_sat.content = new_marker
                    elif drone_id == "DRON_BETA":
                        dron_beta_sat.left, dron_beta_sat.top = x - c_size/2, y - c_size/2
                        dron_beta_sat.content = new_marker
                    elif drone_id == "DRON_GAMMA":
                        dron_gamma_sat.left, dron_gamma_sat.top = x - c_size/2, y - c_size/2
                        dron_gamma_sat.content = new_marker

            if doc:
                drone_cards.controls.append(build_drone_card(doc))
            else:
                drone_cards.controls.append(
                    ft.Container(
                        content=ft.Text(f"No hay datos para {drone_id}", size=12, color="#999"),
                        bgcolor="#181832",
                        border=ft.border.Border.all(1, "#333"),
                        border_radius=16,
                        padding=ft.Padding.symmetric(horizontal=18, vertical=18),
                        expand=True,
                    )
                )

        alpha_docs = list(col_telemetria.find({"drone_id": "DRON_ALPHA"}).sort([("_id", -1)]).limit(20))
        beta_docs = list(col_telemetria.find({"drone_id": "DRON_BETA"}).sort([("_id", -1)]).limit(20))
        gamma_docs = list(col_telemetria.find({"drone_id": "DRON_GAMMA"}).sort([("_id", -1)]).limit(20))
        route_map = build_route_map(list(reversed(alpha_docs)), list(reversed(beta_docs)), list(reversed(gamma_docs)))
        route_container.content = route_map

        # --- ACTUALIZACIÓN DINÁMICA DE LA PESTAÑA DE ALERTAS ---
        try:
            alerts_docs = list(col_alertas.find().sort([("_id", -1)]).limit(20))
            now = datetime.now(timezone.utc)
            
            # Identificar zonas con incendios ACTIVOS (Solo alertas de los últimos 10 segundos)
            active_fire_zones = set()
            current_session_alerts = []
            history_alerts = []

            for a in alerts_docs:
                ts_str = a.get("timestamp_alerta")
                if ts_str:
                    try:
                        # Limpiamos el formato del timestamp para comparar
                        ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                        
                        # CLASIFICACIÓN: ¿Es de esta sesión o antigua?
                        if ts_dt > app_start_time:
                            current_session_alerts.append(a)
                            # Solo las alertas de esta sesión activan el estado CRÍTICO visual
                            if (now - ts_dt).total_seconds() < 10 and a.get("cod_zona") == "ZONA_003":
                                active_fire_zones.add("ZONA_003")
                        else:
                            history_alerts.append(a)
                    except Exception:
                        continue

            # --- EFECTO DE DESTELLO EN ZONA 3 ---
            if "ZONA_003" in active_fire_zones:
                flash_zona_3.opacity = 0.3 if flicker_state[0] else 0.0
            else:
                flash_zona_3.opacity = 0.0

            # Identificar en qué zonas están los drones actualmente
            drone_zones = {latest[d].get("cod_zona") for d in DRONES if latest.get(d)}

            # LÓGICA DE PERSISTENCIA: Si el dron está en una zona con fuego, la "descubre"
            for zid in active_fire_zones:
                if zid == "ZONA_003" and zid in drone_zones:
                    zonas_descubiertas.add("ZONA_003")

            # Actualizar iconos de fuego y humo
            flicker_state[0] = not flicker_state[0]
            scale_val = 1.2 if flicker_state[0] else 0.8

            # Lógica especial para multiplicar fuegos en Zona 3
            if "ZONA_003" in active_fire_zones:
                if flicker_state[0] and len(fuegos_z3_container.controls) < 8:
                    # Añadimos un fuego y un humo nuevo desplazados a la izquierda
                    offset_x = len(fuegos_z3_container.controls) * 15
                    
                    # Agregar Fuego
                    fuegos_z3_container.controls.append(
                        ft.Icon(ft.Icons.LOCAL_FIRE_DEPARTMENT, color="#ff4500", size=30, 
                               left=50 - offset_x, top=30 + random.randint(-10, 10), animate_scale=600)
                    )
                    # Agregar Humo (un poco más grande y arriba que el fuego)
                    humos_z3_container.controls.append(
                        ft.Icon(ft.Icons.CLOUD, color="#555555", size=45, 
                               left=45 - offset_x, top=15 + random.randint(-15, 15), animate_opacity=1000)
                    )

            for zid, icon in fire_icons_sat.items():
                if zid != "ZONA_003":
                    icon.visible = False

            alert_rows = []

            if not alerts_docs:
                # Si no hay datos, mostramos un mensaje simple y claro
                alert_rows.append(
                    ft.Container(
                        content=ft.Text("🔍 No se han detectado parámetros anómalos aún...", color="#888888", size=14),
                        padding=30,
                        alignment=ft.Alignment(0, 0)
                    )
                )
            else:
                # --- SEPARACIÓN DE ALERTAS: NUEVAS VS HISTORIAL ---
                session_alerts = []
                history_alerts = []
                
                for a in alerts_docs:
                    # Clasificación por tiempo de sesión
                    # Extraemos datos del documento de alerta
                    ts = format_timestamp(a.get("timestamp_alerta") or a.get("timestamp") or "-")
                    drone_id = a.get("drone_id", "-")
                    zona = a.get("cod_zona", "-")
                    temp = a.get("temperatura_registrada", 0)
                    co2 = a.get("co2_registrado", 0)
                    
                    # Extraemos el análisis de Neo4j si existe para mostrar qué especies sufren
                    analisis = a.get("analisis_neo4j", {})
                    especies = analisis.get("fauna_local", [])
                    propagacion = analisis.get("zonas_en_cascada", [])
                    viento_dir = analisis.get("rumbo_propagacion", "N/A")

                    # Filtramos valores None para evitar el error de str instance
                    ts_str = a.get("timestamp_alerta")
                    is_new = False
                    if ts_str:
                        try:
                            ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            is_new = ts_dt > app_start_time
                        except:
                            pass

                    # Filtramos valores None para evitar el error de str instance
                    texto_especies = ", ".join([str(e['comun']) for e in especies if e.get('comun')]) if especies else "Monitoreando..."
                    
                    # --- SISTEMA DE 3 NIVELES DE ALERTA ---
                    if temp > 55:
                        severity_label, severity_color, severity_bg = "CRÍTICO", "#ff4d4d", "#331111"
                    elif temp > 45:
                        severity_label, severity_color, severity_bg = "ELEVADO", "#ff9500", "#332211"
                    else:
                        severity_label, severity_color, severity_bg = "PREVENTIVO", "#f1c40f", "#222211"

                    card_bgcolor = "#1c1c3a" if is_new else "#121226"
                    border_color = "#333355"
                    opacity = 1.0 if is_new else 0.6

                    card = ft.Container(
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE, color=severity_color, size=24),
                                            ft.Text(drone_id, size=22, weight="bold", color="white"),
                                            ft.Container(
                                                content=ft.Text(severity_label, size=13, weight="bold", color=severity_color),
                                                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                                border=ft.border.Border.all(1, severity_color),
                                                border_radius=6,
                                                bgcolor=severity_bg,
                                            ),
                                            ft.Container(expand=True),
                                            ft.Text(f"{'NUEVA' if is_new else 'HISTÓRICA'} | {ts}", size=11, color="#777777"),
                                        ]
                                    ),
                                    ft.Divider(color="#222244", height=1),
                                    ft.Row(
                                        [
                                            ft.Column(
                                                [
                                                    ft.Text("LOCALIZACIÓN", size=13, color="#666666", weight="bold"),
                                                    ft.Text(f"{zona}", size=24, color="#99bbff", weight="w500"),
                                                ], spacing=2, expand=1
                                            ),
                                            alert_sensor_box("TEMPERATURA", f"{temp}°C", "", severity_color),
                                            alert_sensor_box("CO2", f"{co2}", "ppm", co2_color(co2)),
                                        ], spacing=15
                                    ),
                                    ft.Container(
                                        content=ft.Column(
                                            [
                                                ft.Row([
                                                    ft.Icon(ft.Icons.G_TRANSLATE_ROUNDED, size=18, color="#ff9999"),
                                                    ft.Text("IMPACTO BIOLÓGICO Y PROPAGACIÓN", size=12, weight="bold", color="#ff9999"),
                                                ], spacing=5),
                                                ft.Text(f"Fauna en riesgo: {texto_especies}", size=16, color="#cccccc"),
                                                ft.Text(
                                                    f"Propagación detectada hacia el {viento_dir} (Zonas en riesgo: {len(propagacion)})" if propagacion else "Sin riesgo inminente de propagación.",
                                                    size=10, color="#888888", italic=True
                                                ),
                                            ], spacing=4
                                        ),
                                        bgcolor="#13132b",
                                        padding=10,
                                        border_radius=8,
                                    ),
                                ], spacing=10
                            ),
                            bgcolor=card_bgcolor,
                            border=ft.border.Border.all(1, border_color),
                            border_radius=12,
                            padding=16,
                            margin=ft.Margin.only(bottom=5),
                            opacity=opacity,
                        )
                    
                    if is_new:
                        session_alerts.append(card)
                    else:
                        history_alerts.append(card)

                if session_alerts:
                    alert_rows.append(ft.Text("🔴 ALERTAS EN ESTA SESIÓN", size=14, weight="bold", color="#ff4d4d"))
                    alert_rows.extend(session_alerts)
                if history_alerts:
                    alert_rows.append(ft.Container(height=10))
                    alert_rows.append(ft.Text("⏳ HISTORIAL ANTERIOR", size=14, weight="bold", color="#777777"))
                    alert_rows.extend(history_alerts)

            alerts_list_column.controls = alert_rows
        except Exception as e:
            print(f"Error al procesar alertas de MongoDB: {e}")

        status_text.value = f"Última actualización: {datetime.now().strftime('%H:%M:%S')}"
        status_text.color = "#bbbbbb"
        status_dot.bgcolor = "#2ecc71"

        # ══════ ACTUALIZACIÓN DE LA PESTAÑA DE PROPAGACIÓN (Neo4j) — PERSISTENTE + ACCIONES ══════
        try:
            hottest_drone = None
            hottest_temp = 0
            hottest_zona = None
            hottest_viento_dir = 0

            for drone_id in DRONES:
                doc = latest.get(drone_id)
                if doc:
                    t = doc.get("lecturas_sensores", {}).get("temperatura_c", 0)
                    if t > hottest_temp:
                        hottest_temp = t
                        hottest_drone = drone_id
                        hottest_zona = doc.get("cod_zona")
                        hottest_viento_dir = doc.get("lecturas_sensores", {}).get("viento_direccion_grados", 90)

            # Si hay incendio activo (>45°C), actualizamos el estado persistente
            if hottest_temp > 45 and hottest_zona:
                ultimo_incendio_data[0] = {
                    "drone": hottest_drone,
                    "temp": hottest_temp,
                    "zona": hottest_zona,
                    "viento_dir": hottest_viento_dir,
                    "timestamp": datetime.now(timezone.utc),
                    "activo": True,
                }
            elif ultimo_incendio_data[0]:
                # El incendio ya no está activo, pero mantenemos el registro
                ultimo_incendio_data[0]["activo"] = False
                ultimo_incendio_data[0]["temp_actual"] = hottest_temp

            propagacion_rows = []
            incendio = ultimo_incendio_data[0]

            if incendio and incendio.get("zona"):
                rumbo = calcular_rumbo_desde_grados(incendio["viento_dir"])
                analisis = query_propagacion_neo4j(incendio["zona"], rumbo)
                is_activo = incendio.get("activo", False)
                elapsed = (datetime.now(timezone.utc) - incendio["timestamp"]).total_seconds()

                # Etiqueta de estado
                if is_activo:
                    estado_text = "🔥 INCENDIO ACTIVO"
                    temp_color = "#e74c3c"
                    border_main = "#e74c3c"
                else:
                    estado_text = f"⏱️ ÚLTIMO INCENDIO (hace {int(elapsed)}s)"
                    temp_color = "#ff9500"
                    border_main = "#ff9500"

                if analisis:
                    # ── CABECERA ZONA DE ORIGEN ──
                    propagacion_rows.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.LOCATION_ON, color="#ff6b35", size=22),
                                    ft.Text(f"ZONA: {analisis['zona_origen_nombre']} ({incendio['zona']})", size=16, weight="bold", color="white"),
                                    ft.Container(expand=True),
                                    ft.Container(
                                        content=ft.Text(estado_text, size=11, color=temp_color, weight="bold"),
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                        border=ft.border.Border.all(1, temp_color),
                                        border_radius=8,
                                    ),
                                ]),
                                ft.Row([
                                    ft.Text(f"Bioma: {analisis['zona_origen_bioma']}", size=12, color="#aaa"),
                                    ft.Text(f"  |  {analisis['zona_origen_sup']} ha", size=12, color="#aaa"),
                                    ft.Text(f"  |  Detectó: {incendio['drone']}", size=12, color="#aaa"),
                                ]),
                                ft.Row([
                                    ft.Text(f"🌡️ Pico: {round(incendio['temp'], 1)}°C", size=14, color=temp_color, weight="bold"),
                                    ft.Text(f"  |  Actual: {round(hottest_temp, 1)}°C", size=12, color="#aaa"),
                                    ft.Text(f"  |  💨 {round(incendio['viento_dir'])}° → {rumbo}", size=12, color="#77aaff"),
                                ]),
                            ], spacing=6),
                            bgcolor="#1a1a3a",
                            border=ft.border.Border.all(2, border_main),
                            border_radius=10,
                            padding=14,
                        )
                    )

                    # ── FAUNA EN RIESGO DIRECTO ──
                    fauna_local = [f for f in analisis["fauna_local"] if f.get("comun")]
                    if fauna_local:
                        fauna_chips = []
                        for f in fauna_local:
                            iucn = f.get("iucn", "?")
                            iucn_color = "#e74c3c" if iucn in ("VU", "EN", "CR") else "#f39c12" if iucn == "NT" else "#2ecc71"
                            fauna_chips.append(
                                ft.Container(
                                    content=ft.Row([
                                        ft.Text(f"🐾 {f['comun']}", size=12, color="white"),
                                        ft.Container(
                                            content=ft.Text(iucn, size=9, color=iucn_color, weight="bold"),
                                            padding=ft.Padding.symmetric(horizontal=5, vertical=1),
                                            border=ft.border.Border.all(1, iucn_color),
                                            border_radius=6,
                                        ),
                                    ], spacing=6),
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                                    bgcolor="#222244",
                                    border_radius=8,
                                )
                            )
                        propagacion_rows.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("🐾 FAUNA EN RIESGO DIRECTO", size=13, weight="bold", color="#ff9999"),
                                    ft.Row(fauna_chips, wrap=True, spacing=8),
                                ], spacing=8),
                                bgcolor="#151530", border_radius=8, padding=12,
                            )
                        )

                    # ── SALTO 1 ──
                    if analisis.get("salto1_cod"):
                        fauna1 = [f for f in analisis["salto1_fauna"] if f.get("comun")]
                        fauna1_text = ", ".join([f"{f['comun']} [{f.get('iucn','')}]" for f in fauna1]) if fauna1 else "Sin fauna registrada"
                        prob1 = analisis.get("salto1_prob", 0) or 0
                        propagacion_rows.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Icon(ft.Icons.ARROW_FORWARD, color="#ff9500", size=20),
                                        ft.Text(f"SALTO 1: {analisis['salto1_nombre']}", size=14, weight="bold", color="#ff9500"),
                                        ft.Text(f"({analisis.get('salto1_bioma', '')})", size=11, color="#888"),
                                        ft.Container(expand=True),
                                        ft.Text(f"Prob: {round(prob1*100)}%", size=12, color="#ff9500", weight="bold"),
                                    ]),
                                    ft.Text(f"Distancia: {analisis.get('salto1_dist', '?')} km | Fauna: {fauna1_text}", size=11, color="#ccc"),
                                    ft.Container(width=max(20, prob1 * 400), height=6, bgcolor="#ff9500", border_radius=3),
                                ], spacing=6),
                                bgcolor="#1e1e38", border=ft.border.Border.all(1, "#ff9500"), border_radius=10, padding=12,
                            )
                        )

                    # ── SALTO 2 ──
                    if analisis.get("salto2_cod"):
                        fauna2 = [f for f in analisis["salto2_fauna"] if f.get("comun")]
                        fauna2_text = ", ".join([f"{f['comun']} [{f.get('iucn','')}]" for f in fauna2]) if fauna2 else "Sin fauna registrada"
                        prob1 = analisis.get("salto1_prob", 0) or 0
                        prob2 = analisis.get("salto2_prob", 0) or 0
                        prob_acum = prob1 * prob2
                        dist_total = round((analisis.get('salto1_dist', 0) or 0) + (analisis.get('salto2_dist', 0) or 0), 1)
                        propagacion_rows.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Icon(ft.Icons.ARROW_FORWARD, color="#f1c40f", size=20),
                                        ft.Icon(ft.Icons.ARROW_FORWARD, color="#f1c40f", size=20),
                                        ft.Text(f"SALTO 2: {analisis['salto2_nombre']}", size=14, weight="bold", color="#f1c40f"),
                                        ft.Container(expand=True),
                                        ft.Text(f"Prob: {round(prob_acum*100)}%", size=12, color="#f1c40f", weight="bold"),
                                    ]),
                                    ft.Text(f"Distancia total: {dist_total} km | Fauna: {fauna2_text}", size=11, color="#ccc"),
                                    ft.Container(width=max(20, prob_acum * 400), height=6, bgcolor="#f1c40f", border_radius=3),
                                ], spacing=6),
                                bgcolor="#1e1e38", border=ft.border.Border.all(1, "#f1c40f"), border_radius=10, padding=12,
                            )
                        )

                    # ══════ PANEL DE ACCIONES DE RESPUESTA ══════
                    acciones = []
                    salto1_nombre = analisis.get("salto1_nombre", "zona vecina")

                    # Acción 1: Redirigir dron
                    acciones.append(ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.FLIGHT, color="#3498db", size=22),
                            ft.Column([
                                ft.Text("REDIRIGIR DRON_GAMMA", size=12, weight="bold", color="#3498db"),
                                ft.Text(f"Enviar dron de patrullaje a vigilar {salto1_nombre} para confirmar propagación.", size=10, color="#aaa"),
                            ], spacing=2, expand=True),
                            ft.Container(
                                content=ft.Text("RECOMENDADO", size=9, color="#3498db", weight="bold"),
                                padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                border=ft.border.Border.all(1, "#3498db"), border_radius=6,
                            ),
                        ], spacing=10),
                        bgcolor="#0d1b2a", border=ft.border.Border.all(1, "#3498db"), border_radius=8, padding=12,
                    ))

                    # Acción 2: Intensificar monitoreo
                    acciones.append(ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.RADAR, color="#9b59b6", size=22),
                            ft.Column([
                                ft.Text("INTENSIFICAR MONITOREO", size=12, weight="bold", color="#9b59b6"),
                                ft.Text(f"Reducir intervalo de lectura a 0.5s en {incendio['zona']} y zonas adyacentes.", size=10, color="#aaa"),
                            ], spacing=2, expand=True),
                        ], spacing=10),
                        bgcolor="#0d1b2a", border=ft.border.Border.all(1, "#9b59b6"), border_radius=8, padding=12,
                    ))

                    # Acción 3: Evacuación de fauna
                    if fauna_local:
                        sp_criticas = [f['comun'] for f in fauna_local if f.get('iucn') in ('VU', 'NT', 'EN', 'CR')]
                        if sp_criticas:
                            acciones.append(ft.Container(
                                content=ft.Row([
                                    ft.Icon(ft.Icons.PETS, color="#e74c3c", size=22),
                                    ft.Column([
                                        ft.Text("PROTOCOLO EVACUACIÓN FAUNA", size=12, weight="bold", color="#e74c3c"),
                                        ft.Text(f"Especies prioritarias: {', '.join(sp_criticas)}. Alertar brigadas de rescate.", size=10, color="#aaa"),
                                    ], spacing=2, expand=True),
                                    ft.Container(
                                        content=ft.Text("URGENTE", size=9, color="#e74c3c", weight="bold"),
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        border=ft.border.Border.all(1, "#e74c3c"), border_radius=6,
                                    ),
                                ], spacing=10),
                                bgcolor="#1a0d0d", border=ft.border.Border.all(1, "#e74c3c"), border_radius=8, padding=12,
                            ))

                    # Acción 4: Cortafuegos preventivo
                    acciones.append(ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SHIELD, color="#27ae60", size=22),
                            ft.Column([
                                ft.Text("CORTAFUEGOS PREVENTIVO", size=12, weight="bold", color="#27ae60"),
                                ft.Text(f"Activar brigada terrestre entre {analisis['zona_origen_nombre']} y {salto1_nombre} ({analisis.get('salto1_dist', '?')} km).", size=10, color="#aaa"),
                            ], spacing=2, expand=True),
                        ], spacing=10),
                        bgcolor="#0d1a0d", border=ft.border.Border.all(1, "#27ae60"), border_radius=8, padding=12,
                    ))

                    # Acción 5: Notificar autoridades
                    acciones.append(ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CAMPAIGN, color="#f39c12", size=22),
                            ft.Column([
                                ft.Text("NOTIFICAR BOMBEROS / DEFENSA CIVIL", size=12, weight="bold", color="#f39c12"),
                                ft.Text(f"Enviar coordenadas GPS del foco y predicción de propagación a central de emergencias.", size=10, color="#aaa"),
                            ], spacing=2, expand=True),
                        ], spacing=10),
                        bgcolor="#1a1500", border=ft.border.Border.all(1, "#f39c12"), border_radius=8, padding=12,
                    ))

                    propagacion_rows.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Divider(color="#333"),
                                ft.Row([
                                    ft.Icon(ft.Icons.EMERGENCY, color="#ff6b35", size=20),
                                    ft.Text("ACCIONES DE RESPUESTA RECOMENDADAS", size=14, weight="bold", color="#ff6b35"),
                                ], spacing=8),
                                ft.Text("Medidas sugeridas por el sistema basadas en el análisis de propagación:", size=11, color="#888"),
                                *acciones,
                            ], spacing=10),
                            padding=ft.Padding.only(top=10),
                        )
                    )

                    # Footer de integración
                    propagacion_rows.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.INFO_OUTLINE, color="#555", size=14),
                                ft.Text("MongoDB (detección) → Neo4j (propagación + fauna) | Análisis persistente hasta nuevo evento", size=10, color="#555"),
                            ], spacing=6),
                            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
                        )
                    )
                else:
                    propagacion_rows.append(ft.Text("⚠️ No se pudo consultar Neo4j. Verificá que el contenedor esté activo.", size=12, color="#ff9500"))
            else:
                propagacion_rows.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.CHECK_CIRCLE, color="#2ecc71", size=40),
                            ft.Text("Sin incendios registrados en esta sesión", size=16, color="#2ecc71", weight="bold"),
                            ft.Text("El análisis de propagación se activará automáticamente cuando se detecte temperatura > 45°C.", size=12, color="#888"),
                            ft.Text(f"Dron más caliente: {hottest_drone or '-'} a {round(hottest_temp,1)}°C", size=11, color="#666"),
                        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=30,
                        alignment=ft.Alignment(0, 0),
                    )
                )

            propagacion_content.controls = propagacion_rows

            # ── ACTUALIZAR GRILLA VISUAL DE RIESGO ──
            # Colores: verde=normal, amarillo=elevado, naranja=propagación, rojo=incendio
            incendio = ultimo_incendio_data[0]
            zonas_riesgo = {}
            if incendio and incendio.get("zona"):
                zona_fuego = incendio["zona"]
                zonas_riesgo[zona_fuego] = "incendio"
                # Si hay análisis de propagación, marcar zonas vecinas
                rumbo_g = calcular_rumbo_desde_grados(incendio.get("viento_dir", 90))
                analisis_g = query_propagacion_neo4j(zona_fuego, rumbo_g)
                if analisis_g:
                    if analisis_g.get("salto1_cod"):
                        zonas_riesgo[analisis_g["salto1_cod"]] = "propagacion"
                    if analisis_g.get("salto2_cod"):
                        zonas_riesgo[analisis_g["salto2_cod"]] = "elevado"

            color_map = {
                "incendio": ("#b71c1c", "#ff5252"),
                "propagacion": ("#e65100", "#ff9800"),
                "elevado": ("#f9a825", "#fff176"),
            }
            for zid in zona_grid_cells:
                if zid in zonas_riesgo:
                    bg, border_c = color_map[zonas_riesgo[zid]]
                    zona_grid_cells[zid].bgcolor = bg
                    zona_grid_cells[zid].border = ft.border.Border.all(2, border_c)
                else:
                    zona_grid_cells[zid].bgcolor = "#1e3a1e"
                    zona_grid_cells[zid].border = ft.border.Border.all(1, "#333")
        except Exception as e:
            print(f"Error en pestaña propagación: {e}")

        page.update()

    def load_latest_docs():
        latest = {}
        for drone_id in DRONES:
            doc = col_telemetria.find_one({"drone_id": drone_id}, sort=[("_id", -1)])
            if doc:
                latest[drone_id] = doc
        return latest

    async def poll_mongo():
        while True:
            try:
                refresh_dashboard(load_latest_docs())
            except Exception as ex:
                status_text.value = f"Error MongoDB: {ex}"
                status_text.color = "#e74c3c"
                status_dot.bgcolor = "#e74c3c"
                try:
                    page.update()
                except Exception:
                    pass
            await asyncio.sleep(1.0)

    page.run_task(poll_mongo)


if __name__ == "__main__":
    ft.run(main, assets_dir=".")
