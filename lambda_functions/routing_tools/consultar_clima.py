"""
Lambda function: consultar_clima
Consulta las condiciones climáticas actuales y pronóstico
"""
import json
import os
import boto3
from datetime import datetime

# Para integración con OpenWeatherMap API
# Requiere configurar API_KEY en variables de entorno


def lambda_handler(event, context):
    """
    Consulta clima actual y pronóstico
    
    Input:
    {
        "ubicacion": {"lat": 19.4384, "lon": -99.1569},
        "hora_estimada": "2026-02-17T14:30:00"
    }
    
    Output:
    {
        "condicion": "despejado",
        "temperatura": 22,
        "factor_tiempo": 1.0,
        "visibilidad_km": 10,
        "recomendaciones": []
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        ubicacion = event.get('ubicacion', {})
        hora_estimada = event.get('hora_estimada')
        
        if not ubicacion:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Ubicación es requerida'
                })
            }
        
        # TODO: Integrar con OpenWeatherMap API
        # Por ahora, simulamos respuesta basada en probabilidades
        
        import random
        
        # Simular condiciones climáticas (Ciudad de México - febrero)
        condiciones_posibles = [
            ("despejado", 1.0, 10, []),
            ("nublado", 1.05, 8, ["Visibilidad reducida"]),
            ("lluvia_ligera", 1.15, 5, ["Reducir velocidad", "Aumentar distancia de seguridad"]),
            ("lluvia_fuerte", 1.30, 3, ["Reducir velocidad significativamente", "Considerar retrasos"])
        ]
        
        # Febrero en CDMX: mayormente despejado
        pesos = [0.6, 0.25, 0.10, 0.05]
        condicion_idx = random.choices(range(len(condiciones_posibles)), weights=pesos)[0]
        condicion, factor_tiempo, visibilidad, recomendaciones = condiciones_posibles[condicion_idx]
        
        temperatura = random.randint(15, 25)  # Temperatura típica de febrero
        
        result = {
            'condicion': condicion,
            'temperatura': temperatura,
            'factor_tiempo': factor_tiempo,
            'visibilidad_km': visibilidad,
            'recomendaciones': recomendaciones,
            'timestamp': datetime.now().isoformat(),
            'ubicacion': ubicacion,
            'nota': 'Simulación - integrar con OpenWeatherMap API'
        }
        
        print(f"Clima consultado: {condicion}, factor: {factor_tiempo}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error consultando clima: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error consultando clima',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "ubicacion": {"lat": 19.4384, "lon": -99.1569},
        "hora_estimada": "2026-02-17T14:30:00"
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
