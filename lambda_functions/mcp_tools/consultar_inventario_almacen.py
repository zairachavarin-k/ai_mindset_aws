"""
Lambda MCP Tool: consultar_inventario_almacen
Consulta DynamoDB tabla inventario_almacen por SKUs
Requisitos: 2.3, 11.2
"""
import json
import os
import boto3
from decimal import Decimal
from typing import Dict, Any, List

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('INVENTARIO_TABLE_NAME', 'inventario_almacen')
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
    Consulta inventario del almacén por SKUs
    
    Args:
        event: {
            "skus": List[str] (opcional, si no se proporciona retorna todo el inventario)
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "productos": [{
                "sku": str,
                "nombre_producto": str,
                "categoria": str,
                "es_fragil": bool,
                "cantidad_disponible_almacen": int,
                "cantidad_en_ruta": int,
                "prioridad_negocio": str,
                "ubicacion_pasillo": str
            }]
        }
    }
    """
    try:
        # Extraer parámetros
        skus = event.get('skus', [])
        
        productos = []
        
        if skus:
            # Consultar SKUs específicos usando batch_get_item
            # DynamoDB batch_get_item tiene límite de 100 items
            for i in range(0, len(skus), 100):
                batch_skus = skus[i:i+100]
                keys = [{'sku': sku} for sku in batch_skus]
                
                response = dynamodb.batch_get_item(
                    RequestItems={
                        table_name: {
                            'Keys': keys
                        }
                    }
                )
                
                productos.extend(response.get('Responses', {}).get(table_name, []))
        else:
            # Si no se proporcionan SKUs, escanear toda la tabla
            response = table.scan()
            productos = response.get('Items', [])
            
            # Continuar escaneando si hay más páginas
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                productos.extend(response.get('Items', []))
        
        # Convertir Decimal a float y estructurar respuesta
        productos_info = []
        for producto in productos:
            producto = decimal_to_float(producto)
            
            producto_info = {
                'sku': producto.get('sku'),
                'nombre_producto': producto.get('nombre_producto'),
                'categoria': producto.get('categoria'),
                'es_fragil': producto.get('es_fragil', False),
                'cantidad_disponible_almacen': producto.get('cantidad_disponible_almacen', 0),
                'cantidad_en_ruta': producto.get('cantidad_en_ruta', 0),
                'prioridad_negocio': producto.get('prioridad_negocio'),
                'ubicacion_pasillo': producto.get('ubicacion_pasillo')
            }
            
            productos_info.append(producto_info)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'productos': productos_info,
                'total': len(productos_info)
            })
        }
        
    except Exception as e:
        print(f"Error consultando inventario: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
