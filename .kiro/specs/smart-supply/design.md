# Documento de Diseño - SmartSupply

## Resumen

SmartSupply es un sistema de resiliencia logística serverless que detecta incidentes críticos y ejecuta reasignación automática de recursos en menos de 3 minutos. El sistema utiliza Amazon Bedrock AgentCore como cerebro central para toma de decisiones inteligentes, procesando eventos desde múltiples canales (voz, web, IoT) mediante arquitectura orientada a eventos con EventBridge.

## Arquitectura

### Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CANALES DE ENTRADA                            │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  Amazon Connect │   Amplify Web   │    IoT Sensors (Kinesis)        │
│   + Transcribe  │  + API Gateway  │                                 │
└────────┬────────┴────────┬────────┴────────┬────────────────────────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                    ┌──────▼──────┐
                    │ EventBridge │ (Bus Central de Eventos)
                    └──────┬──────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
    ┌────▼────────────────────────┐   ┌─────▼──────┐
    │  Bedrock AgentCore          │   │  Lambda    │
    │  ┌──────────────────────┐   │   │  Functions │
    │  │ AgentCore Runtime    │   │   └─────┬──────┘
    │  │ (Serverless Exec)    │   │         │
    │  └──────────────────────┘   │         │
    │  ┌──────────────────────┐   │         │
    │  │ AgentCore Gateway    │◄──┼─────────┘
    │  │ (MCP Tools)          │   │
    │  └──────────────────────┘   │
    │  ┌──────────────────────┐   │
    │  │ AgentCore Memory     │   │
    │  │ (Learning)           │   │
    │  └──────────────────────┘   │
    │  ┌──────────────────────┐   │
    │  │ AgentCore            │   │
    │  │ Observability        │   │
    │  └──────────────────────┘   │
    └────────┬────────────────────┘
             │
    ┌────────┴────────────────────────────────┐
    │                                         │
┌───▼────┐  ┌──────────┐  ┌────────────┐  ┌─▼──────────┐
│DynamoDB│  │    S3    │  │  Location  │  │ QuickSight │
│        │  │ (Routes/ │  │  Service   │  │ Dashboard  │
│        │  │Incidents)│  │            │  │            │
└────────┘  └──────────┘  └────────────┘  └────────────┘
                │
         ┌──────┴──────┐
         │             │
    ┌────▼────┐  ┌─────▼──────┐
    │ Connect │  │  Amplify   │
    │Outbound │  │  Frontend  │
    └─────────┘  └────────────┘
```

### Flujo de Datos Principal

1. **Detección de Incidente**: Conductor llama a Connect / Usuario reporta en web / Sensor IoT detecta anomalía
2. **Normalización**: Lambda normaliza datos y publica evento estandarizado a EventBridge
3. **Análisis Inteligente**: EventBridge invoca Bedrock Agent vía AgentCore Runtime
4. **Consulta de Contexto**: Agent usa herramientas MCP (vía AgentCore Gateway) para consultar DynamoDB/S3
5. **Razonamiento**: Agent analiza impacto, prioriza, considera restricciones, genera plan
6. **Ejecución**: Agent invoca herramientas para actualizar rutas en S3, DynamoDB, enviar notificaciones
7. **Sincronización**: Lambda triggers actualizan DynamoDB desde S3 y viceversa
8. **Visualización**: Location Service y QuickSight muestran estado actualizado en tiempo real

### Decisiones Arquitectónicas

**Event-Driven con EventBridge**:
- Desacoplamiento total entre componentes
- Escalabilidad automática
- Facilita agregar nuevos canales de entrada sin modificar código existente
- Permite replay de eventos para debugging

**Bedrock AgentCore como Orquestador**:
- Razonamiento complejo multi-paso sin código hardcodeado
- Aprendizaje continuo mediante AgentCore Memory
- Observabilidad nativa con AgentCore Observability
- Herramientas MCP permiten extensibilidad

**Dual Storage (S3 + DynamoDB)**:
- S3: Almacenamiento versionado de archivos JSON (rutas, incidencias)
- DynamoDB: Consultas rápidas transaccionales (< 10ms)
- Sincronización bidireccional mediante Lambda triggers
- DynamoDB es fuente de verdad para operaciones en tiempo real

**Serverless 100%**:
- Cero gestión de infraestructura
- Auto-scaling automático
- Pago por uso (costo < $0.50 por incidente)
- Alta disponibilidad nativa

## Componentes e Interfaces

### 1. Capa de Ingesta de Eventos

#### 1.1 Amazon Connect + Transcribe (Canal Voz)

**Responsabilidad**: Recibir llamadas de conductores, transcribir audio, extraer datos estructurados

**Flujo**:
```
Conductor llama → Connect IVR → Transcribe (streaming) → Lambda (NLP extraction) → EventBridge
```

**Lambda: extract_incident_from_voice**
- Input: Transcripción de Transcribe
- Procesamiento: Usa Bedrock (Claude) para extraer: truck_id, tipo_incidente, ubicación, descripción
- Output: Evento estructurado a EventBridge

**Estructura del Evento**:
```json
{
  "source": "smartsupply.voice",
  "detail-type": "IncidentDetected",
  "detail": {
    "incident_id": "INC-{timestamp}-{random}",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410},
    "timestamp": "2026-02-17T14:15:00Z",
    "descripcion": "Impacto lateral severo...",
    "canal": "voz"
  }
}
```

#### 1.2 Amplify + API Gateway (Canal Web)

**Responsabilidad**: Recibir reportes desde formulario web

**API Endpoint**: `POST /api/incidents`

**Lambda: receive_web_incident**
- Input: JSON desde formulario web
- Validación: truck_id existe, ubicación válida, tipo_incidente en enum
- Output: Evento a EventBridge (misma estructura que voz)

**Frontend (Amplify)**:
- Formulario con campos: truck_id (dropdown), tipo_incidente (select), ubicación (mapa interactivo), descripción (textarea)
- Validación client-side antes de enviar
- Feedback visual de envío exitoso

#### 1.3 IoT Sensors + Kinesis (Canal IoT)

**Responsabilidad**: Procesar stream de telemetría de sensores G-Force

**Flujo**:
```
Sensor → Kinesis Data Stream → Lambda (batch processor) → EventBridge
```

**Lambda: process_iot_telemetry**
- Input: Batch de eventos Kinesis
- Lógica de clasificación:
  - `sensor_telemetria_g > 4.0` → "Choque / Colisión Grave" (Crítico)
  - `2.0 < sensor_telemetria_g <= 4.0` → "Falla Mecánica" (Alto)
  - `sensor_telemetria_g < 2.0` → Analizar contexto (Robo o Falla Cadena Frío)
- Output: Evento a EventBridge

**Simulación**: Lambda lee `4_registro_incidencias.json` desde S3 y publica eventos a frecuencia configurable

### 2. Bedrock AgentCore - Motor de Decisiones

#### 2.1 Configuración del Agent

**Modelo**: Claude 3.5 Sonnet (razonamiento complejo)

**Instrucciones del Agent**:
```
Eres un experto en logística y gestión de crisis. Tu objetivo es analizar incidentes 
en operaciones de entrega y generar planes de reasignación óptimos en menos de 3 minutos.

