# SmartSupply Bedrock Agents - Quick Reference

Guía rápida de comandos y referencias para los agentes de SmartSupply.

## Agentes Implementados

### 1. Agente Autónomo
- **Propósito**: Análisis de incidentes y toma de decisiones
- **Modelo**: Claude 3.5 Sonnet
- **Herramientas**: 9 MCP tools (8 originales + 1 para invocar Routing Agent)
- **Directorio**: `bedrock_agents/autonomous_agent/`

### 2. Agente de Ruteo
- **Propósito**: Optimización especializada de rutas
- **Modelo**: Claude 3.5 Sonnet
- **Herramientas**: 9 MCP tools especializadas en ruteo
- **Directorio**: `bedrock_agents/routing_agent/`

### 3. Agente Conversacional
- **Propósito**: Asistente para operadores - consultas, aprobaciones y comandos
- **Modelo**: Claude 3.5 Sonnet
- **Herramientas**: 7 MCP tools para interacción con operadores
- **Directorio**: `bedrock_agents/conversational_agent/`

## Comandos Rápidos

### Despliegue

```bash
# Desplegar infraestructura base
cd infrastructure
./deploy.sh

# Desplegar Agente Autónomo
cd bedrock_agents/autonomous_agent
agentcore launch

# Desplegar Agente de Ruteo
cd bedrock_agents/routing_agent
agentcore launch

# Desplegar Agente Conversacional
cd bedrock_agents/conversational_agent
agentcore launch

# Verificar estado
agentcore status
```

### Testing

```bash
# Test Agente Autónomo (vía EventBridge)
aws events put-events --entries '[{
  "Source": "smartsupply.iot",
  "DetailType": "IncidentDetected",
  "Detail": "{\"incident_id\":\"INC-TEST-001\",\"truck_id\":\"1\",\"tipo_incidente\":\"Choque / Colisión Grave\"}",
  "EventBusName": "smart-supply-events"
}]'

# Test Agente de Ruteo (directo)
aws bedrock-agent-runtime invoke-agent \
  --agent-id $ROUTING_AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-1 \
  --input-text "Optimiza ruta para 3 camiones con 8 paradas"

# Test Agente Conversacional (directo)
aws bedrock-agent-runtime invoke-agent \
  --agent-id $CONVERSATIONAL_AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-1 \
  --input-text "¿Cuál es el estado del camión 1?"

# Test Lambda individual
aws lambda invoke \
  --function-name smartsupply-routing-optimizar_ruta_mtsp \
  --payload file://test.json \
  response.json
```

### Monitoreo

```bash
# Logs Agente Autónomo
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow

# Logs Agente de Ruteo
aws logs tail /aws/bedrock/agentcore/smartsupply-routing-agent --follow

# Logs Lambda específica
aws logs tail /aws/lambda/smartsupply-routing-optimizar_ruta_mtsp --follow

# Dashboard CloudWatch
aws cloudwatch get-dashboard \
  --dashboard-name SmartSupply-BedrockAgent-Dashboard
```

### Configuración

```bash
# Configurar MCP Gateway (Agente Autónomo)
cd bedrock_agents/autonomous_agent
./configure_gateway.sh

# Configurar MCP Gateway (Agente de Ruteo)
cd bedrock_agents/routing_agent
agentcore gateway configure \
  --gateway-name smartsupply-routing-gateway \
  --tools-schema mcp_tools_schema.json

# Configurar Memory
./configure_memory.sh

# Configurar Observability
./configure_observability.sh

# Configurar EventBridge
./configure_eventbridge.sh
```

## Estructura de Archivos

```
bedrock_agents/
├── autonomous_agent/              # Agente Autónomo
│   ├── src/main.py               # Código del agente
│   ├── .bedrock_agentcore.yaml   # Configuración
│   ├── mcp_tools_schema.json     # 9 herramientas MCP
│   ├── configure_*.sh            # Scripts de configuración
│   └── *.md                      # Documentación
│
├── routing_agent/                 # Agente de Ruteo
│   ├── src/main.py               # Código del agente
│   ├── .bedrock_agentcore.yaml   # Configuración
│   ├── mcp_tools_schema.json     # 9 herramientas MCP
│   └── *.md                      # Documentación
│
├── MULTI_AGENT_ARCHITECTURE.md   # Arquitectura multi-agente
├── IMPLEMENTATION_SUMMARY.md     # Resumen de implementación
├── DEPLOYMENT_GUIDE.md           # Guía de despliegue
└── QUICK_REFERENCE.md            # Esta guía

lambda_functions/
├── mcp_tools/                     # Herramientas Agente Autónomo
│   ├── consultar_ruta_afectada.py
│   ├── consultar_flota_disponible.py
│   ├── calcular_ruta_optimizada.py
│   ├── invocar_agente_ruteo.py   # Invoca Routing Agent
│   └── ... (8 funciones total)
│
└── routing_tools/                 # Herramientas Agente de Ruteo
    ├── consultar_trafico.py
    ├── consultar_clima.py
    ├── optimizar_ruta_mtsp.py    # Ant Colony Optimization
    └── ... (9 funciones total)
```

