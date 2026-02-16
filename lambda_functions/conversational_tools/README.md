# Conversational Tools - Lambda Functions

Lambda functions para el Agente Conversacional de SmartSupply.

## Herramientas Implementadas

### 1. consultar_estado_ruta.py
Consulta el estado actual de una ruta específica con todos sus detalles.

**Input:**
```json
{
  "truck_id": "1",
  "fecha": "2026-02-17"
}
```

**Output:**
```json
{
  "truck_id": "1",
  "estado": "En ruta",
  "paradas_totales": 5,
  "paradas_completadas": 2,
  "paradas_pendientes": 3,
  "proxima_parada": {...},
  "conductor": "Juan Pérez",
  "nivel_fatiga": "Bajo"
}
```

### 2. consultar_incidentes.py
Consulta incidentes con filtros opcionales.

**Input:**
```json
{
  "incident_id": "INC-001",
  "truck_id": "1",
  "estado": "Pendiente",
  "limit": 10
}
```

**Output:**
```json
{
  "incidentes": [...],
  "total": 5
}
```

### 3. consultar_inventario.py
Consulta inventario del almacén con filtros.

**Input:**
```json
{
  "sku": "SKU-001",
  "categoria": "Farma",
  "solo_disponibles": true
}
```

**Output:**
```json
{
  "items": [...],
  "total_items": 10
}
```

### 4. consultar_plan_reasignacion.py
Obtiene el plan de reasignación generado por el Agente Autónomo.

**Input:**
```json
{
  "incident_id": "INC-001"
}
```

**Output:**
```json
{
  "plan_id": "PLAN-001",
  "estado": "Pendiente aprobación",
  "solucion": {...},
  "justificacion": "...",
  "puede_aprobar": true
}
```

### 5. aprobar_reasignacion.py ✅
Aprueba o rechaza un plan y ejecuta si es aprobado.

**Input:**
```json
{
  "plan_id": "PLAN-001",
  "aprobado": true,
  "operador": "Maria Lopez",
  "comentarios": "Plan aprobado"
}
```

**Output:**
```json
{
  "success": true,
  "estado": "Ejecutado",
  "acciones_ejecutadas": [...],
  "mensaje": "Plan ejecutado exitosamente"
}
```

### 6. ejecutar_comando.py
Ejecuta comandos operacionales.

**Comandos soportados:**
- `cancelar_parada`: Eliminar una parada de una ruta
- `marcar_incidente_resuelto`: Cerrar un incidente
- `actualizar_nivel_fatiga`: Cambiar estado del conductor

**Input:**
```json
{
  "comando": "cancelar_parada",
  "parametros": {
    "truck_id": "1",
    "stop_id": "STOP-5"
  },
  "operador": "Maria Lopez"
}
```

**Output:**
```json
{
  "success": true,
  "comando": "cancelar_parada",
  "resultado": "Parada cancelada exitosamente"
}
```

### 7. generar_reporte.py
Genera reportes en CSV o JSON.

**Tipos de reporte:**
- `incidentes`: Incidentes por período
- `performance_flota`: Performance de camiones
- `inventario`: Estado actual del inventario
- `tiempos_respuesta`: Tiempos de respuesta del sistema

**Input:**
```json
{
  "tipo_reporte": "incidentes",
  "formato": "csv",
  "fecha_desde": "2026-02-01",
  "fecha_hasta": "2026-02-17"
}
```

**Output:**
```json
{
  "success": true,
  "reporte_id": "REP-001",
  "url_descarga": "https://s3.../reportes/...",
  "registros_totales": 45
}
```

## Testing Local

Cada Lambda function incluye un bloque `if __name__ == "__main__"` para testing:

```bash
cd lambda_functions/conversational_tools

# Test individual
python consultar_estado_ruta.py
python consultar_incidentes.py
python aprobar_reasignacion.py
```

## Despliegue

Las Lambda functions se despliegan con el CDK stack:

```bash
cd infrastructure
./deploy.sh
```

O manualmente:

```bash
# Crear paquete
cd lambda_functions/conversational_tools
pip install -r requirements.txt -t package/
cp *.py package/
cd package && zip -r ../conversational_tools.zip . && cd ..

# Desplegar
aws lambda create-function \
  --function-name consultar_estado_ruta_conversacional \
  --runtime python3.11 \
  --handler consultar_estado_ruta.lambda_handler \
  --zip-file fileb://conversational_tools.zip \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role
```

## Integración con Agente Conversacional

Las Lambda functions se registran como herramientas MCP:

```bash
cd bedrock_agents/conversational_agent

# Configurar gateway
agentcore gateway configure \
  --gateway-name smartsupply-conversational-gateway \
  --tools-schema mcp_tools_schema.json

# Desplegar agente
agentcore launch
```

## Permisos IAM

Las Lambda functions requieren permisos para:

- DynamoDB: `rutas_entregas`, `flota_camiones`, `incidencias`, `inventario_almacen`, `agent_memory`, `conversational_agent_memory`
- S3: `smart-supply-data` (lectura/escritura)
- Lambda: Invocar otras Lambda functions (para ejecución de planes)

## Monitoreo

```bash
# Logs de Lambda específica
aws logs tail /aws/lambda/consultar_estado_ruta_conversacional --follow
aws logs tail /aws/lambda/aprobar_reasignacion --follow

# Métricas
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=aprobar_reasignacion \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

## Próximos Pasos

1. ✅ Implementar Lambda functions core (consultar_estado_ruta, consultar_incidentes, aprobar_reasignacion)
2. ⏳ Implementar Lambda functions restantes (consultar_inventario, consultar_plan_reasignacion, ejecutar_comando, generar_reporte)
3. ⏳ Desplegar Lambda functions a AWS
4. ⏳ Configurar MCP Gateway del Agente Conversacional
5. ⏳ Testing end-to-end con operadores
6. ⏳ Integrar con Amazon Connect para canal de voz

## Referencias

- [Agente Conversacional README](../../bedrock_agents/conversational_agent/README.md)
- [MCP Tools Schema](../../bedrock_agents/conversational_agent/mcp_tools_schema.json)
- [Arquitectura Multi-Agente](../../bedrock_agents/MULTI_AGENT_ARCHITECTURE.md)

---

**Versión**: 1.0.0
**Fecha**: 2026-02-17
