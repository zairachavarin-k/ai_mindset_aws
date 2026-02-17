"""
Sistema Multiagente con LangGraph
"""
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
import operator
import sys
import os
import boto3

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import tools
from agents.tools import (
    get_truck_positions,
    get_distance_to_coordinates,
    get_distance_to_depot,
    get_current_route_plan,
    get_inventory_data,
    generate_incident_report
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_agent: str


# Usar Bedrock Runtime directamente con Converse API
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Modelos disponibles (en orden de preferencia)
# Usando modelos gratuitos/accesibles sin método de pago
MODELS_TO_TRY = [
    "amazon.titan-text-express-v1",             # Titan Express - disponible
    "amazon.titan-text-lite-v1",                # Titan Lite - básico
    "meta.llama3-8b-instruct-v1:0",            # Llama 3 8B - open source
    "meta.llama3-70b-instruct-v1:0",           # Llama 3 70B - más potente
    "mistral.mistral-7b-instruct-v0:2",        # Mistral 7B - alternativa
]

MODEL_ID = MODELS_TO_TRY[0]  # Empezar con Titan Express


def call_llm(messages: list, system_prompt: str = None, tools: list = None) -> dict:
    """
    Llama al LLM usando la API Converse de Bedrock con fallback a diferentes modelos
    Soporta tanto Amazon Titan como Claude
    """
    # Preparar mensajes
    converse_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            # Si ya es un dict, asegurarse que content sea una lista
            if isinstance(msg.get('content'), str):
                converse_messages.append({
                    "role": msg['role'],
                    "content": [{"text": msg['content']}]
                })
            else:
                converse_messages.append(msg)
        elif isinstance(msg, HumanMessage):
            converse_messages.append({
                "role": "user",
                "content": [{"text": msg.content}]
            })
        elif isinstance(msg, AIMessage):
            converse_messages.append({
                "role": "assistant",
                "content": [{"text": msg.content}]
            })
    
    # Preparar parámetros base
    base_params = {
        "messages": converse_messages
    }
    
    if system_prompt:
        base_params["system"] = [{"text": system_prompt}]
    
    if tools:
        base_params["toolConfig"] = {"tools": tools}
    
    # Intentar con diferentes modelos
    last_error = None
    for model_id in MODELS_TO_TRY:
        try:
            params = {**base_params, "modelId": model_id}
            response = bedrock_runtime.converse(**params)
            print(f"✓ Usando modelo: {model_id}")
            return response
        except Exception as e:
            last_error = e
            error_msg = str(e)
            if "ResourceNotFoundException" in error_msg or "use case details" in error_msg or "AccessDeniedException" in error_msg or "INVALID_PAYMENT" in error_msg:
                print(f"✗ Modelo {model_id} no disponible, intentando siguiente...")
                continue
            else:
                # Si es otro tipo de error, lanzarlo
                raise e
    
    # Si ningún modelo funcionó, lanzar el último error
    raise last_error


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
    inventory = get_inventory_data()
    return {"success": True, "data": inventory[:10]} if inventory else {"success": False}


def supervisor_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1]
    
    prompt = f"""Analiza este mensaje del usuario: "{last_message.content}"

Decide qué agente debe manejarlo:
- route_planner: Para preguntas sobre camiones, posiciones, ubicaciones, distancias, rutas, dónde está un camión
- inventory_agent: Para preguntas sobre inventario, productos, stock, reportes, entregas
- FINISH: Para saludos simples como "hola", "buenos días", o preguntas sobre qué puedes hacer

Responde SOLO con una palabra: route_planner, inventory_agent, o FINISH"""
    
    response = call_llm([{"role": "user", "content": prompt}])
    
    # Extraer contenido
    content = ""
    for item in response['output']['message']['content']:
        if 'text' in item:
            content += item['text']
    
    content = content.lower().strip()
    
    # Detección mejorada
    next_agent = "FINISH"
    user_text = last_message.content.lower()
    
    # Palabras clave para route planner
    route_keywords = ["camión", "camion", "truck", "posición", "posicion", "ubicación", "ubicacion", 
                      "dónde", "donde", "está", "esta", "distancia", "ruta", "flota"]
    
    # Palabras clave para inventory
    inventory_keywords = ["inventario", "inventory", "producto", "stock", "reporte", "entrega", 
                         "almacén", "almacen"]
    
    if any(keyword in user_text for keyword in route_keywords):
        next_agent = "route_planner"
    elif any(keyword in user_text for keyword in inventory_keywords):
        next_agent = "inventory_agent"
    elif "route" in content or "planner" in content:
        next_agent = "route_planner"
    elif "inventory" in content:
        next_agent = "inventory_agent"
    
    # Si es FINISH, el supervisor responde directamente
    if next_agent == "FINISH":
        user_response = call_llm([
            {"role": "user", "content": f"""Eres un asistente de logística amigable. 
            
El usuario dice: "{last_message.content}"

Responde de forma natural y amigable en español. Si te saludan, saluda de vuelta. Si preguntan qué puedes hacer, explica brevemente que ayudas con:
- Seguimiento de flota y posiciones de camiones
- Consultas de inventario
- Reportes de entregas"""}
        ])
        
        # Extraer respuesta
        response_text = ""
        for item in user_response['output']['message']['content']:
            if 'text' in item:
                response_text += item['text']
        
        return {"messages": [AIMessage(content=response_text)], "next_agent": "FINISH"}
    
    return {"messages": [], "next_agent": next_agent}


