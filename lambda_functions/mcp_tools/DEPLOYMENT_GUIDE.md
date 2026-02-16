# Guía de Despliegue - Herramientas MCP

## Prerequisitos

1. AWS CLI configurado con credenciales apropiadas
2. Python 3.11+ instalado
3. AWS CDK instalado (para despliegue automatizado)
4. Infraestructura base desplegada (S3, DynamoDB, IAM roles)

## Opción 1: Despliegue Manual (AWS Console)

### Paso 1: Crear Paquete de Despliegue

Para cada Lambda function:

```bash
cd lambda_functions/mcp_tools

# Crear directorio temporal
mkdir -p package

# Instalar dependencias
pip install -r requirements.txt -t package/

# Copiar código de la función
cp consultar_ruta_afectada.py package/

# Crear ZIP
cd package
zip -r ../consultar_ruta_afectada.zip .
cd ..

# Limpiar
rm -rf package
```

### Paso 2: Crear Lambda Functions en AWS Console

Para cada función:

1. Ir a AWS Lambda Console
2. Crear nueva función
3. Configurar:
   - **Runtime**: Python 3.11
   - **Architecture**: x86_64
   - **Role**: `smart-supply-lambda-role`
   - **Timeout**: 30 segundos
   - **Memory**: 256 MB

4. Subir el archivo ZIP
5. Configurar variables de entorno (ver sección Variables de Entorno)

### Paso 3: Configurar Variables de Entorno

#### consultar_ruta_afectada
```
RUTAS_TABLE_NAME=rutas_entregas
```

#### consultar_flota_disponible
```
FLOTA_TABLE_NAME=flota_camiones
```

#### consultar_inventario_almacen
```
INVENTARIO_TABLE_NAME=inventario_almacen
```

#### calcular_distancia
```
ROUTE_CALCULATOR_NAME=smart-supply-route-calculator
```

#### calcular_ruta_optimizada
```
OPTIMIZACION_LAMBDA_NAME=optimizar-rutas-lambda
```

#### actualizar_ruta_s3
```
DATA_BUCKET_NAME=smart-supply-data
```

#### registrar_incidencia
```
DATA_BUCKET_NAME=smart-supply-data
INCIDENCIAS_TABLE_NAME=incidencias
```

#### enviar_notificacion_cliente
```
CONNECT_INSTANCE_ID=<your-connect-instance-id>
CONTACT_FLOW_ID=<your-contact-flow-id>
SOURCE_PHONE_NUMBER=<your-phone-number>
NOTIFICACIONES_TABLE_NAME=notificaciones_clientes
```

## Opción 2: Despliegue Automatizado con AWS CDK

### Paso 1: Actualizar Infrastructure Stack

Agregar las Lambda functions al stack de CDK:

```python
# En infrastructure/stacks/infrastructure_stack.py

from aws_cdk import (
    aws_lambda as lambda_,
    Duration,
)

# Después de crear las tablas DynamoDB...

# Lambda: consultar_ruta_afectada
self.consultar_ruta_lambda = lambda_.Function(
    self,
    "ConsultarRutaAfectada",
    function_name="smart-supply-consultar-ruta-afectada",
    runtime=lambda_.Runtime.PYTHON_3_11,
    handler="consultar_ruta_afectada.lambda_handler",
    code=lambda_.Code.from_asset("../lambda_functions/mcp_tools"),
    role=self.lambda_role,
    timeout=Duration.seconds(30),
    memory_size=256,
    environment={
        "RUTAS_TABLE_NAME": self.rutas_table.table_name,
    }
)

# Repetir para las otras 7 funciones...
```

### Paso 2: Desplegar

```bash
cd infrastructure
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt

cdk synth
cdk deploy
```

## Opción 3: Despliegue con AWS SAM

### Paso 1: Crear template.yaml

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  ConsultarRutaAfectada:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: smart-supply-consultar-ruta-afectada
      Runtime: python3.11
      Handler: consultar_ruta_afectada.lambda_handler
      CodeUri: .
      Timeout: 30
      MemorySize: 256
      Role: !Sub arn:aws:iam::${AWS::AccountId}:role/smart-supply-lambda-role
      Environment:
        Variables:
          RUTAS_TABLE_NAME: rutas_entregas
  
  # Repetir para las otras funciones...
