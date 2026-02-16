# AgentCore Observability Configuration

Esta guía explica cómo configurar observabilidad completa para el Bedrock Agent usando CloudWatch Logs, Metrics, Alarms y X-Ray Tracing.

## Conceptos Clave

### ¿Qué es AgentCore Observability?

AgentCore Observability proporciona visibilidad completa del comportamiento del agente mediante:
- **CloudWatch Logs**: Logs estructurados de cada invocación
- **CloudWatch Metrics**: Métricas de performance (latencia, errores, invocaciones)
- **CloudWatch Alarms**: Alertas automáticas cuando métricas exceden umbrales
- **X-Ray Tracing**: Tracing distribuido end-to-end de cada invocación

### Beneficios para SmartSupply

La observabilidad permite:
1. **Monitoreo en tiempo real**: Ver estado del agente en dashboards
2. **Detección temprana de problemas**: Alarmas cuando latencia > 30s o errores > 5%
3. **Debugging eficiente**: Traces completos de cada invocación
4. **Optimización continua**: Identificar cuellos de botella y herramientas lentas
5. **Auditoría**: Registro completo de decisiones del agente

## Componentes de Observabilidad

### 1. CloudWatch Logs

#### Log Group

```
/aws/bedrock/agentcore/smartsupply-autonomous-agent
```

#### Estructura de Logs

Cada invocación genera logs estructurados:

```json
{
  "timestamp": "2026-02-17T14:15:00Z",
  "level": "INFO",
  "agent_name": "smartsupply-autonomous-agent",
  "invocation_id": "inv-abc123",
  "event": {
    "incident_id": "INC-901",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave"
  },
  "tools_invoked": [
    {"tool": "consultar_ruta_afectada", "duration_ms": 45},
    {"tool": "consultar_flota_disponible", "duration_ms": 32},
    {"tool": "calcular_ruta_optimizada", "duration_ms": 156}
  ],
  "latency_seconds": 2.5,
  "decision": {
    "camion_reemplazo": "3",
    "justificacion": "Camión 3 más cercano..."
  }
}
```

#### Queries Útiles

**Errores recientes:**
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20
```

**Latencia por invocación:**
```
fields @timestamp, latency_seconds
| filter latency_seconds > 0
| stats avg(latency_seconds), max(latency_seconds), min(latency_seconds)
```

**Herramientas MCP más usadas:**
```
fields @timestamp, tools_invoked
| filter tools_invoked != ''
| stats count() by tools_invoked
| sort count desc
```

**Incidentes por tipo:**
```
fields @timestamp, event.tipo_incidente
| stats count() by event.tipo_incidente
```

### 2. CloudWatch Metrics

#### Namespace

```
SmartSupply/BedrockAgent
```

#### Métricas Disponibles

| Métrica | Descripción | Unidad | Dimensiones |
|---------|-------------|--------|-------------|
| Invocations | Número de invocaciones del agente | Count | AgentName |
| Latency | Tiempo de respuesta del agente | Seconds | AgentName |
| Errors | Número de errores | Count | AgentName, ErrorType |
| ToolInvocations | Invocaciones de herramientas MCP | Count | AgentName, ToolName |
| MemoryReads | Lecturas de memoria | Count | AgentName |
| MemoryWrites | Escrituras de memoria | Count | AgentName |

#### Publicar Métricas Personalizadas

```bash
# Publicar latencia
aws cloudwatch put-metric-data \
  --namespace SmartSupply/BedrockAgent \
  --metric-name Latency \
  --dimensions AgentName=smartsupply-autonomous-agent \
  --value 2.5 \
  --unit Seconds

# Publicar invocación de herramienta
aws cloudwatch put-metric-data \
  --namespace SmartSupply/BedrockAgent \
  --metric-name ToolInvocations \
  --dimensions AgentName=smartsupply-autonomous-agent,ToolName=consultar_flota_disponible \
  --value 1 \
  --unit Count
```

### 3. CloudWatch Alarms

#### Alarma 1: Latencia Alta (> 30 segundos)

**Requisito**: 18.3 - Alertar cuando latencia del agente excede 30 segundos

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-autonomous-agent-high-latency \
  --alarm-description "Alerta cuando latencia del agente excede 30 segundos" \
  --metric-name Latency \
  --namespace SmartSupply/BedrockAgent \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 30 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=AgentName,Value=smartsupply-autonomous-agent
```

**Acciones cuando se dispara**:
- Enviar notificación a SNS topic
- Escalar a equipo de operaciones
- Revisar logs y traces para identificar causa

#### Alarma 2: Tasa de Errores Alta (> 5%)

