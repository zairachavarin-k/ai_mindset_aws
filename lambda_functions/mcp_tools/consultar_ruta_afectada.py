"""
Lambda MCP Tool: consultar_ruta_afectada
Consulta DynamoDB para obtener ruta completa del camión afectado
Requisitos: 2.3
"""
import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('RUTAS_TABLE_NAME', 'rutas_entregas')
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
    Consulta la ruta completa del camión afectado
    
    Args:
        event: {
            "truck_id": str,
            "fecha_ruta": str (opcional, default: fecha más reciente)
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "truck_id": str,
            "conductor": str,
            "paradas": [{"stop_id", "cliente", "items_a_entregar", "estado"}],
            "fecha_ruta": str,
            "estado_ruta": str
        }
    }
    """
    try:
        # Extraer parámetros
        truck_id = event.get('truck_id')
        fecha_ruta = event.get('fecha_ruta')
        
        if not truck_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'truck_id es requerido'
                })
            }
        
        # Si no se proporciona fecha, buscar la ruta más reciente
        if not fecha_ruta:
            response = table.query(
                KeyConditionExpression='truck_id = :truck_id',
                ExpressionAttributeValues={
                    ':truck_id': truck_id
                },
                ScanIndexForward=False,  # Orden descendente por fecha
                Limit=1
            )
        else:
            response = table.get_item(
                Key={
                    'truck_id': truck_id,
                    'fecha_ruta': fecha_ruta
                }
            )
            response = {'Items': [response.get('Item')]} if 'Item' in response else {'Items': []}
        
        if not response.get('Items'):
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'No se encontró ruta para truck_id={truck_id}'
                })
            }
        
        ruta = response['Items'][0]
        
        # Convertir Decimal a float para serialización
        ruta = decimal_to_float(ruta)
        
        # Estructurar respuesta
        resultado = {
            'truck_id': ruta.get('truck_id'),
            'conductor': ruta.get('conductor_asignado'),
            'paradas': ruta.get('paradas', []),
            'fecha_ruta': ruta.get('fecha_ruta'),
            'estado_ruta': ruta.get('estado_ruta', 'Activa')
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(resultado)
        }
        
    except Exception as e:
        print(f"Error consultando ruta: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
