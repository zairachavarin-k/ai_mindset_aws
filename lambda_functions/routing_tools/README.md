# Routing Tools - Lambda Functions

Lambda functions especializadas para el Agente de Ruteo.

## Herramientas Implementadas

### 1. consultar_trafico.py
Consulta el estado del tráfico actual en una ruta específica.

**Input:**
```json
{
  "origen": {"lat": 19.4384, "lon": -99.1569},
  "destino": {"lat": 19.4345, "lon": -99.1410}
}
```

**Output:**
```json
{
  "nivel_trafico": "moderado",
  "factor_tiempo": 1.3,
  "incidentes": [...]
}
```

**Integración pendiente:** Google Maps Traffic API o HERE Traffic API

### 2. consultar_clima.py
Consulta las condiciones climáticas actuales y pronóstico.

**Input:**
```json
{
  "ubicacion": {"lat": 19.4384, "lon": -99.1569},
  "hora_estimada": "2026-02-17T14:30:00"
}
```

**Output:**
```json
{
  "condicion": "despejado",
  "temperatura": 22,
  "factor_tiempo": 1.0,
  "visibilidad_km": 10,
  "recomendaciones": []
}
```

**Integración pendiente:** OpenWeatherMap API

### 3. validar_ventanas_entrega.py
Valida si una hora de llegada cumple con la ventana de entrega del cliente.

**Input:**
```json
{
  "stop_id": "STOP-1",
  "hora_llegada_estimada": "14:30"
}
```

**Output:**
```json
{
  "valida": true,
  "ventana_inicio": "08:00",
  "ventana_fin": "18:00",
  "penalizacion": 0
}
```

### 4. calcular_distancia_matriz.py
Calcula matriz de distancias entre múltiples puntos.

**Input:**
```json
{
  "puntos": [
    {"id": "depot", "lat": 19.4384, "lon": -99.1569},
    {"id": "STOP-1", "lat": 19.4345, "lon": -99.1410}
  ]
}
```

**Output:**
```json
{
  "matriz_distancias": [[0, 1.5], [1.5, 0]],
  "matriz_tiempos": [[0, 5], [5, 0]]
}
```

### 5. optimizar_ruta_tsp.py
Aplica algoritmo TSP para optimizar orden de paradas (single truck).

**Input:**
```json
{
  "matriz_distancias": [[0, 1.5, 2.3], [1.5, 0, 1.8], [2.3, 1.8, 0]],
  "punto_inicio": 0
}
```

**Output:**
```json
{
  "orden_optimo": [0, 2, 1, 0],
  "distancia_total": 4.1,
  "mejora_porcentaje": 15.3
}
```

**Algoritmo:** Nearest Neighbor + 2-opt

### 6. optimizar_ruta_mtsp.py
Optimiza rutas para múltiples camiones usando Ant Colony Optimization (ACO).

**Input:**
```json
{
  "num_trucks": 3,
  "paradas": [
    {"stop_id": "STOP-1", "lat": 19.4345, "lon": -99.1410}
  ],
  "origen": {"lat": 19.4384, "lon": -99.1569}
}
```

**Output:**
```json
{
  "status": "success",
  "rutas_optimizadas": [...],
  "metricas": {
    "distancia_total_km": 45.3,
    "mejora_vs_ruta_simple_porcentaje": 18.5
  }
}
```

**Algoritmo:** Ant Colony Optimization (mTSP)

### 7. calcular_tiempo_real.py
Calcula tiempo real de viaje considerando todos los factores.

**Input:**
```json
{
  "distancia_km": 15.5,
  "velocidad_base_kmh": 40,
  "factor_trafico": 1.3,
  "factor_clima": 1.15,
  "tipo_via": "ciudad"
}
```

**Output:**
```json
{
  "tiempo_minutos": 45.2,
  "velocidad_efectiva_kmh": 20.6,
  "factores_aplicados": {...}
}
```

### 8. considerar_fatiga_conductor.py
Calcula descansos necesarios según horas de trabajo del conductor.

**Input:**
```json
{
  "conductor": "Juan Pérez",
  "tiempo_ruta_minutos": 300,
  "hora_inicio": "08:00",
  "nivel_fatiga_actual": "Bajo"
}
```

