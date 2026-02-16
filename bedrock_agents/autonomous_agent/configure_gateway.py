"""
Script para configurar AgentCore Gateway programáticamente
Expone Lambda functions como herramientas MCP para el Bedrock Agent
"""
import boto3
import json
import sys
from typing import List, Dict, Any

# Configuración
GATEWAY_NAME = "smartsupply-mcp-gateway"
AGENT_NAME = "smartsupply-autonomous-agent"
AWS_REGION = "us-east-1"

# Cliente de Bedrock
bedrock_agent_client = boto3.client('bedrock-agent', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)
sts_client = boto3.client('sts')

# Obtener AWS Account ID
AWS_ACCOUNT_ID = sts_client.get_caller_identity()['Account']


def load_tools_schema() -> Dict[str, Any]:
    """Carga el schema de herramientas MCP desde JSON"""
    with open('mcp_tools_schema.json', 'r') as f:
        return json.load(f)


def verify_lambda_functions(tools: List[Dict[str, Any]]) -> bool:
    """Verifica que todas las Lambda functions existen"""
    print("\n🔍 Verificando Lambda functions...")
    
    all_exist = True
    for tool in tools:
        function_name = tool['lambda_function']
        try:
            lambda_client.get_function(FunctionName=function_name)
            print(f"  ✓ {function_name}")
        except lambda_client.exceptions.ResourceNotFoundException:
            print(f"  ✗ {function_name} - NO ENCONTRADA")
            all_exist = False
    
    return all_exist


def create_action_group_schema(tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Crea el schema de OpenAPI para el action group
    Bedrock Agents usa OpenAPI para definir herramientas
    """
    openapi_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "SmartSupply MCP Tools API",
            "description": "Herramientas MCP para el agente autónomo SmartSupply",
            "version": "1.0.0"
        },
        "paths": {}
    }
    
    # Agregar cada herramienta como un path en OpenAPI
    for tool in tools:
        path = f"/{tool['name']}"
        openapi_schema["paths"][path] = {
            "post": {
                "summary": tool['description'],
                "operationId": tool['name'],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": tool['input_schema']
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": tool['output_schema']
                            }
                        }
                    }
                }
            }
        }
    
    return openapi_schema


def configure_agent_action_group(agent_id: str, tools_schema: Dict[str, Any]) -> str:
    """
    Configura el action group del agente con las herramientas MCP
    
    Nota: Esta función usa la API de Bedrock Agents directamente.
    En producción, se recomienda usar agentcore CLI o AWS Console.
    """
    print("\n⚙️  Configurando action group del agente...")
    
    tools = tools_schema['tools']
    openapi_schema = create_action_group_schema(tools)
    
    # Crear action group
    try:
        response = bedrock_agent_client.create_agent_action_group(
            agentId=agent_id,
            agentVersion='DRAFT',
            actionGroupName='mcp-tools',
            description='Herramientas MCP para consultar datos y ejecutar acciones',
            actionGroupExecutor={
                'lambda': f"arn:aws:lambda:{AWS_REGION}:{AWS_ACCOUNT_ID}:function:smartsupply-mcp-router"
            },
            apiSchema={
                'payload': json.dumps(openapi_schema)
            }
        )
        
        action_group_id = response['agentActionGroup']['actionGroupId']
        print(f"  ✓ Action group creado: {action_group_id}")
        return action_group_id
        
    except bedrock_agent_client.exceptions.ConflictException:
        print("  ℹ️  Action group ya existe")
        # Listar action groups existentes
        response = bedrock_agent_client.list_agent_action_groups(
            agentId=agent_id,
            agentVersion='DRAFT'
        )
        for ag in response['actionGroupSummaries']:
            if ag['actionGroupName'] == 'mcp-tools':
                return ag['actionGroupId']
    
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def create_mcp_router_lambda():
    """
    Crea una Lambda function que actúa como router para las herramientas MCP
    Esta Lambda recibe las invocaciones del agente y las enruta a las Lambda functions correctas
    """
    print("\n🔧 Creando Lambda router para MCP tools...")
    
    # Código de la Lambda router
    router_code = '''
import boto3
import json

lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Router que recibe invocaciones del Bedrock Agent y las enruta a las Lambda functions correctas
    """
    # Extraer el nombre de la herramienta desde el evento
    action = event.get('actionGroup', '')
    api_path = event.get('apiPath', '')
    parameters = event.get('parameters', [])
    
    # Mapear path a nombre de Lambda function
    tool_name = api_path.strip('/')
    
    # Construir payload para la Lambda function
    payload = {}
    for param in parameters:
        payload[param['name']] = param['value']
    
    # Invocar la Lambda function correspondiente
    try:
        response = lambda_client.invoke(
            FunctionName=tool_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action,
                'apiPath': api_path,
                'httpMethod': 'POST',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result)
                    }
                }
            }
        }
    except Exception as e:
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': action,
                'apiPath': api_path,
                'httpMethod': 'POST',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({'error': str(e)})
                    }
                }
            }
        }
'''
    
    print("  ℹ️  Código del router preparado")
    print("  ℹ️  Desplegar manualmente usando AWS Console o CDK")
    print(f"  ℹ️  Nombre de función: smartsupply-mcp-router")
    
    # Guardar código en archivo
    with open('mcp_router_lambda.py', 'w') as f:
        f.write(router_code)
    
    print("  ✓ Código guardado en: mcp_router_lambda.py")


def main():
    """Función principal"""
    print("=" * 60)
    print("Configuración de AgentCore Gateway")
    print("SmartSupply - Agente Autónomo")
    print("=" * 60)
    
    # Cargar schema de herramientas
    print("\n📋 Cargando schema de herramientas MCP...")
    tools_schema = load_tools_schema()
    print(f"  ✓ {len(tools_schema['tools'])} herramientas cargadas")
    
    # Verificar Lambda functions
    if not verify_lambda_functions(tools_schema['tools']):
        print("\n⚠️  Algunas Lambda functions no existen")
        print("   Desplegar Lambda functions antes de continuar")
        sys.exit(1)
    
    # Crear Lambda router
    create_mcp_router_lambda()
    
    print("\n" + "=" * 60)
    print("Configuración completada")
    print("=" * 60)
    print("\nPróximos pasos:")
    print("1. Desplegar Lambda router: smartsupply-mcp-router")
    print("2. Obtener Agent ID del agente desplegado")
    print("3. Ejecutar: configure_agent_action_group(agent_id, tools_schema)")
    print("4. Preparar el agente: bedrock_agent_client.prepare_agent(agentId=agent_id)")
    print("5. Probar el agente con herramientas MCP")
    print()


if __name__ == "__main__":
    main()