Proceso de análisis:
1. Consulta la ruta afectada y el inventario del camión
2. Identifica productos dañados/perdidos y su criticidad
3. Consulta flota disponible considerando: capacidad, nivel de fatiga, distancia
4. Consulta inventario del almacén para reabastecimiento
5. Prioriza por: Farma > Salud > Tecnología > Industrial > otros
6. Genera plan con: camión de reemplazo, productos a reabastecer, rutas actualizadas
7. Justifica cada decisión con datos concretos

Restricciones:
- Nivel de fatiga Alto → excluir camión
- Productos frágiles → priorizar camiones con menor fatiga
- Tiempo total de ejecución < 180 segundos
```

#### 2.2 Herramientas MCP (AgentCore Gateway)

**Tool 1: consultar_ruta_afectada**
```python
def consultar_ruta_afectada(truck_id: str) -> dict:
    """
    Consulta DynamoDB para obtener ruta completa del camión afectado
    Returns: {
        "truck_id": str,
        "conductor": str,
        "paradas": [{"stop_id", "cliente", "items_a_entregar", "estado"}],
        "fecha_ruta": str
    }
    """
```

**Tool 2: consultar_flota_disponible**
```python
def consultar_flota_disponible() -> list[dict]:
    """
    Consulta DynamoDB tabla flota_camiones
    Returns: [{
        "truck_id": str,
        "conductor": str,
        "capacidad_max_ton": float,
        "nivel_fatiga": str,  # Alto, Medio, Bajo
        "ubicacion_actual": {"lat": float, "lon": float}
    }]
    """
```

**Tool 3: consultar_inventario_almacen**
```python
def consultar_inventario_almacen(skus: list[str]) -> list[dict]:
    """
    Consulta DynamoDB tabla inventario_almacen
    Returns: [{
        "sku": str,
        "nombre_producto": str,
        "cantidad_disponible_almacen": int,
        "es_fragil": bool,
        "prioridad_negocio": str,
        "ubicacion_pasillo": str
    }]
    """
```

**Tool 4: calcular_distancia**
```python
def calcular_distancia(origen: dict, destino: dict) -> float:
    """
    Calcula distancia en km usando Location Service
    Args:
        origen: {"lat": float, "lon": float}
        destino: {"lat": float, "lon": float}
    Returns: distancia en km
    """
```

**Tool 5: actualizar_ruta_s3**
```python
def actualizar_ruta_s3(truck_id: str, nueva_ruta: dict) -> bool:
    """
    Escribe JSON de ruta actualizada en S3
    Path: s3://smart-supply-data/rutas/{fecha}/{truck_id}.json
    Habilita versionamiento automático
    """
```

**Tool 6: registrar_incidencia**
```python
def registrar_incidencia(incidente: dict) -> str:
    """
    Escribe incidencia en S3 y DynamoDB
    S3: s3://smart-supply-data/incidencias/{año}/{mes}/{incidente_id}.json
    DynamoDB: tabla incidencias
    Returns: incidente_id
    """
```

**Tool 7: enviar_notificacion_cliente**
```python
def enviar_notificacion_cliente(cliente_id: str, mensaje: str, prioridad: str) -> bool:
    """
    Envía notificación vía Amazon Connect (outbound call)
    Si prioridad == "Crítica" → llamada inmediata
    Si prioridad == "Alta" → llamada con retry
    Si prioridad == "Baja" → SMS/email
    """
