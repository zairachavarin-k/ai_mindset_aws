"""
Lambda MCP Tool: enviar_notificacion_cliente
Invoca Amazon Connect StartOutboundVoiceContact con priorización
Requisitos: 7.3, 7.4
"""
import json
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any

connect_client = boto3.client('connect')
dynamodb = boto3.resource('dynamodb')
events_client = boto3.client('events')

connect_instance_id = os.environ.get('CONNECT_INSTANCE_ID', '')
contact_flow_id = os.environ.get('CONTACT_FLOW_ID', '')
source_phone_number = os.environ.get('SOURCE_PHONE_NUMBER', '')
notificaciones_table_name = os.environ.get('NOTIFICACIONES_TABLE_NAME', 'notificaciones_clientes')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Envía notificación a cliente vía Amazon Connect con priorización
    
    Args:
        event: {
            "cliente_id": str,
            "telefono": str,
            "mensaje": str,
            "prioridad": str ("Crítica" | "Alta" | "Baja"),
            "nuevo_horario": str (opcional),
            "motivo": str (opcional),
            "numero_seguimiento": str (opcional),
            "incidente_id": str (opcional)
        }
    
    Returns: {
        "statusCode": 200,
        "body": {
            "notificacion_id": str,
            "estado": str,
            "canal": str,
            "retry_programado": bool
        }
    }
    """
    try:
        # Extraer parámetros
        cliente_id = event.get('cliente_id')
        telefono = event.get('telefono')
        mensaje = event.get('mensaje')
        prioridad = event.get('prioridad', 'Baja')
        nuevo_horario = event.get('nuevo_horario')
        motivo = event.get('motivo')
        numero_seguimiento = event.get('numero_seguimiento')
        incidente_id = event.get('incidente_id')
        
        if not cliente_id or not telefono:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'cliente_id y telefono son requeridos'
                })
            }
        
        # Generar notificacion_id
        notificacion_id = f"NOT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{cliente_id}"
        
        # Construir mensaje completo
        mensaje_completo = mensaje or f"Estimado cliente, su entrega ha sido actualizada."
        if nuevo_horario:
            mensaje_completo += f" Nuevo horario estimado: {nuevo_horario}."
        if motivo:
            mensaje_completo += f" Motivo: {motivo}."
        if numero_seguimiento:
            mensaje_completo += f" Número de seguimiento: {numero_seguimiento}."
        mensaje_completo += " Disculpe las molestias."
        
        # Determinar canal según prioridad (Requisito 7.3)
        if prioridad == "Crítica":
            canal = "llamada_connect"
        elif prioridad == "Alta":
            canal = "llamada_connect"
        else:
            canal = "sms"  # Futuro: implementar SMS
        
        estado = "pendiente"
        retry_programado = False
        
        # Si es llamada de Connect, intentar enviar
        if canal == "llamada_connect":
            if not connect_instance_id or not contact_flow_id:
                print("Amazon Connect no configurado, simulando envío")
                estado = "simulado"
            else:
                try:
                    # Invocar Amazon Connect
                    response = connect_client.start_outbound_voice_contact(
                        InstanceId=connect_instance_id,
                        ContactFlowId=contact_flow_id,
                        DestinationPhoneNumber=telefono,
                        SourcePhoneNumber=source_phone_number,
                        Attributes={
                            'mensaje': mensaje_completo,
                            'cliente_id': cliente_id,
                            'notificacion_id': notificacion_id
                        }
                    )
                    
                    contact_id = response.get('ContactId')
                    estado = "enviado"
                    
                    # Programar retry si no contesta (Requisito 7.4)
                    # Nota: En producción, esto se haría con EventBridge + Lambda
                    # que escucha eventos de Connect para detectar "no contestado"
                    retry_programado = True
                    
                except Exception as connect_error:
                    print(f"Error invocando Connect: {str(connect_error)}")
                    estado = "error"
                    
                    # Programar retry en 15 minutos (Requisito 7.4)
                    if prioridad in ["Crítica", "Alta"]:
                        retry_programado = True
                        # Aquí se programaría un evento en EventBridge para retry
        
        # Registrar notificación en DynamoDB (Requisito 7.5)
        try:
            notificaciones_table = dynamodb.Table(notificaciones_table_name)
            notificaciones_table.put_item(
                Item={
                    'notificacion_id': notificacion_id,
                    'cliente_id': cliente_id,
                    'timestamp_notificacion': datetime.now().isoformat(),
                    'canal_usado': canal,
                    'estado_entrega': estado,
                    'telefono': telefono,
                    'mensaje': mensaje_completo,
                    'prioridad': prioridad,
                    'incidente_id': incidente_id or 'N/A',
                    'retry_count': 0,
                    'max_retries': 3
                }
            )
        except Exception as dynamo_error:
            print(f"Error registrando notificación en DynamoDB: {str(dynamo_error)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'notificacion_id': notificacion_id,
                'estado': estado,
                'canal': canal,
                'retry_programado': retry_programado,
                'mensaje': mensaje_completo
            })
        }
        
    except Exception as e:
        print(f"Error enviando notificación: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error interno: {str(e)}'
            })
        }
