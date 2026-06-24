from neo4j import GraphDatabase

# Configuración de conexión al contenedor de Docker
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

# Consulta estructurada en Cypher para el Parque Nacional Ciervo de los Pantanos
cypher_setup = """
MATCH (n) DETACH DELETE n;

// 1. Creación de las 6 Zonas en Capilla del Monte
CREATE (z1:Zona {cod_zona: 'ZONA_001', nombre: 'Los Terrones', superficie_hectareas: 180.0, tipo_bioma: 'Sierras', riesgo_actual: 'Bajo'})
CREATE (z2:Zona {cod_zona: 'ZONA_002', nombre: 'Centro Capilla', superficie_hectareas: 320.5, tipo_bioma: 'Urbano', riesgo_actual: 'Bajo'})
CREATE (z3:Zona {cod_zona: 'ZONA_003', nombre: 'Base Uritorco', superficie_hectareas: 450.2, tipo_bioma: 'Monte', riesgo_actual: 'Medio'})
CREATE (z4:Zona {cod_zona: 'ZONA_004', nombre: 'Dique El Cajón', superficie_hectareas: 150.0, tipo_bioma: 'Embalse', riesgo_actual: 'Bajo'})
CREATE (z5:Zona {cod_zona: 'ZONA_005', nombre: 'Paso del Indio', superficie_hectareas: 120.0, tipo_bioma: 'Cañadón', riesgo_actual: 'Bajo'})
CREATE (z6:Zona {cod_zona: 'ZONA_006', nombre: 'Cerro Uritorco', superficie_hectareas: 210.8, tipo_bioma: 'Cumbre', riesgo_actual: 'Bajo'})

// 2. Creación de Especies con Taxonomía Oficial (Lista Roja IUCN)
CREATE (e1:Especie {especie_id: 'ESP_01', nombre_comun: 'Lobito de Río', nombre_cientifico: 'Lontra longicaudis', categoria_iucn: 'NT'})
CREATE (e2:Especie {especie_id: 'ESP_02', nombre_comun: 'Puma', nombre_cientifico: 'Puma concolor', categoria_iucn: 'LC'})
CREATE (e3:Especie {especie_id: 'ESP_03', nombre_comun: 'Zorro Gris', nombre_cientifico: 'Lycalopex gymnocercus', categoria_iucn: 'LC'})
CREATE (e4:Especie {especie_id: 'ESP_04', nombre_comun: 'Cóndor Andino', nombre_cientifico: 'Vultur gryphus', categoria_iucn: 'VU'})
CREATE (e5:Especie {especie_id: 'ESP_05', nombre_comun: 'Vizcacha Serrana', nombre_cientifico: 'Lagidium viscacia', categoria_iucn: 'LC'})
CREATE (e6:Especie {especie_id: 'ESP_06', nombre_comun: 'Lagarto Overo', nombre_cientifico: 'Salvator merianae', categoria_iucn: 'LC'})
CREATE (e7:Especie {especie_id: 'ESP_07', nombre_comun: 'Remolinera Serrana', nombre_cientifico: 'Cinclodes comechingonus', categoria_iucn: 'NT'})

// 3. Creación de Drones para el modelo (6 drones: 2 por circuito)
CREATE (d1:Dron {drone_id: 'DRON_ALPHA_1', estado: 'activo', ultimo_timestamp: '', nota: 'Dron piloto circuito Oeste'})
CREATE (d2:Dron {drone_id: 'DRON_ALPHA_2', estado: 'activo', ultimo_timestamp: '', nota: 'Dron respaldo circuito Oeste'})
CREATE (d3:Dron {drone_id: 'DRON_BETA_1', estado: 'activo', ultimo_timestamp: '', nota: 'Dron piloto circuito Centro'})
CREATE (d4:Dron {drone_id: 'DRON_BETA_2', estado: 'activo', ultimo_timestamp: '', nota: 'Dron respaldo circuito Centro'})
CREATE (d5:Dron {drone_id: 'DRON_GAMMA_1', estado: 'activo', ultimo_timestamp: '', nota: 'Dron piloto circuito Este'})
CREATE (d6:Dron {drone_id: 'DRON_GAMMA_2', estado: 'activo', ultimo_timestamp: '', nota: 'Dron respaldo circuito Este'})

// 4. Relaciones Topológicas con Orientación de Vientos (Para el Algoritmo Predictivo)
// Relaciones Horizontales (Oeste <-> Este)
CREATE (z1)-[:LIMITA_CON {direccion: 'Este', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z2), (z2)-[:LIMITA_CON {direccion: 'Oeste', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z1)
CREATE (z2)-[:LIMITA_CON {direccion: 'Este', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z3), (z3)-[:LIMITA_CON {direccion: 'Oeste', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z2)
CREATE (z4)-[:LIMITA_CON {direccion: 'Este', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z5), (z5)-[:LIMITA_CON {direccion: 'Oeste', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z4)
CREATE (z5)-[:LIMITA_CON {direccion: 'Este', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z6), (z6)-[:LIMITA_CON {direccion: 'Oeste', distancia_km: 2.0, probabilidad_propagacion: 0.4}]->(z5)
// Relaciones Verticales (Norte <-> Sur)
CREATE (z1)-[:LIMITA_CON {direccion: 'Sur', distancia_km: 1.5, probabilidad_propagacion: 0.45}]->(z4), (z4)-[:LIMITA_CON {direccion: 'Norte', distancia_km: 1.5, probabilidad_propagacion: 0.45}]->(z1)
CREATE (z2)-[:LIMITA_CON {direccion: 'Sur', distancia_km: 1.5, probabilidad_propagacion: 0.45}]->(z5), (z5)-[:LIMITA_CON {direccion: 'Norte', distancia_km: 1.5, probabilidad_propagacion: 0.45}]->(z2)
CREATE (z3)-[:LIMITA_CON {direccion: 'Sur', distancia_km: 1.5, probabilidad_propagacion: 0.45}]->(z6), (z6)-[:LIMITA_CON {direccion: 'Norte', distancia_km: 1.5, probabilidad_propagacion: 0.45}]->(z3)

// 5. Distribución Biológica (Hábitats y Densidades)
CREATE (e3)-[:HABITA_EN {densidad_estimada_por_ha: 1.2}]->(z1)
CREATE (e5)-[:HABITA_EN {densidad_estimada_por_ha: 0.8}]->(z1)
CREATE (e1)-[:HABITA_EN {densidad_estimada_por_ha: 0.15}]->(z2)
CREATE (e1)-[:HABITA_EN {densidad_estimada_por_ha: 0.25}]->(z3)
CREATE (e2)-[:HABITA_EN {densidad_estimada_por_ha: 0.05}]->(z3)
CREATE (e2)-[:HABITA_EN {densidad_estimada_por_ha: 0.08}]->(z4)
CREATE (e6)-[:HABITA_EN {densidad_estimada_por_ha: 0.6}]->(z4)
CREATE (e4)-[:HABITA_EN {densidad_estimada_por_ha: 0.40}]->(z5)
CREATE (e6)-[:HABITA_EN {densidad_estimada_por_ha: 0.45}]->(z5)
CREATE (e7)-[:HABITA_EN {densidad_estimada_por_ha: 0.30}]->(z5)
CREATE (e5)-[:HABITA_EN {densidad_estimada_por_ha: 1.0}]->(z6)
CREATE (e7)-[:HABITA_EN {densidad_estimada_por_ha: 0.25}]->(z6)
CREATE (e4)-[:HABITA_EN {densidad_estimada_por_ha: 0.15}]->(z6)
"""

def inicializar_grafo(tx):
    # Separamos las consultas por punto y coma y ejecutamos secuencialmente
    for query in [q.strip() for q in cypher_setup.split(";") if q.strip()]:
        tx.run(query)

try:
    print("\\n--- CONFIGURANDO TOPOLOGÍA CON ORIENTACIÓN DE VIENTOS EN NEO4J ---")
    with driver.session() as session:
        session.execute_write(inicializar_grafo)
    print("==================================================================")
    print("🟢 ¡ÉXITO! Ecosistema mapeado con vectores cardinales de propagación.")
    print("🗺️ 6 Zonas creadas y listas para la analítica de viento.")
    print("==================================================================")
except Exception as e:
    print(f"❌ Error al conectar o poblar Neo4j: {e}")
finally:
    driver.close()