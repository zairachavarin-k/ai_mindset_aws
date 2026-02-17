# LangGraph System - Guía Rápida

## 🚀 Inicio Rápido

### 1. Verificar Instalación

```bash
cd ai_mindset_aws
python3 -m pip list | grep langgraph
```

Deberías ver:
- langgraph
- langchain-aws
- langchain-core

### 2. Probar el Sistema

```bash
# Prueba rápida
python3 test_langgraph.py
```

### 3. Iniciar el Servidor

```bash
python3 main.py
```

### 4. Usar desde el Frontend

1. Abre http://localhost:8000
2. Click en el botón de chat (💬)
3. Escribe mensajes como:
   - "Hola, ¿cómo estás?"
   - "¿Dónde están los camiones?"
   - "¿Tenemos vacunas?"

## 📁 Archivos Creados

```
agents/
├── __init__.py                 # Módulo Python
├── tools.py                    # Herramientas compartidas
├── langgraph_system.py         # Sistema LangGraph
└── LANGGRAPH_README.md         # Documentación completa
```

## 🔧 Solución de Problemas

### Error: ModuleNotFoundError

```bash
# Reinstalar dependencias
python3 -m pip install langgraph langchain-aws langchain-core
```

### Error: AWS Credentials

```bash
# Verificar credenciales
aws sts get-caller-identity
```

### Error: No route plans found

```bash
# Verificar que existe un plan de rutas
ls data/route_plan_*.json
```

## ✅ Verificación

Si todo funciona correctamente:

1. ✅ `python3 test_langgraph.py` ejecuta sin errores
2. ✅ `python3 main.py` inicia el servidor
3. ✅ El chat responde a mensajes
4. ✅ Las respuestas son naturales (no predefinidas)

## 🎯 Diferencia Clave

**Antes**: Respuestas predefinidas con if/else
**Ahora**: Claude con LangGraph decide y responde naturalmente

## 📚 Más Información

Ver `agents/LANGGRAPH_README.md` para documentación completa.
