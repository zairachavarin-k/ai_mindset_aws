# SmartSupply MCP Tools - Lambda Functions

Este directorio contiene las herramientas MCP (Model Context Protocol) que serán invocadas por el Bedrock Agent Autónomo para ejecutar acciones de reasignación logística.

## Herramientas Implementadas

### 1. consultar_ruta_afectada.py
**Propósito**: Consulta DynamoDB para obtener la ruta completa del camión afectado por un incidente.

**Input**:
```json
{
  "truck_id": "1",
  "fecha_ruta": "2026-02-17" // opcional
}
```

**Output**:
```json
{
  "truck_id": "1",
  "conductor": "Ing. Ernesto Rosado",
  "paradas": [...],
  "fecha_ruta": "2026-02-17",
  "estado_ruta": "Activa"
}
```

**Requisitos**: 2.3

---

### 2. consultar_flota_disponible.py
**Propósito**: Consulta flota de camiones disponibles, excluyendo aquellos con nivel de fatiga "Alto".

**Input**:
```json
{
  "excluir_fatiga_alta": true,
  "truck_id_excluir": "1" // opcional
}
```

**Output**:
```json
{
  "camiones_disponibles": [
    {
      "truck_id": "2",
      "conductor": "Ing. Ernesto Rosado",
      "capacidad_max_ton": 5.0,
      "nivel_fatiga": "Bajo",
      "ubicacion_actual": {"lat": 19.4326, "lon": -99.1332}
    }
  ],
  "total": 3
}
```

**Requisitos**: 2.3, 3.3

---

### 3. consultar_inventario_almacen.py
**Propósito**: Consulta inventario del almacén por SKUs específicos o todo el inventario.

**Input**:
```json
{
  "skus": ["FAR-001", "MED-002"] // opcional
}
```

**Output**:
```json
{
  "productos": [
    {
      "sku": "FAR-001",
      "nombre_producto": "Vacuna COVID-19",
      "categoria": "Farma",
      "es_fragil": true,
      "cantidad_disponible_almacen": 50,
      "cantidad_en_ruta": 20,
      "prioridad_negocio": "Crítica",
      "ubicacion_pasillo": "Pasillo-A-1"
    }
  ],
  "total": 2
}
```

**Requisitos**: 2.3, 11.2

---

### 4. calcular_distancia.py
**Propósito**: Calcula distancia en kilómetros entre dos puntos usando Amazon Location Service (con fallback a Haversine).

**Input**:
```json
{
  "origen": {"lat": 19.4326, "lon": -99.1332},
  "destino": {"lat": 19.4345, "lon": -99.1410}
}
```

**Output**:
```json
{
  "distancia_km": 1.23,
  "metodo": "location_service"
}
```

**Requisitos**: 2.7

---

### 5. calcular_ruta_optimizada.py
**Propósito**: Wrapper que invoca Lambda existente de optimización de rutas (TSP/VRP).

**Input**:
```json
{
  "paradas": [
    {
      "stop_id": "STOP-1",
      "latitud": 19.4326,
      "longitud": -99.1332,
      "hora_programada": "10:00"
    }
  ],
  "origen": {"lat": 19.4384, "lon": -99.1569},
  "optimizar_por": "distancia_y_tiempo"
}
```

**Output**:
```json
{
  "ruta_optimizada": [
    {"stop_id": "STOP-1", "orden": 1, "hora_estimada": "10:30"}
  ],
  "distancia_total_km": 45.3,
  "tiempo_estimado_minutos": 120,
  "ahorro_vs_ruta_original": 15.2
}
```

**Requisitos**: 20.1, 20.2, 20.4, 20.5

**Nota**: Esta Lambda invoca una función existente llamada `optimizar-rutas-lambda` que debe ser desplegada por separado.

---

### 6. actualizar_ruta_s3.py
**Propósito**: Escribe JSON de ruta actualizada en S3 con versionamiento.

**Input**:
```json
{
  "truck_id": "1",
  "fecha": "2026-02-17",
  "ruta": {
    "truck_id": "1",
    "fecha_ruta": "2026-02-17",
    "conductor_asignado": "Ing. Ernesto Rosado",
    "estado_ruta": "Reasignada",
    "paradas": [...]
  }
}
```

