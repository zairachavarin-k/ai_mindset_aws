# AgentCore Memory Configuration

Esta guía explica cómo configurar AgentCore Memory para permitir que el agente aprenda de decisiones previas y mejore continuamente.

## Conceptos Clave

### ¿Qué es AgentCore Memory?

AgentCore Memory es un sistema de gestión de memoria que permite a los Bedrock Agents:
- **Memoria de Corto Plazo (STM)**: Contexto de la conversación/sesión actual
- **Memoria de Largo Plazo (LTM)**: Aprendizaje persistente de interacciones pasadas

### Beneficios para SmartSupply

El agente autónomo usa memoria para:
1. **Aprender de decisiones previas**: Consultar casos similares antes de decidir
2. **Mejorar con el tiempo**: Identificar patrones en incidentes y reasignaciones
3. **Justificar decisiones**: Referenciar casos exitosos anteriores
4. **Optimizar recursos**: Aprender qué camiones son más eficientes para ciertos tipos de incidentes

## Modos de Memoria

AgentCore soporta tres modos:

### 1. NO_MEMORY (Inicial)

- Sin persistencia de memoria
- Cada invocación es independiente
- Usado para despliegue inicial y testing

### 2. STM_ONLY

- Solo memoria de corto plazo
- Contexto dentro de una sesión
- No persiste entre invocaciones

### 3. STM_AND_LTM (Producción)

- Memoria de corto y largo plazo
- Persiste decisiones en DynamoDB
- Aprende de casos previos

## Estructura de la Tabla DynamoDB

La tabla `agent_memory` tiene la siguiente estructura:

### Schema

```
Partition Key: memory_id (String)
Sort Key: timestamp (String)
GSI: tipo_incidente-index (Partition Key: tipo_incidente)
```

### Atributos

```json
{
  "memory_id": "MEM-{timestamp}-{random}",
  "timestamp": "ISO8601",
  "tipo_incidente": "enum[Choque, Robo, Falla Mecánica, Falla Cadena Frío]",
  "decision_tomada": {
    "camion_reemplazo": "string",
    "productos_reabastecidos": ["array"],
    "justificacion": "string"
  },
  "resultado": {
    "tiempo_respuesta_segundos": "float",
    "satisfaccion_cliente": "float",
    "valor_perdidas_evitadas_usd": "float"
  },
  "contexto_incidente": {
    "truck_id": "string",
    "nivel_gravedad": "string",
    "ubicacion_gps": {"lat": float, "lon": float},
    "inventario_afectado": ["array"]
  }
}
```

## Configuración Paso a Paso

### Paso 1: Verificar Infraestructura

Asegurarse de que la tabla `agent_memory` existe:

```bash
aws dynamodb describe-table --table-name agent_memory
```

Si no existe, desplegar la infraestructura CDK:

```bash
cd infrastructure
./deploy.sh
```

### Paso 2: Configurar el Agente

Ejecutar el script de configuración:

```bash
cd bedrock_agents/autonomous_agent
./configure_memory.sh
```

Este script:
1. Verifica que la tabla DynamoDB existe
2. Actualiza `.bedrock_agentcore.yaml` para habilitar memoria
3. Crea un registro de ejemplo
4. Proporciona instrucciones para redespliegue

### Paso 3: Actualizar Configuración Manual (Alternativa)

Si prefieres actualizar manualmente, editar `.bedrock_agentcore.yaml`:

```yaml
memory:
  mode: STM_AND_LTM  # Cambiar de NO_MEMORY
  table_name: agent_memory
  session_ttl: 3600  # Opcional: TTL de sesión en segundos
```

### Paso 4: Redesplegar el Agente

```bash
agentcore launch
```

El agente ahora usará memoria persistente.

### Paso 5: Verificar Configuración

```bash
# Ver estado del agente
agentcore status

# Debería mostrar:
# Memory: STM_AND_LTM
# Memory Table: agent_memory
```

## Uso de Memoria por el Agente

### Almacenamiento de Decisiones

Después de cada incidente procesado, el agente almacena:

```python
{
  "memory_id": "MEM-2026-02-17-14-18-25-abc123",
  "timestamp": "2026-02-17T14:18:25Z",
  "tipo_incidente": "Choque / Colisión Grave",
  "decision_tomada": {
    "camion_reemplazo": "3",
    "productos_reabastecidos": ["FAR-001", "MED-002"],
    "justificacion": "Camión 3 más cercano (5.2 km) con capacidad suficiente (2.5 ton) y nivel de fatiga Bajo"
  },
  "resultado": {
    "tiempo_respuesta_segundos": 145,
    "satisfaccion_cliente": 4.5,
    "valor_perdidas_evitadas_usd": 15000
  },
  "contexto_incidente": {
    "truck_id": "1",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410},
    "inventario_afectado": [
      {"sku": "FAR-001", "cantidad": 5},
      {"sku": "MED-002", "cantidad": 10}
    ]
  }
}
```

### Consulta de Memoria

Antes de tomar una decisión, el agente consulta memoria:

```python
# Buscar casos similares
SELECT * FROM agent_memory 
WHERE tipo_incidente = "Choque / Colisión Grave"
ORDER BY timestamp DESC
LIMIT 5
```

El agente usa estos casos para:
- Identificar patrones exitosos
- Evitar decisiones que fallaron previamente
- Justificar decisiones con precedentes

### Ejemplo de Razonamiento con Memoria