```

#### 2.3 AgentCore Memory

**Memoria de Corto Plazo** (sesión actual):
- Contexto del incidente actual
- Datos consultados (rutas, flota, inventario)
- Decisiones intermedias

**Memoria de Largo Plazo** (DynamoDB tabla: agent_memory):
```json
{
  "memory_id": "MEM-{timestamp}",
  "tipo_incidente": "Choque / Colisión Grave",
  "decision_tomada": {
    "camion_reemplazo": "3",
    "productos_reabastecidos": ["FAR-001"],
    "justificacion": "Camión 3 más cercano con capacidad..."
  },
  "resultado": {
    "tiempo_respuesta_segundos": 145,
    "satisfaccion_cliente": 4.5,
    "valor_perdidas_evitadas_usd": 15000
  },
  "timestamp": "2026-02-17T14:18:25Z"
}
```

**Uso**: Agent consulta memoria antes de decidir para aprender de casos similares previos

#### 2.4 AgentCore Observability

**Métricas Rastreadas**:
- Latencia por invocación (target: < 30s)
- Herramientas más usadas
- Tasa de éxito (plan ejecutado vs plan fallido)
- Tokens consumidos por invocación

**Dashboard CloudWatch**:
- Gráfico de latencia P50, P90, P99
- Conteo de invocaciones por hora
- Alertas cuando latencia > 30s

**Tracing**: Cada invocación genera trace con:
- Input completo (evento de incidente)
- Herramientas invocadas y sus outputs
- Razonamiento intermedio (chain-of-thought)
- Output final (plan de reasignación)

### 3. Capa de Persistencia

#### 3.1 DynamoDB

**Tabla: rutas_entregas**
- Partition Key: `truck_id`
- Sort Key: `fecha_ruta`
- Atributos: conductor, paradas (list), estado_ruta
- GSI: `estado_ruta-index` para consultas por estado

**Tabla: flota_camiones**
- Partition Key: `truck_id`
- Atributos: placas, conductor, capacidad_max_ton, nivel_fatiga, ubicacion_actual, ultimo_mantenimiento

**Tabla: inventario_almacen**
- Partition Key: `sku`
- Atributos: nombre_producto, categoria, es_fragil, cantidad_disponible_almacen, cantidad_en_ruta, prioridad_negocio

**Tabla: incidencias**
- Partition Key: `incidente_id`
- Sort Key: `timestamp`
- Atributos: truck_id, tipo_incidente, nivel_gravedad, ubicacion_gps, inventario_afectado, acciones_tomadas, tiempo_respuesta_segundos
- GSI: `truck_id-timestamp-index` para consultas por camión

**Tabla: agent_memory**
- Partition Key: `memory_id`
- Sort Key: `timestamp`
- Atributos: tipo_incidente, decision_tomada, resultado
- GSI: `tipo_incidente-index` para consultas por tipo

#### 3.2 S3

**Bucket: smart-supply-data**

**Estructura**:
```
s3://smart-supply-data/
├── rutas/
│   └── 2026-02-17/
│       ├── 1.json
│       ├── 2.json
│       ├── 3.json
│       └── 4.json
├── incidencias/
│   └── 2026/
│       └── 02/
│           ├── INC-901.json
│           ├── INC-772.json
│           └── ...
└── config/
    ├── 1_rutas_entregas_2026_02_17.json (inicial)
    ├── 2_flota_camiones.csv (inicial)
    ├── 3_inventario_almacen.csv (inicial)
    └── 4_registro_incidencias.json (simulación)
```

**Versionamiento**: Habilitado en todo el bucket para historial de cambios

**Lambda Triggers**:
- `s3_to_dynamodb_sync`: Cuando se actualiza JSON en S3 → parsea y actualiza DynamoDB
- `dynamodb_to_s3_sync`: Stream de DynamoDB → genera JSON y escribe en S3

### 4. Capa de Visualización

#### 4.1 Amazon Location Service

**Map**: Mapa base de OpenStreetMap

**Recursos**:
- **Place Index**: Para geocodificación de direcciones
- **Route Calculator**: Para cálculo de distancias y rutas optimizadas
- **Tracker**: Para tracking de posición de camiones en tiempo real

**API Lambda: get_fleet_locations**
```python
def get_fleet_locations() -> list[dict]:
    """
    Consulta DynamoDB y retorna posiciones actuales de todos los camiones
    Returns: [{
        "truck_id": str,
        "lat": float,
        "lon": float,
        "estado": str,  # "En ruta", "Incidente", "Disponible"
        "conductor": str
    }]
    """
```

**API Lambda: get_incident_markers**
```python
def get_incident_markers() -> list[dict]:
    """
    Consulta DynamoDB tabla incidencias (últimas 24h)
    Returns: [{
        "incidente_id": str,
        "lat": float,
        "lon": float,
        "tipo": str,
        "gravedad": str,
        "timestamp": str
    }]
    """
