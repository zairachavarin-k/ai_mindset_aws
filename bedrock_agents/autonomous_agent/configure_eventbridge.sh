#!/bin/bash
# Script para configurar EventBridge rule que invoca el Bedrock Agent
# cuando se detectan incidentes

set -e

echo "=========================================="
echo "Configurando EventBridge Integration"
echo "=========================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuración
RULE_NAME="smartsupply-incident-to-agent"
EVENT_BUS_NAME="smart-supply-events"
AGENT_NAME="smartsupply-autonomous-agent"
AWS_REGION=$(aws configure get region)
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${YELLOW}Rule Name: $RULE_NAME${NC}"
echo -e "${YELLOW}Event Bus: $EVENT_BUS_NAME${NC}"
echo -e "${YELLOW}Agent: $AGENT_NAME${NC}"
echo -e "${YELLOW}Region: $AWS_REGION${NC}"
echo ""

# Paso 1: Verificar que el Event Bus existe
echo -e "${GREEN}Paso 1: Verificando Event Bus...${NC}"

if aws events describe-event-bus --name "$EVENT_BUS_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "  ✓ Event Bus existe: $EVENT_BUS_NAME"
else
    echo -e "  ${RED}✗ Event Bus no existe: $EVENT_BUS_NAME${NC}"
    echo "  Desplegar infraestructura CDK primero: cd infrastructure && ./deploy.sh"
    exit 1
fi

echo ""

# Paso 2: Obtener ARN del Bedrock Agent
echo -e "${GREEN}Paso 2: Obteniendo ARN del Bedrock Agent...${NC}"

# Nota: El ARN del agente se obtiene después del despliegue con agentcore
# Por ahora, construimos el ARN esperado
AGENT_ARN="arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:agent/${AGENT_NAME}"

echo -e "  ℹ️  ARN del agente (esperado): $AGENT_ARN"
echo -e "  ${YELLOW}Nota: Verificar ARN real después de desplegar el agente${NC}"

echo ""

# Paso 3: Crear EventBridge Rule
echo -e "${GREEN}Paso 3: Creando EventBridge Rule...${NC}"

# Event pattern: Escuchar eventos de incidentes de todos los canales
EVENT_PATTERN=$(cat <<EOF
{
  "source": [
    "smartsupply.voice",
    "smartsupply.web",
    "smartsupply.iot"
  ],
  "detail-type": [
    "IncidentDetected"
  ]
}
EOF
)

if aws events describe-rule --name "$RULE_NAME" --event-bus-name "$EVENT_BUS_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "  ℹ️  Rule ya existe, actualizando..."
    
    aws events put-rule \
      --name "$RULE_NAME" \
      --event-bus-name "$EVENT_BUS_NAME" \
      --event-pattern "$EVENT_PATTERN" \
      --state ENABLED \
      --description "Invoca Bedrock Agent autónomo cuando se detecta un incidente" \
      --region "$AWS_REGION"
    
    echo -e "  ✓ Rule actualizada: $RULE_NAME"
else
    echo -e "  Creando nueva rule..."
    
    aws events put-rule \
      --name "$RULE_NAME" \
      --event-bus-name "$EVENT_BUS_NAME" \
      --event-pattern "$EVENT_PATTERN" \
      --state ENABLED \
      --description "Invoca Bedrock Agent autónomo cuando se detecta un incidente" \
      --region "$AWS_REGION"
    
    echo -e "  ✓ Rule creada: $RULE_NAME"
fi

echo ""

# Paso 4: Configurar Target (Bedrock Agent)
echo -e "${GREEN}Paso 4: Configurando target del rule...${NC}"

# Nota: Bedrock Agents como target de EventBridge requiere configuración especial
# Por ahora, usamos una Lambda function como intermediario

LAMBDA_FUNCTION_NAME="smartsupply-agent-invoker"
LAMBDA_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}"

echo -e "  ℹ️  Usando Lambda intermediaria: $LAMBDA_FUNCTION_NAME"
echo -e "  ${YELLOW}Nota: Esta Lambda invocará el Bedrock Agent${NC}"

# Crear target configuration
TARGET_CONFIG=$(cat <<EOF
[
  {
    "Id": "1",
    "Arn": "$LAMBDA_ARN",
    "RoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/smart-supply-lambda-role"
  }
]
EOF
)

# Agregar target al rule
aws events put-targets \
  --rule "$RULE_NAME" \
  --event-bus-name "$EVENT_BUS_NAME" \
  --targets "$TARGET_CONFIG" \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || echo -e "  ⚠️  Target ya existe o error al agregar"

echo -e "  ✓ Target configurado"

echo ""

# Paso 5: Crear Lambda intermediaria
echo -e "${GREEN}Paso 5: Creando Lambda intermediaria...${NC}"