def route_planner_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    user_message = messages[0]
    
    # Obtener datos reales de los camiones
    truck_positions = get_truck_positions()
    
    # Construir información contextual
    trucks_info = []
    for truck_id, info in truck_positions.items():
        pos = info['position']
        trucks_info.append(
            f"- {info['truck_name']} (ID: {truck_id}): "
            f"Posición [{pos[0]:.4f}, {pos[1]:.4f}], "
            f"Parada actual: {info['current_stop']}, "
            f"Estado: {info['status']}"
        )
    
    trucks_context = "\n".join(trucks_info) if trucks_info else "No hay información de camiones disponible."
    
    system_prompt = f"""Eres un agente especializado en planificación de rutas y seguimiento de flota.

INFORMACIÓN ACTUAL DE LA FLOTA:
{trucks_context}

Responde de forma natural y conversacional en español usando ÚNICAMENTE la información real proporcionada arriba.
NO inventes coordenadas ni ubicaciones. Si no tienes la información, dilo claramente."""
    
    response = call_llm(
        [{"role": "user", "content": user_message.content}],
        system_prompt=system_prompt
    )
    
    # Extraer respuesta
    response_text = ""
    for item in response['output']['message']['content']:
        if 'text' in item:
            response_text += item['text']
    
    return {"messages": [AIMessage(content=response_text)], "next_agent": "FINISH"}


def inventory_agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    user_message = messages[0]
    
    # Obtener datos reales del inventario
    inventory = get_inventory_data()
    
    # Construir información contextual (primeros 10 items)
    inventory_info = []
    for idx, item in enumerate(inventory[:10]):
        inventory_info.append(
            f"- {item.get('nombre_producto', 'N/A')}: "
            f"Stock: {item.get('cantidad_disponible', 'N/A')}, "
            f"Precio: ${item.get('valor_unitario_usd', 'N/A')}"
        )
    
    inventory_context = "\n".join(inventory_info) if inventory_info else "No hay información de inventario disponible."
    
    # Obtener información de rutas actuales
    route_plan = get_current_route_plan()
    routes_info = "No hay rutas planificadas."
    if "data" in route_plan:
        total_trucks = len(route_plan["data"].get("routes", []))
        routes_info = f"Hay {total_trucks} camiones con rutas asignadas."
    
    system_prompt = f"""Eres un agente especializado en gestión de inventario y reportes.

INVENTARIO ACTUAL (muestra):
{inventory_context}

RUTAS ACTUALES:
{routes_info}

Responde de forma natural y conversacional en español usando ÚNICAMENTE la información real proporcionada arriba.
NO inventes datos. Si no tienes la información completa, dilo claramente."""
    
    response = call_llm(
        [{"role": "user", "content": user_message.content}],
        system_prompt=system_prompt
    )
    
    # Extraer respuesta
    response_text = ""
    for item in response['output']['message']['content']:
        if 'text' in item:
            response_text += item['text']
    
    return {"messages": [AIMessage(content=response_text)], "next_agent": "FINISH"}


def create_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("route_planner", route_planner_node)
    workflow.add_node("inventory_agent", inventory_agent_node)
    
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x.get("next_agent", "FINISH"),
        {
            "route_planner": "route_planner",
            "inventory_agent": "inventory_agent",
            "FINISH": END
        }
    )
    workflow.add_edge("route_planner", END)
    workflow.add_edge("inventory_agent", END)
    
    return workflow.compile()


agent_graph = create_agent_graph()


def process_message(message: str) -> dict:
    try:
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "next_agent": ""
        }
        
        result = agent_graph.invoke(initial_state)
        
        # Obtener todos los mensajes
        messages = result["messages"]
        
        # El último mensaje debería ser la respuesta del agente
        if messages:
            last_message = messages[-1]
            response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            # Determinar qué agente respondió
            next_agent = result.get("next_agent", "")
            agent_name = "Logistics Agent"
            
            if "route" in str(next_agent).lower():
                agent_name = "Route Planner Agent"
            elif "inventory" in str(next_agent).lower():
                agent_name = "Inventory & Report Agent"
            
            return {
                "agent": agent_name,
                "response": response_text,
                "data": None
            }
        
        return {
            "agent": "System",
            "response": "No pude generar una respuesta.",
            "data": None
        }
        
    except Exception as e:
        import traceback
        print("Error en process_message:")
        traceback.print_exc()
        return {
            "agent": "System",
            "response": f"Error al procesar mensaje: {str(e)}",
            "data": None
        }
