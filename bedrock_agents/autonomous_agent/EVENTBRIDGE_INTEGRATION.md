# EventBridge Integration

Esta guía explica cómo configurar la integración entre EventBridge y el Bedrock Agent para procesamiento automático de incidentes.

## Arquitectura de Integración

```
┌─────────────────────────────────────────────────────────────┐
│                    Canales de Entrada                        │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Amazon Connect │   Amplify Web   │    IoT Sensors          │
│   + Transcribe  │  + API Gateway  │    (Kinesis)            │
└────────┬────────┴────────┬────────┴────────┬────────────────┘
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                    ┌──────▼──────┐
                    │ EventBridge │
                    │ (Bus Central)│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ EventBridge │
                    │    Rule     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Lambda    │
                    │ Intermediaria│
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Bedrock   │
                    │    Agent    │
                    └─────────────┘
```

## Componentes

### 1. Event Bus

**Nombre**: `smart-supply-events`

**Propósito**: Bus central que recibe eventos de todos los canales de entrada.

### 2. EventBridge Rule

**Nombre**: `smartsupply-incident-to-agent`

**Event Pattern**:
```json
{
  "source": [
    "smartsupply.voice",
    "smartsupply.web",
    "smartsupply.iot"
  ],
  "detail-type": [
    "IncidentDetected"
  ]
}
```

**Descripción**: Escucha eventos de incidentes de todos los canales y los enruta al agente.

### 3. Lambda Intermediaria

**Nombre**: `smartsupply-agent-invoker`

**Propósito**: Recibe eventos de EventBridge e invoca el Bedrock Agent.

**¿Por qué una Lambda intermediaria?**
- EventBridge no puede invocar Bedrock Agents directamente
- La Lambda transforma el evento de EventBridge al formato esperado por el agente
- Permite agregar lógica adicional (validación, enriquecimiento, logging)

## Configuración Paso a Paso

### Paso 1: Verificar Infraestructura Base

Asegurarse de que existe:
- Event Bus: `smart-supply-events`
- IAM Role: `smart-supply-lambda-role`
- Bedrock Agent desplegado

```bash
# Verificar Event Bus
aws events describe-event-bus --name smart-supply-events

# Verificar IAM Role
aws iam get-role --role-name smart-supply-lambda-role

# Verificar Agent
agentcore status
```

### Paso 2: Ejecutar Script de Configuración

```bash
cd bedrock_agents/autonomous_agent
./configure_eventbridge.sh
```

Este script:
1. Verifica que el Event Bus existe
2. Crea EventBridge Rule con event pattern
3. Genera código de Lambda intermediaria
4. Configura permisos
5. Proporciona comandos para testing

### Paso 3: Desplegar Lambda Intermediaria

#### Opción A: AWS Console

1. Ir a Lambda Console
2. Crear nueva función:
   - Name: `smartsupply-agent-invoker`
   - Runtime: Python 3.11
   - Role: `smart-supply-lambda-role`
3. Copiar código desde `agent_invoker_lambda.py`
4. Configurar variables de entorno:
   - `AGENT_ID`: ID del agente (obtener con `agentcore status`)
   - `AGENT_ALIAS_ID`: `TSTALIASID` (para testing) o alias de producción
5. Guardar y desplegar

#### Opción B: AWS CLI

```bash
# Empaquetar código
zip agent_invoker_lambda.zip agent_invoker_lambda.py

# Crear función
aws lambda create-function \
  --function-name smartsupply-agent-invoker \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/smart-supply-lambda-role \
  --handler agent_invoker_lambda.lambda_handler \
  --zip-file fileb://agent_invoker_lambda.zip \
  --environment Variables="{AGENT_ID=your-agent-id,AGENT_ALIAS_ID=TSTALIASID}" \
  --timeout 180

# Agregar permiso para EventBridge
aws lambda add-permission \
  --function-name smartsupply-agent-invoker \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:REGION:ACCOUNT_ID:rule/smart-supply-events/smartsupply-incident-to-agent
```

### Paso 4: Obtener Agent ID

```bash
# Opción 1: Usando agentcore CLI
agentcore status --output json | jq -r '.agent_id'

# Opción 2: Usando AWS CLI
aws bedrock-agent list-agents --query 'agentSummaries[?agentName==`smartsupply-autonomous-agent`].agentId' --output text
```

### Paso 5: Actualizar Variables de Entorno de Lambda

