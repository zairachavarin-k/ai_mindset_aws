"""
Lambda function: consultar_incidentes_conversacional
Consulta incidentes con filtros opcionales
"""
import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    """
    Consulta incidentes con filtros
    
    Input:
    {
        "incident_id": "INC-001",  # opcional
        "truck_id": "1",  # opcional
        "tipo_incidente": "Choque",  # opcional
        "estado": "Pendiente",  # opcional
        "fecha_desde": "2026-02-01",  # opcional
        "fecha_hasta": "2026-02-17",  # opcional
        "limit": 10  # opcional
    }
    
    Output:
    {
        "incidentes": [...],
        "total": 5
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        incident_id = event.get('incident_id')
        truck_id = event.get('truck_id')
        tipo_incidente = event.get('tipo_incidente')
        estado = event.get('estado')
        fecha_desde = event.get('fecha_desde')
        fecha_hasta = event.get('fecha_hasta')
        limit = event.get('limit', 10)
        
        incidencias_table = dynamodb.Table('incidencias')
        
        # Si se proporciona incident_id específico, consulta directa
        if incident_id:
            try:
                response = incidencias_table.get_item(
                    Key={'incident_id': incident_id}
                )
                
                if 'Item' in response:
                    incidentes = [response['Item']]
                else:
                    incidentes = []
            except Exception as e:
                print(f"Error consultando incidente específico: {e}")
                incidentes = []
        else:
            # Scan con filtros
            try:
                scan_kwargs = {
                    'Limit': limit
                }
                
                # Construir expresión de filtro
                filter_expressions = []
                expression_values = {}
                expression_names = {}
                
                if truck_id:
                    filter_expressions.append('#truck_id = :truck_id')
                    expression_values[':truck_id'] = truck_id
                    expression_names['#truck_id'] = 'truck_id'
                
                if tipo_incidente:
                    filter_expressions.append('contains(tipo_incidente, :tipo)')
                    expression_values[':tipo'] = tipo_incidente
                
                if estado:
                    filter_expressions.append('#estado = :estado')
                    expression_values[':estado'] = estado
                    expression_names['#estado'] = 'estado'
                
                if filter_expressions:
                    scan_kwargs['FilterExpression'] = ' AND '.join(filter_expressions)
                    scan_kwargs['ExpressionAttributeValues'] = expression_values
                    if expression_names:
                        scan_kwargs['ExpressionAttributeNames'] = expression_names
                
                response = incidencias_table.scan(**scan_kwargs)
                incidentes = response.get('Items', [])
                
            except Exception as e:
                print(f"Error en scan: {e}")
                incidentes = []
        
        # Filtrar por fechas si se proporcionan
        if fecha_desde or fecha_hasta:
            incidentes_filtrados = []
            for inc in incidentes:
                timestamp = inc.get('timestamp', '')
                try:
                    fecha_inc = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    
                    if fecha_desde:
                        fecha_desde_dt = datetime.fromisoformat(fecha_desde).date()
                        if fecha_inc < fecha_desde_dt:
                            continue
                    
                    if fecha_hasta:
                        fecha_hasta_dt = datetime.fromisoformat(fecha_hasta).date()
                        if fecha_inc > fecha_hasta_dt:
                            continue
                    
                    incidentes_filtrados.append(inc)
                except:
                    # Si no se puede parsear fecha, incluir el incidente
                    incidentes_filtrados.append(inc)
            
            incidentes = incidentes_filtrados
        
        # Ordenar por timestamp descendente (más recientes primero)
        incidentes.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Limitar resultados
        incidentes = incidentes[:limit]
        
        result = {
            'incidentes': incidentes,
            'total': len(incidentes)
        }
        
        print(f"Incidentes consultados: {len(incidentes)} resultados")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Error consultando incidentes: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error consultando incidentes',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "estado": "Pendiente",
        "limit": 5
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
