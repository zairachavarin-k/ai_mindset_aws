# Sistema Multiagente con AWS Bedrock Agent Core

## 🎯 Características Principales

### ✅ Memoria Conversacional
- El sistema recuerda el contexto de la conversación
- Cada usuario puede tener su propia sesión independiente
- Mantiene los últimos 20 mensajes por sesión

### ✅ Datos Reales
- Los agentes consultan información real de tus archivos JSON y CSV
- No inventan datos - solo usan información verificada
- Acceso a posiciones de camiones, inventario, y rutas

### ✅ Multi-Agente
- **Supervisor**: Decide qué agente debe responder
- **Route Planner**: Maneja consultas sobre camiones y rutas
- **Inventory Agent**: Maneja consultas sobre inventario y reportes

## 🚀 Cómo Usar

### Iniciar el Servidor

```bash
cd ai_mindset_aws
python3 main.py
```

### Endpoints Disponibles

#### 1. Chat con Memoria
```bash
POST /chat
{
  "message": "¿Dónde está el camión 5?",
  "session_id": "user123"  # Opcional, default: "default"
}
```

#### 2. Limpiar Memoria de Sesión
```bash
POST /chat/clear-session?session_id=user123
```

#### 3. Ver Historial de Conversación
```bash
GET /chat/history/user123
```

## 💬 Ejemplos de Conversación

### Con Memoria:

```
Usuario: Hola
Agente: ¡Hola! Soy tu asistente de logística...

Usuario: ¿Dónde está el camión 5?
Agente: El camión 5 (ID: 4) está en coordenadas [-99.1908, 19.4336]...

Usuario: ¿Y qué tan lejos está del depósito?
Agente: [Recuerda que hablamos del camión 5] El camión 5 está actualmente...
```

### Consultas sobre Camiones:

```
- "¿Dónde está el camión 3?"
- "¿Cuál es la posición del truck 2?"
- "¿Qué camiones están en ruta?"
- "¿Cuántos camiones tengo?"
```

### Consultas sobre Inventario:

```
- "¿Qué productos tengo en stock?"
- "¿Cuánto inventario hay?"
- "Muéstrame los productos disponibles"
```

## 🔧 Arquitectura

```
Usuario
  ↓
FastAPI (/chat)
  ↓
Supervisor Agent (decide qué agente usar)
  ↓
  ├─→ Route Planner Agent (consulta get_truck_positions())
  │   └─→ Responde con datos reales
  │
  └─→ Inventory Agent (consulta get_inventory_data())
      └─→ Responde con datos reales

Memoria Conversacional (mantiene contexto)
```

## 📊 Ventajas vs LangGraph

| Característica | LangGraph | AgentCore |
|---------------|-----------|-----------|
| Memoria | ❌ No | ✅ Sí |
| Sesiones múltiples | ❌ No | ✅ Sí |
| Datos reales | ⚠️ Parcial | ✅ Completo |
| Simplicidad | ⚠️ Complejo | ✅ Simple |
| Mantenimiento | ⚠️ Difícil | ✅ Fácil |

## 🔑 Configuración de Sesiones

### Frontend (JavaScript)

```javascript
// Generar session_id único por usuario
const sessionId = localStorage.getItem('session_id') || 
                  'user_' + Date.now();
localStorage.setItem('session_id', sessionId);

// Enviar con cada mensaje
fetch('/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: userMessage,
    session_id: sessionId
  })
});
```

## 🛠️ Herramientas Disponibles

Los agentes tienen acceso a:

1. `get_truck_positions()` - Posiciones actuales de todos los camiones
2. `get_distance_to_coordinates()` - Calcular distancia a coordenadas
3. `get_distance_to_depot()` - Distancia al depósito
4. `get_current_route_plan()` - Plan de rutas actual
5. `get_inventory_data()` - Datos del inventario
6. `generate_incident_report()` - Generar reporte de incidente

## 🐛 Troubleshooting

### El agente inventa datos
- ✅ Solucionado: Ahora usa datos reales de archivos JSON/CSV

### No recuerda conversaciones anteriores
- ✅ Solucionado: Sistema de memoria implementado

### Confunde números de camiones
- ✅ Solucionado: Instrucciones claras sobre IDs (camión 5 = ID 4)

## 📝 Próximos Pasos

1. ✅ Memoria conversacional - COMPLETADO
2. ⏳ Integrar con AWS Bedrock Agent (cuando tengas método de pago)
3. ⏳ Agregar más herramientas (reportes, análisis)
4. ⏳ Persistencia de memoria en base de datos

## 🔄 Migración desde LangGraph

El sistema anterior (LangGraph) sigue disponible en `langgraph_system.py`.
Para volver a usarlo, cambia en `main.py`:

```python
# De:
from agents.agentcore_system import process_message

# A:
from agents.langgraph_system import process_message
```

## 💡 Notas

- El sistema usa Amazon Titan (gratuito) mientras no tengas método de pago
- Cuando agregues tarjeta, puedes cambiar a Claude para mejores respuestas
- La memoria es en RAM - se pierde al reiniciar el servidor
- Para producción, considera usar DynamoDB para persistencia
