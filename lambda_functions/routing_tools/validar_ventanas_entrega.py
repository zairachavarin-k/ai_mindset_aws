"""
Lambda function: validar_ventanas_entrega
Valida si una hora de llegada cumple con la ventana de entrega del cliente
"""
import json
import boto3
from datetime import datetime, time


def lambda_handler(event, context):
    """
    Valida ventana de entrega
    
    Input:
    {
        "stop_id": "STOP-1",
        "hora_llegada_estimada": "14:30"
    }
    
    Output:
    {
        "valida": true,
        "ventana_inicio": "08:00",
        "ventana_fin": "18:00",
        "minutos_antes_ventana": 0,
        "minutos_despues_ventana": 0,
        "penalizacion": 0
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        stop_id = event.get('stop_id')
        hora_llegada_str = event.get('hora_llegada_estimada')
        
        if not stop_id or not hora_llegada_str:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'stop_id y hora_llegada_estimada son requeridos'
                })
            }
        
        # Consultar ventana de entrega desde S3
        s3 = boto3.client('s3')
        bucket_name = 'smart-supply-data'
        
        try:
            response = s3.get_object(
                Bucket=bucket_name,
                Key='rutas/rutas_entregas_2026_02_17.json'
            )
            rutas_data = json.loads(response['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error leyendo S3, usando valores por defecto: {e}")
            # Valores por defecto si no se puede leer S3
            ventana_inicio = "08:00"
            ventana_fin = "18:00"
        else:
            # Buscar ventana de entrega para el stop_id
            ventana_inicio = "08:00"
            ventana_fin = "18:00"
            
            for ruta in rutas_data.get('rutas', []):
                for parada in ruta.get('paradas', []):
                    if parada.get('stop_id') == stop_id:
                        ventana_inicio = parada.get('ventana_inicio', "08:00")
                        ventana_fin = parada.get('ventana_fin', "18:00")
                        break
        
        # Parsear horas
        hora_llegada = datetime.strptime(hora_llegada_str, "%H:%M").time()
        ventana_inicio_time = datetime.strptime(ventana_inicio, "%H:%M").time()
        ventana_fin_time = datetime.strptime(ventana_fin, "%H:%M").time()
        
        # Convertir a minutos desde medianoche para cálculos
        def time_to_minutes(t):
            return t.hour * 60 + t.minute
        
        llegada_min = time_to_minutes(hora_llegada)
        inicio_min = time_to_minutes(ventana_inicio_time)
        fin_min = time_to_minutes(ventana_fin_time)
        
        # Calcular si está dentro de ventana
        valida = inicio_min <= llegada_min <= fin_min
        
        minutos_antes_ventana = max(0, inicio_min - llegada_min)
        minutos_despues_ventana = max(0, llegada_min - fin_min)
        
        # Calcular penalización
        if minutos_antes_ventana > 0:
            # Llegar antes: penalización menor (espera)
            penalizacion = minutos_antes_ventana * 0.5
        elif minutos_despues_ventana > 0:
            # Llegar tarde: penalización mayor
            penalizacion = minutos_despues_ventana * 2.0
        else:
            penalizacion = 0
        
        result = {
            'valida': valida,
            'ventana_inicio': ventana_inicio,
            'ventana_fin': ventana_fin,
            'hora_llegada': hora_llegada_str,
            'minutos_antes_ventana': minutos_antes_ventana,
            'minutos_despues_ventana': minutos_despues_ventana,
            'penalizacion': penalizacion,
            'stop_id': stop_id
        }
        
        print(f"Ventana validada: {valida}, penalización: {penalizacion}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error validando ventana: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error validando ventana de entrega',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "stop_id": "STOP-1",
        "hora_llegada_estimada": "14:30"
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
