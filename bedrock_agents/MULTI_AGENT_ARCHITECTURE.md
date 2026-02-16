# SmartSupply - Arquitectura Multi-Agente

## Overview

SmartSupply utiliza una arquitectura multi-agente donde cada agente tiene una responsabilidad específica y se especializa en un dominio particular.

## Agentes del Sistema

### 1. Agente Autónomo (Orquestador Principal)
**Directorio**: `bedrock_agents/autonomous_agent/`
**Responsabilidad**: Análisis de incidentes y generación de planes de reasignación

**Funciones**:
- Recibe eventos de incidentes desde EventBridge
- Analiza el impacto del incidente
- Consulta datos de rutas, flota e inventario
- Decide estrategia de reasignación
- **Invoca al Agente de Ruteo** para calcular rutas óptimas
- Ejecuta acciones (actualizar rutas, notificar clientes)
- Registra decisiones en memoria

**Herramientas MCP** (9 herramientas):
1. `invocar_agente_ruteo` ← **NUEVA** - Invoca agente especializado
2. `consultar_ruta_afectada`
3. `consultar_flota_disponible`
4. `consultar_inventario_almacen`
5. `calcular_distancia`
6. `actualizar_ruta_s3`
7. `registrar_incidencia`
8. `enviar_notificacion_cliente`
9. ~~`calcular_ruta_optimizada`~~ ← **DEPRECADA** - Reemplazada por agente de ruteo

**Modelo**: Claude 3.5 Sonnet
**Timeout**: 180 segundos (3 minutos)

---

### 2. Agente de Ruteo Especializado (NUEVO)
**Directorio**: `bedrock_agents/routing_agent/`
**Responsabilidad**: Cálculo de rutas óptimas con contexto completo

**Funciones**:
- Recibe solicitudes de ruteo del Agente Autónomo
- Consulta tráfico en tiempo real
- Consulta condiciones climáticas
- Valida ventanas de entrega
- Calcula matriz de distancias
- Aplica algoritmos TSP/VRP
- Considera fatiga del conductor
- Calcula tiempos precisos
- Valida restricciones
- Retorna ruta optimizada con justificación

**Herramientas MCP** (8 herramientas):
1. `consultar_trafico` - Estado del tráfico en tiempo real
2. `consultar_clima` - Condiciones climáticas
3. `validar_ventanas_entrega` - Valida horarios
4. `calcular_distancia_matriz` - Matriz de distancias
5. `optimizar_ruta_tsp` - Algoritmo TSP
6. `calcular_tiempo_real` - Tiempo con factores
7. `considerar_fatiga_conductor` - Descansos necesarios
8. `validar_restricciones_ruta` - Valida cumplimiento

**Modelo**: Claude 3.5 Sonnet
**Timeout**: 60 segundos (1 minuto)
**Memoria**: 2048 MB (más memoria para algoritmos)

---

### 3. Agente Conversacional (Pendiente - Task 11)
**Directorio**: `bedrock_agents/conversational_agent/` (a crear)
**Responsabilidad**: Interfaz para operadores humanos

**Funciones**:
- Responde consultas de operadores
- Presenta planes de reasignación
- Solicita aprobaciones
- Ejecuta comandos manuales
- Genera reportes

**Herramientas MCP** (7 herramientas - a implementar):
1. `consultar_estado_ruta`
2. `consultar_incidentes`
3. `consultar_inventario`
4. `consultar_plan_reasignacion`
5. `aprobar_reasignacion`
6. `ejecutar_comando`
7. `generar_reporte`

**Modelo**: Claude 3.5 Sonnet
**Canales**: Web chat, voz (Amazon Connect), API REST

---

## Flujo de Comunicación entre Agentes

### Flujo Principal: Procesamiento de Incidente

```
┌─────────────────────────────────────────────────────────────┐
│                    1. Incidente Detectado                    │
│                    (Voz / Web / IoT)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    2. EventBridge                            │
│                    (Bus Central)                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              3. Agente Autónomo (Orquestador)                │
│                                                              │
│  • Analiza incidente                                         │
│  • Consulta ruta afectada                                    │
│  • Consulta flota disponible                                 │
│  • Consulta inventario                                       │
│  • Calcula distancias                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ 4. Invoca Agente de Ruteo
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agente de Ruteo Especializado                   │
│                                                              │
│  • Consulta tráfico actual                                   │
│  • Consulta clima                                            │
│  • Valida ventanas de entrega                                │
│  • Calcula matriz de distancias                              │
│  • Optimiza ruta (TSP/VRP)                                   │
│  • Calcula tiempos precisos                                  │
│  • Considera fatiga conductor                                │
│  • Valida restricciones                                      │
│                                                              │
│  ✓ Retorna: Ruta optimizada + tiempos + justificación       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ 5. Ruta optimizada
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agente Autónomo (Continúa)                      │
│                                                              │
│  • Usa ruta optimizada en el plan                            │
│  • Actualiza rutas en S3                                     │
│  • Registra incidencia                                       │
│  • Envía notificaciones a clientes                           │
│  • Almacena decisión en memoria                              │
│                                                              │
│  ✓ Plan de reasignación completo                             │
└─────────────────────────────────────────────────────────────┘
```

### Flujo Secundario: Aprobación Humana (Futuro)