```
Agente: "Analizando incidente de choque en camión 1...

Consultando memoria de casos similares:
- MEM-001: Choque en zona similar → Camión 3 seleccionado → Éxito (145s)
- MEM-002: Choque con productos frágiles → Camión 2 seleccionado → Éxito (132s)
- MEM-003: Choque en hora pico → Camión 4 seleccionado → Retraso (210s)

Basándome en casos previos, selecciono Camión 3 porque:
1. Ha sido exitoso en incidentes similares (MEM-001)
2. Está a 5.2 km del incidente (más cercano)
3. Tiene nivel de fatiga Bajo (como en MEM-001)
4. Capacidad suficiente para la carga (2.5 ton disponibles)

Justificación: Patrón exitoso identificado en MEM-001 con tiempo de respuesta de 145s."
```

## Monitoreo de Memoria

### Ver Registros de Memoria

```bash
# Listar últimos 10 registros
aws dynamodb scan \
  --table-name agent_memory \
  --limit 10 \
  --scan-index-forward false

# Buscar por tipo de incidente
aws dynamodb query \
  --table-name agent_memory \
  --index-name tipo_incidente-index \
  --key-condition-expression "tipo_incidente = :tipo" \
  --expression-attribute-values '{":tipo":{"S":"Choque / Colisión Grave"}}'
```

### Métricas de Memoria

Crear métricas personalizadas para monitorear:

```bash
# Número de registros por tipo de incidente
aws cloudwatch put-metric-data \
  --namespace SmartSupply/Memory \
  --metric-name MemoryRecords \
  --dimensions TipoIncidente="Choque / Colisión Grave" \
  --value 1

# Tiempo promedio de respuesta de decisiones previas
aws cloudwatch put-metric-data \
  --namespace SmartSupply/Memory \
  --metric-name AverageResponseTime \
  --value 145 \
  --unit Seconds
```

### Dashboard de Memoria

Crear dashboard en CloudWatch para visualizar:
- Número de registros de memoria por tipo de incidente
- Tiempo promedio de respuesta de decisiones previas
- Tasa de éxito de reasignaciones
- Valor de pérdidas evitadas acumulado

## Limpieza y Mantenimiento

### Política de Retención

Configurar TTL en DynamoDB para eliminar registros antiguos:

```bash
aws dynamodb update-time-to-live \
  --table-name agent_memory \
  --time-to-live-specification "Enabled=true, AttributeName=ttl"
```

Agregar atributo `ttl` a nuevos registros:

```python
import time

ttl = int(time.time()) + (90 * 24 * 60 * 60)  # 90 días
```

### Backup de Memoria

Crear backups periódicos:

```bash
# Backup on-demand
aws dynamodb create-backup \
  --table-name agent_memory \
  --backup-name agent-memory-backup-$(date +%Y%m%d)

# Habilitar backups continuos
aws dynamodb update-continuous-backups \
  --table-name agent_memory \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Análisis de Memoria

Exportar datos para análisis:

```bash
# Exportar a S3
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/agent_memory \
  --s3-bucket smart-supply-data \
  --s3-prefix memory-exports/ \
  --export-format DYNAMODB_JSON
```

Analizar con Athena o QuickSight para:
- Identificar patrones de decisiones exitosas
- Detectar anomalías en tiempos de respuesta
- Optimizar selección de camiones

## Troubleshooting

### Error: Memory table not found

**Solución**: Verificar que la tabla existe y está en la región correcta:
```bash
aws dynamodb describe-table --table-name agent_memory --region us-east-1
```

### Error: Permission denied writing to memory table

**Solución**: Verificar permisos del Bedrock Agent role:
```bash
aws iam get-role-policy \
  --role-name smart-supply-bedrock-agent-role \
  --policy-name DynamoDBAccessPolicy
```

### Error: Memory not persisting

**Posibles causas**:
1. Modo de memoria es NO_MEMORY o STM_ONLY
2. Agente no está "prepared" después de cambios
3. Errores en escritura a DynamoDB

**Solución**:
```bash
# Verificar configuración
cat .bedrock_agentcore.yaml | grep -A 3 "memory:"

# Preparar agente
aws bedrock-agent prepare-agent --agent-id <AGENT_ID>

# Ver logs de errores
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow
```

### Memoria crece demasiado rápido

**Solución**: Implementar política de retención con TTL:
```bash
# Configurar TTL de 90 días
aws dynamodb update-time-to-live \
  --table-name agent_memory \
  --time-to-live-specification "Enabled=true, AttributeName=ttl"
```

## Mejores Prácticas

### 1. Estructura Consistente

Mantener estructura consistente en registros de memoria para facilitar consultas.

### 2. Metadata Rica

Incluir contexto completo del incidente para mejorar aprendizaje.

### 3. Evaluación de Resultados

Actualizar registros con resultados reales después de ejecutar planes.

### 4. Limpieza Periódica

Eliminar registros obsoletos o de baja calidad.

### 5. Monitoreo Continuo

Monitorear métricas de memoria para detectar problemas temprano.

## Próximos Pasos

1. **Task 6.4**: Configurar AgentCore Observability
2. **Task 6.5**: Configurar EventBridge rule para invocar Agent
3. **Análisis de Memoria**: Crear dashboard de QuickSight para visualizar patrones

## Referencias

- [AgentCore Memory Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-memory.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [SmartSupply Design Document](../../.kiro/specs/smart-supply/design.md)
