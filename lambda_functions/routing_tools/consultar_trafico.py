"""
Lambda function: consultar_trafico
Consulta el estado del tráfico actual en una ruta específica
"""
import json
import os
import boto3
from datetime import datetime

# Para integración con Google Maps Traffic API o HERE Traffic API
# Requiere configurar API_KEY en variables de entorno


def lambda_handler(event, context):
    """
    Consulta tráfico en tiempo real entre dos puntos
    
    Input:
    {
        "origen": {"lat": 19.4384, "lon": -99.1569},
        "destino": {"lat": 19.4345, "lon": -99.1410}
    }
    
    Output:
    {
        "nivel_trafico": "moderado",
        "factor_tiempo": 1.3,
        "incidentes": [...]
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        origen = event.get('origen', {})
        destino = event.get('destino', {})
        
        if not origen or not destino:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Origen y destino son requeridos'
                })
            }
        
        # TODO: Integrar con Google Maps Traffic API o HERE Traffic API
        # Por ahora, simulamos respuesta basada en hora del día
        
        hora_actual = datetime.now().hour
        
        # Simular tráfico según hora del día (Ciudad de México)
        if 7 <= hora_actual <= 10 or 18 <= hora_actual <= 21:
            # Hora pico
            nivel_trafico = "alto"
            factor_tiempo = 1.6
            incidentes = [
                {
                    "tipo": "Tráfico denso",
                    "ubicacion": "Periférico Sur",
                    "impacto": "alto"
                }
            ]
        elif 11 <= hora_actual <= 17:
            # Hora normal
            nivel_trafico = "moderado"
            factor_tiempo = 1.2
            incidentes = []
        else:
            # Hora baja
            nivel_trafico = "bajo"
            factor_tiempo = 1.0
            incidentes = []
        
        result = {
            'nivel_trafico': nivel_trafico,
            'factor_tiempo': factor_tiempo,
            'incidentes': incidentes,
            'timestamp': datetime.now().isoformat(),
            'origen': origen,
            'destino': destino,
            'nota': 'Simulación - integrar con API de tráfico real'
        }
        
        print(f"Tráfico consultado: {nivel_trafico}, factor: {factor_tiempo}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error consultando tráfico: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error consultando tráfico',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "origen": {"lat": 19.4384, "lon": -99.1569},
        "destino": {"lat": 19.4345, "lon": -99.1410}
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
