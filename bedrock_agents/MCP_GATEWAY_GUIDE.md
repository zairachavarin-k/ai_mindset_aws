# MCP Gateway - Guía de Configuración

## ¿Qué es MCP Gateway?

MCP (Model Context Protocol) Gateway es el sistema de AgentCore que expone Lambda functions como herramientas que los agentes pueden usar. Reemplaza la necesidad de crear Lambda routers manuales.

## Arquitectura

### Antes (Lambda Router Manual)

```
Bedrock Agent
    ↓
Lambda Router (create_mcp_router_lambda.py)
    ↓
Switch/Case para cada herramienta
    ↓
Invocar Lambda específica
```

**Problemas:**
- Código boilerplate repetitivo
- Difícil de mantener
- Requiere actualizar router para cada nueva herramienta

### Ahora (AgentCore Gateway)

```
Bedrock Agent
    ↓
AgentCore Gateway (automático)
    ↓
Lee mcp_tools_schema.json
    ↓
Invoca Lambda directamente
```

**Ventajas:**
- ✅ Sin código boilerplate
- ✅ Configuración declarativa (JSON)
- ✅ Fácil agregar nuevas herramientas
- ✅ Validación automática de schemas

## Configuración

### 1. Definir Herramientas en mcp_tools_schema.json

```json
{
  "gateway_name": "smartsupply-gateway",
  "description": "Herramientas MCP para SmartSupply",
  "tools": [
    {
      "name": "consultar_ruta_afectada",
      "description": "Obtiene la ruta del camión afectado",
      "lambda_function": "consultar_ruta_afectada",
      "input_schema": {
        "type": "object",
        "properties": {
          "truck_id": {"type": "string"}
        },
        "required": ["truck_id"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "ruta": {"type": "object"},
          "paradas": {"type": "array"}
        }
      }
    }
  ]
}
```

### 2. Configurar Gateway

```bash
cd bedrock_agents/autonomous_agent

# Opción A: Usar script de configuración
./configure_gateway.sh

# Opción B: Usar Python script
python configure_gateway.py

# Opción C: Usar CLI de AgentCore
agentcore gateway configure \
  --gateway-name smartsupply-gateway \
  --tools-schema mcp_tools_schema.json
```

### 3. Desplegar Agente

```bash
agentcore launch
```

El gateway se configura automáticamente al desplegar el agente.

## Estructura de mcp_tools_schema.json

### Campos Requeridos

```json
{
  "gateway_name": "string",           // Nombre único del gateway
  "description": "string",            // Descripción del gateway
  "tools": [                          // Array de herramientas
    {
      "name": "string",               // Nombre de la herramienta (único)
      "description": "string",        // Descripción para el agente
      "lambda_function": "string",    // Nombre de la Lambda function
      "input_schema": {...},          // JSON Schema para input
      "output_schema": {...}          // JSON Schema para output (opcional)
    }
  ]
}
```

### Ejemplo Completo

```json
{
  "gateway_name": "smartsupply-gateway",
  "description": "Herramientas MCP para el Agente Autónomo",
  "tools": [
    {
      "name": "consultar_ruta_afectada",
      "description": "Obtiene la ruta completa del camión afectado por un incidente",
      "lambda_function": "consultar_ruta_afectada",
      "input_schema": {
        "type": "object",
        "properties": {
          "truck_id": {
            "type": "string",
            "description": "ID del camión (ej: '1', '2', '3')"
          }
        },
        "required": ["truck_id"]
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "truck_id": {"type": "string"},
          "fecha": {"type": "string"},
          "paradas": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "stop_id": {"type": "string"},
                "cliente": {"type": "string"},
                "estado": {"type": "string"}
              }
            }
          }
        }
      }
    },
    {
      "name": "calcular_ruta_optimizada",
      "description": "Optimiza el orden de paradas para minimizar distancia y tiempo",
      "lambda_function": "calcular_ruta_optimizada",
      "input_schema": {
        "type": "object",
        "properties": {
          "paradas": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "stop_id": {"type": "string"},
                "lat": {"type": "number"},
                "lon": {"type": "number"}
              }
            }
          },
          "origen": {
            "type": "object",
            "properties": {
              "lat": {"type": "number"},
              "lon": {"type": "number"}
            }
          }
        },
        "required": ["paradas", "origen"]
      }
    }
  ]
}
```

