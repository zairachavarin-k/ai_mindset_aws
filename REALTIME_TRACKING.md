# 🚚 Sistema de Tracking en Tiempo Real

## 🎯 Características

- ✅ Actualización automática de posiciones cada 5 segundos
- ✅ Simulación realista de movimiento de camiones
- ✅ Actualización automática del estado de entregas
- ✅ Integración con el chat para consultas en tiempo real
- ✅ API REST para control del simulador

## 🚀 Cómo Usar

### 1. Iniciar el Servidor

```bash
cd ai_mindset_aws
python3 main.py
```

### 2. Iniciar el Simulador

Hay 3 formas de iniciar el simulador:

#### Opción A: Desde el Frontend
1. Abre http://localhost:8000
2. Haz clic en el botón "▶ Start Sim"
3. Los camiones comenzarán a moverse automáticamente

#### Opción B: Desde la API
```bash
curl -X POST http://localhost:8000/simulator/start
```

#### Opción C: Desde JavaScript Console
```javascript
realtimeTracker.start()
```

### 3. Ver Posiciones en Tiempo Real

#### En el Mapa
- Las posiciones se actualizan automáticamente cada 5 segundos
- Los marcadores se mueven suavemente entre paradas

#### En el Chat
```
Usuario: ¿Dónde está el camión 5?
Agente: [Responde con la posición actual en tiempo real]

Usuario: ¿Y ahora dónde está?
Agente: [Responde con la nueva posición actualizada]
```

#### Vía API
```bash
curl http://localhost:8000/trucks/positions
```

## 📊 Endpoints del Simulador

### Iniciar Simulador
```bash
POST /simulator/start
```

Respuesta:
```json
{
  "status": "success",
  "message": "Simulator started successfully",
  "update_interval_seconds": 5.0,
  "speed_kmh": 40.0
}
```

### Detener Simulador
```bash
POST /simulator/stop
```

### Reiniciar con Nuevos Datos
```bash
POST /simulator/reset
```

### Ver Estado del Simulador
```bash
GET /simulator/status
```

Respuesta:
```json
{
  "status": "success",
  "simulator_running": true,
  "update_interval_seconds": 5.0,
  "speed_kmh": 40.0,
  "last_update": "2026-02-16T20:30:00",
  "truck_count": 5,
  "positions": {
    "0": {
      "truck_name": "Truck 1",
      "position": [-99.1908, 19.4336],
      "current_stop": 2,
      "status": "in_progress",
      "progress_to_next": 45.2
    }
  }
}
```

### Obtener Posiciones Actuales
```bash
GET /trucks/positions
```

## ⚙️ Configuración del Simulador

El simulador se puede configurar en `agents/truck_simulator.py`:

```python
simulator = TruckSimulator(
    speed_kmh=40.0,              # Velocidad de los camiones
    update_interval_seconds=5.0   # Frecuencia de actualización
)
```

### Parámetros:

- `speed_kmh`: Velocidad promedio de los camiones (default: 40 km/h)
- `update_interval_seconds`: Cada cuántos segundos actualizar (default: 5s)

## 🔧 Integración con el Frontend

### JavaScript - Registrar Callback

```javascript
// Registrar callback para recibir actualizaciones
realtimeTracker.onUpdate((data) => {
    console.log('Posiciones actualizadas:', data.positions);
    
    // Detectar cambios
    data.changes.forEach(change => {
        if (change.type === 'stop_completed') {
            console.log(`${change.truck_name} completó parada ${change.new_stop}`);
        }
    });
});

// Iniciar tracking
await realtimeTracker.start();
```

### Tipos de Cambios Detectados

```javascript
{
    type: 'position_changed',    // Camión se movió
    type: 'stop_completed',      // Completó una entrega
    type: 'status_changed',      // Cambió de estado
    type: 'new'                  // Nuevo camión detectado
}
```

## 📈 Cómo Funciona

### 1. Simulación de Movimiento

