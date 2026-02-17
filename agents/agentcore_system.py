"""
Sistema Multiagente con OpenAI
Incluye memoria conversacional y manejo avanzado de herramientas
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime
import sys

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import OpenAI
from openai import OpenAI

# Import tools
from agents.tools import (
    get_truck_positions,
    get_distance_to_coordinates,
    get_distance_to_depot,
    get_current_route_plan,
    get_inventory_data,
    generate_incident_report
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')


class ConversationMemory:
    """Maneja la memoria de conversación"""
    
    def __init__(self):
        self.sessions = {}
    
    def get_session(self, session_id: str) -> List[Dict]:
        """Obtiene el historial de una sesión"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str):
        """Agrega un mensaje al historial"""
        session = self.get_session(session_id)
        session.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Mantener solo los últimos 20 mensajes
        if len(session) > 20:
            self.sessions[session_id] = session[-20:]
    
    def get_context(self, session_id: str, max_messages: int = 10) -> str:
        """Obtiene el contexto reciente de la conversación"""
        session = self.get_session(session_id)
        recent = session[-max_messages:] if len(session) > max_messages else session
        
        context_lines = []
        for msg in recent:
            role_label = "Usuario" if msg["role"] == "user" else "Asistente"
            context_lines.append(f"{role_label}: {msg['content']}")
        
        return "\n".join(context_lines) if context_lines else "No hay historial previo."


# Instancia global de memoria
memory = ConversationMemory()


def call_llm(messages: list, system_prompt: str = None) -> str:
    """Llama a OpenAI GPT"""
    try:
        # Construir mensajes para OpenAI
        openai_messages = []
        
        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        for msg in messages:
            if isinstance(msg, dict):
                openai_messages.append({
                    "role": msg.get('role', 'user'),
                    "content": msg.get('content', '')
                })
        
        # Llamar a OpenAI
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=openai_messages,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return f"Error: No se pudo conectar con OpenAI. Verifica tu API key en el archivo .env"