```

### Paso 2: Desplegar con SAM

```bash
cd lambda_functions/mcp_tools
sam build
sam deploy --guided
```

## Verificación del Despliegue

### Test Individual de Lambda

```bash
# Crear evento de prueba
cat > test_event.json << EOF
{
  "truck_id": "1"
}
EOF

# Invocar Lambda
aws lambda invoke \
  --function-name smart-supply-consultar-ruta-afectada \
  --payload file://test_event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# Ver respuesta
cat response.json
```

### Test desde Python

```python
import boto3
import json

lambda_client = boto3.client('lambda')

response = lambda_client.invoke(
    FunctionName='smart-supply-consultar-ruta-afectada',
    InvocationType='RequestResponse',
    Payload=json.dumps({'truck_id': '1'})
)

result = json.loads(response['Payload'].read())
print(json.dumps(result, indent=2))
```

## Configuración Adicional Requerida

### 1. Amazon Location Service

Crear Route Calculator:

```bash
aws location create-route-calculator \
  --calculator-name smart-supply-route-calculator \
  --data-source Esri \
  --pricing-plan RequestBasedUsage
```

### 2. Tabla de Notificaciones en DynamoDB

```bash
aws dynamodb create-table \
  --table-name notificaciones_clientes \
  --attribute-definitions \
    AttributeName=notificacion_id,AttributeType=S \
  --key-schema \
    AttributeName=notificacion_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 3. Amazon Connect (Opcional)

Si deseas usar notificaciones por voz:

1. Crear instancia de Amazon Connect
2. Crear Contact Flow para llamadas salientes
3. Obtener Instance ID y Contact Flow ID
4. Configurar número de teléfono de origen
5. Actualizar variables de entorno de `enviar_notificacion_cliente`

## Troubleshooting

### Error: "Table does not exist"
- Verificar que las tablas DynamoDB estén creadas
- Verificar nombres de tablas en variables de entorno

### Error: "Access Denied"
- Verificar que el IAM role tenga permisos correctos
- Verificar que el role esté asignado a la Lambda

### Error: "Lambda not found" (calcular_ruta_optimizada)
- Esta función invoca otra Lambda que debe existir
- Crear Lambda `optimizar-rutas-lambda` o actualizar variable de entorno

### Error: "Route calculator not found"
- Crear Route Calculator en Amazon Location Service
- O la función usará fallback a Haversine

## Monitoreo

### CloudWatch Logs

```bash
# Ver logs de una función
aws logs tail /aws/lambda/smart-supply-consultar-ruta-afectada --follow
```

### CloudWatch Metrics

Métricas automáticas disponibles:
- Invocations
- Errors
- Duration
- Throttles

### X-Ray Tracing (Opcional)

Habilitar tracing en cada Lambda:

```bash
aws lambda update-function-configuration \
  --function-name smart-supply-consultar-ruta-afectada \
  --tracing-config Mode=Active
```

## Costos Estimados

Basado en 1000 incidentes/mes:

- Lambda invocations: ~$0.20/mes
- DynamoDB reads/writes: ~$1.00/mes
- S3 storage + requests: ~$0.50/mes
- Location Service: ~$0.40/mes
- Amazon Connect: Variable según uso

**Total estimado**: ~$2-5 USD/mes para 1000 incidentes

## Próximos Pasos

1. ✅ Desplegar Lambda functions
2. ⏳ Configurar Bedrock Agent
3. ⏳ Registrar herramientas en AgentCore Gateway
4. ⏳ Configurar EventBridge rules
5. ⏳ Implementar tests de integración
6. ⏳ Configurar monitoreo y alertas

## Soporte

Para problemas o preguntas:
- Revisar logs en CloudWatch
- Verificar permisos IAM
- Consultar documentación de AWS
- Revisar IMPLEMENTATION_SUMMARY.md para detalles técnicos