**Output:**
```json
{
  "descansos_necesarios": [...],
  "tiempo_total_descansos": 30,
  "puede_completar_ruta": true,
  "recomendaciones": [...]
}
```

**Regulaciones:** SCT México - máximo 4 horas de conducción continua

### 9. validar_restricciones_ruta.py
Valida que la ruta cumple con todas las restricciones.

**Input:**
```json
{
  "ruta": {
    "paradas": [...],
    "tiempo_total_minutos": 300,
    "distancia_total_km": 45
  },
  "restricciones": {
    "max_horas_trabajo": 14,
    "capacidad_camion": 1000
  }
}
```

**Output:**
```json
{
  "valida": true,
  "violaciones": [],
  "sugerencias": []
}
```

## Testing Local

Cada Lambda function incluye un bloque `if __name__ == "__main__"` para testing local:

```bash
cd lambda_functions/routing_tools

# Test individual
python consultar_trafico.py
python consultar_clima.py
python optimizar_ruta_mtsp.py
```

## Despliegue

Las Lambda functions se despliegan automáticamente con el CDK stack:

```bash
cd infrastructure
./deploy.sh
```

O manualmente:

```bash
# Crear paquete de deployment
cd lambda_functions/routing_tools
pip install -r requirements.txt -t package/
cp *.py package/
cd package && zip -r ../routing_tools.zip . && cd ..

# Desplegar con AWS CLI
aws lambda create-function \
  --function-name consultar_trafico \
  --runtime python3.11 \
  --handler consultar_trafico.lambda_handler \
  --zip-file fileb://routing_tools.zip \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role
```

## Configuración de APIs Externas

### Google Maps Traffic API

1. Obtener API Key: https://console.cloud.google.com/
2. Habilitar APIs:
   - Directions API
   - Distance Matrix API
   - Traffic API
3. Configurar en Lambda:

```bash
aws lambda update-function-configuration \
  --function-name consultar_trafico \
  --environment Variables={GOOGLE_MAPS_API_KEY=YOUR_KEY}
```

### OpenWeatherMap API

1. Obtener API Key: https://openweathermap.org/api
2. Configurar en Lambda:

```bash
aws lambda update-function-configuration \
  --function-name consultar_clima \
  --environment Variables={OPENWEATHER_API_KEY=YOUR_KEY}
```

## Integración con Agente de Ruteo

Las Lambda functions se registran como herramientas MCP en el Agente de Ruteo:

```bash
cd bedrock_agents/routing_agent

# Configurar gateway
agentcore gateway configure \
  --gateway-name smartsupply-routing-gateway \
  --tools-schema mcp_tools_schema.json

# Desplegar agente
agentcore launch
```

## Monitoreo

Ver logs de las Lambda functions:

```bash
# Logs de tráfico
aws logs tail /aws/lambda/consultar_trafico --follow

# Logs de clima
aws logs tail /aws/lambda/consultar_clima --follow

# Logs de optimización mTSP
aws logs tail /aws/lambda/optimizar_ruta_mtsp --follow
```

## Métricas

CloudWatch métricas automáticas:
- Invocations
- Duration
- Errors
- Throttles

Ver métricas:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=optimizar_ruta_mtsp \
  --start-time 2026-02-17T00:00:00Z \
  --end-time 2026-02-17T23:59:59Z \
  --period 3600 \
  --statistics Average,Maximum
```

## Próximos Pasos

1. ✅ Implementar todas las Lambda functions
2. ⏳ Integrar APIs externas (Google Maps, OpenWeatherMap)
3. ⏳ Desplegar Lambda functions a AWS
4. ⏳ Configurar MCP Gateway del Agente de Ruteo
5. ⏳ Testing end-to-end con Agente Autónomo
6. ⏳ Optimizar performance y costos

## Referencias

- [Agente de Ruteo README](../../bedrock_agents/routing_agent/README.md)
- [MCP Tools Schema](../../bedrock_agents/routing_agent/mcp_tools_schema.json)
- [Arquitectura Multi-Agente](../../bedrock_agents/MULTI_AGENT_ARCHITECTURE.md)
