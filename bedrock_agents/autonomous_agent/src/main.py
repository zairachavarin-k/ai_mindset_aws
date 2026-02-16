"""
SmartSupply Autonomous Agent - Bedrock AgentCore
Analiza incidentes y genera planes de reasignación automática
"""
from bedrock_agentcore import BedrockAgentCoreApp
from typing import Dict, Any
import json

app = BedrockAgentCoreApp()


@app.entrypoint
async def handle_incident(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Punto de entrada del agente autónomo
    Recibe eventos de incidentes desde EventBridge y genera planes de reasignación
    
    Args:
        event: Evento de incidente con estructura estandarizada
        
    Returns:
        Plan de reasignación completo
    """
    # Extraer datos del incidente
    incident_data = event.get('detail', event)
    
    incident_id = incident_data.get('incident_id')
    truck_id = incident_data.get('truck_id')
    tipo_incidente = incident_data.get('tipo_incidente')
    nivel_gravedad = incident_data.get('nivel_gravedad')
    ubicacion_gps = incident_data.get('ubicacion_gps')
    
    # Construir prompt para el agente
    prompt = f"""
Eres un experto en logística y gestión de crisis. Analiza el siguiente incidente 
y genera un plan de reasignación óptimo en menos de 3 minutos.

INCIDENTE:
- ID: {incident_id}
- Camión afectado: {truck_id}
- Tipo: {tipo_incidente}
- Gravedad: {nivel_gravedad}
- Ubicación: {ubicacion_gps}

PROCESO DE ANÁLISIS:
1. Consulta la ruta afectada y el inventario del camión usando consultar_ruta_afectada
2. Identifica productos dañados/perdidos y su criticidad
3. Consulta flota disponible usando consultar_flota_disponible (considera capacidad, fatiga, distancia)
4. Consulta inventario del almacén usando consultar_inventario_almacen para reabastecimiento
5. Prioriza por: Farma > Salud > Tecnología > Industrial > otros
6. Genera plan con: camión de reemplazo, productos a reabastecer, rutas actualizadas
7. Justifica cada decisión con datos concretos

RESTRICCIONES:
- Nivel de fatiga Alto → excluir camión
- Productos frágiles → priorizar camiones con menor fatiga
- Tiempo total de ejecución < 180 segundos

Genera un plan de reasignación completo en formato JSON.
"""
    
    # El agente procesará el prompt y usará las herramientas MCP disponibles
    # para consultar datos y generar el plan
    
    return {
        "incident_id": incident_id,
        "prompt": prompt,
        "status": "processing"
    }
