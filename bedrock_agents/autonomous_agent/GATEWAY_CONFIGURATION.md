# AgentCore Gateway Configuration

Esta guía explica cómo configurar AgentCore Gateway para exponer las Lambda functions como herramientas MCP (Model Context Protocol) para el Bedrock Agent.

## Conceptos Clave

### ¿Qué es AgentCore Gateway?

AgentCore Gateway es un componente que convierte APIs y Lambda functions en herramientas compatibles con MCP que los Bedrock Agents pueden invocar. Actúa como un puente entre el agente y los servicios backend.

### ¿Qué son las herramientas MCP?

MCP (Model Context Protocol) es un estándar para exponer herramientas a modelos de lenguaje. Las herramientas MCP permiten al agente:
- Consultar datos externos (DynamoDB, S3)
- Ejecutar acciones (actualizar rutas, enviar notificaciones)
- Calcular valores (distancias, rutas optimizadas)

## Herramientas Disponibles

El agente autónomo tiene acceso a 8 herramientas MCP:

1. **consultar_ruta_afectada**: Obtiene ruta del camión afectado
2. **consultar_flota_disponible**: Lista camiones disponibles
3. **consultar_inventario_almacen**: Verifica inventario
4. **calcular_distancia**: Calcula distancia entre puntos GPS
5. **calcular_ruta_optimizada**: Genera ruta optimizada
6. **actualizar_ruta_s3**: Actualiza ruta en S3
7. **registrar_incidencia**: Registra incidencia
8. **enviar_notificacion_cliente**: Envía notificación

Ver `mcp_tools_schema.json` para detalles completos de cada herramienta.

## Métodos de Configuración

Hay tres formas de configurar el gateway:

### Método 1: AgentCore CLI (Recomendado)

```bash
# Ejecutar script de configuración
./configure_gateway.sh
```

Este script:
1. Crea el gateway resource
2. Agrega cada Lambda function como target
3. Asocia el gateway con el agente
4. Verifica la configuración

### Método 2: Script Python

```bash
# Ejecutar script Python
python configure_gateway.py
```

Este script:
1. Verifica que las Lambda functions existen
2. Crea el schema OpenAPI para las herramientas
3. Genera código para Lambda router
4. Proporciona instrucciones para completar la configuración

### Método 3: AWS Console (Manual)

1. Ir a Amazon Bedrock Console
2. Seleccionar "Agents" → Tu agente
3. En "Action groups", hacer clic en "Add action group"
4. Configurar:
   - Name: `mcp-tools`
   - Description: `Herramientas MCP para consultar datos y ejecutar acciones`
   - Action group type: `Define with API schemas`
   - API schema: Subir `mcp_tools_schema.json` convertido a OpenAPI
   - Lambda function: `smartsupply-mcp-router`

## Arquitectura del Gateway

```
┌─────────────────────────────────────────────────────────────┐
│                    Bedrock Agent                             │
│  (Claude 3.5 Sonnet con instrucciones de análisis)          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Invoca herramienta MCP
                     │
┌────────────────────▼────────────────────────────────────────┐
│              AgentCore Gateway                               │
│  (Convierte invocaciones a llamadas Lambda)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Enruta a Lambda correcta
                     │
┌────────────────────▼────────────────────────────────────────┐
│           Lambda Router (smartsupply-mcp-router)             │
│  (Recibe invocación y la enruta a Lambda específica)        │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┬───────────────┐
         │                       │               │
┌────────▼────────┐  ┌──────────▼──────┐  ┌────▼──────────┐
│ consultar_ruta  │  │ consultar_flota │  │ calcular_dist │
│   _afectada     │  │   _disponible   │  │    ancia      │
└─────────────────┘  └─────────────────┘  └───────────────┘
         │                       │               │
         └───────────┬───────────┴───────────────┘
                     │
         ┌───────────▼───────────┐
         │   DynamoDB / S3       │
         │   (Datos del sistema) │
         └───────────────────────┘
```

## Lambda Router

El Lambda Router es una función que actúa como dispatcher para las herramientas MCP. Recibe invocaciones del Bedrock Agent y las enruta a las Lambda functions correctas.

### Crear Lambda Router

1. Crear nueva Lambda function en AWS Console:
   - Name: `smartsupply-mcp-router`
   - Runtime: Python 3.11
   - Role: `smart-supply-lambda-role` (ya existe)

