# Routing Tools - Guía de Despliegue

Guía paso a paso para desplegar las Lambda functions del Agente de Ruteo.

## Pre-requisitos

- AWS CLI configurado
- Python 3.11+
- Cuenta de AWS con permisos para Lambda, IAM, S3
- (Opcional) Google Maps API Key
- (Opcional) OpenWeatherMap API Key

## Paso 1: Preparar Paquetes de Deployment

```bash
cd lambda_functions/routing_tools

# Crear directorio para paquetes
mkdir -p packages

# Instalar dependencias
pip install -r requirements.txt -t packages/

# Copiar código de las funciones
cp *.py packages/
```

## Paso 2: Crear Rol de Ejecución IAM

```bash
# Crear política de confianza
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Crear rol
aws iam create-role \
  --role-name smartsupply-routing-lambda-role \
  --assume-role-policy-document file://trust-policy.json

# Adjuntar políticas necesarias
aws iam attach-role-policy \
  --role-name smartsupply-routing-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name smartsupply-routing-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Obtener ARN del rol (guardar para siguiente paso)
aws iam get-role \
  --role-name smartsupply-routing-lambda-role \
  --query 'Role.Arn' \
  --output text
```

## Paso 3: Desplegar Lambda Functions

### Opción A: Despliegue Manual

```bash
cd packages

# Crear ZIP para cada función
for func in consultar_trafico consultar_clima validar_ventanas_entrega \
            calcular_distancia_matriz optimizar_ruta_tsp optimizar_ruta_mtsp \
            calcular_tiempo_real considerar_fatiga_conductor validar_restricciones_ruta
do
  echo "Desplegando $func..."
  
  # Crear función Lambda
  aws lambda create-function \
    --function-name "smartsupply-routing-$func" \
    --runtime python3.11 \
    --handler "${func}.lambda_handler" \
    --role arn:aws:iam::ACCOUNT_ID:role/smartsupply-routing-lambda-role \
    --zip-file fileb://../packages.zip \
    --timeout 60 \
    --memory-size 512 \
    --environment Variables={BUCKET_NAME=smart-supply-data}
done
```

### Opción B: Despliegue con CDK (Recomendado)

El CDK stack ya incluye las Lambda functions. Solo ejecutar:

```bash
cd infrastructure
./deploy.sh
```

## Paso 4: Configurar Variables de Entorno

### Google Maps API (opcional)

```bash
aws lambda update-function-configuration \
  --function-name smartsupply-routing-consultar_trafico \
  --environment Variables={GOOGLE_MAPS_API_KEY=YOUR_KEY_HERE}
```

### OpenWeatherMap API (opcional)

```bash
aws lambda update-function-configuration \
  --function-name smartsupply-routing-consultar_clima \
  --environment Variables={OPENWEATHER_API_KEY=YOUR_KEY_HERE}
```

### S3 Bucket

```bash
# Configurar bucket para todas las funciones
for func in consultar_trafico consultar_clima validar_ventanas_entrega \
            calcular_distancia_matriz optimizar_ruta_tsp optimizar_ruta_mtsp \
            calcular_tiempo_real considerar_fatiga_conductor validar_restricciones_ruta
do
  aws lambda update-function-configuration \
    --function-name "smartsupply-routing-$func" \
    --environment Variables={BUCKET_NAME=smart-supply-data}
done
```

## Paso 5: Testing de Lambda Functions

### Test Individual

```bash
# Test consultar_trafico
aws lambda invoke \
  --function-name smartsupply-routing-consultar_trafico \
  --payload '{"origen":{"lat":19.4384,"lon":-99.1569},"destino":{"lat":19.4345,"lon":-99.1410}}' \
  response.json

cat response.json | jq .

# Test optimizar_ruta_mtsp
aws lambda invoke \
  --function-name smartsupply-routing-optimizar_ruta_mtsp \
  --payload file://test_mtsp.json \
  response.json

cat response.json | jq .
```

### Test Suite Completo

```bash
# Crear script de testing
cat > test_all_functions.sh << 'EOF'
#!/bin/bash

FUNCTIONS=(
  "consultar_trafico"
  "consultar_clima"
  "validar_ventanas_entrega"
  "calcular_distancia_matriz"
  "optimizar_ruta_tsp"
  "optimizar_ruta_mtsp"
  "calcular_tiempo_real"
  "considerar_fatiga_conductor"
  "validar_restricciones_ruta"
)

for func in "${FUNCTIONS[@]}"
do
  echo "Testing $func..."
  aws lambda invoke \
    --function-name "smartsupply-routing-$func" \
    --payload file://test_payloads/${func}.json \
    response_${func}.json
  
  if [ $? -eq 0 ]; then
    echo "✅ $func OK"
  else
    echo "❌ $func FAILED"
  fi
done
EOF

chmod +x test_all_functions.sh
./test_all_functions.sh
```

## Paso 6: Configurar MCP Gateway

```bash
cd bedrock_agents/routing_agent

# Configurar gateway con las Lambda functions
agentcore gateway configure \
  --gateway-name smartsupply-routing-gateway \
  --tools-schema mcp_tools_schema.json

# Verificar configuración
agentcore gateway list
```

## Paso 7: Desplegar Agente de Ruteo