```
┌─────────────────────────────────────────────────────────────┐
│              Agente Autónomo                                 │
│              (Plan generado)                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Notifica plan pendiente
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agente Conversacional                           │
│                                                              │
│  Operador: "Muéstrame el plan para INC-901"                 │
│  Agent: "El plan propone reasignar camión 3..."             │
│  Operador: "¿Cuánto tiempo tomará?"                         │
│  Agent: "Tiempo estimado: 2 horas 15 minutos"               │
│  Operador: "Apruebo"                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Aprobación
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Agente Autónomo                                 │
│              (Ejecuta plan aprobado)                         │
└─────────────────────────────────────────────────────────────┘
```

## Ventajas de la Arquitectura Multi-Agente

### 1. Separación de Responsabilidades
- Cada agente se enfoca en su dominio
- Código más mantenible
- Testing más fácil

### 2. Especialización
- Agente de Ruteo optimizado para cálculos complejos
- Agente Autónomo optimizado para toma de decisiones
- Agente Conversacional optimizado para interacción humana

### 3. Escalabilidad
- Agentes pueden escalar independientemente
- Agente de Ruteo puede procesar múltiples solicitudes en paralelo
- Fácil agregar nuevos agentes especializados

### 4. Reutilización
- Agente de Ruteo puede ser invocado por:
  - Agente Autónomo (reasignaciones)
  - Agente Conversacional (consultas de operadores)
  - Otros sistemas (planificación diaria)

### 5. Mejora Continua
- Cada agente aprende en su dominio
- Agente de Ruteo aprende patrones de tráfico
- Agente Autónomo aprende estrategias de reasignación
- Memoria independiente por agente

### 6. Observabilidad
- Métricas específicas por agente
- Fácil identificar cuellos de botella
- Debugging más simple

## Comparación: Antes vs Después

### Antes (Agente Único)

```
Agente Autónomo
├── Analiza incidente
├── Consulta datos
├── Calcula ruta (simple)  ← Limitado
├── Genera plan
└── Ejecuta acciones

Limitaciones:
- Cálculo de rutas básico
- No considera tráfico/clima
- Tiempos imprecisos
- Difícil de optimizar
```

### Después (Multi-Agente)

```
Agente Autónomo (Orquestador)
├── Analiza incidente
├── Consulta datos
├── Invoca Agente de Ruteo  ← Especializado
│   │
│   └─→ Agente de Ruteo
│       ├── Consulta tráfico
│       ├── Consulta clima
│       ├── Optimiza ruta (TSP/VRP)
│       ├── Calcula tiempos precisos
│       └── Retorna ruta optimizada
│
├── Genera plan (con ruta óptima)
└── Ejecuta acciones

Ventajas:
✓ Cálculo de rutas avanzado
✓ Considera tráfico/clima
✓ Tiempos precisos
✓ Fácil de optimizar
✓ Reutilizable
```

## Implementación

### Estado Actual

- ✅ Agente Autónomo implementado
- ✅ Agente de Ruteo implementado (estructura)
- ✅ Integración entre agentes diseñada
- ⏳ Lambda functions de ruteo (pendiente)
- ⏳ APIs de tráfico/clima (pendiente)
- ❌ Agente Conversacional (Task 11)

### Próximos Pasos

1. **Implementar Lambda functions para Agente de Ruteo**:
   - `consultar_trafico`
   - `consultar_clima`
   - `validar_ventanas_entrega`
   - `calcular_distancia_matriz`
   - `optimizar_ruta_tsp`
   - `calcular_tiempo_real`
   - `considerar_fatiga_conductor`
   - `validar_restricciones_ruta`

2. **Implementar Lambda wrapper**:
   - `invocar_agente_ruteo` (para Agente Autónomo)

3. **Configurar APIs externas**:
   - Google Maps Traffic API
   - OpenWeatherMap API

4. **Desplegar Agente de Ruteo**:
   ```bash
   cd bedrock_agents/routing_agent
   agentcore launch
   ```

5. **Actualizar Agente Autónomo**:
   - Agregar herramienta `invocar_agente_ruteo`
   - Actualizar instrucciones
   - Redesplegar

6. **Testing de integración**:
   - Probar flujo completo
   - Validar tiempos precisos
   - Comparar con ruta simple

## Monitoreo Multi-Agente

### Métricas por Agente

**Agente Autónomo**:
- Invocaciones totales
- Latencia end-to-end
- Tasa de éxito de reasignaciones
- Valor de pérdidas evitadas

**Agente de Ruteo**:
- Cálculos de ruta
- Latencia de cálculo
- Precisión de tiempos (vs real)
- Mejora vs ruta original

**Agente Conversacional** (futuro):
- Consultas de operadores
- Aprobaciones/rechazos
- Tiempo de respuesta
- Satisfacción del operador

### Dashboard Unificado

CloudWatch Dashboard mostrando:
- Estado de todos los agentes
- Flujo de invocaciones entre agentes
- Latencia por agente
- Errores por agente
- Métricas de negocio agregadas

## Referencias

- [Agente Autónomo](./autonomous_agent/README.md)
- [Agente de Ruteo](./routing_agent/README.md)
- [Design Document](../.kiro/specs/smart-supply/design.md)
- [Multi-Agent Systems](https://en.wikipedia.org/wiki/Multi-agent_system)
