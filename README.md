# 🦌 EcoDrones - Sistema de Monitoreo Ambiental con Drones

**EcoDrones** es una plataforma de vigilancia ambiental autónoma para la detección temprana de focos ígneos y la evaluación del riesgo para la biodiversidad, centrada en el área de **Capilla del Monte y el Cerro Uritorco, Córdoba, Argentina**.

> Trabajo Práctico — Ingeniería de Datos 2 — Universidad Argentina De la Empresa (UADE)  
> Profesor: Fernández Alfonso Martín  
> Integrantes: Piña Matias, Vazquez Luciana, Micheli Alejo Gonzalo, Lambert Theo, Huertas Maximiliano Ivan, D'Elia Tomas

---

## 📋 Descripción del Proyecto

El sistema integra múltiples tecnologías para ofrecer una respuesta coordinada ante emergencias climáticas:

1. **Simulación de Telemetría:** Tres drones (Alpha, Beta, Gamma) con sensores diferenciados ejecutan patrones de patrullaje enviando datos cada segundo.
2. **Detección en Tiempo Real:** Un monitor analiza los datos buscando anomalías térmicas (>45°C).
3. **Análisis de Impacto Ecológico:** Mediante algoritmos de grafos (Neo4j), predice la propagación del fuego e identifica 7 especies en riesgo.
4. **Visualización Táctica:** Dashboard interactivo con 4 pestañas: Monitoreo, Alertas, Mapa Operativo y Análisis de Propagación.

---

## 🛠️ Requisitos del Sistema

### Software necesario
| Software | Versión | Para qué |
|----------|---------|----------|
| Python | 3.8+ (recomendado 3.10+) | Ejecutar los scripts del sistema |
| Docker Desktop | Última versión | Levantar MongoDB y Neo4j en contenedores |
| Navegador Web | Chrome, Edge o Firefox | Acceder a Neo4j Browser (opcional) |
| Windows | 10/11 | Scripts .bat de orquestación |

### Librerías de Python
```bash
pip install neo4j pymongo flet --upgrade
```

---

