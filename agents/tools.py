"""
Herramientas para los agentes de logística
"""
import json
import boto3
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import csv
from math import radians, sin, cos, sqrt, atan2

logger = logging.getLogger(__name__)

# Initialize AWS clients
geo_routes_client = boto3.client('geo-routes', region_name='us-east-1')

# Paths
DATA_DIR = Path("data")
INVENTORY_DIR = Path("inventary")

# Import simulator
try:
    from agents.truck_simulator import simulator
    SIMULATOR_AVAILABLE = True
except ImportError:
    SIMULATOR_AVAILABLE = False
    logger.warning("Truck simulator not available")


def calculate_route_between_points(origin: List[float], destination: List[float]) -> Dict:
    """
    Calcula la ruta entre dos puntos usando AWS geo-routes
    Retorna distancia y tiempo de viaje
    
    Args:
        origin: [longitude, latitude] origen
        destination: [longitude, latitude] destino
    
    Returns:
        Dictionary con distance_km, duration_minutes, y detalles
    """
    try:
        response = geo_routes_client.calculate_routes(
            Origin=origin,
            Destination=destination,
            TravelMode='Car',
            LegGeometryFormat='Simple'
        )
        
        if 'Routes' in response and len(response['Routes']) > 0:
            route = response['Routes'][0]
            summary = route.get('Summary', {})
            
            # Distancia en metros, convertir a km
            distance_m = summary.get('Distance', 0)
            distance_km = distance_m / 1000
            
            # Duración en segundos, convertir a minutos
            duration_s = summary.get('Duration', 0)
            duration_minutes = duration_s / 60
            
            return {
                "success": True,
                "distance_km": round(distance_km, 2),
                "duration_minutes": round(duration_minutes, 1),
                "distance_meters": distance_m,
                "duration_seconds": duration_s,
                "origin": origin,
                "destination": destination
            }
        else:
            # Fallback a Haversine si AWS falla
            distance_km = haversine_distance(origin, destination)
            # Estimar tiempo: 40 km/h promedio
            duration_minutes = (distance_km / 40) * 60
            
            return {
                "success": True,
                "distance_km": round(distance_km, 2),
                "duration_minutes": round(duration_minutes, 1),
                "method": "haversine_fallback",
                "origin": origin,
                "destination": destination
            }
            
    except Exception as e:
        logger.error(f"Error calculating route: {e}")
        # Fallback a Haversine
        distance_km = haversine_distance(origin, destination)
        duration_minutes = (distance_km / 40) * 60
        
        return {
            "success": True,
            "distance_km": round(distance_km, 2),
            "duration_minutes": round(duration_minutes, 1),
            "method": "haversine_fallback",
            "error": str(e),
            "origin": origin,
            "destination": destination
        }


def haversine_distance(coord1: List[float], coord2: List[float]) -> float:
    """
    Calcula la distancia en kilómetros entre dos coordenadas usando Haversine
    coord1, coord2: [longitude, latitude]
    """
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    
    R = 6371  # Radio de la Tierra en km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance


