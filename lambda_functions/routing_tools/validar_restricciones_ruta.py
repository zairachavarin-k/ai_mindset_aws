"""
Lambda function: validar_restricciones_ruta
Valida que la ruta cumple con todas las restricciones
"""
import json


def lambda_handler(event, context):
    """
    Valida restricciones de la ruta
    
    Input:
    {
        "ruta": {
            "paradas": [...],
            "tiempo_total_minutos": 300,
            "distancia_total_km": 45
        },
        "restricciones": {
            "max_horas_trabajo": 14,
            "ventanas_entrega": [...],
            "capacidad_camion": 1000
        }
    }
    
    Output:
    {
        "valida": true,
        "violaciones": [],
        "sugerencias": []
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        ruta = event.get('ruta', {})
        restricciones = event.get('restricciones', {})
        
        if not ruta:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'ruta es requerida'
                })
            }
        
        paradas = ruta.get('paradas', [])
        tiempo_total_minutos = ruta.get('tiempo_total_minutos', 0)
        distancia_total_km = ruta.get('distancia_total_km', 0)
        
        max_horas_trabajo = restricciones.get('max_horas_trabajo', 14)
        capacidad_camion = restricciones.get('capacidad_camion', 1000)
        ventanas_entrega = restricciones.get('ventanas_entrega', [])
        
        violaciones = []
        sugerencias = []
        
        # Validar tiempo máximo de trabajo
        horas_trabajo = tiempo_total_minutos / 60
        if horas_trabajo > max_horas_trabajo:
            violaciones.append({
                'tipo': 'tiempo_excedido',
                'descripcion': f'Tiempo de trabajo ({horas_trabajo:.1f}h) excede máximo ({max_horas_trabajo}h)',
                'severidad': 'alta'
            })
            sugerencias.append('Dividir ruta entre múltiples conductores o días')
        
        # Validar capacidad del camión
        peso_total = sum(p.get('peso_kg', 0) for p in paradas if p.get('tipo') == 'parada')
        if peso_total > capacidad_camion:
            violaciones.append({
                'tipo': 'capacidad_excedida',
                'descripcion': f'Peso total ({peso_total}kg) excede capacidad ({capacidad_camion}kg)',
                'severidad': 'alta'
            })
            sugerencias.append('Reducir número de paradas o usar camión con mayor capacidad')
        
        # Validar ventanas de entrega
        for i, parada in enumerate(paradas):
            if parada.get('tipo') != 'parada':
                continue
            
            stop_id = parada.get('stop_id')
            hora_llegada = parada.get('hora_llegada_estimada')
            
            # Buscar ventana de entrega
            ventana = next((v for v in ventanas_entrega if v.get('stop_id') == stop_id), None)
            
            if ventana and hora_llegada:
                ventana_inicio = ventana.get('inicio', '08:00')
                ventana_fin = ventana.get('fin', '18:00')
                
                # Validación simple (requiere parsing completo en producción)
                if hora_llegada < ventana_inicio or hora_llegada > ventana_fin:
                    violaciones.append({
                        'tipo': 'ventana_entrega',
                        'descripcion': f'Parada {stop_id}: llegada {hora_llegada} fuera de ventana {ventana_inicio}-{ventana_fin}',
                        'severidad': 'media'
                    })
        
        # Validar distancia razonable
        if distancia_total_km > 300:
            violaciones.append({
                'tipo': 'distancia_excesiva',
                'descripcion': f'Distancia total ({distancia_total_km}km) es excesiva para un día',
                'severidad': 'media'
            })
            sugerencias.append('Considerar dividir ruta en múltiples días')
        
        # Validar número de paradas
        num_paradas = len([p for p in paradas if p.get('tipo') == 'parada'])
        if num_paradas > 20:
            violaciones.append({
                'tipo': 'demasiadas_paradas',
                'descripcion': f'Número de paradas ({num_paradas}) es muy alto',
                'severidad': 'baja'
            })
            sugerencias.append('Considerar agrupar entregas cercanas')
        
        # Sugerencias adicionales
        if horas_trabajo > 10:
            sugerencias.append('Ruta larga - programar descansos adecuados')
        
        if peso_total > capacidad_camion * 0.9:
            sugerencias.append('Carga cercana al límite - verificar distribución de peso')
        
        valida = len([v for v in violaciones if v['severidad'] == 'alta']) == 0
        
        result = {
            'valida': valida,
            'violaciones': violaciones,
            'sugerencias': sugerencias,
            'metricas': {
                'num_paradas': num_paradas,
                'tiempo_total_horas': round(horas_trabajo, 1),
                'distancia_total_km': distancia_total_km,
                'peso_total_kg': peso_total,
                'capacidad_utilizada_porcentaje': round((peso_total / capacidad_camion) * 100, 1) if capacidad_camion > 0 else 0
            }
        }
        
        print(f"Validación: {'VÁLIDA' if valida else 'INVÁLIDA'}, {len(violaciones)} violaciones")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error validando restricciones: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error validando restricciones de ruta',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "ruta": {
            "paradas": [
                {"tipo": "depot"},
                {"tipo": "parada", "stop_id": "STOP-1", "peso_kg": 200, "hora_llegada_estimada": "09:30"},
                {"tipo": "parada", "stop_id": "STOP-2", "peso_kg": 150, "hora_llegada_estimada": "10:45"},
                {"tipo": "depot"}
            ],
            "tiempo_total_minutos": 180,
            "distancia_total_km": 35
        },
        "restricciones": {
            "max_horas_trabajo": 14,
            "capacidad_camion": 1000,
            "ventanas_entrega": [
                {"stop_id": "STOP-1", "inicio": "08:00", "fin": "12:00"},
                {"stop_id": "STOP-2", "inicio": "10:00", "fin": "14:00"}
            ]
        }
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