## Herramientas MCP

### Agente Autónomo (9 herramientas)

1. `consultar_ruta_afectada` - Obtener ruta del camión afectado
2. `consultar_flota_disponible` - Listar camiones disponibles
3. `consultar_inventario_almacen` - Consultar inventario
4. `calcular_distancia` - Calcular distancia entre puntos GPS
5. `calcular_ruta_optimizada` - Generar ruta optimizada (básica)
6. `actualizar_ruta_s3` - Actualizar ruta en S3
7. `registrar_incidencia` - Registrar incidente
8. `enviar_notificacion_cliente` - Enviar notificación
9. `invocar_agente_ruteo` - **NUEVO** - Invocar Agente de Ruteo

### Agente de Ruteo (9 herramientas)

1. `consultar_trafico` - Tráfico en tiempo real
2. `consultar_clima` - Condiciones climáticas
3. `validar_ventanas_entrega` - Validar horarios de cliente
4. `calcular_distancia_matriz` - Matriz de distancias
5. `optimizar_ruta_tsp` - TSP (single truck)
6. `optimizar_ruta_mtsp` - **mTSP con ACO** (multi-truck)
7. `calcular_tiempo_real` - Tiempo con factores contextuales
8. `considerar_fatiga_conductor` - Descansos obligatorios
9. `validar_restricciones_ruta` - Validación completa

## Flujos de Trabajo

### Flujo 1: Incidente Detectado

```
1. IoT/Voice/Web detecta incidente
   ↓
2. EventBridge recibe evento
   ↓
3. Lambda intermediaria invoca Agente Autónomo
   ↓
4. Agente Autónomo:
   a. Consulta ruta afectada
   b. Consulta flota disponible
   c. Invoca Agente de Ruteo para optimización
   ↓
5. Agente de Ruteo:
   a. Consulta tráfico
   b. Consulta clima
   c. Optimiza ruta (ACO)
   d. Valida restricciones
   ↓
6. Agente Autónomo recibe ruta optimizada
   ↓
7. Agente Autónomo ejecuta acciones:
   a. Actualiza ruta en S3
   b. Registra incidencia
   c. Envía notificaciones
```

### Flujo 2: Optimización de Ruta

```
1. Agente Autónomo necesita ruta optimizada
   ↓
2. Invoca herramienta invocar_agente_ruteo
   ↓
3. Lambda invoca Agente de Ruteo vía Bedrock Runtime
   ↓
4. Agente de Ruteo ejecuta herramientas:
   - consultar_trafico → Factor 1.3
   - consultar_clima → Factor 1.0
   - calcular_distancia_matriz → Matriz 8x8
   - optimizar_ruta_mtsp → ACO optimization
   - calcular_tiempo_real → 4h 15min
   - considerar_fatiga_conductor → 1 descanso
   - validar_ventanas_entrega → Todas válidas
   - validar_restricciones_ruta → Sin violaciones
   ↓
5. Agente de Ruteo retorna ruta optimizada
   ↓
6. Agente Autónomo usa ruta en plan
```

## Variables de Entorno

### Agente Autónomo

```bash
# Lambda invocar_agente_ruteo
ROUTING_AGENT_ID=<agent-id>
ROUTING_AGENT_ALIAS_ID=TSTALIASID

# Lambda intermediaria EventBridge
AGENT_ID=<autonomous-agent-id>
AGENT_ALIAS_ID=TSTALIASID
```

### Agente de Ruteo

```bash
# Lambda consultar_trafico
GOOGLE_MAPS_API_KEY=<your-key>

# Lambda consultar_clima
OPENWEATHER_API_KEY=<your-key>

# Todas las Lambda functions
BUCKET_NAME=smart-supply-data
```

