# Sistema de Orquestación de Incidentes

Sistema multi-agente para manejar incidentes de camiones y redistribuir entregas automáticamente.

## 🔄 Flujo Simplificado

Cuando ocurre un incidente:

1. **Frontend detiene TODOS los camiones** y envía sus posiciones actuales
2. **Backend orquesta la solución** con 5 agentes especializados
3. **Frontend muestra resultado** y permite reanudar con nueva ruta

## 🤖 Arquitectura de Agentes

### 1. 🔍 Agente Analizador (`incident_analyzer_agent`)
- Analiza el incidente reportado
- Identifica entregas pendientes del camión afectado
- Calcula valor total pendiente

### 2. 📦 Agente Verificador de Inventario (`inventory_checker_agent`)
- Verifica disponibilidad de items en almacén
- **Acepta entregas parciales** si al menos 1 item está disponible
- Reporta items no disponibles como advertencias

### 3. 🚚 Agente Selector de Camión (`truck_selector_agent`)
- Encuentra el camión **más cercano al depósito**
- Usa AWS Location Service para calcular distancias reales
- Excluye camiones con incidentes propios

### 4. ✅ Agente Validador (`solution_validator_agent`)
- Valida viabilidad de la solución propuesta
- Usa **LLM (GPT-4)** para análisis inteligente
- Criterios flexibles: acepta hasta 150% de capacidad
- Aprueba si hay al menos 1 item disponible

### 5. 🗺️ Agente Generador de Rutas (`route_generator_agent`)
**SIMPLIFICADO**: Optimiza desde posición actual del camión
- **NO requiere retorno al depósito primero**
- Combina entregas pendientes de ambos camiones
- Usa AWS para optimizar orden de destinos
- Calcula geometría de ruta completa

## 📊 Flujo de Datos

```
Frontend (Incidente) 
  ↓
  Envía: { 
    truck_id: 3,
    truck_positions: {
      0: {lat, lng, currentStop, status, progress},
      1: {lat, lng, currentStop, status, progress},
      ...
    }
  }
  ↓
Backend (/report-incident)
  ↓
  1. Actualiza JSON con posiciones actuales
  2. Genera reporte de incidente
  3. Llama al orquestador
  ↓
Orquestador (orchestrate_incident_response)
  ↓
  PASO 1: Analizar incidente → entregas pendientes
  PASO 2: Verificar inventario → items disponibles
  PASO 3: Seleccionar camión → más cercano al depósito
  PASO 4: Validar solución → LLM aprueba/rechaza
  PASO 5: Generar ruta → desde posición actual
  ↓
  Retorna: { success, solution, validation, new_route }
  ↓
Frontend
  ↓
  Muestra resultado con detalles
  Usuario decide si reanudar simulación
```

## ✨ Características Clave

### Entregas Parciales
- Sistema acepta si al menos 1 item está disponible
- Muestra advertencias para items no disponibles
- Continúa con entregas posibles

### Capacidad Flexible
- Capacidad base: **15 entregas**
- Acepta hasta **150% (22 entregas)** con advertencia
- Solo rechaza si sobrecapacidad crítica (>150%)

### Ruta Simplificada
- Camión seleccionado continúa **desde su posición actual**
- NO necesita ir al depósito primero
- Optimiza orden de todas las entregas pendientes
- Termina en el depósito

### Validación Inteligente
- LLM analiza viabilidad de la solución
- Considera múltiples factores: inventario, capacidad, distancia
- Proporciona razonamiento y nivel de confianza

## 📝 Ejemplo de Respuesta

```json
{
  "status": "success",
  "orchestration": {
    "success": true,
    "solution": {
      "incident_analysis": {
        "truck_id": 3,
        "truck_name": "Truck 4",
        "pending_deliveries": 8,
        "pending_value_usd": 4500
      },
      "inventory_check": {
        "all_available": false,
        "can_proceed": true,
        "available_items": 6,
        "unavailable_items": 2,
        "unavailable_items_list": ["Item A", "Item B"]
      },
      "selected_truck": {
        "truck_id": 1,
        "truck_name": "Truck 2",
        "distance_to_depot_km": 2.5,
        "current_position": [-99.15, 19.42],
        "pending_deliveries": 6
      }
    },
    "validation": {
      "is_approved": true,
      "confidence": 85,
      "partial_delivery": true,
      "unavailable_items": ["Item A", "Item B"]
    },
    "new_route": {
      "truck_id": 1,
      "truck_name": "Truck 2",
      "route_type": "incident_recovery_simplified",
      "waypoints": [...],
      "geometry": [[lng, lat], ...],
      "summary": {
        "total_destinations": 14,
        "total_distance_km": 12.5,
        "total_duration_minutes": 35,
        "items_from_incident_truck": 8,
        "items_from_selected_truck": 6,
        "start_position": [-99.15, 19.42],
        "end_position": [-99.1908, 19.4336]
      }
    }
  }
}
```

## ⚙️ Configuración

### Timeouts Aumentados
Para evitar errores de timeout con AWS:
```python
timeout=30  # optimize_waypoints
timeout=60  # calculate_route
```

### Capacidades
```python
MAX_CAPACITY = 15  # Entregas base
MAX_CAPACITY_WARNING = 22  # 150% con advertencia
```

### Modelo LLM
```python
OPENAI_MODEL = 'gpt-4o-mini'  # Configurable en .env
```

## 🚀 Uso

### Reportar Incidente desde Frontend
```javascript
const response = await fetch(`${CONFIG.apiUrl}/report-incident`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    truck_id: truckId,
    truck_positions: {
      0: {lat: 19.43, lng: -99.17, currentStop: 3, status: 'in_transit', progress: 45},
      1: {lat: 19.42, lng: -99.15, currentStop: 5, status: 'delivering', progress: 60},
      // ... más camiones
    }
  })
});
```

### Respuesta del Backend
```json
{
  "status": "success",
  "message": "Incident reported for truck 4",
  "truck_id": 3,
  "incident_id": "INC-20240216-001",
  "orchestration": {
    "success": true,
    "solution": {...},
    "validation": {...},
    "new_route": {...}
  }
}
```

## 🎯 Próximos Pasos

1. **Ejecución Automática**: Aplicar la nueva ruta automáticamente en el frontend
2. **Visualización**: Mostrar en el mapa qué camión fue seleccionado y su nueva ruta
3. **Edge Cases**: Manejar casos donde no hay camiones disponibles o todos los items no disponibles
4. **Métricas**: Tracking de tiempo de respuesta y éxito de soluciones

## 📁 Archivos Principales

- `agents/incident_orchestrator.py` - Lógica de orquestación y agentes
- `main.py` - Endpoint `/report-incident`
- `static/js/simulation.js` - Frontend (detener camiones, mostrar resultado)
- `agents/tools.py` - Herramientas para obtener datos (posiciones, inventario, rutas)

## 🐛 Solución de Problemas

### Error: TypeError: '>' not supported between instances of 'str' and 'int'
**Solución**: Convertir `cantidad_disponible` a int de manera segura
```python
try:
    available_qty = int(inventory_dict[item_name]['cantidad_disponible'])
except (ValueError, TypeError):
    available_qty = 0
```

### Timeout en AWS API
**Solución**: Aumentar timeouts en requests
```python
response = requests.post(url, json=data, timeout=60)
```

### Items no encontrados en inventario
**Solución**: Matching flexible por primeras 2-3 palabras del nombre del producto
