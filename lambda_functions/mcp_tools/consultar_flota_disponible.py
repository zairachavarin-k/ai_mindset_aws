"""
Lambda MCP Tool: consultar_flota_disponible
Consulta DynamoDB tabla flota_camiones y filtra por nivel de fatiga
Requisitos: 2.3, 3.3
"""
import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any, List

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('FLOTA_TABLE_NAME', 'flota_camiones')
table = dynamodb.Table(table_name)


def decimal_to_float(obj):
    """Convierte Decimal a float para serialización JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Consulta flota disponible excluyendo camiones con fatiga Alta
    
    Args:
        event: {
            "excluir_fatiga_alta": bool (opcional, default: True),
            "truck_id_excluir": str (opcional, excluir camión específico)
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "camiones_disponibles": [{
                "truck_id": str,
                "conductor": str,
                "capacidad_max_ton": float,
                "nivel_fatiga": str,
                "ubicacion_actual": {"lat": float, "lon": float},
                "placas": str
            }]
        }
    }
    """
    try:
        # Extraer parámetros
        excluir_fatiga_alta = event.get('excluir_fatiga_alta', True)
        truck_id_excluir = event.get('truck_id_excluir')
        
        # Escanear toda la tabla de flota
        response = table.scan()
        camiones = response.get('Items', [])
        
        # Continuar escaneando si hay más páginas
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            camiones.extend(response.get('Items', []))
        
        # Filtrar camiones
        camiones_disponibles = []
        for camion in camiones:
            # Excluir camión específico si se proporciona
            if truck_id_excluir and camion.get('truck_id') == truck_id_excluir:
                continue
            
            # Excluir camiones con fatiga Alta (Requisito 3.3)
            if excluir_fatiga_alta and camion.get('nivel_fatiga') == 'Alto':
                continue
            
            # Convertir Decimal a float
            camion = decimal_to_float(camion)
            
            # Estructurar datos del camión
            camion_info = {
                'truck_id': camion.get('truck_id'),
                'conductor': camion.get('conductor'),
                'capacidad_max_ton': camion.get('capacidad_max_ton'),
                'nivel_fatiga': camion.get('nivel_fatiga'),
                'ubicacion_actual': camion.get('ubicacion_actual', {}),
                'placas': camion.get('placas')
            }
            
            camiones_disponibles.append(camion_info)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'camiones_disponibles': camiones_disponibles,
                'total': len(camiones_disponibles)
            })
        }
        
    except Exception as e:
        print(f"Error consultando flota: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
