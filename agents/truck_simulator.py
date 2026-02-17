"""
Simulador de posiciones de camiones en tiempo real
Actualiza las posiciones basándose en las rutas planificadas
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import threading
import math

DATA_DIR = Path("data")


def interpolate_position(start: List[float], end: List[float], progress: float) -> List[float]:
    """
    Interpola entre dos posiciones geográficas
    
    Args:
        start: [lon, lat] inicial
        end: [lon, lat] final
        progress: 0.0 a 1.0 (porcentaje de progreso)
    
    Returns:
        [lon, lat] interpolada
    """
    lon = start[0] + (end[0] - start[0]) * progress
    lat = start[1] + (end[1] - start[1]) * progress
    return [lon, lat]


def calculate_distance(coord1: List[float], coord2: List[float]) -> float:
    """Calcula distancia en km usando Haversine"""
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    
    R = 6371  # Radio de la Tierra en km
    
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance


class TruckSimulator:
    """Simula el movimiento de camiones en tiempo real"""
    
    def __init__(self, speed_kmh: float = 40.0, update_interval_seconds: float = 5.0):
        """
        Args:
            speed_kmh: Velocidad promedio de los camiones en km/h
            update_interval_seconds: Intervalo de actualización en segundos
        """
        self.speed_kmh = speed_kmh
        self.update_interval = update_interval_seconds
        self.running = False
        self.thread = None
        self.current_positions = {}
        self.route_data = None
        self.last_update = None
        
    def load_latest_route(self) -> bool:
        """Carga el plan de rutas más reciente"""
        try:
            route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
            if not route_files:
                print("No route plans found")
                return False
            
            latest_route = route_files[0]
            with open(latest_route, 'r', encoding='utf-8') as f:
                self.route_data = json.load(f)
            
            print(f"Loaded route plan: {latest_route.name}")
            
            # Inicializar posiciones actuales
            for route in self.route_data.get('routes', []):
                truck_id = route['truck_id']
                stops = route.get('stops', [])
                
                # Encontrar la parada actual (última completada o primera pendiente)
                current_stop_idx = 0
                for idx, stop in enumerate(stops):
                    if stop['status'] == 'completed':
                        current_stop_idx = idx
                    else:
                        break
                
                # Si todas están completadas, el camión está en la última parada
                if current_stop_idx >= len(stops) - 1:
                    current_stop_idx = len(stops) - 1
                
                current_stop = stops[current_stop_idx]
                next_stop = stops[current_stop_idx + 1] if current_stop_idx < len(stops) - 1 else None
                
                self.current_positions[truck_id] = {
                    'truck_name': route['truck_name'],
                    'position': [
                        current_stop['coordinates']['longitude'],
                        current_stop['coordinates']['latitude']
                    ],
                    'current_stop_idx': current_stop_idx,
                    'next_stop_idx': current_stop_idx + 1 if next_stop else current_stop_idx,
                    'progress_to_next': 0.0,  # 0.0 a 1.0
                    'status': route['status'],
                    'last_update': datetime.now().isoformat()
                }
            
            self.last_update = datetime.now()
            return True
            
        except Exception as e:
            print(f"Error loading route: {e}")
            return False
    
    def update_positions(self):
        """Actualiza las posiciones de todos los camiones"""
        if not self.route_data:
            return
        
        now = datetime.now()
        time_delta = (now - self.last_update).total_seconds() / 3600  # horas
        distance_traveled = self.speed_kmh * time_delta  # km
        
        for truck_id, pos_data in self.current_positions.items():
            # Encontrar la ruta del camión
            route = next((r for r in self.route_data['routes'] if r['truck_id'] == truck_id), None)
            if not route:
                continue
            
            stops = route['stops']
            current_idx = pos_data['current_stop_idx']
            next_idx = pos_data['next_stop_idx']
            
            # Si ya llegó al final, no mover
            if current_idx >= len(stops) - 1:
                pos_data['status'] = 'completed'
                continue
            
            # Obtener paradas actual y siguiente
            current_stop = stops[current_idx]
            next_stop = stops[next_idx]
            
            current_coords = [
                current_stop['coordinates']['longitude'],
                current_stop['coordinates']['latitude']
            ]
            next_coords = [
                next_stop['coordinates']['longitude'],
                next_stop['coordinates']['latitude']
            ]
            
            # Calcular distancia entre paradas
            segment_distance = calculate_distance(current_coords, next_coords)
            
            # Actualizar progreso
            if segment_distance > 0:
                progress_increment = distance_traveled / segment_distance
                pos_data['progress_to_next'] += progress_increment
                
                # Si llegó a la siguiente parada
                if pos_data['progress_to_next'] >= 1.0:
                    # Marcar parada como completada
                    next_stop['status'] = 'completed'
                    next_stop['actual_delivery_time'] = now.isoformat()
                    
                    # Avanzar a la siguiente parada
                    pos_data['current_stop_idx'] = next_idx
                    pos_data['next_stop_idx'] = next_idx + 1 if next_idx < len(stops) - 1 else next_idx
                    pos_data['progress_to_next'] = 0.0
                    pos_data['position'] = next_coords
                    
                    print(f"✓ {pos_data['truck_name']} llegó a {next_stop['location']}")
                else:
                    # Interpolar posición
                    pos_data['position'] = interpolate_position(
                        current_coords,
                        next_coords,
                        pos_data['progress_to_next']
                    )
            
            pos_data['last_update'] = now.isoformat()
        
        self.last_update = now
        
        # Guardar cambios en el archivo
        self.save_route_data()
    
    def save_route_data(self):
        """Guarda los cambios en el archivo de rutas"""
        try:
            route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
            if route_files:
                latest_route = route_files[0]
                with open(latest_route, 'w', encoding='utf-8') as f:
                    json.dump(self.route_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving route data: {e}")
    
    def get_current_positions(self) -> Dict:
        """Obtiene las posiciones actuales de todos los camiones con información completa"""
        positions = {}
        
        for truck_id, data in self.current_positions.items():
            # Encontrar la ruta del camión
            route = next((r for r in self.route_data['routes'] if r['truck_id'] == truck_id), None)
            if not route:
                continue
            
            stops = route['stops']
            current_idx = data['current_stop_idx']
            
            # Recopilar entregas completadas y pendientes
            delivered_items = []
            pending_items = []
            total_delivered_value = 0.0
            total_pending_value = 0.0
            
            for stop in stops:
                items = stop.get('items', [])
                value = stop.get('items_value_usd', 0.0)
                
                if stop['status'] == 'completed' and stop['stop_number'] > 0:
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
            
            positions[truck_id] = {
                'truck_name': data['truck_name'],
                'position': data['position'],
                'current_stop': data['current_stop_idx'],
                'status': data['status'],
                'last_update': data['last_update'],
                'progress_to_next': round(data['progress_to_next'] * 100, 1),
                'delivered_items': delivered_items,
                'pending_items': pending_items,
                'total_delivered_value': round(total_delivered_value, 2),
                'total_pending_value': round(total_pending_value, 2),
                'total_stops': len([s for s in stops if s['stop_number'] > 0]),
                'completed_stops': len([s for s in stops if s['status'] == 'completed' and s['stop_number'] > 0])
            }
        
        return positions
    
    def run(self):
        """Loop principal del simulador"""
        print("🚚 Truck Simulator started")
        
        while self.running:
            try:
                self.update_positions()
                time.sleep(self.update_interval)
            except Exception as e:
                print(f"Error in simulator loop: {e}")
                time.sleep(self.update_interval)
        
        print("🚚 Truck Simulator stopped")
    
    def start(self):
        """Inicia el simulador en un thread separado"""
        if self.running:
            print("Simulator already running")
            return False
        
        if not self.load_latest_route():
            print("Failed to load route data")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        print("✓ Simulator started successfully")
        return True
    
    def stop(self):
        """Detiene el simulador"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("✓ Simulator stopped")
    
    def reset(self):
        """Reinicia el simulador con la ruta más reciente"""
        was_running = self.running
        if was_running:
            self.stop()
        
        if self.load_latest_route():
            if was_running:
                self.start()
            return True
        return False
    
    def redirect_all_trucks(self, target_location: str = "depot", custom_coords: List[float] = None) -> Dict[str, Any]:
        """
        Redirige todos los camiones a una ubicación específica
        
        Args:
            target_location: "depot" para almacén, "custom" para coordenadas personalizadas
            custom_coords: [lon, lat] si target_location es "custom"
        
        Returns:
            Dict con información de la redirección
        """
        if not self.route_data:
            return {
                "success": False,
                "message": "No hay datos de ruta cargados"
            }
        
        # Definir coordenadas del depósito/almacén
        DEPOT_COORDS = [-99.1908, 19.4336]
        
        # Determinar coordenadas objetivo
        if target_location == "depot":
            target_coords = DEPOT_COORDS
            target_name = "Depósito/Almacén"
        elif target_location == "custom" and custom_coords:
            target_coords = custom_coords
            target_name = f"Ubicación personalizada [{custom_coords[0]}, {custom_coords[1]}]"
        else:
            return {
                "success": False,
                "message": "Ubicación objetivo no válida"
            }
        
        redirected_trucks = []
        
        # Modificar las rutas de todos los camiones
        for route in self.route_data.get('routes', []):
            truck_id = route['truck_id']
            truck_name = route['truck_name']
            
            # Obtener posición actual del camión
            if truck_id not in self.current_positions:
                continue
            
            current_pos = self.current_positions[truck_id]['position']
            current_stop_idx = self.current_positions[truck_id]['current_stop_idx']
            
            # Crear nueva parada de destino
            new_stop = {
                "stop_number": current_stop_idx + 1,
                "location": target_name,
                "coordinates": {
                    "longitude": target_coords[0],
                    "latitude": target_coords[1]
                },
                "arrival_time": datetime.now().isoformat(),
                "departure_time": datetime.now().isoformat(),
                "status": "pending",
                "items": [],
                "redirected": True  # Marca para identificar paradas redirigidas
            }
            
            # Reemplazar todas las paradas pendientes con la nueva parada
            stops = route.get('stops', [])
            
            # Mantener solo las paradas completadas y la actual
            completed_stops = [s for s in stops if s['stop_number'] <= current_stop_idx]
            
            # Agregar la nueva parada de redirección
            route['stops'] = completed_stops + [new_stop]
            
            # Actualizar el estado del camión
            route['status'] = 'redirected'
            route['redirect_info'] = {
                'timestamp': datetime.now().isoformat(),
                'target': target_name,
                'target_coords': target_coords,
                'reason': 'Manual redirect'
            }
            
            # Actualizar posición actual para apuntar a la nueva parada
            self.current_positions[truck_id]['next_stop_idx'] = current_stop_idx + 1
            self.current_positions[truck_id]['progress_to_next'] = 0.0
            self.current_positions[truck_id]['status'] = 'redirected'
            
            redirected_trucks.append({
                'truck_id': truck_id,
                'truck_name': truck_name,
                'current_position': current_pos,
                'new_destination': target_name,
                'new_coordinates': target_coords
            })
            
            print(f"✓ {truck_name} redirigido a {target_name}")
        
        # Guardar cambios en el archivo
        self.save_route_data()
        
        return {
            "success": True,
            "message": f"Todos los camiones redirigidos a {target_name}",
            "target_location": target_name,
            "target_coordinates": target_coords,
            "redirected_trucks": redirected_trucks,
            "total_redirected": len(redirected_trucks),
            "timestamp": datetime.now().isoformat()
        }
    
    def redirect_single_truck(self, truck_id: int, target_coords: List[float], target_name: str = "Nueva ubicación") -> Dict[str, Any]:
        """
        Redirige un camión específico a una ubicación
        
        Args:
            truck_id: ID del camión
            target_coords: [lon, lat] de destino
            target_name: Nombre descriptivo del destino
        
        Returns:
            Dict con información de la redirección
        """
        if not self.route_data:
            return {
                "success": False,
                "message": "No hay datos de ruta cargados"
            }
        
        if truck_id not in self.current_positions:
            return {
                "success": False,
                "message": f"Camión {truck_id} no encontrado"
            }
        
        # Encontrar la ruta del camión
        route = next((r for r in self.route_data['routes'] if r['truck_id'] == truck_id), None)
        if not route:
            return {
                "success": False,
                "message": f"Ruta del camión {truck_id} no encontrada"
            }
        
        truck_name = route['truck_name']
        current_pos = self.current_positions[truck_id]['position']
        current_stop_idx = self.current_positions[truck_id]['current_stop_idx']
        
        # Crear nueva parada de destino
        new_stop = {
            "stop_number": current_stop_idx + 1,
            "location": target_name,
            "coordinates": {
                "longitude": target_coords[0],
                "latitude": target_coords[1]
            },
            "arrival_time": datetime.now().isoformat(),
            "departure_time": datetime.now().isoformat(),
            "status": "pending",
            "items": [],
            "redirected": True
        }
        
        # Mantener solo las paradas completadas y la actual
        stops = route.get('stops', [])
        completed_stops = [s for s in stops if s['stop_number'] <= current_stop_idx]
        
        # Agregar la nueva parada
        route['stops'] = completed_stops + [new_stop]
        
        # Actualizar estado
        route['status'] = 'redirected'
        route['redirect_info'] = {
            'timestamp': datetime.now().isoformat(),
            'target': target_name,
            'target_coords': target_coords,
            'reason': 'Manual redirect'
        }
        
        # Actualizar posición
        self.current_positions[truck_id]['next_stop_idx'] = current_stop_idx + 1
        self.current_positions[truck_id]['progress_to_next'] = 0.0
        self.current_positions[truck_id]['status'] = 'redirected'
        
        # Guardar cambios
        self.save_route_data()
        
        print(f"✓ {truck_name} redirigido a {target_name}")
        
        return {
            "success": True,
            "message": f"{truck_name} redirigido a {target_name}",
            "truck_id": truck_id,
            "truck_name": truck_name,
            "current_position": current_pos,
            "new_destination": target_name,
            "new_coordinates": target_coords,
            "timestamp": datetime.now().isoformat()
        }


# Instancia global del simulador
simulator = TruckSimulator(speed_kmh=40.0, update_interval_seconds=5.0)