```

#### 4.2 QuickSight Dashboard

**Dataset Sources**:
- DynamoDB tabla incidencias (vía Athena query)
- DynamoDB tabla rutas_entregas
- DynamoDB tabla agent_memory

**Visualizaciones**:

1. **KPI Cards**:
   - Total incidentes (hoy)
   - Tiempo promedio de respuesta
   - Valor de pérdidas evitadas (USD)
   - Tasa de éxito de reasignaciones

2. **Gráfico de Barras**: Incidentes por tipo (Choque, Robo, Falla Mecánica, Falla Cadena Frío)

3. **Gráfico de Línea**: Tiempo de respuesta por hora (últimas 24h)

4. **Tabla**: Top 10 incidentes por valor de pérdida

5. **Gráfico de Dona**: Distribución de gravedad (Crítico, Alto, Medio, Bajo)

6. **Mapa de Calor**: Zonas geográficas con mayor incidencia

**Refresh**: Auto-refresh cada 60 segundos

#### 4.3 Amplify Frontend

**Tecnología**: JavaScript vanilla + AWS Amplify SDK

**Páginas**:

1. **Dashboard Principal** (`/`):
   - Mapa con Location Service (camiones + incidentes)
   - KPIs en tiempo real
   - Lista de incidentes recientes

2. **Reportar Incidente** (`/report`):
   - Formulario con validación
   - Selector de ubicación en mapa
   - Confirmación de envío

3. **Detalle de Incidente** (`/incident/:id`):
   - Información completa del incidente
   - Plan de reasignación generado por Agent
   - Timeline de acciones tomadas

4. **Flota** (`/fleet`):
   - Tabla con estado de todos los camiones
   - Filtros por estado, nivel de fatiga
   - Detalle de ruta al hacer clic

**Autenticación**: Amplify Auth (Cognito) para acceso seguro

**APIs Consumidas**:
- `GET /api/incidents` - Lista de incidentes
- `POST /api/incidents` - Crear incidente
- `GET /api/fleet` - Estado de flota
- `GET /api/locations` - Posiciones para mapa

### 5. Capa de Notificaciones

#### 5.1 Amazon Connect Outbound

**Flujo de Llamada**:
```
Lambda trigger → Connect StartOutboundVoiceContact → 
Cliente contesta → Reproducir mensaje TTS → 
Registrar resultado en DynamoDB
```

**Lambda: send_customer_notification**
```python
def send_customer_notification(cliente_id: str, nuevo_horario: str, motivo: str):
    """
    1. Consulta DynamoDB para obtener teléfono del cliente
    2. Genera mensaje personalizado:
       "Estimado {cliente}, su entrega programada para {horario_original} 
        ha sido reprogramada para {nuevo_horario} debido a {motivo}. 
        Disculpe las molestias."
    3. Invoca Connect StartOutboundVoiceContact
    4. Si no contesta → programa retry en 15 minutos (máximo 3 intentos)
    5. Registra resultado en DynamoDB
    """