```bash
AGENT_ID="<agent-id-from-step-4>"

aws lambda update-function-configuration \
  --function-name smartsupply-agent-invoker \
  --environment Variables="{AGENT_ID=$AGENT_ID,AGENT_ALIAS_ID=TSTALIASID}"
```

### Paso 6: Probar la Integración

#### Publicar Evento de Prueba

```bash
aws events put-events --entries '[
  {
    "Source": "smartsupply.iot",
    "DetailType": "IncidentDetected",
    "Detail": "{\"incident_id\":\"INC-TEST-EB-001\",\"truck_id\":\"1\",\"tipo_incidente\":\"Choque / Colisión Grave\",\"nivel_gravedad\":\"Crítico\",\"ubicacion_gps\":{\"lat\":19.4345,\"lon\":-99.1410},\"timestamp\":\"2026-02-17T14:15:00Z\",\"descripcion\":\"Test de integración EventBridge\",\"canal\":\"iot\"}",
    "EventBusName": "smart-supply-events"
  }
]'
```

#### Verificar Procesamiento

```bash
# Ver logs de Lambda intermediaria
aws logs tail /aws/lambda/smartsupply-agent-invoker --follow

# Ver logs del Bedrock Agent
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow

# Verificar que se creó registro en DynamoDB
aws dynamodb get-item \
  --table-name incidencias \
  --key '{"incidente_id":{"S":"INC-TEST-EB-001"},"timestamp":{"S":"2026-02-17T14:15:00Z"}}'
```

## Estructura de Eventos

### Evento de Entrada (EventBridge)

```json
{
  "version": "0",
  "id": "abc123",
  "detail-type": "IncidentDetected",
  "source": "smartsupply.iot",
  "account": "123456789012",
  "time": "2026-02-17T14:15:00Z",
  "region": "us-east-1",
  "resources": [],
  "detail": {
    "incident_id": "INC-901",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {
      "lat": 19.4345,
      "lon": -99.1410
    },
    "timestamp": "2026-02-17T14:15:00Z",
    "descripcion": "Impacto lateral severo en Reforma y Juárez",
    "canal": "iot",
    "sensor_telemetria_g": 5.2
  }
}
```

### Invocación del Bedrock Agent

```python
response = bedrock_agent_runtime.invoke_agent(
    agentId='AGENT_ID',
    agentAliasId='TSTALIASID',
    sessionId='INC-901',
    inputText=json.dumps(detail)
)
```

### Respuesta del Agente

```json
{
  "plan_id": "PLAN-2026-02-17-14-18-25",
  "incidente_id": "INC-901",
  "timestamp_generacion": "2026-02-17T14:18:25Z",
  "camion_reemplazo": {
    "truck_id": "3",
    "conductor": "Ing. Ernesto Rosado",
    "justificacion": "Camión 3 más cercano (5.2 km) con capacidad suficiente (2.5 ton) y nivel de fatiga Bajo"
  },
  "productos_a_reabastecer": [
    {
      "sku": "FAR-001",
      "cantidad": 5,
      "origen": "Almacén",
      "ubicacion_pasillo": "Pasillo-A-3"
    }
  ],
  "rutas_actualizadas": [
    {
      "truck_id": "3",
      "paradas_agregadas": ["STOP-7216", "STOP-7217"],
      "paradas_removidas": [],
      "nuevo_horario_estimado": "15:30"
    }
  ],
  "clientes_a_notificar": [
    {
      "cliente_id": "CLI-001",
      "prioridad_notificacion": "Crítica",
      "nuevo_horario": "15:30",
      "motivo": "Reasignación por incidente en camión 1"
    }
  ],
  "metricas": {
    "tiempo_generacion_segundos": 145,
    "valor_perdidas_evitadas_usd": 15000,
    "numero_clientes_impactados": 3
  }
}
```

## Monitoreo de la Integración

### Métricas de EventBridge

```bash
# Número de eventos publicados
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name Invocations \
  --dimensions Name=RuleName,Value=smartsupply-incident-to-agent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Eventos fallidos
aws cloudwatch get-metric-statistics \
  --namespace AWS/Events \
  --metric-name FailedInvocations \
  --dimensions Name=RuleName,Value=smartsupply-incident-to-agent \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Métricas de Lambda

```bash
# Invocaciones de Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=smartsupply-agent-invoker \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Errores de Lambda
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=smartsupply-agent-invoker \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### Alarmas Recomendadas

