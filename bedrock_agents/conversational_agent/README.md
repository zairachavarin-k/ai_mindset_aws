# Agente Conversacional SmartSupply

Asistente logístico inteligente para operadores - consultas, aprobaciones y comandos operacionales.

## Descripción

El Agente Conversacional es el punto de contacto principal para operadores de SmartSupply. Proporciona una interfaz natural en lenguaje humano para:

- Consultar estado de rutas, incidentes, inventario y flota
- Revisar y aprobar planes de reasignación generados por el Agente Autónomo
- Ejecutar comandos operacionales
- Generar reportes

## Características

### 1. Consultas de Estado

```
Operador: "¿Cuál es el estado del camión 1?"

Agente: "El camión 1 está actualmente detenido debido a un incidente 
de choque grave reportado a las 10:45. Tiene 5 paradas pendientes 
que están siendo reasignadas al camión 3. ¿Quieres ver el plan de 
reasignación?"
```

### 2. Revisión de Planes

```
Operador: "Muéstrame el plan de reasignación para INC-001"

Agente: "Plan de Reasignación #INC-001:

Incidente: Choque grave en camión 1
Gravedad: Crítica

Solución propuesta:
- Camión de reemplazo: Camión 3 (más cercano, 5.2 km)
- Paradas reasignadas: 5 paradas
- Impacto: +15 minutos en entregas
- Clientes afectados: 2 Farma, 3 Salud

Justificación:
El camión 3 tiene capacidad suficiente y está más cerca.
Todas las ventanas de entrega se mantienen.

¿Deseas aprobar este plan?"
```

### 3. Aprobación de Reasignaciones

```
Operador: "Sí, apruébalo"

Agente: "✅ Plan aprobado y ejecutado exitosamente.

Acciones completadas:
- Ruta actualizada para camión 3
- Notificaciones enviadas a 5 clientes
- Incidente registrado en el sistema

¿Necesitas algo más?"
```

### 4. Comandos Operacionales

```
Operador: "Cancela la parada STOP-5 del camión 2"

Agente: "¿Confirmas que deseas cancelar la parada STOP-5 del camión 2?
Esta acción no se puede deshacer."

Operador: "Sí, confirmo"

Agente: "✅ Parada STOP-5 cancelada exitosamente.
Cliente notificado automáticamente."
```

### 5. Generación de Reportes

```
Operador: "Genera un reporte de incidentes de la última semana"

Agente: "Generando reporte de incidentes...

✅ Reporte generado exitosamente:
- Período: 2026-02-10 a 2026-02-17
- Total incidentes: 12
- Formato: CSV
- Tamaño: 45 KB

Descarga: https://s3.../reportes/incidentes_2026-02-17.csv

¿Necesitas algún otro reporte?"
```

## Herramientas MCP (7 herramientas)

1. **consultar_estado_ruta** - Estado actual de una ruta
2. **consultar_incidentes** - Incidentes con filtros
3. **consultar_inventario** - Inventario del almacén
4. **consultar_plan_reasignacion** - Plan generado por Agente Autónomo
5. **aprobar_reasignacion** - Aprobar/rechazar y ejecutar plan
6. **ejecutar_comando** - Comandos operacionales
7. **generar_reporte** - Reportes en CSV/JSON

## Configuración

### Modelo

- **Modelo**: Claude 3.5 Sonnet
- **Timeout**: 60 segundos
- **Memoria**: 1024 MB
- **Memory**: STM_AND_LTM (sesión + histórico)

### Personalidad

- **Profesional**: Lenguaje claro y preciso
- **Conciso**: Respuestas directas
- **Proactivo**: Sugiere acciones relevantes
- **Empático**: Reconoce urgencia de situaciones críticas

## Despliegue

### Paso 1: Instalar dependencias

```bash
cd bedrock_agents/conversational_agent
pip install -r requirements.txt
```

### Paso 2: Configurar agente

```bash
agentcore configure --entrypoint src.main:app --non-interactive
```

### Paso 3: Desplegar

```bash
agentcore launch
```

### Paso 4: Verificar

```bash
agentcore status
```

## Testing

