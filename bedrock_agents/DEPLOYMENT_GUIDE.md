# SmartSupply Bedrock Agents - Guía de Despliegue

Esta guía cubre el despliegue completo de los Bedrock Agents para SmartSupply usando Amazon Bedrock AgentCore.

## Prerequisitos

1. **AWS CLI configurado** con credenciales válidas
2. **Bedrock AgentCore Starter Toolkit** instalado:
   ```bash
   pip install bedrock-agentcore-starter-toolkit
   ```
3. **Acceso a Amazon Bedrock** con modelo Claude 3.5 Sonnet habilitado
4. **Infraestructura base desplegada** (S3, DynamoDB, EventBridge, IAM Roles)

## Arquitectura de Agentes

SmartSupply utiliza dos Bedrock Agents:

1. **Agente Autónomo** (`autonomous_agent/`): Analiza incidentes y genera planes de reasignación automática
2. **Agente Conversacional** (`conversational_agent/`): Interfaz para operadores logísticos (a implementar en Task 11)

## Despliegue del Agente Autónomo

### Paso 1: Verificar Infraestructura Base

Asegurarse de que la infraestructura CDK está desplegada:

```bash
cd infrastructure
./deploy.sh
```

Verificar que existen:
- Bucket S3: `smart-supply-data`
- Tablas DynamoDB: `rutas_entregas`, `flota_camiones`, `inventario_almacen`, `incidencias`, `agent_memory`
- EventBridge bus: `smart-supply-events`
- IAM Role: `smart-supply-bedrock-agent-role`

### Paso 2: Instalar Dependencias del Agente

```bash
cd bedrock_agents/autonomous_agent
pip install -r requirements.txt
```

### Paso 3: Desarrollo Local (Opcional)

Antes de desplegar a AWS, puedes probar el agente localmente:

```bash
# Iniciar servidor de desarrollo
agentcore dev

# En otra terminal, probar el agente
agentcore invoke --dev '{
  "detail": {
    "incident_id": "INC-TEST-001",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410}
  }
}'
```

### Paso 4: Configurar el Agente para Despliegue

```bash
agentcore configure --entrypoint src.main:app --non-interactive
```

Esto creará/actualizará el archivo `.bedrock_agentcore.yaml` con la configuración de despliegue.

### Paso 5: Desplegar a AgentCore Runtime

```bash
agentcore launch
```

Este comando:
- Empaqueta el código del agente
- Crea recursos de AgentCore en AWS
- Despliega el agente en modo serverless
- Configura el runtime con timeout de 180 segundos

**Nota**: El primer despliegue puede tardar 5-10 minutos.

### Paso 6: Verificar el Despliegue

```bash
# Ver estado del agente
agentcore status

# Debería mostrar:
# ✓ Agent: smartsupply-autonomous-agent
# ✓ Status: ACTIVE
# ✓ Runtime: serverless
# ✓ Model: anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Paso 7: Probar el Agente en AWS

```bash
agentcore invoke '{
  "detail": {
    "incident_id": "INC-901",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410},
    "timestamp": "2026-02-17T14:15:00Z",
    "descripcion": "Impacto lateral severo en Reforma y Juárez",
    "canal": "iot"
  }
}'
```

Deberías recibir una respuesta con el plan de reasignación generado.

## Configuración de Herramientas MCP (Task 6.2)

Las herramientas MCP permiten al agente consultar datos y ejecutar acciones. Se configuran usando AgentCore Gateway.

### Herramientas Disponibles

Las siguientes Lambda functions están disponibles como herramientas MCP:

1. `consultar_ruta_afectada` - Obtiene ruta del camión afectado
2. `consultar_flota_disponible` - Lista camiones disponibles
3. `consultar_inventario_almacen` - Verifica inventario
4. `calcular_distancia` - Calcula distancia entre puntos
5. `calcular_ruta_optimizada` - Genera ruta optimizada
6. `actualizar_ruta_s3` - Actualiza ruta en S3
7. `registrar_incidencia` - Registra incidencia
8. `enviar_notificacion_cliente` - Envía notificación

### Configurar Gateway (se implementará en Task 6.2)

```bash
# Crear Gateway resource
agentcore gateway create --name smartsupply-mcp-gateway

# Agregar Lambda functions como targets
agentcore gateway add-target \
  --gateway smartsupply-mcp-gateway \
  --target-type lambda \
  --function-name consultar_ruta_afectada

# Repetir para cada Lambda function...
```

## Configuración de Memoria (Task 6.3)

AgentCore Memory permite al agente aprender de decisiones previas.

### Paso 1: Verificar Tabla DynamoDB

La tabla `agent_memory` debe existir (creada por CDK).

### Paso 2: Actualizar Configuración del Agente

Editar `.bedrock_agentcore.yaml`:

```yaml
memory:
  mode: STM_AND_LTM  # Cambiar de NO_MEMORY
  table_name: agent_memory
