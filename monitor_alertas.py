import time
from datetime import datetime, timezone
from pymongo import MongoClient
from neo4j import GraphDatabase

# Configuración de conexiones en Docker
MONGO_URI = "mongodb://localhost:27017/"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

# Inicializar clientes de bases de datos
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["ecodrones_db"]
col_telemetria = mongo_db["telemetria"]
col_alertas = mongo_db["alertas_disparadas"]

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("📡 MONITOR DE ALERTAS AMBIENTALES ACTIVO")
print("🔍 Escuchando flujo de telemetría en MongoDB...")
print("------------------------------------------------------------------\n")

def calcular_rumbo_viento(grados):
    """
    Traduce los grados del sensor del dron a la dirección hacia donde SOPLA el viento.
    """
    if 45 <= grados <= 135:
        return "Oeste"
    elif 225 <= grados <= 315:
        return "Este"
    else:
        return "Ninguna"


def co2_level(co2):
    if co2 < 600:
        return "Normal"
    if co2 < 1000:
        return "Moderado"
    if co2 < 1500:
        return "Alto"
    return "Muy alto"


def registrar_dron(tx, drone_id):
    query = """
    MERGE (d:Dron {drone_id: $drone_id})
    ON CREATE SET d.estado = 'activo'
    RETURN d.drone_id AS drone_id
    """
    tx.run(query, drone_id=drone_id)


def registrar_lectura(tx, doc, zona):
    lectura_id = str(doc["_id"])
    lecturas = doc["lecturas_sensores"]
    query = """
    MERGE (d:Dron {drone_id: $drone_id})
    ON CREATE SET d.estado = 'activo'
    SET d.ultimo_timestamp = $timestamp
    MERGE (z:Zona {cod_zona: $zona})
    MERGE (l:Lectura {lectura_id: $lectura_id})
    SET l.timestamp = $timestamp,
        l.temperatura_c = $temp,
        l.co2_ppm = $co2,
        l.mongo_doc_id = $lectura_id,
        l.humedad_relativa_porcentaje = $hum,
        l.viento_velocidad_kmh = $viento_vel,
        l.viento_direccion_grados = $viento_dir,
        l.lon = $lon,
        l.lat = $lat
    MERGE (d)-[:REGISTRA]->(l)
    MERGE (l)-[:EN_ZONA]->(z)
    RETURN l.lectura_id AS lectura_id
    """
    tx.run(
        query,
        drone_id=doc["drone_id"],
        timestamp=doc["timestamp"],
        zona=zona,
        lectura_id=lectura_id,
        temp=lecturas["temperatura_c"],
        co2=lecturas["co2_ppm"],
        hum=lecturas["humedad_relativa_porcentaje"],
        viento_vel=lecturas["viento_velocidad_kmh"],
        viento_dir=lecturas["viento_direccion_grados"],
        lon=doc["posicion_geografica"]["coordinates"][0],
        lat=doc["posicion_geografica"]["coordinates"][1],
    )


def registrar_alerta_grafo(tx, doc, nivel, mensaje):
    alerta_id = str(doc["_id"]) + "-alerta"
    query = """
    MERGE (z:Zona {cod_zona: $zona})
    MERGE (a:Alerta {alerta_id: $alerta_id})
    SET a.tipo = $tipo,
        a.nivel = $nivel,
        a.mongo_alerta_id = $alerta_id,
        a.timestamp_alerta = $timestamp_alerta,
        a.mensaje = $mensaje
    MERGE (z)-[:TIENE_ALERTA]->(a)
    WITH a
    MATCH (d:Dron {drone_id: $drone_id})
    MERGE (d)-[:DISPARA]->(a)
    RETURN a.alerta_id AS alerta_id
    """
    tx.run(
        query,
        zona=doc["cod_zona"],
        alerta_id=alerta_id,
        tipo="INCENDIO",
        nivel=nivel,
        timestamp_alerta=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        mensaje=mensaje,
        drone_id=doc["drone_id"],
    )


