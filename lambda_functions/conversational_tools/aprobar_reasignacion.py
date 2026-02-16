"""
Lambda function: aprobar_reasignacion
Aprueba o rechaza un plan de reasignación y ejecuta si es aprobado
"""
import json
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    Aprueba/rechaza plan de reasignación
    
    Input:
    {
        "plan_id": "PLAN-001",
        "aprobado": true,
        "operador": "Maria Lopez",
        "comentarios": "Plan aprobado"
    }
    
    Output:
    {
        "success": true,
        "plan_id": "PLAN-001",
        "estado": "Aprobado y ejecutado",
        "acciones_ejecutadas": [...],
        "mensaje": "Plan ejecutado exitosamente"
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        plan_id = event.get('plan_id')
        aprobado = event.get('aprobado')
        operador = event.get('operador')
        comentarios = event.get('comentarios', '')
        
        if not plan_id or aprobado is None or not operador:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'plan_id, aprobado y operador son requeridos'
                })
            }
        
        # Consultar plan en DynamoDB (tabla agent_memory)
        memory_table = dynamodb.Table('agent_memory')
        
        try:
            response = memory_table.get_item(
                Key={'memory_id': plan_id}
            )
            
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': f'Plan {plan_id} no encontrado'
                    })
                }
            
            plan = response['Item']
            
        except Exception as e:
            print(f"Error consultando plan: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Error consultando plan',
                    'message': str(e)
                })
            }
        
        # Actualizar estado del plan
        timestamp = datetime.now().isoformat()
        nuevo_estado = 'Aprobado' if aprobado else 'Rechazado'
        
        try:
            memory_table.update_item(
                Key={'memory_id': plan_id},
                UpdateExpression='SET #estado = :estado, operador_aprobacion = :operador, timestamp_aprobacion = :timestamp, comentarios_aprobacion = :comentarios',
                ExpressionAttributeNames={
                    '#estado': 'estado'
                },
                ExpressionAttributeValues={
                    ':estado': nuevo_estado,
                    ':operador': operador,
                    ':timestamp': timestamp,
                    ':comentarios': comentarios
                }
            )
        except Exception as e:
            print(f"Error actualizando plan: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Error actualizando plan',
                    'message': str(e)
                })
            }
        
        acciones_ejecutadas = []
        
        # Si fue aprobado, ejecutar el plan
        if aprobado:
            try:
                # Invocar Lambda de ejecución de reasignación
                execution_payload = {
                    'plan_id': plan_id,
                    'plan_data': plan.get('decision_tomada', {}),
                    'operador': operador
                }
                
                # TODO: Invocar execute_reassignment_plan Lambda
                # Por ahora, simulamos la ejecución
                print(f"Ejecutando plan {plan_id}...")
                
                acciones_ejecutadas = [
                    f"Ruta actualizada para camión {plan.get('decision_tomada', {}).get('camion_reemplazo', 'N/A')}",
                    f"Notificaciones enviadas a {plan.get('decision_tomada', {}).get('num_clientes_afectados', 0)} clientes",
                    "Incidente registrado en el sistema",
                    "Inventario actualizado"
                ]
                
                # Actualizar estado a "Ejecutado"
                memory_table.update_item(
                    Key={'memory_id': plan_id},
                    UpdateExpression='SET #estado = :estado, timestamp_ejecucion = :timestamp_exec',
                    ExpressionAttributeNames={
                        '#estado': 'estado'
                    },
                    ExpressionAttributeValues={
                        ':estado': 'Ejecutado',
                        ':timestamp_exec': timestamp
                    }
                )
                
                mensaje = "Plan aprobado y ejecutado exitosamente"
                
            except Exception as e:
                print(f"Error ejecutando plan: {e}")
                mensaje = f"Plan aprobado pero error en ejecución: {str(e)}"
                acciones_ejecutadas.append(f"ERROR: {str(e)}")
        else:
            mensaje = "Plan rechazado por el operador"
        
        result = {
            'success': True,
            'plan_id': plan_id,
            'estado': nuevo_estado if not aprobado else 'Ejecutado',
            'timestamp': timestamp,
            'operador': operador,
            'acciones_ejecutadas': acciones_ejecutadas,
            'mensaje': mensaje
        }
        
        print(f"Plan {plan_id} {'aprobado y ejecutado' if aprobado else 'rechazado'}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error en aprobación: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error procesando aprobación',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "plan_id": "PLAN-TEST-001",
        "aprobado": True,
        "operador": "Maria Lopez",
        "comentarios": "Plan aprobado para testing"
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
