"""
Lambda function: calcular_distancia_matriz
Calcula matriz de distancias entre múltiples puntos
"""
import json
import numpy as np


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


def lambda_handler(event, context):
    """
    Calcula matriz de distancias y tiempos entre puntos
    
    Input:
    {
        "puntos": [
            {"id": "depot", "lat": 19.4384, "lon": -99.1569},
            {"id": "STOP-1", "lat": 19.4345, "lon": -99.1410},
            {"id": "STOP-2", "lat": 19.4456, "lon": -99.1523}
        ]
    }
    
    Output:
    {
        "matriz_distancias": [[0, 1.5, 2.3], [1.5, 0, 1.8], [2.3, 1.8, 0]],
        "matriz_tiempos": [[0, 5, 8], [5, 0, 6], [8, 6, 0]]
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        puntos = event.get('puntos', [])
        
        if not puntos or len(puntos) < 2:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Se requieren al menos 2 puntos'
                })
            }
        
        n = len(puntos)
        
        # Construir matriz de distancias
        matriz_distancias = [[0.0] * n for _ in range(n)]
        matriz_tiempos = [[0.0] * n for _ in range(n)]
        
        # Velocidad promedio en ciudad (km/h)
        velocidad_promedio = 30.0
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    # Soportar ambos formatos: lat/lon y latitud/longitud
                    coord1 = [
                        puntos[i].get('lon', puntos[i].get('longitud')), 
                        puntos[i].get('lat', puntos[i].get('latitud'))
                    ]
                    coord2 = [
                        puntos[j].get('lon', puntos[j].get('longitud')), 
                        puntos[j].get('lat', puntos[j].get('latitud'))
                    ]
                    
                    distancia_km = haversine_distance(coord1, coord2)
                    tiempo_minutos = (distancia_km / velocidad_promedio) * 60
                    
                    matriz_distancias[i][j] = round(distancia_km, 2)
                    matriz_tiempos[i][j] = round(tiempo_minutos, 1)
        
        result = {
            'matriz_distancias': matriz_distancias,
            'matriz_tiempos': matriz_tiempos,
            'num_puntos': n,
            'puntos': [p['id'] for p in puntos],
            'velocidad_promedio_kmh': velocidad_promedio,
            'nota': 'Tiempos base - aplicar factores de tráfico y clima'
        }
        
        print(f"Matriz calculada para {n} puntos")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error calculando matriz: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error calculando matriz de distancias',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "puntos": [
            {"id": "depot", "lat": 19.4384, "lon": -99.1569},
            {"id": "STOP-1", "lat": 19.4345, "lon": -99.1410},
            {"id": "STOP-2", "lat": 19.4456, "lon": -99.1523},
            {"id": "STOP-3", "lat": 19.4200, "lon": -99.1650}
        ]
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