```bash
cd bedrock_agents/routing_agent

# Configurar agente
agentcore configure \
  --entrypoint src.main:app \
  --non-interactive

# Desplegar
agentcore launch

# Obtener Agent ID (guardar para siguiente paso)
agentcore status
```

## Paso 8: Configurar Agente Autónomo

Actualizar la Lambda function `invocar_agente_ruteo`:

```bash
# Obtener Agent ID del Agente de Ruteo
ROUTING_AGENT_ID=$(agentcore status | grep "Agent ID" | awk '{print $3}')

# Configurar en Lambda del Agente Autónomo
aws lambda update-function-configuration \
  --function-name smartsupply-invocar_agente_ruteo \
  --environment Variables={ROUTING_AGENT_ID=$ROUTING_AGENT_ID,ROUTING_AGENT_ALIAS_ID=TSTALIASID}
```

## Paso 9: Testing End-to-End

```bash
# Test 1: Invocar Agente de Ruteo directamente
aws bedrock-agent-runtime invoke-agent \
  --agent-id $ROUTING_AGENT_ID \
  --agent-alias-id TSTALIASID \
  --session-id test-session-1 \
  --input-text "Calcula ruta optimizada para 3 camiones con 8 paradas en Ciudad de México"

# Test 2: Invocar desde Agente Autónomo
aws events put-events --entries '[{
  "Source": "smartsupply.iot",
  "DetailType": "IncidentDetected",
  "Detail": "{\"incident_id\":\"INC-TEST-ROUTING\",\"truck_id\":\"1\",\"tipo_incidente\":\"Choque / Colisión Grave\"}",
  "EventBusName": "smart-supply-events"
}]'

# Verificar logs
aws logs tail /aws/bedrock/agentcore/smartsupply-autonomous-agent --follow
aws logs tail /aws/bedrock/agentcore/smartsupply-routing-agent --follow
```

## Paso 10: Monitoreo y Alarmas

```bash
# Crear alarma para errores
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-routing-errors \
  --alarm-description "Errores en Lambda functions de ruteo" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1

# Crear alarma para latencia
aws cloudwatch put-metric-alarm \
  --alarm-name smartsupply-routing-latency \
  --alarm-description "Latencia alta en optimización mTSP" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=smartsupply-routing-optimizar_ruta_mtsp \
  --statistic Average \
  --period 300 \
  --threshold 30000 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

## Troubleshooting

### Error: "ROUTING_AGENT_ID no está configurado"

```bash
# Verificar que el Agente de Ruteo está desplegado
cd bedrock_agents/routing_agent
agentcore status

# Si no está desplegado
agentcore launch

# Configurar variable de entorno
ROUTING_AGENT_ID=$(agentcore status | grep "Agent ID" | awk '{print $3}')
aws lambda update-function-configuration \
  --function-name smartsupply-invocar_agente_ruteo \
  --environment Variables={ROUTING_AGENT_ID=$ROUTING_AGENT_ID}
```

### Error: "Access Denied" en S3

```bash
# Verificar permisos del rol
aws iam list-attached-role-policies \
  --role-name smartsupply-routing-lambda-role

# Agregar política de S3 si falta
aws iam attach-role-policy \
  --role-name smartsupply-routing-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

### Error: "Timeout" en optimizar_ruta_mtsp

```bash
# Aumentar timeout y memoria
aws lambda update-function-configuration \
  --function-name smartsupply-routing-optimizar_ruta_mtsp \
  --timeout 120 \
  --memory-size 1024
```

### Error: API Keys no funcionan

```bash
# Verificar variables de entorno
aws lambda get-function-configuration \
  --function-name smartsupply-routing-consultar_trafico \
  --query 'Environment.Variables'

# Actualizar si es necesario
aws lambda update-function-configuration \
  --function-name smartsupply-routing-consultar_trafico \
  --environment Variables={GOOGLE_MAPS_API_KEY=YOUR_KEY}
```

## Costos Estimados

### Lambda Functions

- **Invocaciones**: $0.20 por 1M invocaciones
- **Duración**: $0.0000166667 por GB-segundo
- **Estimado mensual**: ~$5-10 USD (100 incidentes/día)

### APIs Externas

- **Google Maps Traffic API**: $5 por 1000 requests
- **OpenWeatherMap API**: Gratis hasta 1000 requests/día
- **Estimado mensual**: ~$15-20 USD

### Bedrock Agent

- **Invocaciones**: $0.003 por request
- **Tokens**: Variable según modelo
- **Estimado mensual**: ~$30-50 USD

**Total estimado**: ~$50-80 USD/mes

## Optimizaciones

### Reducir Costos

1. **Cachear resultados de tráfico/clima** (5 minutos)
2. **Usar Lambda Provisioned Concurrency** solo en horas pico
3. **Reducir iteraciones de ACO** en optimizar_ruta_mtsp
4. **Usar API gratuitas** cuando sea posible

### Mejorar Performance

1. **Aumentar memoria Lambda** para funciones de optimización
2. **Usar Lambda Layers** para dependencias compartidas
3. **Implementar circuit breaker** para APIs externas
4. **Agregar retry logic** con exponential backoff

## Referencias

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Google Maps API](https://developers.google.com/maps/documentation)
- [OpenWeatherMap API](https://openweathermap.org/api)

---

**Última actualización**: 2026-02-17
