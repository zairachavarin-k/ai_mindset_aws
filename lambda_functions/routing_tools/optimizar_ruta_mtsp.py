"""
Lambda function: optimizar_ruta_mtsp
Optimiza rutas para múltiples camiones usando Ant Colony Optimization (ACO)
"""
import json
import numpy as np
from typing import List, Dict, Tuple
import os


def haversine_distance(coord1, coord2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in km
    lat1, lon1 = np.radians(coord1[1]), np.radians(coord1[0])
    lat2, lon2 = np.radians(coord2[1]), np.radians(coord2[0])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


class MTSPAntColony:
    """
    Multi-Traveling Salesman Problem solver using Ant Colony Optimization
    Optimizado para SmartSupply - considera múltiples camiones
    """
    
    def __init__(self, num_trucks, distance_matrix, depot_index=0):
        self.num_trucks = num_trucks
        self.distance_matrix = np.array(distance_matrix)
        self.depot_index = depot_index
        self.num_locations = len(distance_matrix)
        self.num_destinations = self.num_locations - 1
        
        # ACO parameters (optimizados para convergencia rápida)
        self.num_ants = 50  # Reducido para Lambda
        self.num_iterations = 50  # Reducido para Lambda
        self.alpha = 1.0  # Pheromone importance
        self.beta = 3.0   # Distance importance
        self.evaporation_rate = 0.1
        self.pheromone_deposit = 100.0
        self.initial_pheromone = 1.0
        
        # Initialize pheromone matrix
        self.pheromones = np.ones((self.num_locations, self.num_locations)) * self.initial_pheromone
        
        # Heuristic information (inverse of distance)
        self.heuristic = np.zeros_like(self.distance_matrix)
        for i in range(self.num_locations):
            for j in range(self.num_locations):
                if i != j and self.distance_matrix[i][j] > 0:
                    self.heuristic[i][j] = 1.0 / self.distance_matrix[i][j]
    
    def construct_solution(self):
        """Construct a solution using ant colony approach"""
        unvisited = set(range(1, self.num_locations))
        routes = [[] for _ in range(self.num_trucks)]
        current_positions = [self.depot_index] * self.num_trucks
        
        # Distribute destinations among trucks
        while unvisited:
            for truck_id in range(self.num_trucks):
                if not unvisited:
                    break
                
                current = current_positions[truck_id]
                
                # Calculate probabilities for next destination
                probabilities = []
                destinations = list(unvisited)
                
                for dest in destinations:
                    pheromone = self.pheromones[current][dest] ** self.alpha
                    heuristic = self.heuristic[current][dest] ** self.beta
                    probabilities.append(pheromone * heuristic)
                
                # Normalize probabilities
                total = sum(probabilities)
                if total > 0:
                    probabilities = [p / total for p in probabilities]
                else:
                    probabilities = [1.0 / len(destinations)] * len(destinations)
                
                # Select next destination
                next_dest = np.random.choice(destinations, p=probabilities)
                
                routes[truck_id].append(next_dest)
                unvisited.remove(next_dest)
                current_positions[truck_id] = next_dest
        
        # Convert to full routes (depot -> destinations -> depot)
        full_routes = []
        for route in routes:
            if route:
                full_routes.append([self.depot_index] + route + [self.depot_index])
            else:
                full_routes.append([self.depot_index, self.depot_index])
        
        return full_routes
    
    def calculate_route_distance(self, route):
        """Calculate total distance for a single route"""
        distance = 0
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i + 1]]
        return distance
    
    def calculate_total_distance(self, routes):
        """Calculate total distance for all routes"""
        return sum(self.calculate_route_distance(route) for route in routes)
    
    def update_pheromones(self, all_routes, all_distances):
        """Update pheromone levels based on ant solutions"""
        # Evaporation
        self.pheromones *= (1 - self.evaporation_rate)
        
        # Add new pheromones
        for routes, total_distance in zip(all_routes, all_distances):
            if total_distance > 0:
                deposit = self.pheromone_deposit / total_distance
                
                for route in routes:
                    for i in range(len(route) - 1):
                        self.pheromones[route[i]][route[i + 1]] += deposit
                        self.pheromones[route[i + 1]][route[i]] += deposit
    
    def local_search_2opt(self, route):
        """Apply 2-opt local search to improve a single route"""
        if len(route) <= 3:
            return route
        
        improved = True
        best_route = route[:]
        best_distance = self.calculate_route_distance(best_route)
        
        while improved:
            improved = False
            for i in range(1, len(best_route) - 2):
                for j in range(i + 1, len(best_route) - 1):
                    new_route = best_route[:i] + best_route[i:j+1][::-1] + best_route[j+1:]
                    new_distance = self.calculate_route_distance(new_route)
                    
                    if new_distance < best_distance:
                        best_route = new_route
                        best_distance = new_distance
                        improved = True
                        break
                if improved:
                    break
        
        return best_route
    
    def optimize(self):
        """Run the ant colony optimization algorithm"""
        best_routes = None
        best_distance = float('inf')
        
        for iteration in range(self.num_iterations):
            all_routes = []
            all_distances = []
            
            for ant in range(self.num_ants):
                routes = self.construct_solution()
                routes = [self.local_search_2opt(route) for route in routes]
                total_distance = self.calculate_total_distance(routes)
                
                all_routes.append(routes)
                all_distances.append(total_distance)
                
                if total_distance < best_distance:
                    best_distance = total_distance
                    best_routes = routes
            
            self.update_pheromones(all_routes, all_distances)
        
        return best_routes, best_distance


