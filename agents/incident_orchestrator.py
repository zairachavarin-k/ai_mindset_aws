"""
Sistema de Orquestación de Incidentes
Maneja incidentes de camiones y redistribuye entregas automáticamente
"""

import json
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from agents.tools import (
    get_truck_positions,
    get_inventory_data,
    get_current_route_plan,
    get_distance_to_depot
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')


def call_llm(messages: list, system_prompt: str = None, temperature: float = 0.3) -> str:
    """Llama a OpenAI GPT"""
    try:
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
        
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=1000
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return f"Error: {str(e)}"


def incident_analyzer_agent(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agente Analizador de Incidentes
    Analiza el incidente y determina qué entregas están pendientes
    """
    print(f"\n🔍 AGENTE ANALIZADOR: Analizando incidente del camión {incident_data.get('truck_id', 'N/A')}")
    
    truck_id = incident_data.get('truck_id')
    
    # Obtener información del camión
    truck_positions = get_truck_positions()
    route_plan = get_current_route_plan()
    
    if truck_id not in truck_positions:
        return {
            "success": False,
            "error": f"Camión {truck_id} no encontrado"
        }
    
    truck_info = truck_positions[truck_id]
    
    # Obtener entregas pendientes
    pending_items = truck_info.get('pending_items', [])
    pending_value = truck_info.get('total_pending_value', 0)
    
    # Crear análisis estructurado
    analysis = {
        "truck_id": truck_id,
        "truck_name": truck_info.get('truck_name'),
        "incident_type": incident_data.get('incident_type', 'accident'),
        "location": incident_data.get('location'),
        "pending_deliveries": len(pending_items),
        "pending_items": pending_items,
        "pending_value_usd": pending_value,
        "analysis_timestamp": datetime.now().isoformat()
    }
    
    print(f"  ✓ Entregas pendientes: {len(pending_items)}")
    print(f"  ✓ Valor pendiente: ${pending_value} USD")
    
    return {
        "success": True,
        "analysis": analysis
    }


def inventory_checker_agent(pending_items: List[Dict]) -> Dict[str, Any]:
    """
    Agente Verificador de Inventario
    Verifica si hay suficiente inventario para completar las entregas pendientes
    """
    print(f"\n📦 AGENTE INVENTARIO: Verificando disponibilidad de {len(pending_items)} items")
    
    inventory = get_inventory_data()
    
    # Crear diccionario de inventario por nombre de producto
    inventory_dict = {}
    for item in inventory:
        product_name = item['nombre_producto']
        inventory_dict[product_name] = item
    
    # Verificar cada item pendiente
    availability_report = []
    all_available = True
    available_items_list = []
    unavailable_items_list = []
    
    for pending in pending_items:
        item_name = pending['item']
        
        # Buscar en inventario (con coincidencia flexible)
        found = False
        available_qty = 0
        
        # Buscar coincidencia exacta
        if item_name in inventory_dict:
            found = True
            # Convertir a int de manera segura
            try:
                available_qty = int(inventory_dict[item_name]['cantidad_disponible'])
            except (ValueError, TypeError):
                available_qty = 0
        else:
            # Buscar por primeras palabras
            words = item_name.split()
            if len(words) >= 2:
                prefix = ' '.join(words[:2])
                for inv_name, inv_data in inventory_dict.items():
                    if inv_name.startswith(prefix):
                        found = True
                        # Convertir a int de manera segura
                        try:
                            available_qty = int(inv_data['cantidad_disponible'])
                        except (ValueError, TypeError):
                            available_qty = 0
                        break
        
        is_available = found and available_qty > 0
        
        availability_report.append({
            "item": item_name,
            "destination": pending['location'],
            "available": is_available,
            "quantity_available": available_qty if found else 0
        })
        
        if not is_available:
            all_available = False
            unavailable_items_list.append(item_name)
            print(f"  ⚠️ {item_name}: NO DISPONIBLE")
        else:
            available_items_list.append(item_name)
            print(f"  ✓ {item_name}: Disponible ({available_qty} unidades)")
    
    # Determinar si podemos continuar
    can_proceed = len(available_items_list) > 0
    
    if not all_available:
        print(f"\n  ⚠️ ADVERTENCIA: {len(unavailable_items_list)} items NO disponibles")
        print(f"  ✓ Se pueden entregar {len(available_items_list)} de {len(pending_items)} items")
        if can_proceed:
            print(f"  → Continuando con entregas parciales")
    
    return {
        "success": True,
        "all_available": all_available,
        "can_proceed": can_proceed,
        "availability_report": availability_report,
        "total_items_checked": len(pending_items),
        "available_items": len(available_items_list),
        "unavailable_items": len(unavailable_items_list),
        "unavailable_items_list": unavailable_items_list,
        "available_items_list": available_items_list
    }


def truck_selector_agent(incident_truck_id: int, pending_items: List[Dict]) -> Dict[str, Any]:
    """
    Agente Selector de Camión (OPTIMIZADO)
    Calcula ruta completa para cada camión y elige el que minimice tiempo total
    """
    print(f"\n🚚 AGENTE SELECTOR: Evaluando mejor camión para asumir entregas")
    
    from main import geo_routes_client
    
    truck_positions = get_truck_positions()
    route_plan = get_current_route_plan()
    
    # Filtrar camiones disponibles
    available_trucks = []
    
    for truck_id, truck_info in truck_positions.items():
        if truck_id == incident_truck_id:
            continue
        
        if truck_info.get('status') == 'incident':
            continue
        
        # Calcular distancia al depósito (para referencia)
        distance_info = get_distance_to_depot(truck_id)
        
        if 'distance_km' in distance_info:
            available_trucks.append({
                "truck_id": truck_id,
                "truck_name": truck_info['truck_name'],
                "distance_to_depot_km": distance_info['distance_km'],
                "current_position": truck_info['position'],
                "pending_deliveries": len(truck_info.get('pending_items', [])),
                "pending_items": truck_info.get('pending_items', [])
            })
    
    if not available_trucks:
        return {
            "success": False,
            "error": "No hay camiones disponibles"
        }
    
    print(f"  📊 Evaluando {len(available_trucks)} camiones candidatos...")
    
    # Obtener coordenadas de entregas del incidente
    incident_coords = [item['location'] for item in pending_items]
    DEPOT_COORDS = [-99.1908, 19.4336]
    
    # Evaluar cada camión calculando su ruta completa
    evaluations = []
    
    for truck in available_trucks:
        truck_id = truck['truck_id']
        truck_pos = truck['current_position']
        
        # Combinar entregas: propias + del incidente
        all_deliveries = incident_coords.copy()
        
        # Agregar entregas pendientes del camión
        if 'data' in route_plan:
            for route in route_plan['data'].get('routes', []):
                if route['truck_id'] == truck_id:
                    for stop in route.get('stops', []):
                        if stop['status'] == 'pending' and stop['stop_number'] > 0:
                            all_deliveries.append([
                                stop['coordinates']['longitude'],
                                stop['coordinates']['latitude']
                            ])
                    break
        
        total_destinations = len(all_deliveries)
        
        print(f"  🔍 Evaluando {truck['truck_name']}: {total_destinations} destinos totales")
        
        # Calcular ruta completa con AWS
        if geo_routes_client and total_destinations > 0:
            try:
                response = geo_routes_client.calculate_routes(
                    Origin=truck_pos,
                    Destination=DEPOT_COORDS,
                    Waypoints=[{"Position": wp} for wp in all_deliveries],
                    TravelMode='Car',
                    LegGeometryFormat='Simple'
                )
                
                if 'Routes' in response and len(response['Routes']) > 0:
                    total_distance = 0
                    total_duration = 0
                    
                    for leg in response['Routes'][0].get('Legs', []):
                        total_distance += leg.get('Distance', 0)
                        total_duration += leg.get('DurationSeconds', 0)
                    
                    # Agregar tiempo de servicio (5 min por entrega)
                    service_time = total_destinations * 5 * 60  # segundos
                    total_time_with_service = total_duration + service_time
                    
                    evaluations.append({
                        "truck_id": truck_id,
                        "truck_name": truck['truck_name'],
                        "current_position": truck_pos,
                        "distance_to_depot_km": truck['distance_to_depot_km'],
                        "pending_deliveries": truck['pending_deliveries'],
                        "total_destinations": total_destinations,
                        "total_distance_km": total_distance / 1000,
                        "total_duration_minutes": total_duration / 60,
                        "total_time_with_service_minutes": total_time_with_service / 60,
                        "route_calculated": True
                    })
                    
                    print(f"     ✓ Ruta calculada: {total_distance/1000:.1f} km, {total_time_with_service/60:.0f} min total")
                else:
                    raise Exception("No route returned")
                    
            except Exception as e:
                print(f"     ⚠️ Error calculando ruta: {e}")
                # Fallback: usar distancia al depósito como estimación
                estimated_time = truck['distance_to_depot_km'] * 2 + total_destinations * 5
                evaluations.append({
                    "truck_id": truck_id,
                    "truck_name": truck['truck_name'],
                    "current_position": truck_pos,
                    "distance_to_depot_km": truck['distance_to_depot_km'],
                    "pending_deliveries": truck['pending_deliveries'],
                    "total_destinations": total_destinations,
                    "total_time_with_service_minutes": estimated_time,
                    "route_calculated": False
                })
        else:
            # Sin AWS, usar estimación simple
            estimated_time = truck['distance_to_depot_km'] * 2 + total_destinations * 5
            evaluations.append({
                "truck_id": truck_id,
                "truck_name": truck['truck_name'],
                "current_position": truck_pos,
                "distance_to_depot_km": truck['distance_to_depot_km'],
                "pending_deliveries": truck['pending_deliveries'],
                "total_destinations": total_destinations,
                "total_time_with_service_minutes": estimated_time,
                "route_calculated": False
            })
    
    if not evaluations:
        return {
            "success": False,
            "error": "No se pudieron evaluar camiones"
        }
    
    # Ordenar por tiempo total (menor primero)
    evaluations.sort(key=lambda x: x['total_time_with_service_minutes'])
    
    selected_truck = evaluations[0]
    alternatives = evaluations[1:3]
    
    print(f"\n  ✅ MEJOR OPCIÓN: {selected_truck['truck_name']}")
    print(f"     - Tiempo total: {selected_truck['total_time_with_service_minutes']:.0f} min")
    print(f"     - Destinos totales: {selected_truck['total_destinations']}")
    if selected_truck.get('route_calculated'):
        print(f"     - Distancia total: {selected_truck['total_distance_km']:.1f} km")
    
    if alternatives:
        print(f"\n  📋 Alternativas consideradas:")
        for alt in alternatives:
            print(f"     - {alt['truck_name']}: {alt['total_time_with_service_minutes']:.0f} min")
            time_diff = alt['total_time_with_service_minutes'] - selected_truck['total_time_with_service_minutes']
            print(f"       ({time_diff:.0f} min más lento)")
    
    return {
        "success": True,
        "selected_truck": selected_truck,
        "alternatives": alternatives,
        "evaluation_method": "total_time_optimization"
    }


def solution_validator_agent(solution_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agente Solucionador/Validador
    Valida que la solución propuesta sea viable y óptima
    """
    print(f"\n✅ AGENTE SOLUCIONADOR: Validando solución propuesta")
    
    # Extraer información de la solución
    incident_analysis = solution_plan.get('incident_analysis', {})
    inventory_check = solution_plan.get('inventory_check', {})
    selected_truck = solution_plan.get('selected_truck', {})
    
    # Criterios de validación
    validation_criteria = []
    
    # 1. Inventario disponible (ahora más flexible)
    available_count = inventory_check.get('available_items', 0)
    total_count = inventory_check.get('total_items_checked', 0)
    can_proceed = inventory_check.get('can_proceed', False)
    
    if inventory_check.get('all_available'):
        validation_criteria.append({
            "criterion": "Inventario disponible",
            "status": "✓ PASS",
            "details": f"Todos los {total_count} items están disponibles"
        })
    elif can_proceed:
        validation_criteria.append({
            "criterion": "Inventario disponible",
            "status": "⚠️ PARTIAL",
            "details": f"{available_count}/{total_count} items disponibles - Entrega parcial posible"
        })
    else:
        validation_criteria.append({
            "criterion": "Inventario disponible",
            "status": "✗ FAIL",
            "details": f"Ningún item disponible"
        })
    
    # 2. Camión seleccionado válido
    if selected_truck.get('truck_id') is not None:
        validation_criteria.append({
            "criterion": "Camión disponible",
            "status": "✓ PASS",
            "details": f"{selected_truck.get('truck_name')} a {selected_truck.get('distance_to_depot_km', 0):.2f} km del depósito"
        })
    else:
        validation_criteria.append({
            "criterion": "Camión disponible",
            "status": "✗ FAIL",
            "details": "No se encontró camión disponible"
        })
    
    # 3. Capacidad del camión (IGNORADA - siempre pasa)
    pending_deliveries = len(incident_analysis.get('pending_items', []))
    current_deliveries = selected_truck.get('pending_deliveries', 0)
    total_deliveries = pending_deliveries + current_deliveries
    
    # NOTA: Ignoramos capacidad por instrucción del usuario
    validation_criteria.append({
        "criterion": "Capacidad del camión",
        "status": "✓ PASS (ignorada)",
        "details": f"{total_deliveries} entregas totales (capacidad no limitada)"
    })
    
    # 4. Validación simplificada (SIN LLM - aprobación automática si hay items)
    # REGLA SIMPLE: Si hay al menos 1 item disponible → APROBAR
    unavailable_items = inventory_check.get('unavailable_items_list', [])
    
    if can_proceed:
        print(f"  ✓ Aprobación automática: {available_count} items disponibles")
        llm_validation = {
            "is_valid": True,
            "confidence": 90,
            "recommendation": "APPROVE",
            "reasoning": f"Entrega parcial aprobada: {available_count}/{total_count} items disponibles. Capacidad ignorada por configuración.",
            "warnings": [f"{len(unavailable_items)} items no disponibles"] if unavailable_items else []
        }
    else:
        print(f"  ✗ Rechazo automático: ningún item disponible")
        llm_validation = {
            "is_valid": False,
            "confidence": 100,
            "recommendation": "REJECT",
            "reasoning": "No hay items disponibles en inventario para entregar",
            "warnings": ["Todos los items no disponibles"]
        }
    
    print(f"  ✓ Validación: {llm_validation.get('recommendation')}")
    print(f"  ✓ Confianza: {llm_validation.get('confidence')}%")
    print(f"  ✓ Razonamiento: {llm_validation.get('reasoning')}")
    
    if unavailable_items:
        print(f"  ⚠️ Items no disponibles: {len(unavailable_items)}")
        for item in unavailable_items[:3]:
            print(f"     - {item}")
        if len(unavailable_items) > 3:
            print(f"     - ... y {len(unavailable_items) - 3} más")
    
    return {
        "success": True,
        "validation_criteria": validation_criteria,
        "llm_validation": llm_validation,
        "is_approved": llm_validation.get('recommendation') == 'APPROVE',
        "confidence": llm_validation.get('confidence', 0),
        "unavailable_items": unavailable_items,
        "partial_delivery": not inventory_check.get('all_available') and can_proceed
    }


def route_generator_agent(solution_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agente Generador de Rutas (Simplificado)
    Genera ruta optimizada desde posición actual del camión
    """
    print(f"\n🗺️ AGENTE GENERADOR DE RUTAS: Calculando ruta optimizada")
    
    import requests
    
    selected_truck = solution_plan['selected_truck']
    incident_analysis = solution_plan['incident_analysis']
    
    truck_id = selected_truck['truck_id']
    truck_position = selected_truck['current_position']  # Posición ACTUAL del camión
    
    print(f"  📍 Posición actual del camión: [{truck_position[0]:.4f}, {truck_position[1]:.4f}]")
    
    # Obtener plan de rutas actual
    route_plan = get_current_route_plan()
    
    if 'data' not in route_plan:
        return {
            "success": False,
            "error": "No se pudo obtener el plan de rutas"
        }
    
    # Encontrar las rutas
    selected_truck_route = None
    incident_truck_route = None
    
    for route in route_plan['data'].get('routes', []):
        if route['truck_id'] == truck_id:
            selected_truck_route = route
        if route['truck_id'] == incident_analysis['truck_id']:
            incident_truck_route = route
    
    if not selected_truck_route or not incident_truck_route:
        return {
            "success": False,
            "error": "No se encontraron las rutas necesarias"
        }
    
    # Recopilar SOLO destinos pendientes (desde posición actual)
    all_destinations = []
    
    # Destinos pendientes del camión seleccionado
    for stop in selected_truck_route.get('stops', []):
        if stop['status'] == 'pending' and stop['stop_number'] > 0:
            all_destinations.append({
                "coords": [stop['coordinates']['longitude'], stop['coordinates']['latitude']],
                "location": stop['location'],
                "items": stop.get('items', []),
                "stop_number": stop['stop_number'],
                "from_truck": selected_truck['truck_name']
            })
    
    # Destinos pendientes del camión con incidente
    for stop in incident_truck_route.get('stops', []):
        if stop['status'] == 'pending' and stop['stop_number'] > 0:
            all_destinations.append({
                "coords": [stop['coordinates']['longitude'], stop['coordinates']['latitude']],
                "location": stop['location'],
                "items": stop.get('items', []),
                "stop_number": stop['stop_number'],
                "from_truck": incident_analysis['truck_name']
            })
    
    print(f"  ✓ Total destinos a visitar: {len(all_destinations)}")
    print(f"     - Del camión seleccionado: {len([d for d in all_destinations if d['from_truck'] == selected_truck['truck_name']])}")
    print(f"     - Del camión con incidente: {len([d for d in all_destinations if d['from_truck'] == incident_analysis['truck_name']])}")
    
    if len(all_destinations) == 0:
        return {
            "success": False,
            "error": "No hay destinos pendientes"
        }
    
    # Optimizar orden de destinos desde posición actual
    # OPTIMIZACIÓN: Solo optimizar si hay 3-7 destinos (rango óptimo)
    destination_coords = [dest['coords'] for dest in all_destinations]
    DEPOT_COORDS = [-99.1908, 19.4336]
    
    if 3 <= len(all_destinations) <= 7:
        print(f"  📍 Optimizando orden de {len(all_destinations)} destinos...")
        try:
            response = requests.post(
                'http://localhost:8000/optimize-waypoints',
                json={
                    "origin": truck_position,
                    "destination": DEPOT_COORDS,
                    "waypoints": destination_coords
                },
                timeout=20  # Timeout más corto
            )
            
            if response.ok:
                optimization_result = response.json()
                optimized_order = []
                if 'WaypointIndices' in optimization_result:
                    for idx in optimization_result['WaypointIndices']:
                        optimized_order.append(all_destinations[idx])
                else:
                    optimized_order = all_destinations
                print(f"     ✓ Orden optimizado")
            else:
                print(f"     ⚠️ Usando orden original")
                optimized_order = all_destinations
        except Exception as e:
            print(f"     ⚠️ Timeout/Error, usando orden original")
            optimized_order = all_destinations
    else:
        if len(all_destinations) < 3:
            print(f"  📍 Pocos destinos ({len(all_destinations)}), sin optimización")
        else:
            print(f"  📍 Muchos destinos ({len(all_destinations)}), sin optimización (evitar timeout)")
        optimized_order = all_destinations
    
    # Calcular ruta completa desde posición actual con AWS
    print(f"  📍 Calculando ruta con AWS Location Service")
    
    waypoint_coords = [dest['coords'] for dest in optimized_order]
    
    # Llamar directamente a AWS (sin límite de waypoints)
    from main import geo_routes_client
    
    if not geo_routes_client:
        print(f"     ⚠️ Cliente AWS no disponible, usando fallback")
        route_geometry = [truck_position, *waypoint_coords, DEPOT_COORDS]
        import math
        total_distance = sum(
            math.sqrt((route_geometry[i+1][0]-route_geometry[i][0])**2 + 
                     (route_geometry[i+1][1]-route_geometry[i][1])**2) * 111000
            for i in range(len(route_geometry)-1)
        )
        total_duration = total_distance / 8.33
        print(f"     ✓ Fallback: {total_distance/1000:.2f} km, {total_duration/60:.2f} min")
    else:
        route_geometry = []
        total_distance = 0
        total_duration = 0
        
        print(f"     → Calculando ruta completa con {len(waypoint_coords)} waypoints...")
        try:
            response = geo_routes_client.calculate_routes(
                Origin=truck_position,
                Destination=DEPOT_COORDS,
                Waypoints=[{"Position": wp} for wp in waypoint_coords],
                TravelMode='Car',
                LegGeometryFormat='Simple'
            )
            
            if 'Routes' in response and len(response['Routes']) > 0:
                for leg in response['Routes'][0].get('Legs', []):
                    total_distance += leg.get('Distance', 0)
                    total_duration += leg.get('DurationSeconds', 0)
                    leg_geometry = leg.get('Geometry', {})
                    if 'LineString' in leg_geometry:
                        route_geometry.extend(leg_geometry['LineString'])
            
            print(f"     ✓ Ruta AWS: {total_distance/1000:.2f} km, {total_duration/60:.2f} min")
            print(f"     ✓ Geometría: {len(route_geometry)} puntos")
                
        except Exception as e:
            print(f"     ⚠️ Error AWS: {e}")
            route_geometry = []
        
        # Si falló, usar fallback
        if len(route_geometry) == 0:
            print(f"     → Usando fallback (líneas rectas)")
            route_geometry = [truck_position, *waypoint_coords, DEPOT_COORDS]
            import math
            total_distance = 0
            for i in range(len(route_geometry) - 1):
                p1, p2 = route_geometry[i], route_geometry[i+1]
                dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2) * 111000
                total_distance += dist
            total_duration = total_distance / 8.33
            print(f"     ✓ Fallback: {total_distance/1000:.2f} km, {total_duration/60:.2f} min")
    
    # Construir plan de ruta simplificado
    new_route_plan = {
        "truck_id": truck_id,
        "truck_name": selected_truck['truck_name'],
        "route_type": "incident_recovery_simplified",
        "created_at": datetime.now().isoformat(),
        "description": "Ruta desde posición actual (sin retorno a depósito)",
        "waypoints": optimized_order,
        "geometry": route_geometry,
        "summary": {
            "total_destinations": len(optimized_order),
            "total_distance_km": total_distance / 1000,
            "total_duration_minutes": total_duration / 60,
            "items_from_incident_truck": len([d for d in optimized_order if d['from_truck'] == incident_analysis['truck_name']]),
            "items_from_selected_truck": len([d for d in optimized_order if d['from_truck'] == selected_truck['truck_name']]),
            "start_position": truck_position,
            "end_position": DEPOT_COORDS
        }
    }
    
    print(f"\n  ✅ RUTA GENERADA (Simplificada):")
    print(f"     • Desde posición actual del camión")
    print(f"     • {len(optimized_order)} entregas totales")
    print(f"     • {new_route_plan['summary']['total_distance_km']:.2f} km")
    print(f"     • {new_route_plan['summary']['total_duration_minutes']:.1f} min")
    print(f"     • Termina en depósito")
    
    return {
        "success": True,
        "new_route": new_route_plan
    }


def orchestrate_incident_response(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orquestador Principal
    Coordina todos los agentes para resolver el incidente
    """
    import time
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"🚨 ORQUESTADOR: Iniciando respuesta a incidente")
    print(f"{'='*60}")
    
    response = {
        "incident_id": incident_data.get('incident_id'),
        "timestamp": datetime.now().isoformat(),
        "steps": []
    }
    
    # PASO 1: Analizar incidente
    step_start = time.time()
    print(f"\n📋 PASO 1: Análisis del incidente")
    analysis_result = incident_analyzer_agent(incident_data)
    response['steps'].append({"step": 1, "agent": "Analyzer", "result": analysis_result})
    print(f"   ⏱️ Tiempo: {time.time() - step_start:.2f}s")
    
    if not analysis_result.get('success'):
        response['success'] = False
        response['error'] = analysis_result.get('error')
        return response
    
    incident_analysis = analysis_result['analysis']
    pending_items = incident_analysis['pending_items']
    
    # PASO 2: Verificar inventario
    step_start = time.time()
    print(f"\n📋 PASO 2: Verificación de inventario")
    inventory_result = inventory_checker_agent(pending_items)
    response['steps'].append({"step": 2, "agent": "Inventory Checker", "result": inventory_result})
    print(f"   ⏱️ Tiempo: {time.time() - step_start:.2f}s")
    
    if not inventory_result.get('all_available'):
        print(f"  ⚠️ ADVERTENCIA: No todos los items están disponibles")
    
    # PASO 3: Seleccionar camión alternativo
    step_start = time.time()
    print(f"\n📋 PASO 3: Selección de camión alternativo")
    selector_result = truck_selector_agent(incident_data.get('truck_id'), pending_items)
    response['steps'].append({"step": 3, "agent": "Truck Selector", "result": selector_result})
    print(f"   ⏱️ Tiempo: {time.time() - step_start:.2f}s")
    
    if not selector_result.get('success'):
        response['success'] = False
        response['error'] = selector_result.get('error')
        return response
    
    # PASO 4: Validar solución
    step_start = time.time()
    print(f"\n📋 PASO 4: Validación de solución")
    solution_plan = {
        "incident_analysis": incident_analysis,
        "inventory_check": inventory_result,
        "selected_truck": selector_result['selected_truck']
    }
    
    validation_result = solution_validator_agent(solution_plan)
    response['steps'].append({"step": 4, "agent": "Solution Validator", "result": validation_result})
    print(f"   ⏱️ Tiempo: {time.time() - step_start:.2f}s")
    
    # Si la solución no es aprobada, terminar aquí
    if not validation_result.get('is_approved', False):
        response['success'] = False
        response['solution'] = solution_plan
        response['validation'] = validation_result
        
        print(f"\n{'='*60}")
        print(f"❌ SOLUCIÓN RECHAZADA")
        print(f"   Razón: {validation_result.get('llm_validation', {}).get('reasoning')}")
        print(f"{'='*60}\n")
        
        return response
    
    # PASO 5: Generar nueva ruta
    step_start = time.time()
    print(f"\n📋 PASO 5: Generación de nueva ruta")
    route_result = route_generator_agent(solution_plan)
    response['steps'].append({"step": 5, "agent": "Route Generator", "result": route_result})
    print(f"   ⏱️ Tiempo: {time.time() - step_start:.2f}s")
    
    # Resultado final
    response['success'] = route_result.get('success', False)
    response['solution'] = solution_plan
    response['validation'] = validation_result
    response['new_route'] = route_result.get('new_route') if route_result.get('success') else None
    
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    if response['success']:
        print(f"✅ SOLUCIÓN COMPLETA Y APROBADA")
        print(f"   Camión {selector_result['selected_truck']['truck_name']} asumirá las entregas")
        if response['new_route']:
            summary = response['new_route']['summary']
            print(f"   Nueva ruta: {summary['total_destinations']} destinos")
            print(f"   Distancia total: {summary['total_distance_km']:.2f} km")
            print(f"   Tiempo estimado: {summary['total_duration_minutes']:.1f} min")
    else:
        print(f"❌ ERROR EN GENERACIÓN DE RUTA")
        print(f"   Razón: {route_result.get('error', 'Error desconocido')}")
    print(f"   ⏱️ TIEMPO TOTAL: {total_time:.2f}s")
    print(f"{'='*60}\n")
    
    return response