def analizar_impacto_ecologico(tx, cod_zona, direccion_propagacion):
    """
    Consulta Cypher en Neo4j para extraer el impacto de la zona afectada
    y predecir la propagación según el vector de viento.
    """
    query = """
    MATCH (z:Zona {cod_zona: $zona})
    OPTIONAL MATCH (especie:Especie)-[:HABITA_EN]->(z)
    OPTIONAL MATCH (d:Dron)-[:REGISTRA]->(:Lectura)-[:EN_ZONA]->(z)
    OPTIONAL MATCH (z)-[:TIENE_ALERTA]->(alerta:Alerta)

    WITH z,
         collect(DISTINCT {comun: especie.nombre_comun, iucn: especie.categoria_iucn}) AS fauna_local_origin,
         collect(DISTINCT d.drone_id) AS drones_recientes_origin,
         count(DISTINCT alerta) AS alerta_count_origin

    OPTIONAL MATCH (z)-[r1:LIMITA_CON {direccion: $dir_viento}]->(z1:Zona)
    OPTIONAL MATCH (e1:Especie)-[:HABITA_EN]->(z1)
    WITH z, fauna_local_origin, drones_recientes_origin, alerta_count_origin,
         z1, r1, collect(DISTINCT {comun: e1.nombre_comun, iucn: e1.categoria_iucn}) AS fauna1

    OPTIONAL MATCH (z1)-[r2:LIMITA_CON {direccion: $dir_viento}]->(z2:Zona)
    OPTIONAL MATCH (e2:Especie)-[:HABITA_EN]->(z2)
    WITH z, fauna_local_origin, drones_recientes_origin, alerta_count_origin,
         z1, r1, fauna1,
         z2, r2, collect(DISTINCT {comun: e2.nombre_comun, iucn: e2.categoria_iucn}) AS fauna2

    RETURN
      z.nombre AS zona_nombre,
      z.riesgo_actual AS zona_riesgo,
      fauna_local_origin AS fauna_local,
      drones_recientes_origin AS drones_recientes,
      alerta_count_origin AS alerta_count,
      z1.cod_zona AS vecina_cod,
      z1.nombre AS vecina_nombre,
      r1.distancia_km AS distancia_vecina,
      r1.probabilidad_propagacion AS probabilidad_vecina,
      fauna1 AS fauna_vecina,
      [
        CASE WHEN z1 IS NOT NULL THEN {
            cod_zona: z1.cod_zona,
            nombre: z1.nombre,
            distancia_km: r1.distancia_km,
            probabilidad_propagacion: r1.probabilidad_propagacion,
            fauna: fauna1
        } ELSE NULL END,
        CASE WHEN z2 IS NOT NULL THEN {
            cod_zona: z2.cod_zona,
            nombre: z2.nombre,
            distancia_km: r1.distancia_km + r2.distancia_km,
            probabilidad_propagacion: r1.probabilidad_propagacion * r2.probabilidad_propagacion,
            fauna: fauna2
        } ELSE NULL END
      ] AS zonas_en_cascada
    """
    result = tx.run(query, zona=cod_zona, dir_viento=direccion_propagacion)
    return result.single()

# Al iniciar, marcamos el último ID existente para solo procesar datos nuevos
ultimo_registro_inicial = col_telemetria.find_one(sort=[("_id", -1)])
ultimo_id_procesado = ultimo_registro_inicial["_id"] if ultimo_registro_inicial else None

try:
    while True:
        # Buscamos todos los registros nuevos desde el último procesado
        filtro = {"_id": {"$gt": ultimo_id_procesado}} if ultimo_id_procesado else {}
        ultimo_registro = col_telemetria.find(filtro).sort("_id", 1)
        
        for doc in ultimo_registro:
            ultimo_id_procesado = doc["_id"]
            
            lecturas = doc["lecturas_sensores"]
            temp = lecturas["temperatura_c"]
            
            if temp > 45.0:
                drone = doc["drone_id"]
                zona = doc["cod_zona"]
                viento_grados = lecturas["viento_direccion_grados"]
                viento_vel = lecturas["viento_velocidad_kmh"]

                alerta_log = {
                    "timestamp_alerta": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
                    "telemetria_origen_id": doc["_id"],
                    "drone_id": drone,
                    "cod_zona": zona,
                    "temperatura_registrada": temp,
                    "co2_registrado": lecturas["co2_ppm"],
                    "atendido_por_brigada": False
                }
                inserted_alert = col_alertas.insert_one(alerta_log)
                alerta_mongo_id = inserted_alert.inserted_id

                rumbo_propagacion = calcular_rumbo_viento(viento_grados)
                alerta_nivel = "Muy alto" if temp > 55.0 else "Alto"
                alerta_mensaje = f"Incendio detectado en {zona} por {drone} con {temp}°C"

                with neo4j_driver.session() as session:
                    session.execute_write(registrar_lectura, doc, zona)
                    session.execute_write(registrar_alerta_grafo, doc, alerta_nivel, alerta_mensaje)
                    analisis = session.execute_read(analizar_impacto_ecologico, zona, rumbo_propagacion)

                if analisis:
                    analisis_dict = {
                        "zona_nombre": analisis["zona_nombre"],
                        "zona_riesgo": analisis["zona_riesgo"],
                        "drones_recientes": list(analisis["drones_recientes"]),
                        "alerta_count": analisis["alerta_count"],
                        "fauna_local": analisis["fauna_local"],
                        "zonas_en_cascada": [z for z in analisis["zonas_en_cascada"] if z],
                        "rumbo_propagacion": rumbo_propagacion
                    }
                    col_alertas.update_one({"_id": alerta_mongo_id}, {"$set": {"analisis_neo4j": analisis_dict}})

                    print("\n" + "!"*70)
                    print(f"🚨 ALERTA TEMPRANA DE INCENDIO DETECTADA POR {drone} 🚨")
                    print(f"📍 Zona Afectada: {zona} - {analisis['zona_nombre']} | 🌡️ Temp: {temp}°C")
                    print("!"*70)

                    print(f"\n🐾 FAUNA EN RIESGO DIRECTO:")
                    for esp in analisis["fauna_local"]:
                        print(f"  • {esp['comun']} [IUCN: {esp['iucn']}]")
                    
                    if analisis_dict["zonas_en_cascada"]:
                        print(f"\n🔥 RIESGO DE PROPAGACIÓN INMINENTE HACIA:")
                        for z_c in analisis_dict["zonas_en_cascada"]:
                            print(f"  ➔ {z_c['nombre']} ({z_c['distancia_km']} km)")
                            print(f"    🐾 Fauna a evacuar: {', '.join([e['comun'] for e in z_c['fauna']])}")
                
        
        # Escaneamos MongoDB cada 1 segundo
        time.sleep(1.0)

except KeyboardInterrupt:
    print("\n🛑 Monitor de alertas apagado por el usuario.")
finally:
    mongo_client.close()
    neo4j_driver.close()