```bash
# Crear métrica matemática
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-autonomous-agent-high-error-rate \
  --alarm-description "Alerta cuando tasa de errores excede 5%" \
  --metrics '[
    {
      "Id": "errors",
      "MetricStat": {
        "Metric": {
          "Namespace": "SmartSupply/BedrockAgent",
          "MetricName": "Errors",
          "Dimensions": [{"Name": "AgentName", "Value": "smartsupply-autonomous-agent"}]
        },
        "Period": 300,
        "Stat": "Sum"
      }
    },
    {
      "Id": "invocations",
      "MetricStat": {
        "Metric": {
          "Namespace": "SmartSupply/BedrockAgent",
          "MetricName": "Invocations",
          "Dimensions": [{"Name": "AgentName", "Value": "smartsupply-autonomous-agent"}]
        },
        "Period": 300,
        "Stat": "Sum"
      }
    },
    {
      "Id": "error_rate",
      "Expression": "(errors / invocations) * 100"
    }
  ]' \
  --evaluation-periods 2 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

#### Alarma 3: Tiempo de Respuesta de Incidentes (> 180 segundos)

**Requisito**: 8.3 - Alertar cuando tiempo de respuesta excede 3 minutos

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-incident-response-timeout \
  --alarm-description "Alerta cuando tiempo de respuesta de incidente excede 180 segundos" \
  --metric-name IncidentResponseTime \
  --namespace SmartSupply/BedrockAgent \
  --statistic Maximum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 180 \
  --comparison-operator GreaterThanThreshold
```

### 4. X-Ray Tracing

#### Habilitar Tracing

En `.bedrock_agentcore.yaml`:

```yaml
observability:
  tracing: true
  metrics: true
  logs:
    level: INFO
    retention_days: 30
```

#### Estructura de Traces

Cada invocación genera un trace con:

```
Trace ID: 1-abc123-def456
├─ Segment: BedrockAgent (smartsupply-autonomous-agent)
│  ├─ Subsegment: EventProcessing
│  ├─ Subsegment: ToolInvocation (consultar_ruta_afectada)
│  │  └─ Subsegment: DynamoDB Query
│  ├─ Subsegment: ToolInvocation (consultar_flota_disponible)
│  │  └─ Subsegment: DynamoDB Scan
│  ├─ Subsegment: ToolInvocation (calcular_ruta_optimizada)
│  │  └─ Subsegment: Lambda Invoke
│  ├─ Subsegment: DecisionGeneration
│  └─ Subsegment: MemoryWrite
│     └─ Subsegment: DynamoDB PutItem
```

#### Analizar Traces

```bash
# Obtener traces recientes
aws xray get-trace-summaries \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date -u +%s) \
  --filter-expression 'service(id(name: "smartsupply-autonomous-agent"))'

# Obtener trace específico
aws xray batch-get-traces --trace-ids <TRACE_ID>
```

#### Service Map

X-Ray genera automáticamente un service map mostrando:
- Bedrock Agent → Lambda Functions
- Lambda Functions → DynamoDB
- Lambda Functions → S3
- Latencia entre servicios
- Tasa de errores por servicio

## Dashboard de CloudWatch

### Crear Dashboard

```bash
./configure_observability.sh
```

Este script crea un dashboard con:

1. **Widget de Invocaciones**: Gráfico de línea con invocaciones por hora
2. **Widget de Latencia**: Gráfico con P50, P90, P99
3. **Widget de Errores**: Gráfico de barras con errores por tipo
4. **Widget de Logs**: Logs recientes del agente

### Acceder al Dashboard

```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=SmartSupply-Agent-Observability
```

### Widgets Adicionales Recomendados

#### Widget de Herramientas MCP

```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["SmartSupply/BedrockAgent", "ToolInvocations", {"stat": "Sum"}]
    ],
    "period": 300,
    "stat": "Sum",
    "region": "us-east-1",
    "title": "MCP Tool Invocations",
    "yAxis": {
      "left": {
        "min": 0
      }
    }
  }
}
```

#### Widget de Memoria

```json
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["SmartSupply/BedrockAgent", "MemoryReads", {"stat": "Sum", "label": "Memory Reads"}],
      [".", "MemoryWrites", {"stat": "Sum", "label": "Memory Writes"}]
    ],
    "period": 300,
    "stat": "Sum",
    "region": "us-east-1",
    "title": "Memory Operations"
  }
}
```

## Configuración Paso a Paso

### Paso 1: Ejecutar Script de Configuración

```bash
cd bedrock_agents/autonomous_agent
./configure_observability.sh
```

Este script:
1. Crea/verifica CloudWatch Log Group
2. Habilita X-Ray Tracing
3. Crea métricas personalizadas
4. Crea alarmas
5. Crea dashboard

