# Configuración de OpenAI API

## 🔑 Obtener tu API Key

1. Ve a https://platform.openai.com/api-keys
2. Inicia sesión o crea una cuenta
3. Haz clic en "Create new secret key"
4. Copia la API key (empieza con `sk-...`)

## ⚙️ Configurar en el Proyecto

1. Abre el archivo `.env` en la carpeta `ai_mindset_aws`
2. Reemplaza `your-api-key-here` con tu API key:

```env
OPENAI_API_KEY=sk-tu-api-key-aqui
OPENAI_MODEL=gpt-4o-mini
```

## 💰 Modelos Disponibles

### gpt-4o-mini (Recomendado)
- **Precio**: ~$0.15 por 1M tokens input, ~$0.60 por 1M tokens output
- **Velocidad**: Muy rápido
- **Calidad**: Excelente para la mayoría de tareas
- **Uso recomendado**: Chat, consultas generales

### gpt-4o
- **Precio**: ~$2.50 por 1M tokens input, ~$10 por 1M tokens output
- **Velocidad**: Rápido
- **Calidad**: Máxima calidad
- **Uso recomendado**: Tareas complejas, análisis avanzado

### gpt-3.5-turbo
- **Precio**: ~$0.50 por 1M tokens input, ~$1.50 por 1M tokens output
- **Velocidad**: Muy rápido
- **Calidad**: Buena
- **Uso recomendado**: Tareas simples, alta frecuencia

## 🚀 Iniciar el Sistema

Una vez configurada la API key:

```bash
cd ai_mindset_aws
python3 main.py
```

Deberías ver:
```
INFO:main:Starting FastAPI server...
```

## ✅ Probar el Sistema

1. Abre http://localhost:8000
2. Haz clic en el botón de chat 💬
3. Prueba:
   - "Hola"
   - "¿Dónde está el camión 3?"
   - "¿Qué tan lejos está el camión 2 del 4?"

## 🐛 Troubleshooting

### Error: "No se pudo conectar con OpenAI"
- Verifica que la API key esté correctamente copiada en `.env`
- Asegúrate de que no haya espacios extra
- La API key debe empezar con `sk-`

### Error: "Rate limit exceeded"
- Has excedido el límite de requests
- Espera unos minutos o agrega créditos en OpenAI

### Error: "Invalid API key"
- La API key es incorrecta o ha expirado
- Genera una nueva en https://platform.openai.com/api-keys

## 💡 Ventajas de OpenAI vs AWS Bedrock

✅ No requiere método de pago en AWS
✅ Mejor seguimiento de instrucciones
✅ Cálculos más precisos
✅ Respuestas más naturales
✅ Más fácil de configurar
✅ Mejor manejo de contexto

## 📊 Estimación de Costos

Para un uso típico del chat de logística:

- **Consultas simples**: ~500 tokens = $0.0001 (menos de 1 centavo)
- **Consultas con cálculos**: ~1000 tokens = $0.0002
- **100 consultas al día**: ~$0.02/día = $0.60/mes

Es muy económico para uso normal.

## 🔒 Seguridad

- ⚠️ NUNCA compartas tu API key
- ⚠️ NO la subas a GitHub (el archivo `.env` está en `.gitignore`)
- ⚠️ Rótala periódicamente en OpenAI dashboard
- ✅ Configura límites de gasto en OpenAI

## 📝 Cambiar de Modelo

Para usar un modelo diferente, edita `.env`:

```env
# Para máxima calidad
OPENAI_MODEL=gpt-4o

# Para máxima economía
OPENAI_MODEL=gpt-3.5-turbo

# Balance (recomendado)
OPENAI_MODEL=gpt-4o-mini
```

Reinicia el servidor después de cambiar.