def lambda_handler(event, context):
    """
    Lambda handler para optimización de rutas mTSP
    
    Input:
    {
        "num_trucks": 3,
        "paradas": [
            {"stop_id": "STOP-1", "lat": 19.4345, "lon": -99.1410},
            {"stop_id": "STOP-2", "lat": 19.4456, "lon": -99.1523}
        ],
        "origen": {"lat": 19.4384, "lon": -99.1569}
    }
    
    Output:
    {
        "status": "success",
        "rutas_optimizadas": [...],
        "distancia_total_km": 45.3,
        "distancias_por_camion": [15.2, 18.1, 12.0],
        "mejora_porcentaje": 18.5
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Extraer parámetros
        num_trucks = event.get('num_trucks', 1)
        paradas = event.get('paradas', [])
        origen = event.get('origen', {})
        
        if not paradas:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'No se proporcionaron paradas',
                    'message': 'El campo paradas es requerido'
                })
            }
        
        if not origen:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'No se proporcionó origen',
                    'message': 'El campo origen es requerido'
                })
            }
        
        # Construir lista de coordenadas
        # Soportar ambos formatos: lat/lon y latitud/longitud
        depot_coords = [
            origen.get('lon', origen.get('longitud')), 
            origen.get('lat', origen.get('latitud'))
        ]
        destination_coords = [
            [
                p.get('lon', p.get('longitud')), 
                p.get('lat', p.get('latitud'))
            ] 
            for p in paradas
        ]
        
        # Construir matriz de distancias
        all_locations = [depot_coords] + destination_coords
        n = len(all_locations)
        distance_matrix = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distance_matrix[i][j] = haversine_distance(all_locations[i], all_locations[j])
        
        print(f"Optimizando rutas para {num_trucks} camiones y {len(paradas)} paradas...")
        
        # Resolver mTSP usando ACO
        aco = MTSPAntColony(num_trucks, distance_matrix, depot_index=0)
        best_routes, best_distance = aco.optimize()
        
        # Calcular distancias individuales
        truck_distances = [aco.calculate_route_distance(route) for route in best_routes]
        
        # Calcular distancia de ruta simple (sin optimizar) para comparación
        simple_distance = sum(distance_matrix[0][i] for i in range(1, n))
        simple_distance += distance_matrix[n-1][0]  # Regreso al depot
        
        mejora_porcentaje = ((simple_distance - best_distance) / simple_distance) * 100 if simple_distance > 0 else 0
        
        # Construir rutas con información de paradas
        rutas_detalladas = []
        for truck_idx, route in enumerate(best_routes):
            if len(route) <= 2:  # Solo depot ida y vuelta
                continue
            
            paradas_ruta = []
            for i, location_idx in enumerate(route):
                if location_idx == 0:  # Depot
                    paradas_ruta.append({
                        'orden': i,
                        'tipo': 'depot',
                        'ubicacion': origen
                    })
                else:  # Parada
                    parada_original = paradas[location_idx - 1]
                    paradas_ruta.append({
                        'orden': i,
                        'tipo': 'parada',
                        'stop_id': parada_original.get('stop_id'),
                        'ubicacion': {
                            'lat': parada_original.get('lat', parada_original.get('latitud')),
                            'lon': parada_original.get('lon', parada_original.get('longitud'))
                        },
                        'cliente': parada_original.get('cliente'),
                        'distancia_desde_anterior_km': distance_matrix[route[i-1]][location_idx] if i > 0 else 0
                    })
            
            rutas_detalladas.append({
                'truck_id': truck_idx + 1,
                'paradas': paradas_ruta,
                'distancia_total_km': float(truck_distances[truck_idx]),
                'num_paradas': len([p for p in paradas_ruta if p['tipo'] == 'parada'])
            })
        
        result = {
            'status': 'success',
            'algoritmo': 'Ant Colony Optimization (mTSP)',
            'num_trucks': num_trucks,
            'num_paradas': len(paradas),
            'rutas_optimizadas': rutas_detalladas,
            'metricas': {
                'distancia_total_km': float(best_distance),
                'distancias_por_camion': [float(d) for d in truck_distances],
                'distancia_promedio_por_camion': float(np.mean(truck_distances)),
                'distancia_maxima_camion': float(max(truck_distances)),
                'distancia_minima_camion': float(min(truck_distances)),
                'mejora_vs_ruta_simple_porcentaje': float(mejora_porcentaje),
                'trucks_utilizados': len(rutas_detalladas)
            }
        }
        
        print(f"Optimización completada: {best_distance:.2f} km total, mejora: {mejora_porcentaje:.1f}%")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error en optimización: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error en optimización de rutas',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    # Evento de prueba
    test_event = {
        "num_trucks": 3,
        "paradas": [
            {"stop_id": "STOP-1", "lat": 19.4326, "lon": -99.1332, "cliente": "Cliente 1"},
            {"stop_id": "STOP-2", "lat": 19.4141, "lon": -99.1696, "cliente": "Cliente 2"},
            {"stop_id": "STOP-3", "lat": 19.3629, "lon": -99.2736, "cliente": "Cliente 3"},
            {"stop_id": "STOP-4", "lat": 19.3601, "lon": -99.1774, "cliente": "Cliente 4"},
            {"stop_id": "STOP-5", "lat": 19.3894, "lon": -99.1866, "cliente": "Cliente 5"},
            {"stop_id": "STOP-6", "lat": 19.4034, "lon": -99.2045, "cliente": "Cliente 6"},
            {"stop_id": "STOP-7", "lat": 19.4000, "lon": -99.1245, "cliente": "Cliente 7"},
            {"stop_id": "STOP-8", "lat": 19.4361, "lon": -99.0745, "cliente": "Cliente 8"}
        ],
        "origen": {"lat": 19.4336, "lon": -99.1908}
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
