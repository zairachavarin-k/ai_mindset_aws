# Solicitar Acceso a Claude en AWS Bedrock

## ⚠️ Error Actual

```
ResourceNotFoundException: Model use case details have not been submitted for this account.
```

Esto significa que necesitas solicitar acceso a los modelos de Claude en AWS Bedrock.

## 🔑 Pasos para Solicitar Acceso

### 1. Ir a AWS Bedrock Console

Abre tu navegador y ve a:
```
https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
```

O navega manualmente:
1. AWS Console → Servicios
2. Busca "Bedrock"
3. En el menú lateral: "Model access"

### 2. Solicitar Acceso

1. Click en **"Manage model access"** o **"Edit"**
2. Busca **"Anthropic"** en la lista
3. Selecciona los modelos:
   - ✅ **Claude 3 Haiku** (recomendado - más rápido y económico)
   - ✅ **Claude 3 Sonnet** (opcional - más potente)
   - ✅ **Claude 3.5 Sonnet** (opcional - más reciente)
4. Click en **"Request model access"** o **"Save changes"**

### 3. Esperar Aprobación

- **Claude 3 Haiku**: Usualmente aprobación instantánea ✅
- **Claude 3 Sonnet**: Puede requerir aprobación (1-15 minutos)
- **Claude 3.5 Sonnet**: Puede requerir formulario de caso de uso

### 4. Verificar Acceso

Ejecuta este comando para verificar:

```bash
aws bedrock list-foundation-models \
  --region us-east-1 \
  --by-provider anthropic \
  --query 'modelSummaries[].{ModelId:modelId,Status:modelLifecycle.status}'
```

Deberías ver:
```json
[
    {
        "ModelId": "anthropic.claude-3-haiku-20240307-v1:0",
        "Status": "ACTIVE"
    }
]
```

## 🎯 Modelos Recomendados

### Claude 3 Haiku (Recomendado para empezar)
- **ID**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Ventajas**: Rápido, económico, aprobación instantánea
- **Costo**: ~$0.25 por 1M tokens input
- **Uso**: Perfecto para chat y tareas generales

### Claude 3 Sonnet
- **ID**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Ventajas**: Más potente, mejor razonamiento
- **Costo**: ~$3 por 1M tokens input
- **Uso**: Tareas complejas

### Claude 3.5 Sonnet (Más reciente)
- **ID**: `anthropic.claude-3-5-sonnet-20240620-v1:0`
- **Ventajas**: Última versión, mejor rendimiento
- **Costo**: ~$3 por 1M tokens input
- **Uso**: Tareas más avanzadas

## 📝 Formulario de Caso de Uso

Si te piden llenar un formulario, aquí hay un ejemplo:

**Use Case**: Logistics Management System
**Description**: AI-powered multi-agent system for fleet tracking, route optimization, and inventory management
**Industry**: Logistics & Transportation
**Expected Monthly Usage**: < 1M tokens
**Data Sensitivity**: Low (test data only)

## 🔍 Troubleshooting

### Error: "Model not found"
- Verifica que solicitaste acceso al modelo correcto
- Espera 15 minutos después de la aprobación
- Verifica la región (debe ser us-east-1)

### Error: "Access denied"
- Verifica tus credenciales AWS
- Asegúrate de tener permisos de Bedrock en tu IAM user/role

### Error: "Throttling"
- Estás haciendo demasiadas requests
- Espera unos segundos entre requests

## ✅ Una Vez Aprobado

1. Reinicia el servidor:
   ```bash
   python3 main.py
   ```

2. Prueba el chat:
   - "Hola, ¿cómo estás?"
   - "¿Qué puedes hacer?"
   - "¿Dónde están los camiones?"

3. Verás en los logs:
   ```
   ✓ Usando modelo: anthropic.claude-3-haiku-20240307-v1:0
   ```

## 🚀 Siguiente Paso

Una vez que tengas acceso aprobado, el sistema funcionará automáticamente. No necesitas cambiar ningún código.

## 💡 Alternativa Temporal

Si no puedes obtener acceso a Claude, puedo modificar el sistema para usar:
- Amazon Titan (modelo de AWS)
- Meta Llama (open source)
- Mistral AI

Déjame saber si necesitas esta alternativa.