```

### Paso 3: Redesplegar

```bash
agentcore launch
```

El agente ahora almacenará decisiones en DynamoDB y las consultará para mejorar futuras reasignaciones.

## Configuración de Observabilidad (Task 6.4)

### CloudWatch Logs

Los logs del agente están en:
```
/aws/bedrock/agentcore/smartsupply-autonomous-agent
```

Ver logs:
```bash
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow
```

### CloudWatch Metrics

Métricas disponibles en namespace `SmartSupply/BedrockAgent`:
- `Invocations`: Número de invocaciones
- `Latency`: Tiempo de respuesta
- `Errors`: Número de errores

Ver métricas:
```bash
aws cloudwatch get-metric-statistics \
  --namespace SmartSupply/BedrockAgent \
  --metric-name Latency \
  --dimensions Name=AgentName,Value=smartsupply-autonomous-agent \
  --start-time 2026-02-17T00:00:00Z \
  --end-time 2026-02-17T23:59:59Z \
  --period 300 \
  --statistics Average
```

### Alarmas

Dos alarmas están configuradas:
1. **Latencia > 30s**: Alerta cuando el agente tarda más de 30 segundos
2. **Tasa de errores > 5%**: Alerta cuando más del 5% de invocaciones fallan

Ver alarmas:
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix smartsupply-autonomous-agent
```

### X-Ray Tracing

El tracing está habilitado automáticamente. Ver traces en AWS X-Ray Console.

## Integración con EventBridge (Task 6.5)

Para que el agente procese eventos de incidentes automáticamente, se debe crear una regla de EventBridge.

### Crear Regla de EventBridge

```bash
aws events put-rule \
  --name smartsupply-incident-to-agent \
  --event-pattern '{
    "source": ["smartsupply.voice", "smartsupply.web", "smartsupply.iot"],
    "detail-type": ["IncidentDetected"]
  }' \
  --state ENABLED
```

### Configurar Target (Bedrock Agent)

```bash
# Obtener ARN del agente
AGENT_ARN=$(agentcore status --output json | jq -r '.agent_arn')

# Agregar agente como target
aws events put-targets \
  --rule smartsupply-incident-to-agent \
  --targets "Id"="1","Arn"="$AGENT_ARN","RoleArn"="arn:aws:iam::ACCOUNT_ID:role/smart-supply-bedrock-agent-role"
```

Reemplazar `ACCOUNT_ID` con tu AWS Account ID.

## Verificación End-to-End

### 1. Publicar Evento de Prueba

```bash
aws events put-events \
  --entries '[{
    "Source": "smartsupply.iot",
    "DetailType": "IncidentDetected",
    "Detail": "{\"incident_id\":\"INC-TEST-E2E\",\"truck_id\":\"1\",\"tipo_incidente\":\"Choque / Colisión Grave\",\"nivel_gravedad\":\"Crítico\",\"ubicacion_gps\":{\"lat\":19.4345,\"lon\":-99.1410}}",
    "EventBusName": "smart-supply-events"
  }]'
```

### 2. Verificar Procesamiento

```bash
# Ver logs del agente
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow

# Verificar que se creó un plan en DynamoDB
aws dynamodb scan --table-name incidencias --filter-expression "incident_id = :id" --expression-attribute-values '{":id":{"S":"INC-TEST-E2E"}}'
```

### 3. Verificar Métricas

Esperar 5 minutos y verificar métricas en CloudWatch Console.

## Troubleshooting

### Error: Model access denied

**Solución**: Habilitar acceso al modelo Claude 3.5 Sonnet en Bedrock Console:
1. Ir a Amazon Bedrock Console
2. Seleccionar "Model access" en el menú lateral
3. Hacer clic en "Manage model access"
4. Habilitar "Claude 3.5 Sonnet"
5. Guardar cambios

### Error: Timeout después de 180 segundos

**Solución**: El agente está configurado con timeout de 3 minutos. Si excede este tiempo:
1. Revisar la complejidad del análisis
2. Optimizar consultas a DynamoDB
3. Considerar aumentar el timeout en `.bedrock_agentcore.yaml`

### Error: Herramientas MCP no disponibles

**Solución**: Verificar que AgentCore Gateway está configurado:
```bash
agentcore gateway list
```

Si no hay gateways, seguir las instrucciones en Task 6.2.

### Error: Memory table not found

**Solución**: Verificar que la tabla `agent_memory` existe:
```bash
aws dynamodb describe-table --table-name agent_memory
```

Si no existe, desplegar la infraestructura CDK.

## Limpieza

Para destruir todos los recursos del agente:

```bash
# Vista previa
agentcore destroy --dry-run

# Destruir
agentcore destroy
```

**Nota**: Esto NO destruye la infraestructura base (S3, DynamoDB, etc.). Para eso, usar:
```bash
cd infrastructure
cdk destroy
```

## Próximos Pasos

1. **Task 6.2**: Registrar herramientas MCP en AgentCore Gateway
2. **Task 6.3**: Configurar AgentCore Memory
3. **Task 6.4**: Configurar AgentCore Observability
4. **Task 6.5**: Configurar EventBridge rule para invocar Agent
5. **Task 11**: Implementar Agente Conversacional

## Referencias

- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AgentCore CLI Reference](https://github.com/awslabs/bedrock-agentcore-starter-toolkit)
- [SmartSupply Design Document](../.kiro/specs/smart-supply/design.md)