def route_planner_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """
    Agente especializado en planificación de rutas y seguimiento de flota
    Usa datos del JSON de rutas
    """
    # Obtener datos del JSON
    truck_positions = get_truck_positions()
    
    # Detectar si la consulta requiere información de inventario
    user_lower = user_message.lower()
    needs_inventory = any(word in user_lower for word in ['almacén', 'almacen', 'stock', 'quedan', 'disponible', 'inventario', 'lleva'])
    
    # Si necesita inventario, obtenerlo
    inventory_context = ""
    inventory_dict = {}  # Para búsqueda rápida
    if needs_inventory:
        inventory = get_inventory_data()
        if inventory:
            # Crear diccionario para búsqueda rápida por nombre de producto
            for item in inventory:
                inventory_dict[item['nombre_producto'].lower()] = item
            
            inventory_context = "\n\nINVENTARIO DEL ALMACÉN (para consultas cruzadas):\n"
            for item in inventory:  # Todos los items (ahora es un inventario pequeño)
                inventory_context += f"- {item['nombre_producto']}: {item['cantidad_disponible']} unidades (SKU: {item['sku']}, ${item['valor_unitario_usd']} USD)\n"
    
    # Detectar si necesita calcular distancias
    distance_calculation = None
    
    import re
    
    # Detectar menciones de camiones
    truck_mentions = re.findall(r'cami[oó]n\s+(\d+)|truck\s+(\d+)', user_lower)
    truck_ids = [int(m[0] or m[1]) - 1 for m in truck_mentions]
    
    # Si no se menciona camión pero hay contexto, buscar en mensajes anteriores
    if not truck_ids:
        recent_context = memory.get_context(session_id, max_messages=2)
        if recent_context:
            # Buscar menciones de camiones en el contexto
            context_mentions = re.findall(r'cami[oó]n\s+(\d+)|truck\s+(\d+)', recent_context.lower())
            if context_mentions:
                # Usar el último camión mencionado
                truck_ids = [int(context_mentions[-1][0] or context_mentions[-1][1]) - 1]
    
    # Caso 1: Distancia entre dos camiones
    if len(truck_ids) >= 2 and any(word in user_lower for word in ['distancia', 'lejos', 'cerca', 'distance', 'tiempo', 'tarda']):
        truck1_id = truck_ids[0]
        truck2_id = truck_ids[1]
        
        if truck1_id in truck_positions and truck2_id in truck_positions:
            pos1 = truck_positions[truck1_id]['position']
            pos2 = truck_positions[truck2_id]['position']
            
            # Usar AWS geo-routes para obtener distancia Y tiempo
            from agents.tools import calculate_route_between_points
            route_info = calculate_route_between_points(pos1, pos2)
            
            distance_calculation = {
                'type': 'truck_to_truck',
                'truck1': truck_positions[truck1_id]['truck_name'],
                'truck2': truck_positions[truck2_id]['truck_name'],
                'distance_km': route_info['distance_km'],
                'duration_minutes': route_info['duration_minutes'],
                'pos1': pos1,
                'pos2': pos2,
                'method': route_info.get('method', 'aws_geo_routes')
            }
    
    # Caso 2: Distancia al depósito/almacén
    elif len(truck_ids) >= 1 and any(word in user_lower for word in ['depósito', 'deposito', 'depot', 'almacén', 'almacen', 'base', 'bodega']):
        truck_id = truck_ids[0]
        
        if truck_id in truck_positions:
            result = get_distance_to_depot(truck_id)
            
            if 'distance_km' in result:
                # Calcular también el tiempo usando AWS
                from agents.tools import calculate_route_between_points
                route_info = calculate_route_between_points(
                    result['current_position'],
                    result['target_coordinates']
                )
                
                distance_calculation = {
                    'type': 'truck_to_depot',
                    'truck': result['truck_name'],
                    'distance_km': route_info['distance_km'],
                    'duration_minutes': route_info['duration_minutes'],
                    'truck_position': result['current_position'],
                    'depot_position': result['target_coordinates']
                }
    
    # Construir información de camiones
    trucks_info = []
    for truck_id, info in truck_positions.items():
        pos = info['position']
        
        # Información básica
        truck_text = f"- {info['truck_name']} (ID: {truck_id}):\n"
        truck_text += f"  Posición: [{pos[0]:.6f}, {pos[1]:.6f}]\n"
        truck_text += f"  Parada actual: {info['current_stop']}\n"
        truck_text += f"  Estado: {info['status']}\n"
        
        # Si hay incidente, mostrarlo
        if info.get('status') == 'incident' and 'incident' in info:
            incident = info['incident']
            truck_text += f"  ⚠️ INCIDENTE REPORTADO:\n"
            truck_text += f"     Tipo: {incident.get('type', 'N/A')}\n"
            truck_text += f"     Descripción: {incident.get('description', 'N/A')}\n"
            truck_text += f"     Tiempo de recuperación: {incident.get('recovery_time_minutes', 'N/A')} minutos\n"
        else:
            truck_text += f"  Progreso: {info.get('completed_stops', 0)}/{info.get('total_stops', 0)} entregas completadas\n"
        
        # Items entregados
        delivered = info.get('delivered_items', [])
        if delivered:
            truck_text += f"  ✅ Entregado ({len(delivered)} items, ${info.get('total_delivered_value', 0)} USD):\n"
            for item_info in delivered[:3]:  # Mostrar primeros 3
                truck_text += f"     • {item_info['item']} en {item_info['location']}\n"
            if len(delivered) > 3:
                truck_text += f"     • ... y {len(delivered) - 3} más\n"
        
        # Items pendientes (solo si no hay incidente)
        if info.get('status') != 'incident':
            pending = info.get('pending_items', [])
            if pending:
                truck_text += f"  📦 Por entregar ({len(pending)} items, ${info.get('total_pending_value', 0)} USD):\n"
                for item_info in pending[:3]:  # Mostrar primeros 3
                    truck_text += f"     • {item_info['item']} → {item_info['location']}\n"
                if len(pending) > 3:
                    truck_text += f"     • ... y {len(pending) - 3} más\n"
        
        trucks_info.append(truck_text)
    
    trucks_context = "\n".join(trucks_info) if trucks_info else "No hay información de camiones disponible."
    
    # Agregar información del depósito/almacén
    depot_info = """

UBICACIÓN DEL DEPÓSITO/ALMACÉN:
- Coordenadas: [-99.1908, 19.4336]
- Ubicación: Ciudad de México (punto de partida y retorno de todos los camiones)"""
    
    trucks_context += depot_info
    
    # Agregar cálculo de distancia si existe
    distance_context = ""
    if distance_calculation:
        if distance_calculation['type'] == 'truck_to_truck':
            method_text = "AWS Geo-Routes" if distance_calculation.get('method') != 'haversine_fallback' else "Haversine (estimado)"
            distance_context = f"""

CÁLCULO DE DISTANCIA Y TIEMPO ({method_text}):
- Entre: {distance_calculation['truck1']} y {distance_calculation['truck2']}
- Distancia: {distance_calculation['distance_km']} km
- Tiempo de viaje: {distance_calculation['duration_minutes']} minutos (en carro)
- Posición {distance_calculation['truck1']}: {distance_calculation['pos1']}
- Posición {distance_calculation['truck2']}: {distance_calculation['pos2']}"""
        
        elif distance_calculation['type'] == 'truck_to_depot':
            distance_context = f"""

CÁLCULO DE DISTANCIA Y TIEMPO AL DEPÓSITO/ALMACÉN:
- Camión: {distance_calculation['truck']}
- Distancia al depósito: {distance_calculation['distance_km']} km
- Tiempo de viaje: {distance_calculation['duration_minutes']} minutos (en carro)
- Posición del camión: {distance_calculation['truck_position']}
- Posición del depósito/almacén: {distance_calculation['depot_position']}"""
    
    # Contexto de conversación (últimos 3 mensajes)
    conversation_context = memory.get_context(session_id, max_messages=3)
    
    system_prompt = f"""Eres un agente especializado en planificación de rutas y seguimiento de flota.

INFORMACIÓN DE LA FLOTA:
{trucks_context}{distance_context}{inventory_context}

CONTEXTO DE LA CONVERSACIÓN:
{conversation_context}

INSTRUCCIONES:
- Usa ÚNICAMENTE la información proporcionada arriba
- El DEPÓSITO/ALMACÉN está en [-99.1908, 19.4336] - todos los camiones parten y regresan ahí
- Si preguntan por distancia al "almacén", "depósito", "bodega" o "base", usa las coordenadas del depósito
- Cada camión tiene información de:
  * Posición actual y parada
  * Items ENTREGADOS (✅) con ubicación donde se entregaron
  * Items PENDIENTES (📦) con destino donde se entregarán
  * Valor total en USD de entregas completadas y pendientes
- Si preguntan qué transporta un camión, menciona los items PENDIENTES
- Si preguntan qué ha entregado, menciona los items ENTREGADOS
- Si hay un CÁLCULO DE DISTANCIA Y TIEMPO, usa esos resultados exactos
- Cuando menciones distancias entre camiones, SIEMPRE incluye el tiempo de viaje
- El tiempo está calculado usando rutas reales de AWS (no en línea recta)
- Si el usuario pregunta por un camión específico (ej: "camión 5"), usa el ID correcto (ID 4 para "camión 5")
- CONSULTAS CRUZADAS CON INVENTARIO:
  * Si preguntan "cuánto queda en el almacén de lo que lleva el camión X", debes:
    1. Identificar los items PENDIENTES del camión X
    2. Para cada item, buscar su nombre en el INVENTARIO DEL ALMACÉN
    3. Reportar la cantidad disponible en almacén de cada item
  * Busca coincidencias exactas o parciales en los nombres de productos
  * Si un item del camión no aparece en el inventario mostrado, indica que no se encontró
- NO inventes datos ni coordenadas
- Responde de forma natural y conversacional en español"""
    
    response = call_llm(
        [{"role": "user", "content": user_message}],
        system_prompt=system_prompt
    )
    
    return {
        "agent": "Route Planner Agent",
        "response": response,
        "data": {
            "truck_positions": truck_positions,
            "total_trucks": len(truck_positions),
            "distance_calculation": distance_calculation
        }
    }


