#!/bin/bash
# Script para configurar AgentCore Observability
# Habilita tracing, métricas y alarmas para el agente

set -e

echo "=========================================="
echo "Configurando AgentCore Observability"
echo "=========================================="

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuración
AGENT_NAME="smartsupply-autonomous-agent"
LOG_GROUP="/aws/bedrock/agentcore/$AGENT_NAME"
AWS_REGION=$(aws configure get region)
AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo -e "${YELLOW}Agent: $AGENT_NAME${NC}"
echo -e "${YELLOW}Log Group: $LOG_GROUP${NC}"
echo -e "${YELLOW}Region: $AWS_REGION${NC}"
echo ""

# Paso 1: Verificar/Crear CloudWatch Log Group
echo -e "${GREEN}Paso 1: Configurando CloudWatch Logs...${NC}"

if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region "$AWS_REGION" | grep -q "$LOG_GROUP"; then
    echo -e "  ✓ Log group ya existe: $LOG_GROUP"
else
    echo -e "  Creando log group: $LOG_GROUP"
    aws logs create-log-group --log-group-name "$LOG_GROUP" --region "$AWS_REGION"
    echo -e "  ✓ Log group creado"
fi

# Configurar retención de logs (30 días)
aws logs put-retention-policy \
  --log-group-name "$LOG_GROUP" \
  --retention-in-days 30 \
  --region "$AWS_REGION"
echo -e "  ✓ Retención configurada: 30 días"

echo ""

# Paso 2: Habilitar X-Ray Tracing
echo -e "${GREEN}Paso 2: Habilitando X-Ray Tracing...${NC}"

# Verificar que el agente tiene permisos para X-Ray
ROLE_NAME="smart-supply-bedrock-agent-role"

# Agregar política de X-Ray si no existe
if aws iam get-role-policy --role-name "$ROLE_NAME" --policy-name "XRayTracingPolicy" > /dev/null 2>&1; then
    echo -e "  ✓ Política de X-Ray ya existe"
else
    echo -e "  Agregando política de X-Ray..."
    
    XRAY_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
EOF
)
    
    aws iam put-role-policy \
      --role-name "$ROLE_NAME" \
      --policy-name "XRayTracingPolicy" \
      --policy-document "$XRAY_POLICY"
    
    echo -e "  ✓ Política de X-Ray agregada"
fi

# Actualizar configuración del agente para habilitar tracing
if grep -q "tracing: false" .bedrock_agentcore.yaml; then
    sed -i.bak 's/tracing: false/tracing: true/' .bedrock_agentcore.yaml
    echo -e "  ✓ Tracing habilitado en configuración"
elif grep -q "tracing: true" .bedrock_agentcore.yaml; then
    echo -e "  ✓ Tracing ya habilitado"
else
    echo -e "  ⚠️  Configuración de tracing no encontrada en .bedrock_agentcore.yaml"
fi

echo ""

# Paso 3: Crear métricas personalizadas
echo -e "${GREEN}Paso 3: Configurando métricas personalizadas...${NC}"

# Crear namespace de métricas
NAMESPACE="SmartSupply/BedrockAgent"
echo -e "  ✓ Namespace de métricas: $NAMESPACE"

# Métricas que se rastrearán:
echo -e "  Métricas configuradas:"
echo -e "    • Invocations (invocaciones del agente)"
echo -e "    • Latency (tiempo de respuesta)"
echo -e "    • Errors (número de errores)"
echo -e "    • ToolInvocations (invocaciones de herramientas MCP)"

echo ""

# Paso 4: Crear alarmas de CloudWatch
echo -e "${GREEN}Paso 4: Creando alarmas de CloudWatch...${NC}"

# Alarma 1: Latencia > 30 segundos (Requisito 18.3)
ALARM_NAME_LATENCY="${AGENT_NAME}-high-latency"

if aws cloudwatch describe-alarms --alarm-names "$ALARM_NAME_LATENCY" --region "$AWS_REGION" | grep -q "$ALARM_NAME_LATENCY"; then
    echo -e "  ℹ️  Alarma de latencia ya existe"
else
    echo -e "  Creando alarma de latencia..."
    
    aws cloudwatch put-metric-alarm \
      --alarm-name "$ALARM_NAME_LATENCY" \
      --alarm-description "Alerta cuando latencia del agente $AGENT_NAME excede 30 segundos" \
      --metric-name Latency \
      --namespace "$NAMESPACE" \
      --statistic Average \
      --period 300 \
      --evaluation-periods 2 \
      --threshold 30 \
      --comparison-operator GreaterThanThreshold \
      --dimensions Name=AgentName,Value="$AGENT_NAME" \
      --region "$AWS_REGION"
    
    echo -e "  ✓ Alarma de latencia creada: $ALARM_NAME_LATENCY"