def get_truck_positions() -> Dict[int, Dict]:
    """
    Obtiene las posiciones actuales de todos los camiones
    Incluye información de carga y entregas
    """
    # Intentar usar el simulador primero
    if SIMULATOR_AVAILABLE and simulator.running:
        try:
            return simulator.get_current_positions()
        except Exception as e:
            logger.warning(f"Simulator error, falling back to file: {e}")
    
    # Fallback: leer del archivo
    try:
        route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
        if not route_files:
            return {}
        
        latest_route = route_files[0]
        with open(latest_route, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        truck_positions = {}
        for route in route_data.get('routes', []):
            truck_id = route['truck_id']
            stops = route.get('stops', [])
            
            # Encontrar la ÚLTIMA parada completada
            current_position = None
            current_stop = 0
            
            # Recopilar entregas completadas y pendientes
            delivered_items = []
            pending_items = []
            total_delivered_value = 0.0
            total_pending_value = 0.0
            
            # Buscar de atrás hacia adelante para encontrar la última completada
            for stop in reversed(stops):
                if stop['status'] == 'completed':
                    current_position = [
                        stop['coordinates']['longitude'],
                        stop['coordinates']['latitude']
                    ]
                    current_stop = stop['stop_number']
                    break
            
            # Recopilar items entregados y pendientes
            for stop in stops:
                items = stop.get('items', [])
                value = stop.get('items_value_usd', 0.0)
                
                if stop['status'] == 'completed' and stop['stop_number'] > 0:  # Excluir depósito
                    delivered_items.extend([{
                        'item': item,
                        'location': stop['location'],
                        'stop_number': stop['stop_number']
                    } for item in items])
                    total_delivered_value += value
                elif stop['status'] == 'pending' and stop['stop_number'] > 0:
                    pending_items.extend([{
                        'item': item,
                        'location': stop['location'],
                        'stop_number': stop['stop_number']
                    } for item in items])
                    total_pending_value += value
            
            # Si no hay ninguna completada, usar la primera (depósito)
            if current_position is None and stops:
                first_stop = stops[0]
                current_position = [
                    first_stop['coordinates']['longitude'],
                    first_stop['coordinates']['latitude']
                ]
                current_stop = 0
            
            truck_positions[truck_id] = {
                'position': current_position,
                'current_stop': current_stop,
                'status': route['status'],
                'truck_name': route['truck_name'],
                'delivered_items': delivered_items,
                'pending_items': pending_items,
                'total_delivered_value': round(total_delivered_value, 2),
                'total_pending_value': round(total_pending_value, 2),
                'total_stops': len([s for s in stops if s['stop_number'] > 0]),
                'completed_stops': len([s for s in stops if s['status'] == 'completed' and s['stop_number'] > 0])
            }
            
            # Agregar información de incidente si existe
            if 'incident' in route:
                truck_positions[truck_id]['incident'] = route['incident']
        
        return truck_positions
    except Exception as e:
        logger.error(f"Error getting truck positions: {e}")
        return {}


def get_distance_to_coordinates(truck_id: int, target_coords: List[float]) -> Dict:
    """
    Calcula la distancia de un camión a coordenadas específicas
    """
    truck_positions = get_truck_positions()
    
    if truck_id not in truck_positions:
        return {"error": f"Truck {truck_id} not found"}
    
    truck_pos = truck_positions[truck_id]['position']
    if not truck_pos:
        return {"error": f"Truck {truck_id} position unknown"}
    
    distance_km = haversine_distance(truck_pos, target_coords)
    
    return {
        "truck_id": truck_id,
        "truck_name": truck_positions[truck_id]['truck_name'],
        "current_position": truck_pos,
        "target_coordinates": target_coords,
        "distance_km": round(distance_km, 2),
        "current_stop": truck_positions[truck_id]['current_stop']
    }


def get_distance_to_depot(truck_id: int, depot_coords: List[float] = None) -> Dict:
    """
    Calcula la distancia de un camión al depósito
    """
    if depot_coords is None:
        depot_coords = [-99.1908, 19.4336]
    
    return get_distance_to_coordinates(truck_id, depot_coords)


def optimize_route_with_georoutes(origin: List[float], destination: List[float], 
                                   waypoints: List[List[float]]) -> Dict:
    """
    Optimiza una ruta usando AWS geo-routes
    """
    try:
        response = geo_routes_client.optimize_waypoints(
            Origin=origin,
            Destination=destination,
            Waypoints=[{"Position": wp} for wp in waypoints],
            TravelMode='Car',
            OptimizeSequencingFor='FastestRoute'
        )
        return response
    except Exception as e:
        logger.error(f"Error optimizing route: {e}")
        return {"error": str(e)}


def get_current_route_plan() -> Dict:
    """
    Obtiene el plan de rutas más reciente
    """
    try:
        route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
        if not route_files:
            return {"error": "No route plans found"}
        
        latest_route = route_files[0]
        with open(latest_route, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        return {
            "filename": latest_route.name,
            "data": route_data
        }
    except Exception as e:
        logger.error(f"Error reading route plan: {e}")
        return {"error": str(e)}


def get_inventory_data() -> List[Dict]:
    """
    Lee el inventario del almacén
    """
    try:
        inventory_file = INVENTORY_DIR / "3_inventario_almacen.csv"
        if not inventory_file.exists():
            return []
        
        inventory = []
        with open(inventory_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Normalizar nombres de columnas
                inventory.append({
                    'sku': row.get('sku', ''),
                    'nombre_producto': row.get('nombre_producto', ''),
                    'categoria': row.get('categoria', ''),
                    'cantidad_disponible': row.get('cantidad_disponible_almacen', row.get('cantidad_disponible', 'N/A')),
                    'cantidad_total': row.get('cantidad_total', 'N/A'),
                    'cantidad_en_ruta': row.get('cantidad_en_ruta', 'N/A'),
                    'valor_unitario_usd': row.get('valor_unitario_usd', 'N/A'),
                    'prioridad': row.get('prioridad_negocio', 'N/A'),
                    'ubicacion': row.get('ubicacion_pasillo', 'N/A'),
                    'es_fragil': row.get('es_fragil', 'No')
                })
        
        return inventory
    except Exception as e:
        logger.error(f"Error reading inventory: {e}")
        return []


def generate_incident_report(truck_id: int, incident_type: str, 
                             description: str, location: List[float] = None) -> Dict:
    """
    Genera un reporte de incidente para un camión
    """
    try:
        truck_positions = get_truck_positions()
        route_plan = get_current_route_plan()
        
        if truck_id not in truck_positions:
            return {"error": f"Truck {truck_id} not found"}
        
        truck_info = truck_positions[truck_id]
        
        truck_route = None
        if "data" in route_plan:
            for route in route_plan["data"].get("routes", []):
                if route["truck_id"] == truck_id:
                    truck_route = route
                    break
        
        incident_location = location if location else truck_info['position']
        
        report = {
            "incident_id": f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}-T{truck_id}",
            "timestamp": datetime.now().isoformat(),
            "truck_id": truck_id,
            "truck_name": truck_info['truck_name'],
            "incident_type": incident_type,
            "description": description,
            "location": {
                "coordinates": incident_location,
                "current_stop": truck_info['current_stop']
            },
            "route_info": {
                "total_stops": len(truck_route['stops']) if truck_route else 0,
                "completed_stops": truck_info['current_stop'],
                "remaining_stops": (len(truck_route['stops']) - truck_info['current_stop'] - 1) if truck_route else 0
            },
            "status": "reported",
            "requires_attention": True
        }
        
        # Guardar el reporte
        reports_dir = DATA_DIR / "incident_reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"{report['incident_id']}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Incident report created: {report['incident_id']}")
        
        return report
    except Exception as e:
        logger.error(f"Error generating incident report: {e}")
        return {"error": str(e)}
