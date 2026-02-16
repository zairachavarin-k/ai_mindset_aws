# SmartSupply Routing Agent

Agente especializado en cálculo de rutas óptimas con contexto completo (tráfico, clima, restricciones).

## Descripción

Este agente se enfoca exclusivamente en optimización de rutas logísticas, considerando múltiples factores contextuales que afectan los tiempos de viaje y la eficiencia de las entregas.

## Características

### Análisis Contextual Completo

- **Tráfico en Tiempo Real**: Consulta estado actual del tráfico en cada segmento
- **Condiciones Climáticas**: Ajusta tiempos según clima (lluvia, nieve, etc.)
- **Ventanas de Entrega**: Valida y optimiza para cumplir horarios de clientes
- **Fatiga del Conductor**: Calcula descansos obligatorios según regulaciones
- **Restricciones de Capacidad**: Valida que el camión puede llevar toda la carga
- **Prioridad de Clientes**: Considera criticidad (Farma > Salud > Tecnología)

### Algoritmos de Optimización

- **TSP (Traveling Salesman Problem)**: Para rutas con un solo camión
- **VRP (Vehicle Routing Problem)**: Para múltiples camiones
- **Optimización con Restricciones**: Considera ventanas de tiempo, capacidad, etc.
- **Heurísticas Avanzadas**: Nearest Neighbor, 2-opt, 3-opt

### Cálculo de Tiempos Precisos

- Tiempo base según distancia y velocidad
- Ajuste por tráfico (factor 1.0 - 2.0)
- Ajuste por clima (lluvia +15%, nieve +30%)
- Tiempo de descarga por parada (5-15 minutos)
- Descansos del conductor (30 min cada 4 horas)

## Herramientas MCP (8 herramientas)

1. **consultar_trafico**: Estado del tráfico en tiempo real
2. **consultar_clima**: Condiciones climáticas actuales y pronóstico
3. **validar_ventanas_entrega**: Valida horarios de entrega
4. **calcular_distancia_matriz**: Matriz de distancias entre puntos
5. **optimizar_ruta_tsp**: Algoritmo TSP para orden óptimo
6. **calcular_tiempo_real**: Tiempo real considerando factores
7. **considerar_fatiga_conductor**: Descansos necesarios
8. **validar_restricciones_ruta**: Valida cumplimiento de restricciones

## Uso

### Invocación desde Agente Autónomo

El Agente Autónomo invoca al Agente de Ruteo cuando necesita calcular rutas:

```python
# El Agente Autónomo invoca al Agente de Ruteo
routing_request = {
    "paradas": [
        {"stop_id": "STOP-1", "lat": 19.4345, "lon": -99.1410},
        {"stop_id": "STOP-2", "lat": 19.4456, "lon": -99.1523},
        {"stop_id": "STOP-3", "lat": 19.4567, "lon": -99.1634}
    ],
    "origen": {"lat": 19.4384, "lon": -99.1569},  # Almacén
    "truck_id": "3",
    "conductor": "Ing. Ernesto Rosado",
    "restricciones": {
        "max_horas_trabajo": 8,
        "nivel_fatiga_actual": "Bajo",
        "capacidad_camion_ton": 2.5,
        "ventanas_entrega": [
            {"stop_id": "STOP-1", "inicio": "10:00", "fin": "12:00"},
            {"stop_id": "STOP-2", "inicio": "13:00", "fin": "15:00"},
            {"stop_id": "STOP-3", "inicio": "15:30", "fin": "17:00"}
        ]
    }
}

# Invocar agente de ruteo
response = bedrock_agent_runtime.invoke_agent(
    agentId='routing-agent-id',
    agentAliasId='TSTALIASID',
    sessionId='routing-session-123',
    inputText=json.dumps(routing_request)
)
```

### Respuesta del Agente de Ruteo

```json
{
  "ruta_optimizada": [
    {
      "orden": 1,
      "stop_id": "STOP-1",
      "hora_llegada": "10:30",
      "tiempo_desde_anterior": 25,
      "distancia_desde_anterior_km": 5.2,
      "factores": {
        "trafico": 1.1,
        "clima": 1.0
      }
    },
    {
      "orden": 2,
      "stop_id": "STOP-2",
      "hora_llegada": "13:15",
      "tiempo_desde_anterior": 30,
      "distancia_desde_anterior_km": 6.8,
      "factores": {
        "trafico": 1.3,
        "clima": 1.0
      }
    },
    {
      "orden": 3,
      "stop_id": "STOP-3",
      "hora_llegada": "15:45",
      "tiempo_desde_anterior": 20,
      "distancia_desde_anterior_km": 4.5,
      "factores": {
        "trafico": 1.0,
        "clima": 1.0
      }
    }
  ],
  "metricas": {
    "distancia_total_km": 16.5,
    "tiempo_total_minutos": 195,
    "tiempo_viaje_minutos": 75,
    "tiempo_descansos_minutos": 30,
    "tiempo_descargas_minutos": 30,
    "tiempo_esperas_minutos": 60,
    "ahorro_vs_original_km": 3.2,
    "ahorro_vs_original_minutos": 25
  },
  "descansos": [
    {
      "despues_parada": 2,
      "duracion_minutos": 30,
      "motivo": "Descanso obligatorio después de 4 horas"
    }
  ],
  "validacion": {
    "cumple_ventanas": true,
    "cumple_horas_trabajo": true,
    "cumple_capacidad": true,
    "violaciones": []
  },
  "justificacion": "Ruta optimizada considerando tráfico moderado en hora pico (13:00-14:00). Se programó descanso de 30 minutos después de STOP-2 para cumplir regulaciones. Todas las ventanas de entrega se cumplen con margen de seguridad.",
  "factores_considerados": [
    "Tráfico en tiempo real (factor promedio: 1.13)",
    "Clima despejado (sin impacto)",
    "Ventanas de entrega validadas",
    "Descanso obligatorio incluido",
    "Prioridad de clientes respetada"
  ]
}
```

