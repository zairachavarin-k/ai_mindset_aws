#!/bin/bash
# Script para configurar AgentCore Memory
# Permite al agente aprender de decisiones previas

set -e

echo "=========================================="
echo "Configurando AgentCore Memory"
echo "=========================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
AGENT_NAME="smartsupply-autonomous-agent"
MEMORY_TABLE="agent_memory"
AWS_REGION=$(aws configure get region)
AWS_REGION=${AWS_REGION:-us-east-1}

echo -e "${YELLOW}Agent: $AGENT_NAME${NC}"
echo -e "${YELLOW}Memory Table: $MEMORY_TABLE${NC}"
echo -e "${YELLOW}Region: $AWS_REGION${NC}"
echo ""

# Paso 1: Verificar que la tabla DynamoDB existe
echo -e "${GREEN}Paso 1: Verificando tabla DynamoDB...${NC}"

if aws dynamodb describe-table --table-name "$MEMORY_TABLE" --region "$AWS_REGION" > /dev/null 2>&1; then
    echo -e "  ✓ Tabla $MEMORY_TABLE existe"
else
    echo -e "  ✗ Tabla $MEMORY_TABLE no existe"
    echo "  Desplegar infraestructura CDK primero: cd infrastructure && ./deploy.sh"
    exit 1
fi

echo ""

# Paso 2: Verificar estructura de la tabla
echo -e "${GREEN}Paso 2: Verificando estructura de la tabla...${NC}"

TABLE_INFO=$(aws dynamodb describe-table --table-name "$MEMORY_TABLE" --region "$AWS_REGION")

# Verificar partition key
PK=$(echo "$TABLE_INFO" | jq -r '.Table.KeySchema[] | select(.KeyType=="HASH") | .AttributeName')
if [ "$PK" == "memory_id" ]; then
    echo -e "  ✓ Partition Key: memory_id"
else
    echo -e "  ✗ Partition Key incorrecto: $PK (esperado: memory_id)"
fi

# Verificar sort key
SK=$(echo "$TABLE_INFO" | jq -r '.Table.KeySchema[] | select(.KeyType=="RANGE") | .AttributeName')
if [ "$SK" == "timestamp" ]; then
    echo -e "  ✓ Sort Key: timestamp"
else
    echo -e "  ✗ Sort Key incorrecto: $SK (esperado: timestamp)"
fi

# Verificar GSI
GSI=$(echo "$TABLE_INFO" | jq -r '.Table.GlobalSecondaryIndexes[]? | select(.IndexName=="tipo_incidente-index") | .IndexName')
if [ "$GSI" == "tipo_incidente-index" ]; then
    echo -e "  ✓ GSI: tipo_incidente-index"
else
    echo -e "  ⚠️  GSI tipo_incidente-index no encontrado"
fi

echo ""

# Paso 3: Actualizar configuración del agente
echo -e "${GREEN}Paso 3: Actualizando configuración del agente...${NC}"

# Verificar que el archivo .bedrock_agentcore.yaml existe
if [ ! -f ".bedrock_agentcore.yaml" ]; then
    echo -e "  ✗ Archivo .bedrock_agentcore.yaml no encontrado"
    echo "  Ejecutar desde el directorio del agente: bedrock_agents/autonomous_agent/"
    exit 1
fi

# Backup del archivo original
cp .bedrock_agentcore.yaml .bedrock_agentcore.yaml.backup
echo -e "  ✓ Backup creado: .bedrock_agentcore.yaml.backup"

# Actualizar configuración de memoria
# Cambiar de NO_MEMORY a STM_AND_LTM
if grep -q "mode: NO_MEMORY" .bedrock_agentcore.yaml; then
    sed -i.bak 's/mode: NO_MEMORY/mode: STM_AND_LTM/' .bedrock_agentcore.yaml
    echo -e "  ✓ Modo de memoria actualizado: NO_MEMORY → STM_AND_LTM"
else
    echo -e "  ℹ️  Modo de memoria ya configurado"
fi

# Agregar table_name si no existe
if ! grep -q "table_name:" .bedrock_agentcore.yaml; then
    # Insertar table_name después de la línea mode
    sed -i.bak "/mode: STM_AND_LTM/a\\    table_name: $MEMORY_TABLE" .bedrock_agentcore.yaml
    echo -e "  ✓ Table name agregado: $MEMORY_TABLE"
else
    echo -e "  ℹ️  Table name ya configurado"
fi

echo ""

# Paso 4: Mostrar configuración actualizada
echo -e "${GREEN}Paso 4: Configuración de memoria actualizada:${NC}"
echo ""
grep -A 3 "memory:" .bedrock_agentcore.yaml
echo ""

# Paso 5: Instrucciones para redespliegue
echo -e "${GREEN}Paso 5: Próximos pasos${NC}"
echo ""
echo "Para aplicar los cambios, redesplegar el agente:"
echo ""
echo -e "  ${YELLOW}agentcore launch${NC}"
echo ""
echo "Después del despliegue, el agente:"
echo "  • Almacenará decisiones en DynamoDB"
echo "  • Consultará memoria antes de decidir"
echo "  • Aprenderá de casos similares previos"
echo ""

# Paso 6: Crear registro de memoria de ejemplo
echo -e "${GREEN}Paso 6: Creando registro de memoria de ejemplo...${NC}"

EXAMPLE_MEMORY=$(cat <<EOF
{
  "memory_id": {"S": "MEM-EXAMPLE-001"},
  "timestamp": {"S": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"},
  "tipo_incidente": {"S": "Choque / Colisión Grave"},
  "decision_tomada": {"M": {
    "camion_reemplazo": {"S": "3"},
    "productos_reabastecidos": {"L": [{"S": "FAR-001"}]},
    "justificacion": {"S": "Camión 3 más cercano con capacidad suficiente y nivel de fatiga Bajo"}
  }},
  "resultado": {"M": {
    "tiempo_respuesta_segundos": {"N": "145"},
    "satisfaccion_cliente": {"N": "4.5"},
    "valor_perdidas_evitadas_usd": {"N": "15000"}
  }}
}
EOF
)

echo "$EXAMPLE_MEMORY" > example_memory.json
echo -e "  ✓ Ejemplo guardado en: example_memory.json"

echo ""
echo "Para insertar el ejemplo en DynamoDB:"
echo -e "  ${YELLOW}aws dynamodb put-item --table-name $MEMORY_TABLE --item file://example_memory.json${NC}"
echo ""

echo -e "${GREEN}=========================================="
echo "Configuración de memoria completada!"
echo "==========================================${NC}"
echo ""
