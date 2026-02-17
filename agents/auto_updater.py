"""
Auto-actualizador de posiciones de camiones
Simula progreso automático basado en el tiempo transcurrido
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")


def update_truck_positions_auto():
    """
    Actualiza automáticamente las posiciones de los camiones
    basándose en el tiempo transcurrido desde la última actualización
    """
    try:
        route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
        if not route_files:
            return False
        
        latest_route = route_files[0]
        with open(latest_route, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        now = datetime.now()
        updated = False
        
        for route in route_data.get('routes', []):
            stops = route.get('stops', [])
            
            # Encontrar la última parada completada
            last_completed_idx = -1
            for idx, stop in enumerate(stops):
                if stop['status'] == 'completed':
                    last_completed_idx = idx
            
            # Si hay paradas pendientes
            if last_completed_idx < len(stops) - 1:
                next_stop_idx = last_completed_idx + 1
                next_stop = stops[next_stop_idx]
                
                # Verificar si es tiempo de completar la siguiente parada
                if last_completed_idx >= 0:
                    last_stop = stops[last_completed_idx]
                    last_delivery_time = last_stop.get('actual_delivery_time')
                    
                    if last_delivery_time:
                        last_time = datetime.fromisoformat(last_delivery_time)
                    else:
                        # Si no hay tiempo de entrega, usar el tiempo de salida
                        last_time = datetime.fromisoformat(last_stop.get('departure_time', now.isoformat()))
                    
                    # Calcular tiempo esperado para llegar a la siguiente parada
                    # Usar el tiempo de servicio + tiempo de viaje estimado
                    expected_arrival = datetime.fromisoformat(next_stop['arrival_time'])
                    
                    # Si ya pasó el tiempo de llegada esperado, marcar como completada
                    if now >= expected_arrival:
                        next_stop['status'] = 'completed'
                        next_stop['actual_delivery_time'] = now.isoformat()
                        updated = True
                        logger.info(f"✓ Auto-completed: {route['truck_name']} - Stop {next_stop['stop_number']} ({next_stop['location']})")
        
        # Guardar cambios si hubo actualizaciones
        if updated:
            with open(latest_route, 'w', encoding='utf-8') as f:
                json.dump(route_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Route data updated: {latest_route.name}")
        
        return updated
        
    except Exception as e:
        logger.error(f"Error auto-updating positions: {e}")
        return False


def simulate_progress_since_last_update():
    """
    Simula el progreso de los camiones desde la última actualización
    Marca entregas como completadas si ya pasó el tiempo esperado
    """
    try:
        route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
        if not route_files:
            return False
        
        latest_route = route_files[0]
        with open(latest_route, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        now = datetime.now()
        updated = False
        
        for route in route_data.get('routes', []):
            stops = route.get('stops', [])
            
            for stop in stops:
                # Si la parada está pendiente y ya pasó su hora de llegada
                if stop['status'] == 'pending' and stop['stop_number'] > 0:
                    arrival_time = datetime.fromisoformat(stop['arrival_time'])
                    
                    # Si ya pasó el tiempo de llegada, marcar como completada
                    if now >= arrival_time:
                        stop['status'] = 'completed'
                        stop['actual_delivery_time'] = arrival_time.isoformat()
                        updated = True
                        logger.info(f"✓ Simulated delivery: {route['truck_name']} - {stop['location']}")
        
        # Guardar cambios
        if updated:
            with open(latest_route, 'w', encoding='utf-8') as f:
                json.dump(route_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Simulated progress updated")
        
        return updated
        
    except Exception as e:
        logger.error(f"Error simulating progress: {e}")
        return False