2. Copiar código desde `mcp_router_lambda.py` (generado por `configure_gateway.py`)

3. Configurar permisos:
   - El role ya tiene permisos para invocar otras Lambda functions

4. Probar la función:
```json
{
  "actionGroup": "mcp-tools",
  "apiPath": "/consultar_flota_disponible",
  "httpMethod": "POST",
  "parameters": []
}
```

## Configuración de Permisos IAM

Los permisos IAM ya están configurados en el stack de infraestructura:

### Bedrock Agent Role

El role `smart-supply-bedrock-agent-role` tiene permisos para:
- Invocar Lambda functions
- Leer/escribir en DynamoDB
- Leer/escribir en S3
- Invocar modelos de Bedrock

### Lambda Role

El role `smart-supply-lambda-role` tiene permisos para:
- Leer/escribir en DynamoDB
- Leer/escribir en S3
- Invocar otras Lambda functions
- Publicar eventos a EventBridge

## Verificación de la Configuración

### 1. Verificar Gateway

```bash
agentcore gateway list
```

Debería mostrar:
```
✓ Gateway: smartsupply-mcp-gateway
  Status: ACTIVE
  Targets: 8
```

### 2. Verificar Targets

```bash
agentcore gateway list-targets --gateway smartsupply-mcp-gateway
```

Debería listar las 8 Lambda functions.

### 3. Probar Herramienta Individual

```bash
# Probar consultar_flota_disponible
aws lambda invoke \
  --function-name consultar_flota_disponible \
  --payload '{}' \
  response.json

cat response.json
```

### 4. Probar Agente con Herramientas

```bash
agentcore invoke '{
  "detail": {
    "incident_id": "INC-TEST-TOOLS",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410}
  }
}'
```

El agente debería:
1. Invocar `consultar_ruta_afectada` para obtener la ruta del camión 1
2. Invocar `consultar_flota_disponible` para ver camiones disponibles
3. Invocar `consultar_inventario_almacen` para verificar productos
4. Generar un plan de reasignación

## Troubleshooting

### Error: Gateway not found

**Solución**: Ejecutar `./configure_gateway.sh` para crear el gateway.

### Error: Lambda function not found

**Solución**: Verificar que las Lambda functions están desplegadas:
```bash
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `consultar_`) || starts_with(FunctionName, `calcular_`) || starts_with(FunctionName, `actualizar_`) || starts_with(FunctionName, `registrar_`) || starts_with(FunctionName, `enviar_`)].FunctionName'
```

### Error: Permission denied

**Solución**: Verificar que el Bedrock Agent role tiene permisos para invocar Lambda:
```bash
aws iam get-role-policy \
  --role-name smart-supply-bedrock-agent-role \
  --policy-name BedrockAgentLambdaInvokePolicy
```

### Error: Agent doesn't use tools

**Posibles causas**:
1. Action group no está asociado al agente
2. Agent no está "prepared" (necesita preparación después de cambios)
3. Instrucciones del agente no mencionan las herramientas

**Solución**:
```bash
# Preparar el agente después de cambios
aws bedrock-agent prepare-agent --agent-id <AGENT_ID>

# Verificar que action group está activo
aws bedrock-agent list-agent-action-groups \
  --agent-id <AGENT_ID> \
  --agent-version DRAFT
```

## Monitoreo de Herramientas

### CloudWatch Logs

Cada invocación de herramienta genera logs en:
- `/aws/lambda/consultar_ruta_afectada`
- `/aws/lambda/consultar_flota_disponible`
- etc.

### CloudWatch Metrics

Métricas disponibles:
- `Invocations`: Número de invocaciones por herramienta
- `Duration`: Tiempo de ejecución
- `Errors`: Número de errores

### X-Ray Tracing

El tracing está habilitado. Ver traces en AWS X-Ray Console para:
- Ver qué herramientas invoca el agente
- Identificar cuellos de botella
- Debuggear errores

## Próximos Pasos

1. **Task 6.3**: Configurar AgentCore Memory
2. **Task 6.4**: Configurar AgentCore Observability
3. **Task 6.5**: Configurar EventBridge rule para invocar Agent

## Referencias

- [AgentCore Gateway Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action-groups.html)
- [MCP Tools Schema](./mcp_tools_schema.json)
- [Lambda Functions](../../lambda_functions/mcp_tools/)