### Paso 2: Actualizar Configuración del Agente

Verificar que `.bedrock_agentcore.yaml` tiene:

```yaml
observability:
  tracing: true
  metrics: true
  logs:
    level: INFO
    retention_days: 30
```

### Paso 3: Redesplegar el Agente

```bash
agentcore launch
```

### Paso 4: Verificar Observabilidad

```bash
# Ver logs en tiempo real
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow

# Ver métricas
aws cloudwatch get-metric-statistics \
  --namespace SmartSupply/BedrockAgent \
  --metric-name Latency \
  --dimensions Name=AgentName,Value=smartsupply-autonomous-agent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# Ver alarmas
aws cloudwatch describe-alarms \
  --alarm-name-prefix smartsupply-autonomous-agent
```

## Monitoreo en Producción

### Checklist Diario

- [ ] Revisar dashboard de CloudWatch
- [ ] Verificar que no hay alarmas activas
- [ ] Revisar logs de errores
- [ ] Analizar latencia P99
- [ ] Verificar tasa de éxito de invocaciones

### Checklist Semanal

- [ ] Analizar service map de X-Ray
- [ ] Identificar herramientas MCP más lentas
- [ ] Revisar patrones de memoria
- [ ] Optimizar queries a DynamoDB
- [ ] Actualizar umbrales de alarmas si es necesario

### Checklist Mensual

- [ ] Generar reporte de performance
- [ ] Analizar tendencias de latencia
- [ ] Revisar costos de observabilidad
- [ ] Optimizar retención de logs
- [ ] Actualizar dashboard con nuevas métricas

## Troubleshooting

### No se generan logs

**Solución**: Verificar permisos del Bedrock Agent role:
```bash
aws iam get-role-policy \
  --role-name smart-supply-bedrock-agent-role \
  --policy-name CloudWatchLogsPolicy
```

### No se generan métricas

**Solución**: Verificar que observability está habilitado en `.bedrock_agentcore.yaml`:
```bash
grep -A 5 "observability:" .bedrock_agentcore.yaml
```

### Traces no aparecen en X-Ray

**Solución**: Verificar permisos de X-Ray:
```bash
aws iam get-role-policy \
  --role-name smart-supply-bedrock-agent-role \
  --policy-name XRayTracingPolicy
```

### Alarmas no se disparan

**Solución**: Verificar que las métricas se están publicando:
```bash
aws cloudwatch list-metrics \
  --namespace SmartSupply/BedrockAgent
```

## Mejores Prácticas

### 1. Logs Estructurados

Usar formato JSON para logs para facilitar queries:

```json
{
  "timestamp": "ISO8601",
  "level": "INFO|WARN|ERROR",
  "agent_name": "string",
  "invocation_id": "string",
  "event": {},
  "decision": {},
  "latency_seconds": "float"
}
```

### 2. Métricas Granulares

Publicar métricas con dimensiones para análisis detallado:

```python
cloudwatch.put_metric_data(
    Namespace='SmartSupply/BedrockAgent',
    MetricData=[{
        'MetricName': 'ToolInvocations',
        'Dimensions': [
            {'Name': 'AgentName', 'Value': 'smartsupply-autonomous-agent'},
            {'Name': 'ToolName', 'Value': 'consultar_flota_disponible'},
            {'Name': 'IncidentType', 'Value': 'Choque'}
        ],
        'Value': 1,
        'Unit': 'Count'
    }]
)
```

### 3. Alarmas Progresivas

Configurar alarmas en múltiples niveles:
- Warning: Latencia > 20s
- Critical: Latencia > 30s
- Emergency: Latencia > 60s

### 4. Retención Optimizada

Configurar retención según importancia:
- Logs de producción: 30 días
- Logs de desarrollo: 7 días
- Traces: 7 días
- Métricas: 15 meses (default)

### 5. Dashboards por Rol

Crear dashboards específicos:
- **Operaciones**: Invocaciones, errores, alarmas
- **Desarrollo**: Latencia por herramienta, traces
- **Negocio**: Tiempo de respuesta, valor de pérdidas evitadas

## Próximos Pasos

1. **Task 6.5**: Configurar EventBridge rule para invocar Agent
2. **Integración con QuickSight**: Visualizar métricas de negocio
3. **Alertas a SNS**: Notificar equipo cuando alarmas se disparan

## Referencias

- [CloudWatch Logs Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [CloudWatch Metrics Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/)
- [X-Ray Documentation](https://docs.aws.amazon.com/xray/latest/devguide/)
- [SmartSupply Design Document](../../.kiro/specs/smart-supply/design.md)
