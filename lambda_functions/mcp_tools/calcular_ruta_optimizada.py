"""
Lambda MCP Tool: calcular_ruta_optimizada
Invoca el Agente de Ruteo para optimización avanzada de rutas
O usa Lambda de optimización mTSP directamente para casos simples
Requisitos: 20.1, 20.2, 20.4, 20.5
"""
import json
import os
import boto3
from typing import Dict, Any, List

lambda_client = boto3.client('lambda')
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Configuración
routing_agent_id = os.environ.get('ROUTING_AGENT_ID')
routing_agent_alias_id = os.environ.get('ROUTING_AGENT_ALIAS_ID', 'TSTALIASID')
mtsp_lambda_name = os.environ.get('MTSP_LAMBDA_NAME', 'smartsupply-routing-optimizar_ruta_mtsp')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Optimiza rutas usando el Agente de Ruteo (recomendado) o Lambda mTSP directa
    
    Args:
        event: {
            "paradas": [
                {
                    "stop_id": str,
                    "lat": float,
                    "lon": float,
                    "hora_programada": str (opcional),
                    "cliente": str (opcional)
                }
            ],
            "origen": {"lat": float, "lon": float},
            "num_trucks": int (opcional, default: 1),
            "usar_agente_ruteo": bool (opcional, default: true si está configurado),
            "considerar_trafico": bool (opcional, default: false),
            "considerar_clima": bool (opcional, default: false)
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "ruta_optimizada": [...],
            "distancia_total_km": float,
            "tiempo_estimado_minutos": float,
            "metodo_usado": str
        }
    }
    """
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Extraer parámetros
        paradas = event.get('paradas', [])
        origen = event.get('origen', {})
        num_trucks = event.get('num_trucks', 1)
        usar_agente_ruteo = event.get('usar_agente_ruteo', routing_agent_id is not None)
        considerar_trafico = event.get('considerar_trafico', False)
        considerar_clima = event.get('considerar_clima', False)
        
        # Validaciones
        if not paradas:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'paradas es requerido y debe contener al menos una parada'
                })
            }
        
        if not origen or 'lat' not in origen or 'lon' not in origen:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'origen es requerido con formato {"lat": float, "lon": float}'
                })
            }
        
        # Opción 1: Usar Agente de Ruteo (recomendado para optimización avanzada)
        if usar_agente_ruteo and routing_agent_id:
            print(f"Usando Agente de Ruteo: {routing_agent_id}")
            
            try:
                # Construir prompt para el agente
                prompt = f"""Optimiza la ruta para {num_trucks} camión(es) con {len(paradas)} paradas.

Origen: {origen}
Paradas: {json.dumps(paradas, indent=2)}

Considera:
- Tráfico: {'Sí' if considerar_trafico else 'No'}
- Clima: {'Sí' if considerar_clima else 'No'}
- Ventanas de entrega
- Fatiga del conductor

Proporciona la ruta optimizada con distancia total y tiempo estimado."""

                # Invocar Agente de Ruteo
                response = bedrock_agent_runtime.invoke_agent(
                    agentId=routing_agent_id,
                    agentAliasId=routing_agent_alias_id,
                    sessionId=context.request_id if context else 'optimization-session',
                    inputText=prompt
                )
                
                # Procesar respuesta del agente
                agent_response = ''
                for event_chunk in response.get('completion', []):
                    if 'chunk' in event_chunk:
                        chunk = event_chunk['chunk']
                        if 'bytes' in chunk:
                            agent_response += chunk['bytes'].decode('utf-8')
                
                print(f"Respuesta del Agente de Ruteo: {len(agent_response)} caracteres")
                
                # Intentar extraer JSON de la respuesta
                import re
                json_match = re.search(r'\{.*\}', agent_response, re.DOTALL)
                if json_match:
                    resultado = json.loads(json_match.group())
                    resultado['metodo_usado'] = 'Agente de Ruteo'
                else:
                    # Si no hay JSON, usar respuesta de texto
                    resultado = {
                        'respuesta': agent_response,
                        'metodo_usado': 'Agente de Ruteo (texto)',
                        'nota': 'Respuesta en formato texto - parsear manualmente'
                    }
                
                return {
                    'statusCode': 200,
                    'body': json.dumps(resultado)
                }
                
            except Exception as e:
                print(f"Error invocando Agente de Ruteo: {e}")
                print("Fallback a Lambda mTSP directa...")
                # Continuar con fallback
        
        # Opción 2: Usar Lambda mTSP directa (fallback o para casos simples)
        print(f"Usando Lambda mTSP directa: {mtsp_lambda_name}")
        
        # Preparar payload para Lambda mTSP
        mtsp_payload = {
            'num_trucks': num_trucks,
            'paradas': paradas,
            'origen': origen
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName=mtsp_lambda_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(mtsp_payload)
            )
            
            # Leer respuesta
            response_payload = json.loads(response['Payload'].read())
            
            # Si hay error
            if response.get('FunctionError'):
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': f'Error en Lambda mTSP: {response_payload}'
                    })
                }
            
            # Extraer resultado
            if isinstance(response_payload, dict) and 'body' in response_payload:
                body = response_payload['body']
                if isinstance(body, str):
                    body = json.loads(body)
                resultado = body
            else:
                resultado = response_payload
            
            # Agregar metadatos
            resultado['metodo_usado'] = 'Lambda mTSP (ACO)'
            
            return {
                'statusCode': 200,
                'body': json.dumps(resultado)
            }
            
        except lambda_client.exceptions.ResourceNotFoundException:
            return {
                'statusCode': 503,
                'body': json.dumps({
                    'error': f'Lambda mTSP "{mtsp_lambda_name}" no encontrada',
                    'nota': 'Desplegar Lambda de optimización mTSP primero'
                })
            }
        
    except Exception as e:
        print(f"Error en optimización de rutas: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }


# Para testing local
if __name__ == "__main__":
    test_event = {
        "paradas": [
            {"stop_id": "STOP-1", "lat": 19.4326, "lon": -99.1332, "cliente": "Cliente 1"},
            {"stop_id": "STOP-2", "lat": 19.4141, "lon": -99.1696, "cliente": "Cliente 2"},
            {"stop_id": "STOP-3", "lat": 19.3629, "lon": -99.2736, "cliente": "Cliente 3"}
        ],
        "origen": {"lat": 19.4336, "lon": -99.1908},
        "num_trucks": 1,
        "usar_agente_ruteo": False  # Usar Lambda directa para testing
    }
    
    result = lambda_handler(test_event, None)
    print("\n" + "="*60)
    print("RESULTADO:")
    print("="*60)
    print(json.dumps(json.loads(result['body']), indent=2))