### Test directo del agente

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id $CONVERSATIONAL_AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-session \
  --input-text "¿Cuál es el estado del camión 1?"
```

### Test de herramientas MCP

```bash
# Test consultar_estado_ruta
aws lambda invoke \
  --function-name consultar_estado_ruta_conversacional \
  --payload '{"truck_id":"1"}' \
  response.json

# Test aprobar_reasignacion
aws lambda invoke \
  --function-name aprobar_reasignacion \
  --payload '{"plan_id":"PLAN-001","aprobado":true,"operador":"Test"}' \
  response.json
```

## Integración con Canales

### Amazon Connect (Voz)

```
Cliente llama → Amazon Connect
  ↓
Transcribe (voz → texto)
  ↓
Agente Conversacional
  ↓
Polly (texto → voz)
  ↓
Respuesta al cliente
```

### Web Chat

```
Operador escribe → API Gateway
  ↓
Lambda intermediaria
  ↓
Agente Conversacional
  ↓
Respuesta JSON
  ↓
Frontend muestra respuesta
```

## Memoria y Aprendizaje

El agente mantiene memoria de:

- **Sesión (STM)**: Consultas previas del operador en la conversación actual
- **Largo plazo (LTM)**: Patrones de consultas, preferencias del operador, decisiones históricas

Tabla DynamoDB: `conversational_agent_memory`

## Monitoreo

### Logs

```bash
aws logs tail /aws/bedrock/agentcore/smartsupply-conversational-agent --follow
```

### Métricas

- Invocaciones por operador
- Tiempo de respuesta promedio
- Tasa de aprobación de planes
- Comandos ejecutados

### Alarmas

- Latencia > 10 segundos
- Tasa de error > 5%
- Aprobaciones rechazadas > 20%

## Casos de Uso

### Caso 1: Consulta Rápida

```
Operador: "¿Cuántas paradas tiene pendientes el camión 3?"
Agente: "El camión 3 tiene 4 paradas pendientes. La próxima es 
en 15 minutos (STOP-7, Cliente Farma ABC)."
```

### Caso 2: Aprobación de Plan

```
Operador: "Muéstrame el plan para el incidente INC-045"
Agente: [Presenta plan detallado]
Operador: "Apruébalo"
Agente: [Ejecuta plan y confirma]
```

### Caso 3: Comando Operacional

```
Operador: "Marca el incidente INC-042 como resuelto"
Agente: "✅ Incidente INC-042 marcado como resuelto."
```

### Caso 4: Reporte

```
Operador: "Dame un reporte de performance de la flota del mes"
Agente: [Genera y proporciona URL de descarga]
```

## Mejores Prácticas

### Para Operadores

1. **Sé específico**: "Estado del camión 1" es mejor que "¿Cómo va todo?"
2. **Confirma acciones**: El agente pedirá confirmación para comandos críticos
3. **Usa contexto**: El agente recuerda la conversación actual
4. **Pide ayuda**: "¿Qué puedes hacer?" muestra capacidades

### Para Administradores

1. **Monitorea aprobaciones**: Revisa tasa de aprobación/rechazo
2. **Analiza consultas**: Identifica patrones para mejorar el sistema
3. **Actualiza memoria**: Limpia memoria antigua periódicamente
4. **Entrena operadores**: Proporciona guía de uso efectivo

## Limitaciones

- No puede modificar datos directamente sin aprobación
- Requiere que el Agente Autónomo haya generado un plan primero
- Comandos críticos requieren confirmación explícita
- Reportes grandes pueden tardar varios segundos

## Próximos Pasos

1. Integrar con Amazon Connect para canal de voz
2. Agregar más comandos operacionales
3. Implementar sugerencias proactivas basadas en patrones
4. Mejorar memoria con embeddings para búsqueda semántica

## Referencias

- [Agente Autónomo](../autonomous_agent/README.md)
- [Agente de Ruteo](../routing_agent/README.md)
- [Arquitectura Multi-Agente](../MULTI_AGENT_ARCHITECTURE.md)
- [Lambda Functions](../../lambda_functions/conversational_tools/README.md)

---

**Versión**: 1.0.0
**Fecha**: 2026-02-17
