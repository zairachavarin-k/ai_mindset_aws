#!/bin/bash
# Script para configurar AgentCore Gateway con herramientas MCP
# Expone Lambda functions como herramientas para el Bedrock Agent

set -e

echo "=========================================="
echo "Configurando AgentCore Gateway"
echo "=========================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Nombre del gateway
GATEWAY_NAME="smartsupply-mcp-gateway"

# Verificar que agentcore CLI está instalado
if ! command -v agentcore &> /dev/null; then
    echo "Error: agentcore CLI no está instalado"
    echo "Instalar con: pip install bedrock-agentcore-starter-toolkit"
    exit 1
fi

# Obtener AWS Account ID y Region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${YELLOW}AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo -e "${YELLOW}AWS Region: $AWS_REGION${NC}"
echo ""

# Paso 1: Crear Gateway resource
echo -e "${GREEN}Paso 1: Creando Gateway resource...${NC}"
agentcore gateway create \
  --name "$GATEWAY_NAME" \
  --description "Gateway para herramientas MCP del agente autónomo SmartSupply" \
  || echo "Gateway ya existe, continuando..."

echo ""

# Paso 2: Agregar Lambda functions como targets
echo -e "${GREEN}Paso 2: Agregando Lambda functions como targets...${NC}"

# Lista de Lambda functions (herramientas MCP)
declare -a LAMBDA_FUNCTIONS=(
    "consultar_ruta_afectada"
    "consultar_flota_disponible"
    "consultar_inventario_almacen"
    "calcular_distancia"
    "calcular_ruta_optimizada"
    "actualizar_ruta_s3"
    "registrar_incidencia"
    "enviar_notificacion_cliente"
)

# Agregar cada Lambda function como target
for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
    echo -e "  Agregando: ${YELLOW}$FUNCTION_NAME${NC}"
    
    # Construir ARN de la Lambda function
    FUNCTION_ARN="arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${FUNCTION_NAME}"
    
    # Agregar target al gateway
    agentcore gateway add-target \
      --gateway "$GATEWAY_NAME" \
      --target-type lambda \
      --target-name "$FUNCTION_NAME" \
      --function-arn "$FUNCTION_ARN" \
      || echo "    Target ya existe, continuando..."
done

echo ""

# Paso 3: Configurar permisos IAM
echo -e "${GREEN}Paso 3: Configurando permisos IAM...${NC}"

# El IAM role del agente ya tiene permisos para invocar Lambda functions
# (configurado en infrastructure/stacks/infrastructure_stack.py)
echo "  Permisos IAM ya configurados en el stack de infraestructura"

echo ""

# Paso 4: Asociar Gateway con el agente
echo -e "${GREEN}Paso 4: Asociando Gateway con el agente...${NC}"

# Obtener el nombre del agente
AGENT_NAME="smartsupply-autonomous-agent"

# Asociar gateway con el agente
agentcore gateway attach \
  --gateway "$GATEWAY_NAME" \
  --agent "$AGENT_NAME" \
  || echo "Gateway ya está asociado, continuando..."

echo ""

# Paso 5: Verificar configuración
echo -e "${GREEN}Paso 5: Verificando configuración...${NC}"

echo "  Listando gateways:"
agentcore gateway list

echo ""
echo "  Listando targets del gateway:"
agentcore gateway list-targets --gateway "$GATEWAY_NAME"

echo ""
echo -e "${GREEN}=========================================="
echo "Gateway configurado exitosamente!"
echo "==========================================${NC}"
echo ""
echo "Próximos pasos:"
echo "1. Redesplegar el agente: agentcore launch"
echo "2. Probar herramientas: agentcore invoke '{\"detail\": {...}}'"
echo ""
