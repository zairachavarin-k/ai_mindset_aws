"""
Lambda MCP Tool: calcular_distancia
Usa Amazon Location Service para calcular distancia entre dos puntos
Requisitos: 2.7
"""
import json
import os
import boto3
from typing import Dict, Any
from math import radians, sin, cos, sqrt, atan2

location_client = boto3.client('location')
calculator_name = os.environ.get('ROUTE_CALCULATOR_NAME', 'smart-supply-route-calculator')


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula distancia en km usando fórmula de Haversine (fallback si Location Service falla)
    
    Args:
        lat1, lon1: Coordenadas del punto 1
        lat2, lon2: Coordenadas del punto 2
    
    Returns:
        Distancia en kilómetros
    """
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Calcula distancia entre dos puntos usando Amazon Location Service
    
    Args:
        event: {
            "origen": {"lat": float, "lon": float},
            "destino": {"lat": float, "lon": float}
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "distancia_km": float,
            "metodo": "location_service" | "haversine"
        }
    }
    """
    try:
        # Extraer parámetros
        origen = event.get('origen', {})
        destino = event.get('destino', {})
        
        if not origen or not destino:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'origen y destino son requeridos con formato {"lat": float, "lon": float}'
                })
            }
        
        # Soportar ambos formatos: lat/lon y latitud/longitud
        lat1 = origen.get('lat', origen.get('latitud'))
        lon1 = origen.get('lon', origen.get('longitud'))
        lat2 = destino.get('lat', destino.get('latitud'))
        lon2 = destino.get('lon', destino.get('longitud'))
        
        if None in [lat1, lon1, lat2, lon2]:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'lat y lon son requeridos en origen y destino'
                })
            }
        
        # Intentar usar Amazon Location Service
        try:
            response = location_client.calculate_route(
                CalculatorName=calculator_name,
                DeparturePosition=[lon1, lat1],  # Location Service usa [lon, lat]
                DestinationPosition=[lon2, lat2]
            )
            
            # Extraer distancia de la respuesta (en metros)
            distancia_metros = response['Summary']['Distance']
            distancia_km = distancia_metros / 1000
            metodo = 'location_service'
            
        except Exception as location_error:
            # Fallback a cálculo Haversine si Location Service falla
            print(f"Location Service falló, usando Haversine: {str(location_error)}")
            distancia_km = haversine_distance(lat1, lon1, lat2, lon2)
            metodo = 'haversine'
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'distancia_km': round(distancia_km, 2),
                'metodo': metodo
            })
        }
        
    except Exception as e:
        print(f"Error calculando distancia: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