```
Parada A ----[progreso: 0% → 100%]----> Parada B
   ↓                                        ↓
[lon1, lat1]                          [lon2, lat2]
```

El simulador:
1. Calcula la distancia entre paradas
2. Mueve el camión basándose en velocidad y tiempo
3. Interpola la posición entre paradas
4. Marca entregas como completadas al llegar

### 2. Actualización del Estado

```
Cada 5 segundos:
  1. Calcular distancia recorrida (velocidad × tiempo)
  2. Actualizar progreso hacia siguiente parada
  3. Si progreso >= 100%:
     - Marcar parada como completada
     - Avanzar a siguiente parada
     - Guardar en JSON
  4. Interpolar posición actual
  5. Notificar a clientes
```

### 3. Persistencia

Los cambios se guardan automáticamente en:
```
data/route_plan_YYYYMMDD_HHMMSS.json
```

El archivo se actualiza con:
- Nuevas posiciones
- Estados de entregas
- Timestamps de entregas completadas

## 🎮 Controles

### Desde el Frontend

```javascript
// Iniciar
await realtimeTracker.start()

// Detener
await realtimeTracker.stop()

// Reiniciar con nuevos datos
await realtimeTracker.reset()

// Ver estado
const status = await realtimeTracker.getStatus()
```

### Desde Python

```python
from agents.truck_simulator import simulator

# Iniciar
simulator.start()

# Obtener posiciones
positions = simulator.get_current_positions()

# Detener
simulator.stop()

# Reiniciar
simulator.reset()
```

## 🐛 Troubleshooting

### El simulador no inicia
- Verifica que exista un archivo `route_plan_*.json` en `data/`
- Revisa los logs del servidor

### Las posiciones no se actualizan
- Verifica que el simulador esté corriendo: `GET /simulator/status`
- Revisa la consola del navegador para errores

### Los camiones se mueven muy rápido/lento
- Ajusta `speed_kmh` en `truck_simulator.py`
- Ajusta `update_interval_seconds` para más/menos frecuencia

## 💡 Casos de Uso

### 1. Monitoreo en Vivo
```javascript
realtimeTracker.onUpdate((data) => {
    // Actualizar mapa
    updateMapMarkers(data.positions);
    
    // Actualizar dashboard
    updateKPIs(data.positions);
});
```

### 2. Alertas de Entregas
```javascript
realtimeTracker.onUpdate((data) => {
    data.changes.forEach(change => {
        if (change.type === 'stop_completed') {
            showNotification(`${change.truck_name} completó entrega`);
        }
    });
});
```

### 3. Chat con Datos en Tiempo Real
```
Usuario: ¿Dónde está el camión 3?
Agente: [Consulta posición actual del simulador]
        El camión 3 está en [-99.1234, 19.5678], 
        va hacia la parada 4 (progreso: 67%)
```

## 🔄 Flujo Completo

```
1. Usuario optimiza rutas
   ↓
2. Se genera route_plan_*.json
   ↓
3. Usuario inicia simulador
   ↓
4. Simulador carga rutas y comienza movimiento
   ↓
5. Cada 5 segundos:
   - Actualiza posiciones
   - Marca entregas completadas
   - Guarda cambios en JSON
   ↓
6. Frontend consulta posiciones
   ↓
7. Mapa y chat muestran datos actualizados
   ↓
8. Usuario puede consultar en tiempo real
```

## 📝 Próximas Mejoras

- [ ] WebSocket para push en lugar de polling
- [ ] Simulación de tráfico y retrasos
- [ ] Alertas de incidentes
- [ ] Reasignación automática de rutas
- [ ] Persistencia en base de datos
- [ ] Replay de rutas históricas

## 🎉 ¡Listo!

Ahora tienes un sistema completo de tracking en tiempo real. Los camiones se mueven automáticamente, las entregas se marcan como completadas, y puedes consultar todo desde el chat o el mapa.