```

**Priorización**:
- Clientes con productos de prioridad "Crítica" (Farma, Salud) → llamada inmediata
- Clientes con prioridad "Alta" → llamada con retry
- Clientes con prioridad "Baja" → SMS o email (futuro)

## Modelos de Datos

### Evento de Incidente (EventBridge)

```json
{
  "source": "smartsupply.{canal}",
  "detail-type": "IncidentDetected",
  "detail": {
    "incident_id": "INC-{timestamp}-{random}",
    "truck_id": "string",
    "tipo_incidente": "enum[Choque, Robo, Falla Mecánica, Falla Cadena Frío]",
    "nivel_gravedad": "enum[Crítico, Alto, Medio, Bajo]",
    "ubicacion_gps": {
      "lat": "float",
      "lon": "float"
    },
    "timestamp": "ISO8601",
    "descripcion": "string",
    "canal": "enum[voz, web, iot]",
    "sensor_telemetria_g": "float (opcional, solo IoT)"
  }
}
```

### Ruta de Entrega (S3 + DynamoDB)

```json
{
  "truck_id": "string",
  "fecha_ruta": "YYYY-MM-DD",
  "conductor_asignado": "string",
  "estado_ruta": "enum[Activa, Completada, Incidente, Reasignada]",
  "paradas": [
    {
      "stop_id": "string",
      "hora_programada": "HH:MM",
      "latitud": "float",
      "longitud": "float",
      "cliente": "string",
      "direccion": "string",
      "items_a_entregar": [
        {
          "sku": "string",
          "producto": "string",
          "cantidad": "int",
          "es_fragil": "boolean",
          "valor_total_envio_usd": "float"
        }
      ],
      "estado_entrega": "enum[Pendiente, En Camino, Entregada, Reasignada, Cancelada]"
    }
  ]
}
```

### Plan de Reasignación (Output del Agent)

```json
{
  "plan_id": "PLAN-{timestamp}",
  "incidente_id": "string",
  "timestamp_generacion": "ISO8601",
  "camion_reemplazo": {
    "truck_id": "string",
    "conductor": "string",
    "justificacion": "string"
  },
  "productos_a_reabastecer": [
    {
      "sku": "string",
      "cantidad": "int",
      "origen": "Almacén",
      "ubicacion_pasillo": "string"
    }
  ],
  "rutas_actualizadas": [
    {
      "truck_id": "string",
      "paradas_agregadas": ["array de stop_id"],
      "paradas_removidas": ["array de stop_id"],
      "nuevo_horario_estimado": "HH:MM"
    }
  ],
  "clientes_a_notificar": [
    {
      "cliente_id": "string",
      "prioridad_notificacion": "enum[Crítica, Alta, Baja]",
      "nuevo_horario": "HH:MM",
      "motivo": "string"
    }
  ],
  "metricas": {
    "tiempo_generacion_segundos": "float",
    "valor_perdidas_evitadas_usd": "float",
    "numero_clientes_impactados": "int"
  }
}
```

### Incidencia Registrada (DynamoDB + S3)

```json
{
  "incidente_id": "string (PK)",
  "timestamp": "ISO8601 (SK)",
  "truck_id": "string",
  "tipo_incidente": "string",
  "nivel_gravedad": "string",
  "ubicacion_gps": {
    "lat": "float",
    "lon": "float"
  },
  "sensor_telemetria_g": "float",
  "descripcion_evento": "string",
  "inventario_afectado": [
    {
      "sku": "string",
      "producto": "string",
      "categoria": "string",
      "cantidad": "int",
      "valor_unitario_usd": "float",
      "estado_bien": "string",
      "prioridad_reposicion": "string"
    }
  ],
  "valor_total_perdida_estimada": "float",
  "plan_reasignacion": {
    "plan_id": "string",
    "camion_reemplazo": "string",
    "productos_reabastecidos": ["array"],
    "clientes_notificados": "int"
  },
  "tiempo_respuesta_segundos": "float",
  "estado_resolucion": "enum[Pendiente, En Proceso, Resuelto, Escalado]"
}
```



## Propiedades de Correctitud

Una propiedad es una característica o comportamiento que debe mantenerse verdadero en todas las ejecuciones válidas del sistema - esencialmente, una declaración formal sobre lo que el sistema debe hacer. Las propiedades sirven como puente entre especificaciones legibles por humanos y garantías de correctitud verificables por máquina.

### Propiedad 1: Normalización Multicanal de Eventos

*Para cualquier* incidente reportado por cualquier canal (voz, web, IoT), el evento publicado a EventBridge debe contener la estructura estandarizada con todos los campos requeridos: incident_id, truck_id, tipo_incidente, nivel_gravedad, ubicacion_gps, timestamp, descripcion, canal.

**Valida: Requisitos 1.1, 1.2, 1.3, 1.4, 1.5**

### Propiedad 2: Invocación de Herramientas del Agent

*Para cualquier* incidente procesado por Bedrock Agent, el agent debe invocar las herramientas de consulta necesarias: consultar_ruta_afectada, consultar_flota_disponible, consultar_inventario_almacen.

**Valida: Requisitos 2.3**

### Propiedad 3: Completitud del Plan de Reasignación

*Para cualquier* plan de reasignación generado por Bedrock Agent, el plan debe contener todos los campos requeridos: camion_reemplazo (con justificación), productos_a_reabastecer, rutas_actualizadas, clientes_a_notificar, metricas (tiempo_generacion_segundos, valor_perdidas_evitadas_usd).

**Valida: Requisitos 2.4, 2.8**

### Propiedad 4: Priorización por Criticidad

*Para cualquier* conjunto de incidentes con diferentes categorías de productos, el orden de procesamiento debe respetar: Farma > Salud > Tecnología > Industrial > otros.

**Valida: Requisitos 2.5**

### Propiedad 5: Priorización de Productos Frágiles

*Para cualquier* par de incidentes idénticos donde uno involucra productos frágiles (es_fragil=true) y el otro no, el incidente con productos frágiles debe tener mayor prioridad de reasignación.

**Valida: Requisitos 2.6, 10.1**

### Propiedad 6: Consideración de Variables de Decisión

*Para cualquier* plan de reasignación, la justificación debe mencionar o considerar las variables clave: capacidad de carga, distancia desde almacén, horarios de entrega.

**Valida: Requisitos 2.7**

### Propiedad 7: Aprendizaje Continuo del Agent

*Para cualquier* incidente procesado completamente, debe existir un registro en la tabla agent_memory de DynamoDB con: tipo_incidente, decision_tomada, resultado.

**Valida: Requisitos 2.10**

### Propiedad 8: Selección del Camión Más Cercano

*Para cualquier* reasignación donde existe un camión disponible, el camión seleccionado debe ser el más cercano al punto del incidente entre todos los camiones disponibles (excluyendo aquellos con fatiga Alta).

**Valida: Requisitos 3.1**

### Propiedad 9: División de Carga por Capacidad Insuficiente

*Para cualquier* reasignación donde la carga total excede la capacidad del camión más cercano, el plan debe asignar múltiples camiones cuya capacidad combinada sea suficiente.

**Valida: Requisitos 3.2**

### Propiedad 10: Exclusión de Conductores con Fatiga Alta

*Para cualquier* plan de reasignación generado, ningún camión con nivel_fatiga="Alto" debe ser seleccionado como camión de reemplazo.

**Valida: Requisitos 3.3, 10.2**

### Propiedad 11: Reabastecimiento desde Almacén

*Para cualquier* incidente donde productos afectados tienen cantidad_disponible_almacen > 0, el plan debe incluir una orden de reabastecimiento para esos productos.

**Valida: Requisitos 3.5**

### Propiedad 12: Recalculo de Horarios

*Para cualquier* ruta reasignada, los nuevos horarios de entrega deben ser posteriores a los horarios originales (considerando el tiempo adicional de viaje).

**Valida: Requisitos 3.6**

### Propiedad 13: Persistencia Completa de Reasignación

*Para cualquier* reasignación completada, deben actualizarse todas las tablas relevantes en DynamoDB: rutas_entregas (con nuevas paradas), incidencias (con registro completo), flota_camiones (con ubicaciones actualizadas).

**Valida: Requisitos 4.1, 4.2, 4.4**

### Propiedad 14: Invariante de Inventario del Almacén

*Para cualquier* producto en el inventario, la invariante debe mantenerse: cantidad_total = cantidad_disponible_almacen + cantidad_en_ruta. Cuando se reasignan productos, cantidad_disponible_almacen debe decrementar y cantidad_en_ruta debe incrementar por la misma cantidad.

**Valida: Requisitos 4.3, 11.4, 11.5**

### Propiedad 15: Registro de Timestamps para Auditoría

*Para cualquier* registro creado o actualizado en DynamoDB (incidencias, rutas, notificaciones), debe incluir un campo timestamp con formato ISO8601.

**Valida: Requisitos 4.5**

### Propiedad 16: Reintentos ante Fallos

*Para cualquier* operación de actualización de DynamoDB que falla, el sistema debe reintentar exactamente 3 veces antes de escalar el error.

**Valida: Requisitos 4.6**

### Propiedad 17: Completitud de APIs de Visualización

*Para cualquier* camión o incidente consultado vía API, la respuesta debe contener todos los campos requeridos. Para camiones: conductor, carga_actual, proxima_parada, nivel_fatiga. Para incidentes: tipo, gravedad, inventario_afectado, acciones_tomadas.

**Valida: Requisitos 5.5, 5.6**

### Propiedad 18: Cálculo Correcto de KPIs

*Para cualquier* conjunto de incidentes en un período, los KPIs calculados deben ser correctos: total_incidentes = count(incidentes), valor_perdidas = sum(valor_total_perdida_estimada), tiempo_promedio_respuesta = avg(tiempo_respuesta_segundos).

**Valida: Requisitos 6.1, 6.2, 6.3**

### Propiedad 19: Alertas de Stock Bajo

*Para cualquier* producto en inventario donde cantidad_disponible_almacen < umbral_minimo (10% de cantidad_total), debe generarse una alerta de stock crítico.

**Valida: Requisitos 6.4**

### Propiedad 20: Filtrado Correcto de Datos

*Para cualquier* consulta con filtros aplicados (rango de fechas, tipo de incidente), todos los registros retornados deben cumplir exactamente los criterios del filtro.

**Valida: Requisitos 6.6**

### Propiedad 21: Identificación de Clientes Afectados

*Para cualquier* reasignación de paradas, el sistema debe identificar correctamente todos los clientes cuyas entregas fueron afectadas consultando las paradas reasignadas o canceladas.

**Valida: Requisitos 7.1**

### Propiedad 22: Completitud de Notificaciones a Clientes

*Para cualquier* notificación enviada a un cliente, el mensaje debe contener: nuevo_horario_estimado, motivo_del_cambio, numero_seguimiento. El registro en DynamoDB debe contener: cliente_id, timestamp_notificacion, canal_usado, estado_entrega.

**Valida: Requisitos 7.2, 7.5**

### Propiedad 23: Notificación Prioritaria por Connect

*Para cualquier* cliente con productos de prioridad_negocio="Crítica" (Farma, Salud), el sistema debe enviar notificación vía Amazon Connect (llamada saliente) en lugar de otros canales.

**Valida: Requisitos 7.3**

### Propiedad 24: Reintentos de Llamadas No Contestadas

*Para cualquier* llamada de Connect que no es contestada, el sistema debe programar un reintento después de exactamente 15 minutos, con máximo 3 intentos totales.

**Valida: Requisitos 7.4**

### Propiedad 25: Tiempo de Respuesta Menor a 3 Minutos

*Para cualquier* incidente procesado, el tiempo_respuesta_segundos registrado en DynamoDB debe ser menor a 180 segundos.

**Valida: Requisitos 8.1, 8.2**

### Propiedad 26: Registro de KPIs de Negocio

*Para cualquier* incidente completado, el sistema debe calcular y registrar: reduccion_tiempo_vs_manual (en segundos), valor_perdidas_evitadas_usd, tasa_exito_reasignacion (booleano).

**Valida: Requisitos 8.4**

### Propiedad 27: Priorización de Incidentes Críticos

*Para cualquier* cola de incidentes pendientes, los incidentes con nivel_gravedad="Crítico" deben procesarse antes que aquellos con gravedad "Alto", "Medio" o "Bajo".

**Valida: Requisitos 8.6**

### Propiedad 28: Clasificación Correcta por G-Force

*Para cualquier* evento de sensor IoT, la clasificación debe ser correcta según el valor de sensor_telemetria_g:
- Si g > 4.0 → "Choque / Colisión Grave" (Crítico)
- Si 2.0 < g ≤ 4.0 → "Falla Mecánica" (Alto)
- Si g ≤ 2.0 → "Robo" o "Falla Cadena de Frío" (según contexto)

**Valida: Requisitos 9.2, 9.3, 9.4**

### Propiedad 29: Publicación de Eventos Simulados

*Para cualquier* evento leído desde 4_registro_incidencias.json, el sistema debe publicar un evento válido a EventBridge o Kinesis con la estructura estandarizada.

**Valida: Requisitos 9.5**

### Propiedad 30: Validación de Capacidad para Carga Frágil

*Para cualquier* reasignación de productos frágiles, el camión seleccionado debe tener capacidad_max_ton suficiente para la carga total de productos frágiles.

**Valida: Requisitos 10.3**

### Propiedad 31: Notificación Especial para Productos Frágiles

*Para cualquier* reasignación que incluye productos frágiles, debe existir una notificación al conductor con instrucciones especiales de manejo.

**Valida: Requisitos 10.4**

### Propiedad 32: Registro de Manejo Especial

*Para cualquier* incidente con productos frágiles, el registro en DynamoDB debe incluir un flag manejo_especial=true.

**Valida: Requisitos 10.5**

### Propiedad 33: Verificación de Disponibilidad en Almacén

*Para cualquier* orden de reabastecimiento generada, el sistema debe haber verificado previamente que cantidad_disponible_almacen >= cantidad_solicitada para cada producto.

**Valida: Requisitos 11.2**

### Propiedad 34: Alerta de Stock Insuficiente

*Para cualquier* intento de reabastecimiento donde cantidad_disponible_almacen < cantidad_solicitada, el sistema debe generar una alerta de stock crítico.

**Valida: Requisitos 11.3**

### Propiedad 35: Inclusión de Ubicación de Pasillo

*Para cualquier* orden de reabastecimiento, cada producto debe incluir el campo ubicacion_pasillo para facilitar el picking en almacén.

**Valida: Requisitos 11.6**

### Propiedad 36: Persistencia Correcta en S3

*Para cualquier* ruta actualizada o incidencia registrada, debe existir un archivo JSON correspondiente en S3 con la estructura de path correcta:
- Rutas: s3://smart-supply-data/rutas/{fecha}/{truck_id}.json
- Incidencias: s3://smart-supply-data/incidencias/{año}/{mes}/{incidente_id}.json

**Valida: Requisitos 12.1, 12.2, 12.3**

### Propiedad 37: Sincronización S3 a EventBridge

*Para cualquier* actualización de archivo JSON en S3, el sistema debe publicar un evento a EventBridge para disparar la sincronización con DynamoDB.

**Valida: Requisitos 12.6**

### Propiedad 38: Sincronización Bidireccional S3-DynamoDB (Round-Trip)

*Para cualquier* ruta actualizada, si se escribe en DynamoDB, debe reflejarse en S3, y viceversa. La sincronización debe ser bidireccional: DynamoDB → S3 → DynamoDB debe producir el mismo estado.

**Valida: Requisitos 13.1, 13.2**

### Propiedad 39: Validación Client-Side de Formulario

*Para cualquier* intento de envío del formulario web de reporte de incidentes, si algún campo requerido está vacío, el sistema debe prevenir el envío y mostrar mensaje de error.

**Valida: Requisitos 15.4**

### Propiedad 40: Rastreo de Invocaciones del Agent

*Para cualquier* invocación de Bedrock Agent, AgentCore Observability debe crear un registro de tracing con: timestamp, input, output, latencia, herramientas_usadas.

**Valida: Requisitos 18.1**

### Propiedad 41: Evaluación de Calidad de Decisiones

*Para cualquier* incidente completado, AgentCore Evaluations debe generar una evaluación comparando: plan_generado vs resultado_real, satisfaccion_cliente, valor_perdidas_evitadas.

**Valida: Requisitos 18.4**

## Manejo de Errores

### Estrategia General

El sistema implementa manejo de errores en múltiples capas:

1. **Validación de Entrada**: Todos los endpoints de API Gateway validan payloads antes de procesamiento
2. **Reintentos Automáticos**: Lambda configurado con retry policy (3 intentos con backoff exponencial)
3. **Dead Letter Queues**: Eventos que fallan después de 3 reintentos van a DLQ para análisis
4. **Circuit Breaker**: Si Bedrock Agent falla consistentemente, se activa modo degradado
5. **Alertas CloudWatch**: Errores críticos disparan alarmas a equipo de operaciones

### Casos de Error Específicos

**Error 1: Bedrock Agent No Responde**
- Timeout: 30 segundos
- Acción: Reintentar hasta 3 veces
- Si falla: Escalar a operador humano, registrar en DLQ

**Error 2: DynamoDB Throttling**
- Acción: Backoff exponencial automático (SDK)
- Si persiste: Aumentar capacidad provisionada automáticamente

**Error 3: S3 Write Failure**
- Acción: Reintentar hasta 3 veces
- Si falla: Continuar con DynamoDB como fuente de verdad, registrar inconsistencia

**Error 4: Connect Call Failure**
- Acción: Programar retry en 15 minutos
- Máximo 3 intentos
- Si falla: Enviar SMS/email como fallback

**Error 5: Datos Inválidos en Evento**
- Acción: Validar schema con JSON Schema
- Si inválido: Rechazar evento, registrar en CloudWatch Logs, no procesar

**Error 6: Camión No Encontrado**
- Acción: Verificar que truck_id existe en tabla flota_camiones
- Si no existe: Retornar error 404, solicitar corrección

**Error 7: Inventario Insuficiente**
- Acción: Generar alerta de stock crítico
- Buscar productos alternativos o proveedores externos
- Notificar a gerente de inventario

### Logging y Observabilidad

**CloudWatch Logs**:
- Todos los Lambda functions logean: input, output, errores, latencia
- Nivel de log configurable: DEBUG, INFO, WARN, ERROR
- Retención: 30 días

**CloudWatch Metrics**:
- Invocaciones por función
- Errores por tipo
- Latencia P50, P90, P99
- Costo por invocación

**X-Ray Tracing**:
- Tracing end-to-end de cada incidente
- Visualización de cuellos de botella
- Análisis de dependencias entre servicios

## Estrategia de Testing

### Enfoque Dual: Unit Tests + Property-Based Tests

El sistema requiere dos tipos complementarios de testing:

**Unit Tests**: Verifican ejemplos específicos, casos borde y condiciones de error
- Útiles para casos concretos y edge cases
- Validan integraciones entre componentes
- Prueban manejo de errores específicos

**Property-Based Tests**: Verifican propiedades universales sobre todos los inputs
- Generan cientos de inputs aleatorios
- Validan correctitud general del sistema
- Descubren bugs inesperados

Ambos son necesarios para cobertura completa: unit tests capturan bugs concretos, property tests verifican correctitud general.

### Configuración de Property-Based Testing

**Librería**: Hypothesis (Python) para Lambda functions, fast-check (JavaScript) para frontend

**Configuración**:
- Mínimo 100 iteraciones por property test
- Cada test debe referenciar su propiedad del documento de diseño
- Formato de tag: `# Feature: smart-supply, Property {número}: {texto de propiedad}`