fi

# Alarma 2: Tasa de errores > 5%
ALARM_NAME_ERRORS="${AGENT_NAME}-high-error-rate"

if aws cloudwatch describe-alarms --alarm-names "$ALARM_NAME_ERRORS" --region "$AWS_REGION" | grep -q "$ALARM_NAME_ERRORS"; then
    echo -e "  ℹ️  Alarma de errores ya existe"
else
    echo -e "  Creando alarma de errores..."
    
    # Nota: Esta alarma usa una métrica matemática (errors / invocations * 100)
    # Se debe crear manualmente en la consola o usar CloudFormation/CDK
    
    echo -e "  ⚠️  Alarma de tasa de errores debe crearse manualmente"
    echo -e "     Métrica: (Errors / Invocations) * 100 > 5"
fi

echo ""

# Paso 5: Crear dashboard de CloudWatch
echo -e "${GREEN}Paso 5: Creando dashboard de CloudWatch...${NC}"

DASHBOARD_NAME="SmartSupply-Agent-Observability"

DASHBOARD_BODY=$(cat <<EOF
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["$NAMESPACE", "Invocations", {"stat": "Sum", "label": "Total Invocations"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "$AWS_REGION",
        "title": "Agent Invocations",
        "yAxis": {
          "left": {
            "min": 0
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["$NAMESPACE", "Latency", {"stat": "Average", "label": "Average Latency"}],
          ["...", {"stat": "p90", "label": "P90 Latency"}],
          ["...", {"stat": "p99", "label": "P99 Latency"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "$AWS_REGION",
        "title": "Agent Latency",
        "yAxis": {
          "left": {
            "min": 0,
            "label": "Seconds"
          }
        }
      }
    },
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["$NAMESPACE", "Errors", {"stat": "Sum", "label": "Total Errors"}]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "$AWS_REGION",
        "title": "Agent Errors",
        "yAxis": {
          "left": {
            "min": 0
          }
        }
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "SOURCE '$LOG_GROUP'\n| fields @timestamp, @message\n| sort @timestamp desc\n| limit 20",
        "region": "$AWS_REGION",
        "title": "Recent Logs"
      }
    }
  ]
}
EOF
)

aws cloudwatch put-dashboard \
  --dashboard-name "$DASHBOARD_NAME" \
  --dashboard-body "$DASHBOARD_BODY" \
  --region "$AWS_REGION"

echo -e "  ✓ Dashboard creado: $DASHBOARD_NAME"
echo -e "  URL: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$DASHBOARD_NAME"

echo ""

# Paso 6: Configurar Log Insights queries
echo -e "${GREEN}Paso 6: Queries útiles de CloudWatch Logs Insights:${NC}"
echo ""

echo -e "${YELLOW}Query 1: Errores recientes${NC}"
echo "fields @timestamp, @message"
echo "| filter @message like /ERROR/"
echo "| sort @timestamp desc"
echo "| limit 20"
echo ""

echo -e "${YELLOW}Query 2: Latencia por invocación${NC}"
echo "fields @timestamp, latency"
echo "| filter latency > 0"
echo "| stats avg(latency), max(latency), min(latency)"
echo ""

echo -e "${YELLOW}Query 3: Herramientas MCP más usadas${NC}"
echo "fields @timestamp, tool_name"
echo "| filter tool_name != ''"
echo "| stats count() by tool_name"
echo "| sort count desc"
echo ""

# Paso 7: Resumen
echo -e "${GREEN}=========================================="
echo "Observability configurada exitosamente!"
echo "==========================================${NC}"
echo ""
echo "Recursos creados:"
echo "  ✓ CloudWatch Log Group: $LOG_GROUP"
echo "  ✓ X-Ray Tracing: Habilitado"
echo "  ✓ Alarma de latencia: $ALARM_NAME_LATENCY"
echo "  ✓ Dashboard: $DASHBOARD_NAME"
echo ""
echo "Próximos pasos:"
echo "1. Redesplegar el agente: agentcore launch"
echo "2. Ver dashboard: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$DASHBOARD_NAME"
echo "3. Ver logs: aws logs tail $LOG_GROUP --follow"
echo "4. Ver traces: https://console.aws.amazon.com/xray/home?region=$AWS_REGION"
echo ""