def inventory_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """
    Agente especializado en gestión de inventario y reportes
    """
    # Obtener datos reales
    inventory = get_inventory_data()
    route_plan = get_current_route_plan()
    
    # Construir información contextual (todos los items)
    inventory_info = []
    for idx, item in enumerate(inventory):
        inventory_info.append(
            f"- {item.get('nombre_producto', 'N/A')} (SKU: {item.get('sku', 'N/A')})\n"
            f"  Stock disponible: {item.get('cantidad_disponible', 'N/A')} unidades\n"
            f"  Categoría: {item.get('categoria', 'N/A')}\n"
            f"  Precio: ${item.get('valor_unitario_usd', 'N/A')} USD\n"
            f"  Ubicación: {item.get('ubicacion', 'N/A')}"
        )
    
    inventory_context = "\n\n".join(inventory_info) if inventory_info else "No hay información de inventario."
    
    # Información de rutas
    routes_info = "No hay rutas planificadas."
    if "data" in route_plan:
        total_trucks = len(route_plan["data"].get("routes", []))
        routes_info = f"Hay {total_trucks} camiones con rutas asignadas."
    
    # Obtener contexto de conversación
    conversation_context = memory.get_context(session_id, max_messages=3)
    
    system_prompt = f"""Eres un agente especializado en gestión de inventario y reportes.

INVENTARIO ACTUAL (muestra de 20 items):
{inventory_context}

RUTAS ACTUALES:
{routes_info}

CONTEXTO DE LA CONVERSACIÓN:
{conversation_context}

INSTRUCCIONES:
- Usa ÚNICAMENTE la información real proporcionada
- El inventario muestra: nombre, SKU, stock disponible, categoría, precio y ubicación
- Si preguntan por un producto específico, busca en la lista por nombre o categoría
- Si preguntan "cuántas pantallas", busca productos con "Monitor", "Pantalla" o "Display"
- Si preguntan por stock, usa el campo "Stock disponible"
- NO inventes datos de inventario
- Responde de forma natural y conversacional en español"""
    
    response = call_llm(
        [{"role": "user", "content": user_message}],
        system_prompt=system_prompt
    )
    
    return {
        "agent": "Inventory & Report Agent",
        "response": response,
        "data": {
            "inventory_count": len(inventory),
            "routes_count": len(route_plan.get("data", {}).get("routes", []))
        }
    }


