import time
import math
import random
from datetime import datetime, timezone
from pymongo import MongoClient
from neo4j import GraphDatabase

# Configuración de MongoDB en Docker
MONGO_URI = "mongodb://localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["ecodrones_db"]

# Neo4j config for propagation
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
coleccion_telemetria = db["telemetria"]

print("🟢 Conectado exitosamente a MongoDB.")
print(" Iniciando patrullaje de drones... (Presioná Ctrl+C para detener)\n")

# Límites para Capilla del Monte
MIN_LON, MAX_LON = -64.5400, -64.5050
MIN_LAT, MAX_LAT = -30.8750, -30.8500

ZONAS_GPS = {
    "ZONA_001": {"min_lon": -64.5400, "max_lon": -64.5282, "min_lat": -30.8625, "max_lat": -30.8500, "nombre": "Los Terrones"},
    "ZONA_002": {"min_lon": -64.5282, "max_lon": -64.5166, "min_lat": -30.8625, "max_lat": -30.8500, "nombre": "Centro Capilla"},
    "ZONA_003": {"min_lon": -64.5166, "max_lon": -64.5050, "min_lat": -30.8625, "max_lat": -30.8500, "nombre": "Base Uritorco"},
    "ZONA_004": {"min_lon": -64.5400, "max_lon": -64.5282, "min_lat": -30.8750, "max_lat": -30.8625, "nombre": "Dique El Cajón"},
    "ZONA_005": {"min_lon": -64.5282, "max_lon": -64.5166, "min_lat": -30.8750, "max_lat": -30.8625, "nombre": "Paso del Indio"},
    "ZONA_006": {"min_lon": -64.5166, "max_lon": -64.5050, "min_lat": -30.8750, "max_lat": -30.8625, "nombre": "Cerro Uritorco"}
}

START_LON = -64.5224
START_LAT = -30.85625

# Lon_base calculada como centro de cada par de zonas (Oeste, Centro, Este)
drones_estado = {
    # Alpha: ZONA_001 (N) <-> ZONA_004 (S). Lon: -64.5341
    "DRON_ALPHA": {"lon_base": -64.5341, "lat": -30.851, "dir": -1, "v": 0.00025, "offset": 0.0, "t": 0.0},
    # Beta: ZONA_005 (S) <-> ZONA_002 (N). Lon: -64.5224
    "DRON_BETA":  {"lon_base": -64.5224, "lat": -30.874, "dir": 1,  "v": 0.00030, "offset": 0.0, "t": 2.0},
    # Gamma: ZONA_006 (S) <-> ZONA_003 (N). Lon: -64.5108
    "DRON_GAMMA": {"lon_base": -64.5108, "lat": -30.874, "dir": 1,  "v": 0.00020, "offset": 0.0, "t": 4.0}
}

ACTIVE_FIRE_ZONES = {"ZONA_003"} # FOCO ÚNICO PERMANENTE EN ZONA 3