**Ejemplo de Property Test**:

```python
from hypothesis import given, strategies as st
import pytest

# Feature: smart-supply, Property 1: Normalización Multicanal de Eventos
@given(
    canal=st.sampled_from(['voz', 'web', 'iot']),
    truck_id=st.integers(min_value=1, max_value=4),
    tipo=st.sampled_from(['Choque', 'Robo', 'Falla Mecánica', 'Falla Cadena Frío']),
    lat=st.floats(min_value=19.0, max_value=20.0),
    lon=st.floats(min_value=-100.0, max_value=-99.0)
)
def test_multicanal_normalization(canal, truck_id, tipo, lat, lon):
    """
    Property 1: Para cualquier incidente de cualquier canal,
    el evento debe tener estructura estandarizada
    """
    evento = procesar_incidente(canal, truck_id, tipo, lat, lon)
    
    # Verificar campos requeridos
    assert 'incident_id' in evento
    assert 'truck_id' in evento
    assert 'tipo_incidente' in evento
    assert 'nivel_gravedad' in evento
    assert 'ubicacion_gps' in evento
    assert 'timestamp' in evento
    assert 'descripcion' in evento
    assert 'canal' in evento
    
    # Verificar tipos correctos
    assert isinstance(evento['truck_id'], str)
    assert evento['canal'] == canal
    assert evento['ubicacion_gps']['lat'] == lat
    assert evento['ubicacion_gps']['lon'] == lon
```