## Permisos IAM

El agente necesita permisos para invocar las Lambda functions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:REGION:ACCOUNT_ID:function:consultar_ruta_afectada",
        "arn:aws:lambda:REGION:ACCOUNT_ID:function:consultar_flota_disponible",
        "arn:aws:lambda:REGION:ACCOUNT_ID:function:calcular_ruta_optimizada"
      ]
    }
  ]
}
```

AgentCore configura estos permisos automáticamente al desplegar.

## Testing

### Test de Gateway

```bash
# Listar gateways configurados
agentcore gateway list

# Ver detalles de un gateway
agentcore gateway describe --gateway-name smartsupply-gateway

# Test de herramienta individual
aws lambda invoke \
  --function-name consultar_ruta_afectada \
  --payload '{"truck_id":"1"}' \
  response.json
```

### Test del Agente con Herramientas

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-session \
  --input-text "¿Cuál es la ruta del camión 1?"
```

## Agregar Nueva Herramienta

### Paso 1: Crear Lambda Function

```python
# lambda_functions/mcp_tools/nueva_herramienta.py
def lambda_handler(event, context):
    # Tu lógica aquí
    return {
        'statusCode': 200,
        'body': json.dumps({'resultado': 'ok'})
    }
```

### Paso 2: Agregar a mcp_tools_schema.json

```json
{
  "name": "nueva_herramienta",
  "description": "Descripción de la nueva herramienta",
  "lambda_function": "nueva_herramienta",
  "input_schema": {...},
  "output_schema": {...}
}
```

### Paso 3: Reconfigurar Gateway

```bash
agentcore gateway configure \
  --gateway-name smartsupply-gateway \
  --tools-schema mcp_tools_schema.json
```

### Paso 4: Redesplegar Agente

```bash
agentcore launch
```

¡Listo! El agente ahora puede usar la nueva herramienta.

## Troubleshooting

### Error: "Tool not found"

**Causa**: La herramienta no está registrada en el gateway

**Solución**:
```bash
# Verificar herramientas registradas
agentcore gateway describe --gateway-name smartsupply-gateway

# Reconfigurar gateway
agentcore gateway configure \
  --gateway-name smartsupply-gateway \
  --tools-schema mcp_tools_schema.json
```

### Error: "Lambda function not found"

**Causa**: La Lambda function no existe o el nombre es incorrecto

**Solución**:
```bash
# Verificar que la Lambda existe
aws lambda get-function --function-name consultar_ruta_afectada

# Verificar nombre en mcp_tools_schema.json
cat mcp_tools_schema.json | jq '.tools[] | .lambda_function'
```

### Error: "Access denied"

**Causa**: El agente no tiene permisos para invocar la Lambda

**Solución**:
```bash
# Verificar permisos del rol del agente
aws iam get-role-policy \
  --role-name smart-supply-bedrock-agent-role \
  --policy-name lambda-invoke-policy

# Agregar permisos si faltan
aws iam put-role-policy \
  --role-name smart-supply-bedrock-agent-role \
  --policy-name lambda-invoke-policy \
  --policy-document file://lambda-policy.json
```

## Comparación: Router Manual vs AgentCore Gateway

| Aspecto | Router Manual | AgentCore Gateway |
|---------|---------------|-------------------|
| Código boilerplate | Alto | Ninguno |
| Configuración | Python code | JSON declarativo |
| Agregar herramienta | Modificar código | Agregar entrada JSON |
| Validación | Manual | Automática |
| Mantenimiento | Difícil | Fácil |
| Performance | Bueno | Excelente |
| Escalabilidad | Limitada | Alta |

## Conclusión

**NO necesitas crear `create_mcp_router_lambda.py`** porque AgentCore Gateway maneja todo automáticamente. Solo necesitas:

1. ✅ Definir herramientas en `mcp_tools_schema.json`
2. ✅ Configurar gateway con `agentcore gateway configure`
3. ✅ Desplegar agente con `agentcore launch`

El sistema es más simple, más mantenible y más escalable.

## Referencias

- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [MCP Tools Schema](./autonomous_agent/mcp_tools_schema.json)
- [Gateway Configuration Script](./autonomous_agent/configure_gateway.sh)

---

**Versión**: 1.0.0
**Fecha**: 2026-02-17