## 🚀 Guía de Instalación y Ejecución

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/maximilianohuertasuade-coder/ecodrones.git
cd ecodrones
```

### Paso 2: Instalar dependencias
```bash
pip install neo4j pymongo flet --upgrade
```

### Paso 3: Iniciar Docker Desktop
Abrir Docker Desktop y verificar que esté corriendo (ícono verde en la barra de tareas).

### Paso 4: Ejecutar el sistema
Hacer doble clic en `iniciar_servicios.bat`. El script automáticamente:
1. Descarga e inicia contenedores MongoDB y Neo4j
2. Espera que Neo4j esté listo
3. Carga el ecosistema (6 zonas, 7 especies) en el grafo
4. Lanza el simulador de drones y el monitor de alertas

### Paso 5: Abrir el Dashboard
Desde el menú que aparece en la terminal, presionar **D** para abrir la interfaz visual.

### Paso 6: Detener el sistema
Presionar **Q** en el menú, o ejecutar `detener_servicios.bat`.

---

## 🏗️ Arquitectura de Datos

Arquitectura **Políglota** (Multi-base de datos):

| Tecnología | Modelo | Rol | Puerto |
|-----------|--------|-----|--------|
| **MongoDB** | Documental | Telemetría masiva + alertas | 27017 |
| **Neo4j** | Grafos | Ecosistema + propagación | 7687 |
| **Flet** | — | Dashboard táctico | — |
| **Docker** | — | Infraestructura | — |

### Integración Bidireccional
- **MongoDB → Neo4j:** Al detectar alerta, se registran nodos Lectura y Alerta en el grafo.
- **Neo4j → MongoDB:** El resultado del análisis de propagación se embebe en el documento de alerta.

---

## 📂 Estructura del Proyecto

| Archivo | Función |
|---------|---------|
| `iniciar_servicios.bat` | Orquestador: levanta Docker + Python con un comando |
| `detener_servicios.bat` | Apagado seguro de contenedores y procesos |
| `cargar_neo4j.py` | Inicialización del grafo (6 zonas, 7 especies, relaciones) |
| `simulador_continuo.py` | Generador de telemetría con modelo físico realista |
| `monitor_alertas.py` | Motor de reglas + análisis de impacto ecológico |
| `dashboard.py` | Interfaz gráfica táctica con 4 pestañas |
| `informe_etapa_1.html` | Informe Etapa I: Diseño Conceptual |
| `informe_etapa_FINAL.html` | Informe Etapa Final: Documento completo |
| `README.md` | Este archivo |

---

## 🚁 Flota de Drones (Esquema Flexible)

Cada dron tiene sensores distintos, demostrando la ventaja de esquema flexible de MongoDB:

| Dron | Hardware | Sensores Base | Sensores Exclusivos |
|------|----------|---------------|---------------------|
| ALPHA | Hexacopter-V2-Eco | Temp, CO₂, Humedad, Viento | — |
| BETA | Hexacopter-V3-Pro | Temp, CO₂, Humedad, Viento | UV, Presión Atmosférica |
| GAMMA | Quadcopter-X1-Scout | Temp, CO₂, Humedad, Viento | Luminosidad, PM2.5 |

---

## � Especies Monitoreadas (7 — Autóctonas de Córdoba)

| Especie | Nombre Científico | IUCN | Zonas |
|---------|-------------------|------|-------|
| Lobito de Río | *Lontra longicaudis* | NT | Z2, Z3 |
| Puma | *Puma concolor* | LC | Z3, Z4 |
| Zorro Gris | *Lycalopex gymnocercus* | LC | Z1 |
| Cóndor Andino | *Vultur gryphus* | VU | Z5, Z6 |
| Vizcacha Serrana | *Lagidium viscacia* | LC | Z1, Z6 |
| Lagarto Overo | *Salvator merianae* | LC | Z4, Z5 |
| Remolinera Serrana | *Cinclodes comechingonus* | NT | Z5, Z6 |

> La Remolinera Serrana es **endémica** de las sierras de Córdoba — no existe en ningún otro lugar del mundo.

---

## 📊 Esquema de Datos (MongoDB)

### Colección: `telemetria`
```json
{
  "drone_id": "DRON_BETA",
  "timestamp": "2026-06-17T14:30:00Z",
  "modelo_hardware": "Hexacopter-V3-Pro",
  "cod_zona": "ZONA_003",
  "estado_bateria_porcentaje": 87.5,
  "posicion_geografica": {
    "type": "Point",
    "coordinates": [-64.5108, -30.851]
  },
  "lecturas_sensores": {
    "temperatura_c": 57.3,
    "co2_ppm": 1180.5,
    "humedad_relativa_porcentaje": 45.2,
    "viento_velocidad_kmh": 32.5,
    "viento_direccion_grados": 95.0,
    "radiacion_uv_indice": 7.2,
    "presion_atmosferica_hpa": 1011.3
  }
}
```

---

## � Análisis Dinámico

Cuando el sistema detecta temperatura superior a **45°C**, se dispara el protocolo de emergencia:

1. Identifica fauna en peligro directo en la zona afectada
2. Calcula hacia qué zona se propaga el fuego según dirección del viento
3. Identifica especies a evacuar en zonas de propagación (hasta 2 saltos)
4. Sugiere acciones de respuesta (redirigir dron, evacuar fauna, cortafuegos, notificar bomberos)

---

## 🖥️ Dashboard — Pestañas

| Pestaña | Función |
|---------|---------|
| **Monitoreo** | Tarjetas por dron con sensores en vivo (diferenciados por hardware) |
| **Alertas** | Listado cronológico de incendios con análisis de impacto |
| **Mapa Operativo** | Mapa satelital con posición GPS de drones + fuego/humo en zona activa |
| **🔥 Propagación** | Mapa de riesgo (Neo4j en vivo) + fauna + acciones de respuesta |

---

## � Accesos

| Servicio | URL |
|----------|-----|
| Neo4j Browser | http://localhost:7474 (usuario: `neo4j` / contraseña: `password`) |
| MongoDB | `mongodb://localhost:27017/ecodrones_db` |

---

## 📄 Informes

- `informe_etapa_1.html` — Diseño conceptual (Etapa I)
- `informe_etapa_FINAL.html` — Documento final completo (Etapa Final)

Abrir en cualquier navegador para visualizar con formato.
