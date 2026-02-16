"""
Lambda function: calcular_tiempo_real
Calcula tiempo real de viaje considerando todos los factores
"""
import json


def lambda_handler(event, context):
    """
    Calcula tiempo real considerando múltiples factores
    
    Input:
    {
        "distancia_km": 15.5,
        "velocidad_base_kmh": 40,
        "factor_trafico": 1.3,
        "factor_clima": 1.15,
        "tipo_via": "ciudad"
    }
    
    Output:
    {
        "tiempo_minutos": 45.2,
        "velocidad_efectiva_kmh": 20.6,
        "factores_aplicados": {
            "trafico": 1.3,
            "clima": 1.15,
            "tipo_via": 0.8
        }
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        distancia_km = event.get('distancia_km')
        velocidad_base_kmh = event.get('velocidad_base_kmh', 40.0)
        factor_trafico = event.get('factor_trafico', 1.0)
        factor_clima = event.get('factor_clima', 1.0)
        tipo_via = event.get('tipo_via', 'ciudad')
        
        if distancia_km is None:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'distancia_km es requerida'
                })
            }
        
        # Factor según tipo de vía
        factores_via = {
            'autopista': 1.2,  # Más rápido
            'carretera': 1.0,  # Normal
            'ciudad': 0.7      # Más lento (semáforos, tráfico)
        }
        
        factor_via = factores_via.get(tipo_via, 1.0)
        
        # Calcular velocidad efectiva
        velocidad_efectiva = velocidad_base_kmh * factor_via
        
        # Aplicar factores de tráfico y clima (reducen velocidad)
        velocidad_efectiva = velocidad_efectiva / (factor_trafico * factor_clima)
        
        # Calcular tiempo en minutos
        tiempo_horas = distancia_km / velocidad_efectiva
        tiempo_minutos = tiempo_horas * 60
        
        # Agregar tiempo de maniobras (5 min por cada 10 km en ciudad)
        if tipo_via == 'ciudad':
            tiempo_maniobras = (distancia_km / 10) * 5
            tiempo_minutos += tiempo_maniobras
        
        result = {
            'tiempo_minutos': round(tiempo_minutos, 1),
            'velocidad_efectiva_kmh': round(velocidad_efectiva, 1),
            'factores_aplicados': {
                'trafico': factor_trafico,
                'clima': factor_clima,
                'tipo_via': factor_via
            },
            'distancia_km': distancia_km,
            'velocidad_base_kmh': velocidad_base_kmh,
            'tipo_via': tipo_via
        }
        
        print(f"Tiempo calculado: {tiempo_minutos:.1f} min para {distancia_km} km")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error calculando tiempo: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error calculando tiempo real',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "distancia_km": 15.5,
        "velocidad_base_kmh": 40,
        "factor_trafico": 1.3,
        "factor_clima": 1.15,
        "tipo_via": "ciudad"
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
