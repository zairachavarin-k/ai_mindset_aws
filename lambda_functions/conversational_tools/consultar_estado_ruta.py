"""
Lambda function: consultar_estado_ruta_conversacional
Consulta el estado actual de una ruta específica para el agente conversacional
"""
import json
import boto3
from datetime import datetime, date
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    Consulta estado de ruta
    
    Input:
    {
        "truck_id": "1",
        "fecha": "2026-02-17"  # opcional
    }
    
    Output:
    {
        "truck_id": "1",
        "estado": "En ruta",
        "paradas_totales": 5,
        "paradas_completadas": 2,
        "paradas_pendientes": 3,
        "proxima_parada": {...},
        "ubicacion_actual": {...},
        "conductor": "Juan Pérez",
        "nivel_fatiga": "Bajo"
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        truck_id = event.get('truck_id')
        fecha = event.get('fecha', date.today().isoformat())
        
        if not truck_id:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'truck_id es requerido'
                })
            }
        
        # Consultar ruta en DynamoDB
        rutas_table = dynamodb.Table('rutas_entregas')
        
        try:
            response = rutas_table.get_item(
                Key={
                    'truck_id': truck_id,
                    'fecha': fecha
                }
            )
            
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': f'No se encontró ruta para camión {truck_id} en fecha {fecha}'
                    })
                }
            
            ruta = response['Item']
            
        except Exception as e:
            print(f"Error consultando DynamoDB: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Error consultando base de datos',
                    'message': str(e)
                })
            }
        
        # Consultar información del camión
        flota_table = dynamodb.Table('flota_camiones')
        
        try:
            camion_response = flota_table.get_item(
                Key={'truck_id': truck_id}
            )
            camion = camion_response.get('Item', {})
        except:
            camion = {}
        
        # Procesar paradas
        paradas = ruta.get('paradas', [])
        paradas_completadas = [p for p in paradas if p.get('estado') == 'Completada']
        paradas_pendientes = [p for p in paradas if p.get('estado') != 'Completada']
        
        # Determinar próxima parada
        proxima_parada = None
        if paradas_pendientes:
            proxima = paradas_pendientes[0]
            proxima_parada = {
                'stop_id': proxima.get('stop_id'),
                'cliente': proxima.get('cliente'),
                'eta': proxima.get('eta', 'N/A'),
                'ventana_entrega': f"{proxima.get('ventana_inicio', '08:00')}-{proxima.get('ventana_fin', '18:00')}"
            }
        
        # Determinar estado general
        if ruta.get('tiene_incidente'):
            estado = 'Incidente'
        elif len(paradas_pendientes) == 0:
            estado = 'Completado'
        elif len(paradas_completadas) > 0:
            estado = 'En ruta'
        else:
            estado = 'Pendiente'
        
        result = {
            'truck_id': truck_id,
            'fecha': fecha,
            'estado': estado,
            'paradas_totales': len(paradas),
            'paradas_completadas': len(paradas_completadas),
            'paradas_pendientes': len(paradas_pendientes),
            'proxima_parada': proxima_parada,
            'ubicacion_actual': camion.get('ubicacion_actual', {'lat': 0, 'lon': 0}),
            'conductor': camion.get('conductor', 'N/A'),
            'nivel_fatiga': camion.get('nivel_fatiga', 'Desconocido'),
            'distancia_total_km': ruta.get('distancia_total_km', 0),
            'tiempo_estimado_minutos': ruta.get('tiempo_estimado_minutos', 0)
        }
        
        print(f"Estado de ruta consultado: {truck_id}, estado: {estado}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error consultando estado de ruta: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error consultando estado de ruta',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "truck_id": "1",
        "fecha": "2026-02-17"
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
