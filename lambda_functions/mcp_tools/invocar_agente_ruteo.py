"""
Lambda function: invocar_agente_ruteo
Invoca el Agente de Ruteo especializado desde el Agente Autónomo
"""
import json
import boto3
import os


def lambda_handler(event, context):
    """
    Invoca el Agente de Ruteo para calcular rutas optimizadas
    
    Input:
    {
        "solicitud": "Calcular ruta optimizada para 3 camiones",
        "contexto": {
            "num_trucks": 3,
            "paradas": [...],
            "origen": {...},
            "restricciones": {...}
        }
    }
    
    Output:
    {
        "status": "success",
        "respuesta": "...",
        "rutas_optimizadas": [...],
        "metricas": {...}
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        solicitud = event.get('solicitud', '')
        contexto = event.get('contexto', {})
        
        if not solicitud:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'solicitud es requerida'
                })
            }
        
        # Configurar cliente de Bedrock Agent Runtime
        bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')
        
        # ID del Agente de Ruteo (debe configurarse en variables de entorno)
        routing_agent_id = os.environ.get('ROUTING_AGENT_ID')
        routing_agent_alias_id = os.environ.get('ROUTING_AGENT_ALIAS_ID', 'TSTALIASID')
        
        if not routing_agent_id:
            # Si no está configurado, retornar error informativo
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Agente de Ruteo no configurado',
                    'message': 'ROUTING_AGENT_ID no está configurado en variables de entorno',
                    'nota': 'Desplegar Agente de Ruteo primero: cd bedrock_agents/routing_agent && agentcore launch'
                })
            }
        
        # Construir prompt para el Agente de Ruteo
        prompt = f"""
{solicitud}

Contexto:
{json.dumps(contexto, indent=2)}

Por favor, calcula la ruta optimizada considerando:
- Tráfico actual
- Condiciones climáticas
- Ventanas de entrega
- Fatiga del conductor
- Restricciones de capacidad
"""
        
        print(f"Invocando Agente de Ruteo: {routing_agent_id}")
        
        # Invocar el Agente de Ruteo
        response = bedrock_agent_runtime.invoke_agent(
            agentId=routing_agent_id,
            agentAliasId=routing_agent_alias_id,
            sessionId=context.request_id if context else 'test-session',
            inputText=prompt
        )
        
        # Procesar respuesta del agente
        agent_response = ''
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    agent_response += chunk['bytes'].decode('utf-8')
        
        print(f"Respuesta del Agente de Ruteo recibida: {len(agent_response)} caracteres")
        
        # Intentar extraer JSON de la respuesta
        try:
            # Buscar JSON en la respuesta
            import re
            json_match = re.search(r'\{.*\}', agent_response, re.DOTALL)
            if json_match:
                rutas_data = json.loads(json_match.group())
            else:
                rutas_data = {}
        except:
            rutas_data = {}
        
        result = {
            'status': 'success',
            'respuesta': agent_response,
            'rutas_optimizadas': rutas_data.get('rutas_optimizadas', []),
            'metricas': rutas_data.get('metricas', {}),
            'agente_invocado': 'routing_agent',
            'agent_id': routing_agent_id
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error invocando Agente de Ruteo: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error invocando Agente de Ruteo',
                'message': str(e)
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "solicitud": "Calcular ruta optimizada para 3 camiones con 8 paradas",
        "contexto": {
            "num_trucks": 3,
            "paradas": [
                {"stop_id": "STOP-1", "lat": 19.4326, "lon": -99.1332},
                {"stop_id": "STOP-2", "lat": 19.4141, "lon": -99.1696}
            ],
            "origen": {"lat": 19.4336, "lon": -99.1908}
        }
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