## Desarrollo Local

### 1. Instalar dependencias

```bash
cd bedrock_agents/routing_agent
pip install -r requirements.txt
```

### 2. Iniciar servidor de desarrollo

```bash
agentcore dev
```

### 3. Probar localmente

```bash
agentcore invoke --dev '{
  "paradas": [
    {"stop_id": "STOP-1", "lat": 19.4345, "lon": -99.1410},
    {"stop_id": "STOP-2", "lat": 19.4456, "lon": -99.1523}
  ],
  "origen": {"lat": 19.4384, "lon": -99.1569},
  "truck_id": "3",
  "conductor": "Ing. Ernesto Rosado"
}'
```

## Despliegue a AWS

### 1. Configurar el agente

```bash
agentcore configure --entrypoint src.main:app --non-interactive
```

### 2. Desplegar

```bash
agentcore launch
```

### 3. Verificar

```bash
agentcore status
```

## Integración con Agente Autónomo

Para que el Agente Autónomo pueda invocar al Agente de Ruteo, se debe:

1. **Agregar herramienta MCP al Agente Autónomo**:
   - Nombre: `invocar_agente_ruteo`
   - Descripción: "Invoca al agente especializado de ruteo para calcular rutas óptimas"
   - Lambda: Wrapper que invoca el Agente de Ruteo

2. **Actualizar instrucciones del Agente Autónomo**:
   ```
   Cuando necesites calcular rutas optimizadas, usa la herramienta 
   invocar_agente_ruteo en lugar de calcular_ruta_optimizada.
   El agente de ruteo considera tráfico, clima y restricciones.
   ```

## Memoria del Agente

El agente almacena patrones de tráfico y tiempos reales en DynamoDB:

```json
{
  "memory_id": "ROUTING-MEM-001",
  "timestamp": "2026-02-17T14:30:00Z",
  "ruta": {
    "origen": {"lat": 19.4384, "lon": -99.1569},
    "destino": {"lat": 19.4345, "lon": -99.1410}
  },
  "tiempo_estimado_minutos": 25,
  "tiempo_real_minutos": 28,
  "factores": {
    "trafico": 1.1,
    "clima": 1.0,
    "hora_dia": "10:30"
  },
  "precision": 0.89
}
```

Con el tiempo, el agente aprende:
- Patrones de tráfico por hora del día
- Impacto real del clima
- Tiempos de descarga por tipo de cliente
- Rutas más eficientes

## Métricas y Observabilidad

### CloudWatch Metrics

- `RoutingCalculations`: Número de cálculos de ruta
- `RoutingLatency`: Tiempo de cálculo
- `RoutingAccuracy`: Precisión vs tiempos reales
- `OptimizationImprovement`: Mejora vs ruta original

### CloudWatch Logs

Logs estructurados con:
- Solicitud de ruteo
- Factores considerados
- Ruta calculada
- Justificación

## Troubleshooting

### Ruta no cumple ventanas de entrega

**Causa**: Restricciones muy estrictas o tráfico excesivo

**Solución**: 
- Revisar ventanas de entrega
- Considerar agregar más camiones
- Ajustar prioridades

### Tiempos muy optimistas

**Causa**: Factores de tráfico/clima no actualizados

**Solución**:
- Verificar APIs de tráfico/clima
- Ajustar factores manualmente
- Revisar memoria del agente

### Algoritmo muy lento

**Causa**: Demasiadas paradas (>20)

**Solución**:
- Usar heurísticas más rápidas
- Dividir en múltiples rutas
- Aumentar memoria del agente

## Próximos Pasos

1. Implementar Lambda functions para herramientas MCP
2. Configurar APIs de tráfico (Google Maps, HERE, TomTom)
3. Configurar API de clima (OpenWeatherMap)
4. Integrar con Agente Autónomo
5. Entrenar con datos históricos

## Referencias

- [TSP Algorithms](https://en.wikipedia.org/wiki/Travelling_salesman_problem)
- [VRP Algorithms](https://en.wikipedia.org/wiki/Vehicle_routing_problem)
- [SmartSupply Design Document](../../.kiro/specs/smart-supply/design.md)