try:
    while True:
        for drone_id, estado in drones_estado.items():
            estado["t"] += 0.02 # Avance para la batería
            
            # Movimiento lineal vertical con rebote
            estado["lat"] += estado["v"] * estado["dir"]
            
            # Al tocar los bordes (Norte: -30.851, Sur: -30.874), invierte y desplaza
            if estado["lat"] <= -30.874 or estado["lat"] >= -30.851:
                estado["dir"] *= -1
                # Desplazamiento lateral suave para no repetir camino (reducido para evitar saltos)
                estado["offset"] = random.uniform(-0.0008, 0.0008)
            
            current_lat = estado["lat"]
            current_lon = estado["lon_base"] + estado["offset"]
            
            # Ajuste de seguridad: No salir nunca de los bordes
            current_lon = max(MIN_LON, min(MAX_LON, current_lon))
            current_lat = max(MIN_LAT, min(MAX_LAT, current_lat))

            # 2. DETECCIÓN DINÁMICA DE ZONA BASADA EN GRILLA (Chocolate)
            zona_actual = "ZONA_001"
            for zid, bounds in ZONAS_GPS.items():
                if bounds["min_lon"] <= current_lon <= bounds["max_lon"] and bounds["min_lat"] <= current_lat <= bounds["max_lat"]:
                    zona_actual = zid
                    break
            
            # 3. CÁLCULO DE LA FÍSICA BASADA EN FOCO ÚNICO (ZONA 3)
            # Ubicación central del incendio en Base Uritorco
            fire_box = ZONAS_GPS["ZONA_003"]
            f_target_lon = (fire_box["min_lon"] + fire_box["max_lon"]) / 2
            f_target_lat = (fire_box["min_lat"] + fire_box["max_lat"]) / 2
            
            # Distancia real 2D normalizada
            d_real = math.hypot(current_lon - f_target_lon, current_lat - f_target_lat)
            m_dist = math.hypot(MAX_LON - MIN_LON, MAX_LAT - MIN_LAT)
            dist_norm = d_real / m_dist
            
            # Variables base (Clima normal del parque)
            temp_base = 22.0
            co2_base = 400.0
            humedad_base = 65.0
            
            # Efecto de proximidad: a menor distancia, mayor calor/co2 (curva exponencial inversa)
            factor_fuego = math.exp(-dist_norm * 8.0) 
            
            temperatura = temp_base + (40.0 * factor_fuego) + random.uniform(-0.5, 0.5)
            co2 = co2_base + (1000.0 * factor_fuego) + random.uniform(-10.0, 10.0)
            humedad = humedad_base - (45.0 * factor_fuego) + random.uniform(-1.0, 1.0)

            # 4. SENSOR DE VIENTO DINÁMICO
            viento_velocidad = 12.0 + (25.0 * factor_fuego) + random.uniform(-2.0, 2.0)
            viento_direccion = 90.0 + random.uniform(-15.0, 15.0) # Viento dominante del Este (apunta hacia el Oeste)

            # 5. ARMADO DEL DOCUMENTO CON ESTÁNDAR IOT GEOJSON
            # Modelo de hardware diferenciado por dron
            modelos_hw = {
                "DRON_ALPHA": "Hexacopter-V2-Eco",
                "DRON_BETA": "Hexacopter-V3-Pro",
                "DRON_GAMMA": "Quadcopter-X1-Scout",
            }

            payload_telemetria = {
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "drone_id": drone_id,
                "modelo_hardware": modelos_hw.get(drone_id, "Hexacopter-V2-Eco"),
                "cod_zona": zona_actual,
                "estado_bateria_porcentaje": round(max(5.0, 100.0 - (estado["t"] * 0.2)), 1),
                "posicion_geografica": {
                    "type": "Point",
                    "coordinates": [round(current_lon, 6), round(current_lat, 6)]
                },
                "lecturas_sensores": {
                    "temperatura_c": round(temperatura, 2),
                    "co2_ppm": round(co2, 2),
                    "humedad_relativa_porcentaje": round(humedad, 2),
                    "viento_velocidad_kmh": round(viento_velocidad, 2),
                    "viento_direccion_grados": round(viento_direccion, 2)
                }
            }

            # SENSORES ADICIONALES POR MODELO (esquema flexible — demuestra ventaja NoSQL)
            if drone_id == "DRON_BETA":
                # Beta tiene sensor UV y barómetro
                payload_telemetria["lecturas_sensores"]["radiacion_uv_indice"] = round(
                    3.0 + (5.0 * factor_fuego) + random.uniform(-0.3, 0.3), 1
                )
                payload_telemetria["lecturas_sensores"]["presion_atmosferica_hpa"] = round(
                    1013.25 - (current_lat + 30.87) * 100 + random.uniform(-0.5, 0.5), 1
                )
            elif drone_id == "DRON_GAMMA":
                # Gamma tiene sensor de luminosidad y detector de partículas PM2.5
                payload_telemetria["lecturas_sensores"]["luminosidad_lux"] = round(
                    max(50, 800 - (600 * factor_fuego) + random.uniform(-20, 20)), 1
                )
                payload_telemetria["lecturas_sensores"]["particulas_pm25_ugm3"] = round(
                    12.0 + (180.0 * factor_fuego) + random.uniform(-3, 3), 1
                )
            
            # Inyección en tiempo real en MongoDB
            coleccion_telemetria.insert_one(payload_telemetria)
            
            # Imprimir traza en consola para verificar que se está moviendo bien
            color_traza = "\033[91m🔥" if temperatura > 45.0 else "\033[92m🟢"
            extra_info = ""
            if drone_id == "DRON_BETA":
                extra_info = f" | UV: {payload_telemetria['lecturas_sensores']['radiacion_uv_indice']} | Presión: {payload_telemetria['lecturas_sensores']['presion_atmosferica_hpa']} hPa"
            elif drone_id == "DRON_GAMMA":
                extra_info = f" | Luz: {payload_telemetria['lecturas_sensores']['luminosidad_lux']} lux | PM2.5: {payload_telemetria['lecturas_sensores']['particulas_pm25_ugm3']} μg/m³"
            print(f"{color_traza} [{drone_id}] en {zona_actual} ({ZONAS_GPS[zona_actual]['nombre']}) -> "
                  f"Temp: {round(temperatura, 1)}°C | CO2: {round(co2, 1)} ppm | Viento: {round(viento_velocidad, 1)} km/h a {round(viento_direccion, 0)}°{extra_info}\033[0m")
            
        # Esperamos 1 segundo exacto antes de la próxima ráfaga de telemetría
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\n🛑 Simulador detenido por el usuario de forma limpia.")
finally:
    client.close()
    neo4j_driver.close()