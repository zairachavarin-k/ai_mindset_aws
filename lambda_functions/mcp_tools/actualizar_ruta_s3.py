"""
Lambda MCP Tool: actualizar_ruta_s3
Escribe JSON de ruta actualizada en S3
Requisitos: 12.3, 12.6
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any

s3_client = boto3.client('s3')
bucket_name = os.environ.get('DATA_BUCKET_NAME', 'smart-supply-data')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Escribe ruta actualizada en S3 con versionamiento
    
    Args:
        event: {
            "truck_id": str,
            "fecha": str (opcional, default: fecha actual YYYY-MM-DD),
            "ruta": {
                "truck_id": str,
                "fecha_ruta": str,
                "conductor_asignado": str,
                "estado_ruta": str,
                "paradas": [...]
            }
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "s3_path": str,
            "version_id": str,
            "timestamp": str
        }
    }
    """
    try:
        # Extraer parámetros
        truck_id = event.get('truck_id')
        fecha = event.get('fecha')
        ruta = event.get('ruta', {})
        
        if not truck_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'truck_id es requerido'
                })
            }
        
        if not ruta:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'ruta es requerida'
                })
            }
        
        # Si no se proporciona fecha, usar fecha actual
        if not fecha:
            fecha = datetime.now().strftime('%Y-%m-%d')
        
        # Construir path en S3: s3://smart-supply-data/rutas/{fecha}/{truck_id}.json
        s3_key = f"rutas/{fecha}/{truck_id}.json"
        
        # Agregar metadata de actualización
        ruta['ultima_actualizacion'] = datetime.now().isoformat()
        
        # Escribir a S3
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(ruta, indent=2, ensure_ascii=False),
            ContentType='application/json',
            Metadata={
                'truck_id': truck_id,
                'fecha': fecha,
                'updated_at': datetime.now().isoformat()
            }
        )
        
        # Obtener version_id (si versionamiento está habilitado)
        version_id = response.get('VersionId', 'N/A')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                's3_path': f"s3://{bucket_name}/{s3_key}",
                'version_id': version_id,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        print(f"Error escribiendo ruta a S3: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
