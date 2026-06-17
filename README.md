# 🦌 EcoDrones - Sistema de Monitoreo Ambiental con Drones

**EcoDrones** es una plataforma de software de vanguardia diseñada para la vigilancia ambiental autónoma. Su objetivo principal es la detección temprana de focos ígneos y la evaluación del riesgo para la biodiversidad en regiones críticas, específicamente centrado en el área de **Capilla del Monte y el Cerro Uritorco, Córdoba, Argentina**.

---

## 📋 Descripción del Proyecto

El sistema integra múltiples tecnologías para ofrecer una respuesta coordinada ante emergencias climáticas:

1.  **Simulación de Telemetría:** Tres drones (**Alpha, Beta y Gamma**) ejecutan patrones de patrullaje enviando ráfagas de datos de sensores cada segundo.
2.  **Detección en Tiempo Real:** Un monitor de alertas analiza los datos entrantes buscando anomalías térmicas.
3.  **Análisis de Impacto Ecológico:** Mediante algoritmos de grafos, el sistema predice hacia dónde se moverá el fuego según el viento y qué especies animales específicas están en la línea de peligro.
4.  **Visualización Táctica:** Un dashboard interactivo permite a los operadores ver la posición de los drones, los niveles de CO2 y las zonas de riesgo en un mapa satelital.

---

## 🛠️ Requisitos del Sistema

Para que el sistema funcione correctamente, se deben cumplir los siguientes requisitos:

### 🔹 Software y Versiones
*   **Python:** Versión 3.8 o superior (Recomendado 3.10+).
*   **Docker Desktop:** Necesario para levantar las bases de datos.
*   **Navegador Web:** Chrome, Edge o Firefox (para acceder a Neo4j Browser).
*   **Sistemas Operativos:** Windows 10/11 (por los scripts `.bat`), o Linux/macOS (ejecutando los comandos equivalentes).

### 🔹 Librerías de Python
Es necesario instalar las dependencias mediante `pip`:
```bash
pip install neo4j pymongo flet --upgrade
```

---

## 🏗️ Arquitectura de Datos

El sistema utiliza una **Arquitectura Políglota** (Multi-base de datos) para aprovechar las fortalezas de cada tecnología:

### **1. MongoDB (Base Documental)**
*   **Rol:** Almacenamiento masivo de telemetría e histórico de alertas.
*   **Versión:** `latest` (v6.0+ recomendado).
*   **Optimización:** Uso de **objetos embebidos** (`posicion_geografica`, `lecturas_sensores`) para evitar fragmentación de datos y mejorar la velocidad de lectura/escritura en ráfagas de telemetría.

### **2. Neo4j (Base de Grafos)**
*   **Rol:** Modelado del ecosistema y análisis de propagación.
*   **Versión:** `latest` (v5.0+ recomendado).
*   **Funcionalidad:** Implementación de algoritmos de vecindad para predecir la expansión de incendios basándose en vectores cardinales de viento.

---

## 📂 Estructura de la Entrega

El proyecto final consta exclusivamente de los siguientes archivos:

| Archivo | Función |
| :--- | :--- |
| `iniciar_servicios.bat` | Orquestador principal de contenedores y servicios Python. |
| `detener_servicios.bat` | Script de apagado seguro de la infraestructura Docker. |
| `cargar_neo4j.py` | Script de inicialización de la topología y fauna en el grafo. |
| `simulador_continuo.py` | Generador de telemetría física realista. |
| `monitor_alertas.py` | Motor de reglas, detección de incendios y análisis de impacto. |
| `dashboard.py` | Interfaz gráfica táctica (Flet) para monitoreo en tiempo real. |
| `README.md` | Manual de usuario y especificaciones técnicas. |

---

## 📊 Esquema de Datos (JSON)

### Colección: `telemetria`
Representa el estado de un dron en un momento exacto.

```json
{
  "drone_id": "DRON_ALPHA",
  "timestamp": "2023-10-27T14:30:00Z",
  "cod_zona": "ZONA_003",
  "posicion_geografica": {           // <--- OBJETO EMBEBIDO (GeoJSON)
    "type": "Point",
    "coordinates": [-64.5108, -30.851]
  },
  "lecturas_sensores": {             // <--- OBJETO EMBEBIDO (Métricas)
    "temperatura_c": 57.3,
    "co2_ppm": 1180.5,
    "humedad_relativa_porcentaje": 45.2,
    "viento_velocidad_kmh": 32.5,
    "viento_direccion_grados": 95.0
  }
}
```

---

## 🚀 Guía de Uso Rápido

1.  **Iniciar Docker:** Asegúrate de que Docker Desktop esté abierto y funcionando.
2.  **Ejecutar el Lanzador:** Haz doble clic en `iniciar_servicios.bat`. Este script realizará automáticamente:
    *   La descarga e inicio de contenedores MongoDB y Neo4j.
    *   La carga de la topología del parque en el grafo.
    *   El lanzamiento del simulador de drones y el monitor de alertas.
3.  **Abrir el Dashboard:** Desde el menú del script `iniciar_servicios.bat`, presiona la tecla `D` para abrir la interfaz visual.

---

## 📊 Análisis Dinámico

Cuando el sistema detecta una temperatura superior a **45°C**, se dispara el protocolo de emergencia:

- Qué fauna está en peligro directo en la zona afectada
- Hacia qué zona vecina se va a propagar el fuego según la dirección del viento
- Qué especies de esa zona vecina deben ser evacuadas
