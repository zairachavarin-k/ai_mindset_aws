"""
Lambda function: optimizar_ruta_tsp
Aplica algoritmo TSP para optimizar orden de paradas (single truck)
"""
import json
import numpy as np
from typing import List, Tuple


def nearest_neighbor_tsp(distance_matrix, start_index=0):
    """
    Algoritmo Nearest Neighbor para TSP
    Simple y rápido para Lambda
    """
    n = len(distance_matrix)
    unvisited = set(range(n))
    unvisited.remove(start_index)
    
    current = start_index
    route = [current]
    total_distance = 0
    
    while unvisited:
        nearest = min(unvisited, key=lambda x: distance_matrix[current][x])
        total_distance += distance_matrix[current][nearest]
        current = nearest
        route.append(current)
        unvisited.remove(current)
    
    # Regresar al inicio
    total_distance += distance_matrix[current][start_index]
    route.append(start_index)
    
    return route, total_distance


def two_opt_improvement(route, distance_matrix):
    """
    Mejora la ruta usando 2-opt local search
    """
    improved = True
    best_route = route[:]
    best_distance = calculate_route_distance(best_route, distance_matrix)
    
    while improved:
        improved = False
        for i in range(1, len(best_route) - 2):
            for j in range(i + 1, len(best_route) - 1):
                # Invertir segmento entre i y j
                new_route = best_route[:i] + best_route[i:j+1][::-1] + best_route[j+1:]
                new_distance = calculate_route_distance(new_route, distance_matrix)
                
                if new_distance < best_distance:
                    best_route = new_route
                    best_distance = new_distance
                    improved = True
                    break
            if improved:
                break
    
    return best_route, best_distance


def calculate_route_distance(route, distance_matrix):
    """Calcula distancia total de una ruta"""
    distance = 0
    for i in range(len(route) - 1):
        distance += distance_matrix[route[i]][route[i + 1]]
    return distance


def lambda_handler(event, context):
    """
    Optimiza orden de paradas usando TSP
    
    Input:
    {
        "matriz_distancias": [[0, 1.5, 2.3], [1.5, 0, 1.8], [2.3, 1.8, 0]],
        "punto_inicio": 0,
        "restricciones": {
            "ventanas_entrega": [...],
            "prioridades": [...]
        }
    }
    
    Output:
    {
        "orden_optimo": [0, 2, 1, 0],
        "distancia_total": 4.1,
        "mejora_porcentaje": 15.3
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        matriz_distancias = event.get('matriz_distancias', [])
        punto_inicio = event.get('punto_inicio', 0)
        restricciones = event.get('restricciones', {})
        
        if not matriz_distancias:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'matriz_distancias es requerida'
                })
            }
        
        # Convertir a numpy array
        distance_matrix = np.array(matriz_distancias)
        n = len(distance_matrix)
        
        print(f"Optimizando TSP para {n} puntos, inicio: {punto_inicio}")
        
        # Calcular ruta simple (orden original)
        simple_route = list(range(n)) + [punto_inicio]
        simple_distance = calculate_route_distance(simple_route, distance_matrix)
        
        # Aplicar Nearest Neighbor
        nn_route, nn_distance = nearest_neighbor_tsp(distance_matrix, punto_inicio)
        
        # Mejorar con 2-opt
        optimized_route, optimized_distance = two_opt_improvement(nn_route, distance_matrix)
        
        # Calcular mejora
        mejora_porcentaje = ((simple_distance - optimized_distance) / simple_distance) * 100 if simple_distance > 0 else 0
        
        result = {
            'orden_optimo': optimized_route,
            'distancia_total': float(optimized_distance),
            'mejora_porcentaje': float(mejora_porcentaje),
            'distancia_original': float(simple_distance),
            'algoritmo': 'Nearest Neighbor + 2-opt',
            'num_puntos': n
        }
        
        print(f"TSP optimizado: {optimized_distance:.2f} km, mejora: {mejora_porcentaje:.1f}%")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error en TSP: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error optimizando ruta TSP',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "matriz_distancias": [
            [0, 1.5, 2.3, 3.1],
            [1.5, 0, 1.8, 2.5],
            [2.3, 1.8, 0, 1.2],
            [3.1, 2.5, 1.2, 0]
        ],
        "punto_inicio": 0
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