#### Alarma 1: Eventos Fallidos

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-eventbridge-failed-invocations \
  --alarm-description "Alerta cuando eventos de EventBridge fallan" \
  --metric-name FailedInvocations \
  --namespace AWS/Events \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=RuleName,Value=smartsupply-incident-to-agent
```

#### Alarma 2: Lambda Errors

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-agent-invoker-errors \
  --alarm-description "Alerta cuando Lambda intermediaria falla" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=smartsupply-agent-invoker
```

## Troubleshooting

### Evento no llega al agente

**Verificar**:
1. Evento se publicó correctamente a EventBridge
2. Event pattern del rule coincide con el evento
3. Lambda intermediaria tiene permisos para ser invocada
4. Lambda puede invocar el Bedrock Agent

**Solución**:
```bash
# Verificar que el evento coincide con el pattern
aws events test-event-pattern \
  --event-pattern file://event_pattern.json \
  --event file://test_event.json

# Verificar permisos de Lambda
aws lambda get-policy --function-name smartsupply-agent-invoker

# Ver logs de Lambda
aws logs tail /aws/lambda/smartsupply-agent-invoker --follow
```

### Lambda falla al invocar el agente

**Posibles causas**:
- AGENT_ID incorrecto
- Agente no está desplegado
- Permisos insuficientes

**Solución**:
```bash
# Verificar variables de entorno
aws lambda get-function-configuration \
  --function-name smartsupply-agent-invoker \
  --query 'Environment.Variables'

# Verificar que el agente existe
aws bedrock-agent get-agent --agent-id <AGENT_ID>

# Verificar permisos del role
aws iam get-role-policy \
  --role-name smart-supply-lambda-role \
  --policy-name BedrockAgentInvokePolicy
```

### Agente no procesa el evento correctamente

**Verificar**:
1. Formato del evento es correcto
2. Agente tiene acceso a herramientas MCP
3. Herramientas MCP funcionan correctamente

**Solución**:
```bash
# Ver logs del agente
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow

# Probar herramienta MCP directamente
aws lambda invoke \
  --function-name consultar_ruta_afectada \
  --payload '{"truck_id":"1"}' \
  response.json

cat response.json
```

## Mejores Prácticas

### 1. Dead Letter Queue (DLQ)

Configurar DLQ para eventos que fallan:

```bash
# Crear SQS queue para DLQ
aws sqs create-queue --queue-name smartsupply-eventbridge-dlq

# Configurar DLQ en Lambda
aws lambda update-function-configuration \
  --function-name smartsupply-agent-invoker \
  --dead-letter-config TargetArn=arn:aws:sqs:REGION:ACCOUNT_ID:queue/smartsupply-eventbridge-dlq
```

### 2. Retry Policy

Configurar reintentos en Lambda:

```bash
aws lambda put-function-event-invoke-config \
  --function-name smartsupply-agent-invoker \
  --maximum-retry-attempts 2 \
  --maximum-event-age-in-seconds 3600
```

### 3. Idempotencia

Asegurar que el agente puede procesar el mismo evento múltiples veces sin efectos secundarios:

```python
# En Lambda intermediaria
def lambda_handler(event, context):
    incident_id = event['detail']['incident_id']
    
    # Verificar si ya se procesó
    response = dynamodb.get_item(
        TableName='incidencias',
        Key={'incidente_id': incident_id}
    )
    
    if 'Item' in response:
        print(f"Incident {incident_id} already processed")
        return {'statusCode': 200, 'body': 'Already processed'}
    
    # Procesar evento...
```

### 4. Enriquecimiento de Eventos

Agregar contexto adicional antes de invocar el agente:

```python
# Enriquecer con datos de DynamoDB
truck_data = dynamodb.get_item(
    TableName='flota_camiones',
    Key={'truck_id': event['detail']['truck_id']}
)

event['detail']['truck_data'] = truck_data['Item']
```

## Próximos Pasos

1. **Task 7**: Checkpoint - Verificar Agent Autónomo
2. **Implementar DLQ**: Para manejo de errores robusto
3. **Agregar métricas custom**: Para monitoreo detallado
4. **Implementar circuit breaker**: Para protección contra fallos en cascada

## Referencias

- [EventBridge Documentation](https://docs.aws.amazon.com/eventbridge/latest/userguide/)
- [Bedrock Agent Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_InvokeAgent.html)
- [SmartSupply Design Document](../../.kiro/specs/smart-supply/design.md)