### Unit Tests Específicos

**Test 1: Extracción de Datos desde Voz**
```python
def test_extract_incident_from_voice_specific_example():
    """
    Ejemplo específico: Transcripción de choque
    """
    transcripcion = "Soy el conductor del camión 1, tuve un choque en Reforma y Juárez"
    resultado = extract_incident_from_voice(transcripcion)
    
    assert resultado['truck_id'] == '1'
    assert resultado['tipo_incidente'] == 'Choque / Colisión Grave'
    assert 'Reforma' in resultado['descripcion']
```

**Test 2: Clasificación de G-Force en Límites**
```python
def test_gforce_classification_boundary_cases():
    """
    Edge cases: Valores exactos en límites de rangos
    """
    assert classify_incident(4.0) == 'Choque / Colisión Grave'
    assert classify_incident(4.1) == 'Choque / Colisión Grave'
    assert classify_incident(2.0) in ['Robo', 'Falla Cadena de Frío']
    assert classify_incident(2.1) == 'Falla Mecánica'
```

**Test 3: Manejo de Inventario Insuficiente**
```python
def test_insufficient_inventory_alert():
    """
    Error case: Inventario insuficiente debe generar alerta
    """
    incidente = crear_incidente_con_productos(['FAR-001'], cantidad=100)
    inventario_almacen = {'FAR-001': {'cantidad_disponible': 50}}
    
    plan = bedrock_agent.generar_plan(incidente, inventario_almacen)
    
    assert plan['alertas']['stock_critico'] == True
    assert 'FAR-001' in plan['alertas']['productos_insuficientes']
```