## Métricas Clave

### Agente Autónomo

- **Latencia**: < 180s (SLA)
- **Tasa de error**: < 5%
- **Invocaciones**: ~100/día
- **Costo**: ~$0.50/incidente

### Agente de Ruteo

- **Latencia**: < 30s
- **Precisión de tiempos**: > 85%
- **Mejora vs ruta simple**: 15-25%
- **Costo**: ~$0.20/optimización

## Troubleshooting

### Problema: Agente no responde

```bash
# Verificar estado
agentcore status

# Ver logs
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow

# Verificar acceso a modelo
aws bedrock list-foundation-models --query 'modelSummaries[?modelId==`anthropic.claude-3-5-sonnet-20241022-v2:0`]'
```

### Problema: Herramienta MCP falla

```bash
# Test Lambda directamente
aws lambda invoke \
  --function-name smartsupply-consultar_ruta_afectada \
  --payload '{"truck_id":"1"}' \
  response.json

# Ver logs de Lambda
aws logs tail /aws/lambda/smartsupply-consultar_ruta_afectada --follow

# Verificar permisos IAM
aws iam get-role-policy \
  --role-name smart-supply-lambda-role \
  --policy-name lambda-policy
```

### Problema: Routing Agent no se invoca

```bash
# Verificar variable de entorno
aws lambda get-function-configuration \
  --function-name smartsupply-invocar_agente_ruteo \
  --query 'Environment.Variables'

# Actualizar si falta
ROUTING_AGENT_ID=$(cd bedrock_agents/routing_agent && agentcore status | grep "Agent ID" | awk '{print $3}')
aws lambda update-function-configuration \
  --function-name smartsupply-invocar_agente_ruteo \
  --environment Variables={ROUTING_AGENT_ID=$ROUTING_AGENT_ID}
```

### Problema: Timeout en optimización

```bash
# Aumentar timeout y memoria
aws lambda update-function-configuration \
  --function-name smartsupply-routing-optimizar_ruta_mtsp \
  --timeout 120 \
  --memory-size 1024
```

## Costos Estimados

### Mensual (100 incidentes/día)

| Componente | Costo |
|------------|-------|
| Agente Autónomo | $30-50 |
| Agente de Ruteo | $30-50 |
| Lambda Functions | $10-15 |
| APIs Externas | $15-20 |
| S3 + DynamoDB | $3-5 |
| CloudWatch | $2-3 |
| **Total** | **$90-143** |

## Documentación Completa

### Agente Autónomo
- [README](autonomous_agent/README.md)
- [Gateway Configuration](autonomous_agent/GATEWAY_CONFIGURATION.md)
- [Memory Configuration](autonomous_agent/MEMORY_CONFIGURATION.md)
- [Observability Configuration](autonomous_agent/OBSERVABILITY_CONFIGURATION.md)
- [EventBridge Integration](autonomous_agent/EVENTBRIDGE_INTEGRATION.md)

### Agente de Ruteo
- [README](routing_agent/README.md)
- [Complete Implementation](routing_agent/COMPLETE_IMPLEMENTATION.md)
- [Implementation Summary](routing_agent/IMPLEMENTATION_SUMMARY.md)

### Lambda Functions
- [MCP Tools README](../lambda_functions/mcp_tools/README.md)
- [Routing Tools README](../lambda_functions/routing_tools/README.md)
- [Routing Tools Deployment](../lambda_functions/routing_tools/DEPLOYMENT_GUIDE.md)

### General
- [Multi-Agent Architecture](MULTI_AGENT_ARCHITECTURE.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

## Enlaces Útiles

- [AWS Bedrock Console](https://console.aws.amazon.com/bedrock/)
- [CloudWatch Dashboard](https://console.aws.amazon.com/cloudwatch/)
- [Lambda Functions](https://console.aws.amazon.com/lambda/)
- [DynamoDB Tables](https://console.aws.amazon.com/dynamodb/)
- [S3 Buckets](https://console.aws.amazon.com/s3/)
- [EventBridge Rules](https://console.aws.amazon.com/events/)

## Soporte

Para problemas o preguntas:
1. Revisar logs en CloudWatch
2. Consultar documentación específica
3. Verificar configuración con `agentcore status`
4. Revisar métricas en CloudWatch Dashboard

---

**Última actualización**: 2026-02-17
**Versión**: 1.0.0
