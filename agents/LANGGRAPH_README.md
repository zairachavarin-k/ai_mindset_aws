# Sistema Multiagente con LangGraph

## 🎯 Nuevo Sistema desde Cero

He creado un sistema multiagente completamente nuevo usando **LangGraph**, el framework moderno de LangChain para crear agentes con grafos de estados.

## 🏗️ Arquitectura con LangGraph

```
┌─────────────────────────────────────────┐
│           Usuario                       │
│      "¿Dónde están los camiones?"       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│        SUPERVISOR NODE                  │
│        (Claude decide)                  │
│                                         │
│  Analiza mensaje →                      │
│  Decide agente apropiado                │
└────────────┬────────────────────────────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│  Route   │  │Inventory │
│ Planner  │  │  Agent   │
│  Node    │  │   Node   │
└────┬─────┘  └────┬─────┘
     │             │
     │ Usa tools   │ Usa tools
     ▼             ▼
┌──────────┐  ┌──────────┐
│  Route   │  │Inventory │
│  Tools   │  │  Tools   │
└──────────┘  └──────────┘
```

## 📦 Componentes

### 1. Estado del Grafo (AgentState)
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str
```

### 2. Nodos del Grafo

**Supervisor Node**
- Analiza el mensaje del usuario
- Decide qué agente debe manejar la solicitud
- Retorna: `route_planner`, `inventory_agent`, o `FINISH`

**Route Planner Node**
- Especializado en rutas y posiciones
- Tiene acceso a herramientas de rutas
- Usa Claude con tool calling

**Inventory Agent Node**
- Especializado en inventario y reportes
- Tiene acceso a herramientas de inventario
- Usa Claude con tool calling

### 3. Herramientas (Tools)

Definidas con el decorador `@tool` de LangChain:

```python
@tool
def get_trucks_positions() -> dict:
    """Obtiene las posiciones actuales de todos los camiones."""
    return get_truck_positions()

@tool
def calculate_distance_to_depot(truck_id: int) -> dict:
    """Calcula la distancia de un camión al depósito."""
    return get_distance_to_depot(truck_id)

@tool
def get_inventory() -> dict:
    """Obtiene el inventario del almacén."""
    return get_inventory_data()
```

## 🔄 Flujo de Ejecución

1. **Usuario envía mensaje** → Estado inicial creado
2. **Supervisor analiza** → Decide qué agente usar
3. **Agente procesa** → Usa herramientas si es necesario
4. **Respuesta generada** → Claude responde naturalmente
5. **Estado final** → Respuesta retornada al usuario

## 💡 Ventajas de LangGraph

### vs Sistema Anterior

❌ **Antes (Manual)**:
- Lógica de decisión manual con if/else
- Difícil de mantener y extender
- No hay visualización del flujo
- Manejo de estado complejo

✅ **Ahora (LangGraph)**:
- Grafo declarativo y visual
- Fácil de extender (agregar nodos)
- Estado manejado automáticamente
- Tool calling integrado
- Flujos condicionales claros

### Características Clave

1. **Grafos de Estados**: Flujo visual y declarativo
2. **Tool Calling Nativo**: Integración automática con herramientas
3. **Condicionales**: Edges condicionales basados en estado
4. **Extensible**: Fácil agregar nuevos agentes/nodos
5. **Debugging**: Visualización del flujo de ejecución

## 🚀 Uso

### Desde el Frontend

```bash
# Iniciar servidor
python main.py

# Abrir http://localhost:8000
# El chat ahora usa LangGraph automáticamente
```

### Desde Python

```python
from agents.langgraph_system import process_message

response = process_message("¿Dónde están los camiones?")
print(response["response"])
```

### Desde API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "¿Dónde están los camiones?"}'
```

## 📊 Ejemplo de Flujo

```
Usuario: "¿Dónde están los camiones?"
   ↓
Supervisor: Analiza → "route_planner"
   ↓
Route Planner: 
   - Recibe mensaje
   - Claude decide usar get_trucks_positions()
   - Ejecuta herramienta
   - Recibe datos
   - Genera respuesta natural
   ↓
Respuesta: "Encontré 5 camiones activos. El Truck 1 está en..."
```

## 🔧 Configuración

### Dependencias

```bash
pip install langgraph langchain-aws langchain-core
```

### Variables de Entorno

```bash
# AWS credentials (ya configuradas)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

## 🎨 Personalización

### Agregar Nuevo Agente

```python
# 1. Definir herramientas
@tool
def my_new_tool() -> dict:
    """Descripción de la herramienta"""
    return {"result": "data"}

# 2. Crear nodo
def my_agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    llm_with_tools = llm.bind_tools([my_new_tool])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response], "next_agent": "FINISH"}

# 3. Agregar al grafo
workflow.add_node("my_agent", my_agent_node)
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x.get("next_agent"),
    {
        "my_agent": "my_agent",
        ...
    }
)
```

### Modificar Supervisor

```python
def supervisor_node(state: AgentState) -> AgentState:
    # Personalizar lógica de decisión
    prompt = """Tu prompt personalizado"""
    response = llm.invoke([HumanMessage(content=prompt)])
    # Determinar next_agent basado en respuesta
    return {"messages": [response], "next_agent": next_agent}
```

## 📈 Ventajas del Nuevo Sistema

1. **Más Robusto**: Manejo de estado automático
2. **Más Escalable**: Fácil agregar agentes
3. **Más Mantenible**: Código más limpio y organizado
4. **Mejor Debugging**: Visualización del flujo
5. **Estándar de Industria**: LangGraph es el framework moderno

## 🔍 Debugging

### Ver el Grafo

```python
from agents.langgraph_system import agent_graph

# Visualizar estructura
print(agent_graph.get_graph().draw_ascii())
```

### Logs Detallados

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Verás cada paso del grafo
```

## 📚 Recursos

- [LangGraph Docs](https://python.langchain.com/docs/langgraph)
- [LangChain Tools](https://python.langchain.com/docs/modules/agents/tools/)
- [ChatBedrock](https://python.langchain.com/docs/integrations/chat/bedrock)

## ✅ Estado Actual

- ✅ Sistema con LangGraph implementado
- ✅ Supervisor que decide agentes
- ✅ Route Planner con herramientas
- ✅ Inventory Agent con herramientas
- ✅ Integrado con main.py
- ✅ Funciona desde el frontend

¡El sistema ahora usa LangGraph, el framework moderno para agentes con LLMs! 🎉