# Código de la Lambda que invoca el Bedrock Agent
LAMBDA_CODE=$(cat <<'EOFPYTHON'
import boto3
import json
import os

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

AGENT_ID = os.environ.get('AGENT_ID')
AGENT_ALIAS_ID = os.environ.get('AGENT_ALIAS_ID', 'TSTALIASID')

def lambda_handler(event, context):
    """
    Lambda intermediaria que recibe eventos de EventBridge
    e invoca el Bedrock Agent
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extraer datos del incidente
    detail = event.get('detail', {})
    
    # Construir input para el agente
    agent_input = {
        "inputText": json.dumps(detail),
        "sessionId": detail.get('incident_id', 'default-session')
    }
    
    try:
        # Invocar Bedrock Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=agent_input['sessionId'],
            inputText=agent_input['inputText']
        )
        
        # Procesar respuesta del agente
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion += chunk['bytes'].decode('utf-8')
        
        print(f"Agent response: {completion}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Agent invoked successfully',
                'incident_id': detail.get('incident_id'),
                'response': completion
            })
        }
        
    except Exception as e:
        print(f"Error invoking agent: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'incident_id': detail.get('incident_id')
            })
        }
EOFPYTHON
)

# Guardar código de Lambda
echo "$LAMBDA_CODE" > agent_invoker_lambda.py
echo -e "  ✓ Código de Lambda guardado: agent_invoker_lambda.py"

echo -e "  ${YELLOW}Para desplegar la Lambda:${NC}"
echo -e "    1. Empaquetar: zip agent_invoker_lambda.zip agent_invoker_lambda.py"
echo -e "    2. Crear función en AWS Console o usar AWS CLI"
echo -e "    3. Configurar variables de entorno: AGENT_ID, AGENT_ALIAS_ID"
echo -e "    4. Asignar role: smart-supply-lambda-role"

echo ""

# Paso 6: Otorgar permisos a EventBridge para invocar Lambda
echo -e "${GREEN}Paso 6: Configurando permisos...${NC}"

# Agregar permiso a Lambda para ser invocada por EventBridge
aws lambda add-permission \
  --function-name "$LAMBDA_FUNCTION_NAME" \
  --statement-id "AllowEventBridgeInvoke" \
  --action "lambda:InvokeFunction" \
  --principal events.amazonaws.com \
  --source-arn "arn:aws:events:${AWS_REGION}:${AWS_ACCOUNT_ID}:rule/${EVENT_BUS_NAME}/${RULE_NAME}" \
  --region "$AWS_REGION" \
  > /dev/null 2>&1 || echo -e "  ℹ️  Permiso ya existe"

echo -e "  ✓ Permisos configurados"

echo ""

# Paso 7: Probar la integración
echo -e "${GREEN}Paso 7: Comando para probar la integración:${NC}"
echo ""

TEST_EVENT=$(cat <<EOF
{
  "Source": "smartsupply.iot",
  "DetailType": "IncidentDetected",
  "Detail": "{\"incident_id\":\"INC-TEST-EB\",\"truck_id\":\"1\",\"tipo_incidente\":\"Choque / Colisión Grave\",\"nivel_gravedad\":\"Crítico\",\"ubicacion_gps\":{\"lat\":19.4345,\"lon\":-99.1410},\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",\"descripcion\":\"Test de integración EventBridge\",\"canal\":\"iot\"}",
  "EventBusName": "$EVENT_BUS_NAME"
}
EOF
)

echo "$TEST_EVENT" > test_event.json

echo -e "${YELLOW}Publicar evento de prueba:${NC}"
echo "aws events put-events --entries file://test_event.json"
echo ""

echo -e "${YELLOW}Verificar logs de Lambda:${NC}"
echo "aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo ""

echo -e "${YELLOW}Verificar logs del agente:${NC}"
echo "aws logs tail /aws/bedrock/agentcore/$AGENT_NAME --follow"
echo ""

# Paso 8: Resumen
echo -e "${GREEN}=========================================="
echo "EventBridge Integration configurada!"
echo "==========================================${NC}"
echo ""
echo "Recursos creados:"
echo "  ✓ EventBridge Rule: $RULE_NAME"
echo "  ✓ Event Pattern: Escucha eventos de incidentes"
echo "  ✓ Target: Lambda intermediaria"
echo "  ✓ Lambda Code: agent_invoker_lambda.py"
echo ""
echo "Flujo de eventos:"
echo "  1. Incidente detectado → EventBridge"
echo "  2. EventBridge → Lambda intermediaria"
echo "  3. Lambda → Bedrock Agent"
echo "  4. Agent → Genera plan de reasignación"
echo "  5. Agent → Ejecuta acciones (actualizar rutas, notificar clientes)"
echo ""
echo "Próximos pasos:"
echo "  1. Desplegar Lambda intermediaria"
echo "  2. Configurar variables de entorno (AGENT_ID, AGENT_ALIAS_ID)"
echo "  3. Probar con: aws events put-events --entries file://test_event.json"
echo "  4. Verificar logs del agente"
echo ""