def supervisor_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """
    Agente supervisor que decide qué agente debe manejar la consulta
    """
    # Obtener contexto de conversación
    conversation_context = memory.get_context(session_id, max_messages=5)
    
    # Detección basada en palabras clave (más confiable que LLM para esto)
    user_text = user_message.lower()
    
    route_keywords = ["camión", "camion", "truck", "posición", "posicion", "ubicación", 
                      "ubicacion", "dónde", "donde", "está", "esta", "distancia", 
                      "ruta", "flota", "coordenadas"]
    
    inventory_keywords = ["inventario", "inventory", "producto", "stock", "reporte", 
                         "entrega", "almacén", "almacen", "items", "artículos"]
    
    # Saludos simples
    greeting_keywords = ["hola", "buenos días", "buenas tardes", "buenas noches", 
                        "hey", "qué tal", "cómo estás"]
    
    is_greeting = any(keyword in user_text for keyword in greeting_keywords) and len(user_text) < 30
    
    if is_greeting and not conversation_context:
        # Saludo inicial
        response = """¡Hola! Soy tu asistente de logística. Puedo ayudarte con:

🚚 Seguimiento de flota y posiciones de camiones
📦 Consultas de inventario y stock
📊 Reportes de entregas y rutas

¿En qué puedo ayudarte hoy?"""
        
        return {
            "agent": "Logistics Agent",
            "response": response,
            "data": None
        }
    
    # Decidir qué agente usar
    if any(keyword in user_text for keyword in route_keywords):
        return route_planner_agent(user_message, session_id)
    elif any(keyword in user_text for keyword in inventory_keywords):
        return inventory_agent(user_message, session_id)
    else:
        # Usar LLM para decidir en casos ambiguos
        decision_prompt = f"""Analiza este mensaje: "{user_message}"

Contexto previo:
{conversation_context}

¿De qué trata? Responde SOLO con una palabra:
- ROUTE: si es sobre camiones, posiciones, rutas, distancias
- INVENTORY: si es sobre inventario, productos, stock
- GENERAL: si es un saludo o pregunta general"""
        
        decision = call_llm([{"role": "user", "content": decision_prompt}])
        
        if "ROUTE" in decision.upper():
            return route_planner_agent(user_message, session_id)
        elif "INVENTORY" in decision.upper():
            return inventory_agent(user_message, session_id)
        else:
            # Respuesta general
            response = call_llm([
                {"role": "user", "content": f"""Eres un asistente de logística amigable.

Contexto previo:
{conversation_context}

Usuario: {user_message}

Responde de forma natural en español. Si preguntan qué puedes hacer, menciona seguimiento de flota e inventario."""}
            ])
            
            return {
                "agent": "Logistics Agent",
                "response": response,
                "data": None
            }


def process_message(message: str, session_id: str = "default") -> Dict[str, Any]:
    """
    Procesa un mensaje del usuario con memoria conversacional
    
    Args:
        message: Mensaje del usuario
        session_id: ID de sesión para mantener contexto
    
    Returns:
        Respuesta del agente con contexto
    """
    try:
        # Agregar mensaje del usuario a la memoria
        memory.add_message(session_id, "user", message)
        
        # Procesar con el supervisor
        result = supervisor_agent(message, session_id)
        
        # Agregar respuesta del agente a la memoria
        memory.add_message(session_id, "assistant", result["response"])
        
        return result
        
    except Exception as e:
        import traceback
        print("Error en process_message:")
        traceback.print_exc()
        return {
            "agent": "System",
            "response": f"Error al procesar mensaje: {str(e)}",
            "data": None
        }


def clear_session(session_id: str = "default"):
    """Limpia la memoria de una sesión"""
    if session_id in memory.sessions:
        del memory.sessions[session_id]


def get_session_history(session_id: str = "default") -> List[Dict]:
    """Obtiene el historial de una sesión"""
    return memory.get_session(session_id)
