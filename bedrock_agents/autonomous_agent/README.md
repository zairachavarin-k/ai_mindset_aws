# SmartSupply Autonomous Agent

Agente autónomo de Bedrock AgentCore para análisis de incidentes y reasignación automática de recursos logísticos.

## Descripción

Este agente procesa eventos de incidentes críticos (choques, robos, fallas mecánicas) y genera planes de reasignación óptimos en menos de 3 minutos. Utiliza Amazon Bedrock con Claude 3.5 Sonnet para razonamiento complejo multi-paso.

## Características

- **Análisis Inteligente**: Razonamiento multi-paso usando Claude 3.5 Sonnet
- **Herramientas MCP**: Acceso a Lambda functions para consultar datos
- **Memoria**: Aprendizaje continuo de decisiones previas (AgentCore Memory)
- **Observabilidad**: Tracing completo de invocaciones y métricas
- **Serverless**: Ejecución en AgentCore Runtime con auto-scaling

## Requisitos

- Python 3.11+
- AWS CLI configurado
- Bedrock AgentCore Starter Toolkit: `pip install bedrock-agentcore-starter-toolkit`
- Acceso a Amazon Bedrock (modelo Claude 3.5 Sonnet)

## Desarrollo Local

### 1. Instalar dependencias

```bash
cd bedrock_agents/autonomous_agent
pip install -r requirements.txt
```

### 2. Iniciar servidor de desarrollo

```bash
agentcore dev
```

El servidor estará disponible en `http://localhost:8080/invocations`

### 3. Probar localmente

```bash
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

## Despliegue a AWS

### 1. Configurar el agente

```bash
agentcore configure --entrypoint src.main:app --non-interactive
```

### 2. Desplegar a AgentCore Runtime

```bash
agentcore launch
```

### 3. Verificar estado

```bash
agentcore status
```

### 4. Probar en la nube

```bash
agentcore invoke '{
  "detail": {
    "incident_id": "INC-901",
    "truck_id": "1",
    "tipo_incidente": "Choque / Colisión Grave",
    "nivel_gravedad": "Crítico",
    "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410}
  }
}'
```

## Herramientas MCP Disponibles

El agente tiene acceso a las siguientes herramientas (configuradas en AgentCore Gateway):

1. **consultar_ruta_afectada**: Obtiene ruta completa del camión afectado
2. **consultar_flota_disponible**: Lista camiones disponibles con capacidad y fatiga
3. **consultar_inventario_almacen**: Verifica disponibilidad de productos en almacén
4. **calcular_distancia**: Calcula distancia entre dos puntos GPS
5. **calcular_ruta_optimizada**: Genera ruta optimizada para paradas
6. **actualizar_ruta_s3**: Escribe ruta actualizada en S3
7. **registrar_incidencia**: Registra incidencia en S3 y DynamoDB
8. **enviar_notificacion_cliente**: Envía notificación vía Amazon Connect

## Configuración de Memoria

Después del despliegue inicial, actualizar `.bedrock_agentcore.yaml` para habilitar memoria:

```yaml
memory:
  mode: STM_AND_LTM
  table_name: agent_memory
```

Luego redesplegar:

```bash
agentcore launch
```

## Observabilidad

### CloudWatch Logs

Los logs están disponibles en CloudWatch Logs con el grupo:
- `/aws/bedrock/agentcore/smartsupply-autonomous-agent`

### CloudWatch Metrics

Métricas disponibles:
- Invocaciones por hora
- Latencia (P50, P90, P99)
- Errores por tipo
- Herramientas más usadas

### X-Ray Tracing

Cada invocación genera un trace completo visible en AWS X-Ray.

## Estructura del Plan de Reasignación

El agente genera planes con la siguiente estructura:

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

## Limpieza

Para destruir todos los recursos:

```bash
# Vista previa
agentcore destroy --dry-run

# Destruir
agentcore destroy
```

## Troubleshooting

### Error: Model access denied
Verificar que tienes acceso al modelo Claude 3.5 Sonnet en la consola de Bedrock.

### Error: Timeout después de 180 segundos
El agente está configurado con timeout de 3 minutos. Si excede este tiempo, revisar la complejidad del análisis.

### Error: Herramientas MCP no disponibles
Verificar que AgentCore Gateway está configurado correctamente con las Lambda functions.

## Referencias

- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [SmartSupply Design Document](../../.kiro/specs/smart-supply/design.md)
- [SmartSupply Requirements](../../.kiro/specs/smart-supply/requirements.md)
