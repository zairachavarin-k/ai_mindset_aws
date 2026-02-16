"""
Lambda MCP Tool: registrar_incidencia
Escribe incidencia en S3 y DynamoDB, calcula tiempo_respuesta_segundos
Requisitos: 4.2, 8.2
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

bucket_name = os.environ.get('DATA_BUCKET_NAME', 'smart-supply-data')
table_name = os.environ.get('INCIDENCIAS_TABLE_NAME', 'incidencias')
table = dynamodb.Table(table_name)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Registra incidencia en S3 y DynamoDB con cálculo de tiempo de respuesta
    
    Args:
        event: {
            "incidente": {
                "incidente_id": str,
                "timestamp": str (ISO8601),
                "truck_id": str,
                "tipo_incidente": str,
                "nivel_gravedad": str,
                "ubicacion_gps": {"lat": float, "lon": float},
                "descripcion_evento": str,
                "inventario_afectado": [...],
                "plan_reasignacion": {...} (opcional),
                "timestamp_deteccion": str (ISO8601, opcional),
                "timestamp_resolucion": str (ISO8601, opcional)
            }
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "incidente_id": str,
            "s3_path": str,
            "dynamodb_written": bool,
            "tiempo_respuesta_segundos": float
        }
    }
    """
    try:
        # Extraer incidente
        incidente = event.get('incidente', {})
        
        if not incidente:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'incidente es requerido'
                })
            }
        
        incidente_id = incidente.get('incidente_id')
        if not incidente_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'incidente_id es requerido'
                })
            }
        
        # Calcular tiempo_respuesta_segundos (Requisito 8.2)
        timestamp_deteccion = incidente.get('timestamp_deteccion') or incidente.get('timestamp')
        timestamp_resolucion = incidente.get('timestamp_resolucion') or datetime.now().isoformat()
        
        if timestamp_deteccion:
            try:
                deteccion_dt = datetime.fromisoformat(timestamp_deteccion.replace('Z', '+00:00'))
                resolucion_dt = datetime.fromisoformat(timestamp_resolucion.replace('Z', '+00:00'))
                tiempo_respuesta_segundos = (resolucion_dt - deteccion_dt).total_seconds()
            except Exception as e:
                print(f"Error calculando tiempo de respuesta: {str(e)}")
                tiempo_respuesta_segundos = 0
        else:
            tiempo_respuesta_segundos = 0
        
        # Agregar tiempo_respuesta_segundos al incidente
        incidente['tiempo_respuesta_segundos'] = tiempo_respuesta_segundos
        
        # Agregar timestamp de registro si no existe
        if 'timestamp' not in incidente:
            incidente['timestamp'] = datetime.now().isoformat()
        
        # Agregar estado de resolución si no existe
        if 'estado_resolucion' not in incidente:
            incidente['estado_resolucion'] = 'Resuelto' if incidente.get('plan_reasignacion') else 'Pendiente'
        
        # Escribir a DynamoDB
        try:
            table.put_item(Item=incidente)
            dynamodb_written = True
        except Exception as dynamo_error:
            print(f"Error escribiendo a DynamoDB: {str(dynamo_error)}")
            dynamodb_written = False
        
        # Escribir a S3: s3://smart-supply-data/incidencias/{año}/{mes}/{incidente_id}.json
        timestamp_obj = datetime.fromisoformat(incidente['timestamp'].replace('Z', '+00:00'))
        año = timestamp_obj.strftime('%Y')
        mes = timestamp_obj.strftime('%m')
        
        s3_key = f"incidencias/{año}/{mes}/{incidente_id}.json"
        
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(incidente, indent=2, ensure_ascii=False),
                ContentType='application/json',
                Metadata={
                    'incidente_id': incidente_id,
                    'truck_id': incidente.get('truck_id', ''),
                    'tipo_incidente': incidente.get('tipo_incidente', ''),
                    'nivel_gravedad': incidente.get('nivel_gravedad', '')
                }
            )
            s3_path = f"s3://{bucket_name}/{s3_key}"
        except Exception as s3_error:
            print(f"Error escribiendo a S3: {str(s3_error)}")
            s3_path = None
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'incidente_id': incidente_id,
                's3_path': s3_path,
                'dynamodb_written': dynamodb_written,
                'tiempo_respuesta_segundos': tiempo_respuesta_segundos
            })
        }
        
    except Exception as e:
        print(f"Error registrando incidencia: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