**Output**:
```json
{
  "s3_path": "s3://smart-supply-data/rutas/2026-02-17/1.json",
  "version_id": "abc123",
  "timestamp": "2026-02-17T14:30:00Z"
}
```

**Requisitos**: 12.3, 12.6

---

### 7. registrar_incidencia.py
**Propósito**: Registra incidencia en S3 y DynamoDB, calculando tiempo de respuesta.

**Input**:
```json
{
  "incidente": {
    "incidente_id": "INC-901",
    "timestamp": "2026-02-17T14:15:00Z",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410},
    "descripcion_evento": "Impacto lateral severo",
    "inventario_afectado": [...],
    "plan_reasignacion": {...},
    "timestamp_deteccion": "2026-02-17T14:15:00Z",
    "timestamp_resolucion": "2026-02-17T14:17:30Z"
  }
}
```

**Output**:
```json
{
  "incidente_id": "INC-901",
  "s3_path": "s3://smart-supply-data/incidencias/2026/02/INC-901.json",
  "dynamodb_written": true,
  "tiempo_respuesta_segundos": 150
}
```

**Requisitos**: 4.2, 8.2

---

### 8. enviar_notificacion_cliente.py
**Propósito**: Envía notificación a cliente vía Amazon Connect con priorización y retry automático.

**Input**:
```json
{
  "cliente_id": "CLI-001",
  "telefono": "+525512345678",
  "mensaje": "Su entrega ha sido reprogramada",
  "prioridad": "Crítica",
  "nuevo_horario": "15:30",
  "motivo": "Incidente en ruta",
  "numero_seguimiento": "TRACK-123",
  "incidente_id": "INC-901"
}
```

**Output**:
```json
{
  "notificacion_id": "NOT-20260217143000-CLI-001",
  "estado": "enviado",
  "canal": "llamada_connect",
  "retry_programado": true,
  "mensaje": "Estimado cliente, su entrega ha sido actualizada..."
}
```

**Requisitos**: 7.3, 7.4

---

## Variables de Entorno Requeridas

Cada Lambda function requiere las siguientes variables de entorno:

```bash
# Comunes
DATA_BUCKET_NAME=smart-supply-data

# consultar_ruta_afectada
RUTAS_TABLE_NAME=rutas_entregas

# consultar_flota_disponible
FLOTA_TABLE_NAME=flota_camiones

# consultar_inventario_almacen
INVENTARIO_TABLE_NAME=inventario_almacen

# calcular_distancia
ROUTE_CALCULATOR_NAME=smart-supply-route-calculator

# calcular_ruta_optimizada
OPTIMIZACION_LAMBDA_NAME=optimizar-rutas-lambda

# registrar_incidencia
INCIDENCIAS_TABLE_NAME=incidencias

# enviar_notificacion_cliente
CONNECT_INSTANCE_ID=<connect-instance-id>
CONTACT_FLOW_ID=<contact-flow-id>
SOURCE_PHONE_NUMBER=<phone-number>
NOTIFICACIONES_TABLE_NAME=notificaciones_clientes
```

## Despliegue

Estas Lambda functions deben ser desplegadas con:
- Runtime: Python 3.11+
- Timeout: 30 segundos (mínimo)
- Memory: 256 MB (mínimo)
- IAM Role: `smart-supply-lambda-role` (creado en infrastructure stack)

### Usando AWS CDK

Las Lambda functions se desplegarán automáticamente en la siguiente fase del proyecto mediante AWS CDK, configurando:
- Permisos IAM para DynamoDB, S3, Location Service, Connect
- Variables de entorno
- Integración con Bedrock Agent vía AgentCore Gateway

## Testing

Para probar localmente, usar `boto3` con credenciales de AWS configuradas:

```python
import json
from consultar_ruta_afectada import lambda_handler

event = {"truck_id": "1"}
context = {}
response = lambda_handler(event, context)
print(json.dumps(response, indent=2))
```

## Integración con Bedrock Agent

Estas herramientas serán registradas en AgentCore Gateway como herramientas MCP que el Bedrock Agent puede invocar durante el proceso de análisis y reasignación de incidentes.

El Agent recibirá descripciones de cada herramienta y sus parámetros, permitiéndole decidir cuándo y cómo invocarlas según el contexto del incidente.
