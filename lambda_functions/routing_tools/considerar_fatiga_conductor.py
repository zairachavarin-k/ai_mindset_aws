"""
Lambda function: considerar_fatiga_conductor
Calcula descansos necesarios según horas de trabajo del conductor
"""
import json
from datetime import datetime, timedelta


def lambda_handler(event, context):
    """
    Calcula descansos necesarios por fatiga
    
    Input:
    {
        "conductor": "Juan Pérez",
        "tiempo_ruta_minutos": 300,
        "hora_inicio": "08:00",
        "nivel_fatiga_actual": "Bajo"
    }
    
    Output:
    {
        "descansos_necesarios": [
            {
                "despues_parada": 3,
                "duracion_minutos": 30,
                "motivo": "Descanso obligatorio cada 4 horas"
            }
        ],
        "tiempo_total_descansos": 30,
        "puede_completar_ruta": true,
        "recomendaciones": [...]
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        conductor = event.get('conductor')
        tiempo_ruta_minutos = event.get('tiempo_ruta_minutos')
        hora_inicio = event.get('hora_inicio', '08:00')
        nivel_fatiga_actual = event.get('nivel_fatiga_actual', 'Bajo')
        
        if not conductor or tiempo_ruta_minutos is None:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'conductor y tiempo_ruta_minutos son requeridos'
                })
            }
        
        # Regulaciones de trabajo (México - SCT)
        MAX_HORAS_CONDUCCION_CONTINUA = 4  # 4 horas máximo sin descanso
        DESCANSO_MINIMO_MINUTOS = 30
        MAX_HORAS_TRABAJO_DIA = 14  # Máximo 14 horas de trabajo al día
        
        descansos_necesarios = []
        tiempo_total_descansos = 0
        recomendaciones = []
        
        # Calcular número de descansos necesarios
        horas_ruta = tiempo_ruta_minutos / 60
        num_descansos = int(horas_ruta / MAX_HORAS_CONDUCCION_CONTINUA)
        
        # Agregar descansos cada 4 horas
        for i in range(num_descansos):
            descanso = {
                'despues_parada': (i + 1) * 3,  # Aproximadamente cada 3 paradas
                'duracion_minutos': DESCANSO_MINIMO_MINUTOS,
                'motivo': 'Descanso obligatorio cada 4 horas de conducción'
            }
            descansos_necesarios.append(descanso)
            tiempo_total_descansos += DESCANSO_MINIMO_MINUTOS
        
        # Considerar nivel de fatiga actual
        if nivel_fatiga_actual == 'Alto':
            # Agregar descanso adicional al inicio
            descansos_necesarios.insert(0, {
                'despues_parada': 0,
                'duracion_minutos': 45,
                'motivo': 'Descanso adicional por nivel de fatiga alto'
            })
            tiempo_total_descansos += 45
            recomendaciones.append('Conductor con fatiga alta - considerar reemplazo')
        elif nivel_fatiga_actual == 'Medio':
            recomendaciones.append('Monitorear nivel de fatiga durante la ruta')
        
        # Calcular tiempo total incluyendo descansos
        tiempo_total_con_descansos = tiempo_ruta_minutos + tiempo_total_descansos
        horas_totales = tiempo_total_con_descansos / 60
        
        # Verificar si puede completar la ruta
        puede_completar = horas_totales <= MAX_HORAS_TRABAJO_DIA
        
        if not puede_completar:
            recomendaciones.append(
                f'Ruta excede máximo de {MAX_HORAS_TRABAJO_DIA}h - dividir entre 2 conductores'
            )
        
        # Verificar hora de finalización
        try:
            hora_inicio_dt = datetime.strptime(hora_inicio, '%H:%M')
            hora_fin_dt = hora_inicio_dt + timedelta(minutes=tiempo_total_con_descansos)
            hora_fin = hora_fin_dt.strftime('%H:%M')
            
            # Verificar si termina muy tarde
            if hora_fin_dt.hour >= 22:
                recomendaciones.append('Ruta termina después de las 22:00 - considerar iniciar más temprano')
        except:
            hora_fin = 'N/A'
        
        result = {
            'descansos_necesarios': descansos_necesarios,
            'tiempo_total_descansos': tiempo_total_descansos,
            'puede_completar_ruta': puede_completar,
            'recomendaciones': recomendaciones,
            'conductor': conductor,
            'tiempo_ruta_minutos': tiempo_ruta_minutos,
            'tiempo_total_con_descansos': tiempo_total_con_descansos,
            'hora_inicio': hora_inicio,
            'hora_fin_estimada': hora_fin,
            'nivel_fatiga_actual': nivel_fatiga_actual
        }
        
        print(f"Fatiga calculada: {len(descansos_necesarios)} descansos, {tiempo_total_descansos} min")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error calculando fatiga: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error calculando fatiga del conductor',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "conductor": "Juan Pérez",
        "tiempo_ruta_minutos": 300,
        "hora_inicio": "08:00",
        "nivel_fatiga_actual": "Bajo"
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