### Tests de Integración

**Test 1: Flujo End-to-End Completo**
```python
def test_e2e_incident_to_reassignment():
    """
    Flujo completo: Incidente → Agent → Reasignación → Notificación
    """
    # 1. Publicar evento de incidente
    evento = publicar_incidente_test(truck_id='1', tipo='Choque')
    
    # 2. Esperar procesamiento (max 180 segundos)
    time.sleep(5)
    
    # 3. Verificar que se generó plan
    plan = consultar_plan_by_incidente(evento['incident_id'])
    assert plan is not None
    assert 'camion_reemplazo' in plan
    
    # 4. Verificar que se actualizó DynamoDB
    ruta = consultar_ruta(truck_id='1')
    assert ruta['estado_ruta'] == 'Incidente'
    
    # 5. Verificar que se notificó a clientes
    notificaciones = consultar_notificaciones_by_incidente(evento['incident_id'])
    assert len(notificaciones) > 0
```

### Cobertura de Testing

**Objetivo**: 80% de cobertura de código

**Prioridades**:
1. Lógica de negocio crítica (clasificación, priorización): 100%
2. Herramientas MCP del Agent: 90%
3. Lambda functions de procesamiento: 85%
4. APIs de visualización: 75%
5. Frontend: 70%

**Herramientas**:
- pytest + pytest-cov para Python
- Jest para JavaScript
- Moto para mocking de servicios AWS
- LocalStack para testing local de AWS services

### CI/CD Pipeline

**Stages**:
1. **Lint**: Verificar estilo de código (pylint, eslint)
2. **Unit Tests**: Ejecutar todos los unit tests
3. **Property Tests**: Ejecutar property-based tests (100 iteraciones)
4. **Integration Tests**: Ejecutar tests e2e en ambiente de staging
5. **Deploy**: Desplegar a producción si todos los tests pasan

**Criterios de Aprobación**:
- Todos los tests deben pasar
- Cobertura >= 80%
- No errores de linting
- Performance tests: tiempo de respuesta < 3 minutos

