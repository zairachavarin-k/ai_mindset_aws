"""
Script de prueba local para las Lambda functions MCP
Ejecutar: python test_local.py
"""
import json
import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

# Configurar variables de entorno para testing local
os.environ['RUTAS_TABLE_NAME'] = 'rutas_entregas'
os.environ['FLOTA_TABLE_NAME'] = 'flota_camiones'
os.environ['INVENTARIO_TABLE_NAME'] = 'inventario_almacen'
os.environ['DATA_BUCKET_NAME'] = 'smart-supply-data'
os.environ['INCIDENCIAS_TABLE_NAME'] = 'incidencias'
os.environ['ROUTE_CALCULATOR_NAME'] = 'smart-supply-route-calculator'
os.environ['OPTIMIZACION_LAMBDA_NAME'] = 'optimizar-rutas-lambda'
os.environ['NOTIFICACIONES_TABLE_NAME'] = 'notificaciones_clientes'

# Importar las funciones
try:
    from consultar_ruta_afectada import lambda_handler as consultar_ruta
    from consultar_flota_disponible import lambda_handler as consultar_flota
    from consultar_inventario_almacen import lambda_handler as consultar_inventario
    from calcular_distancia import lambda_handler as calcular_distancia
    from calcular_ruta_optimizada import lambda_handler as calcular_ruta_optimizada
    from actualizar_ruta_s3 import lambda_handler as actualizar_ruta_s3
    from registrar_incidencia import lambda_handler as registrar_incidencia
    from enviar_notificacion_cliente import lambda_handler as enviar_notificacion
    
    print("✅ Todas las funciones importadas correctamente\n")
except ImportError as e:
    print(f"❌ Error importando funciones: {e}")
    sys.exit(1)


def test_function(name, handler, event):
    """Prueba una función Lambda localmente"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    print(f"Input: {json.dumps(event, indent=2)}")
    
    try:
        # Nota: Esto fallará si no hay credenciales AWS configuradas
        # pero al menos valida que el código no tiene errores de sintaxis
        response = handler(event, {})
        print(f"\nOutput: {json.dumps(response, indent=2)}")
        
        status_code = response.get('statusCode', 500)
        if status_code == 200:
            print(f"✅ {name} - SUCCESS")
        else:
            print(f"⚠️  {name} - Returned status {status_code}")
            
    except Exception as e:
        print(f"❌ {name} - ERROR: {str(e)}")
        print("   (Esto es esperado si no hay credenciales AWS configuradas)")


def main():
    """Ejecuta pruebas de todas las funciones"""
    print("\n" + "="*60)
    print("PRUEBAS LOCALES DE LAMBDA FUNCTIONS MCP")
    print("="*60)
    print("\nNota: Estas pruebas validarán la sintaxis y estructura del código.")
    print("Para pruebas completas, se requieren credenciales AWS y recursos desplegados.\n")
    
    # Test 1: consultar_ruta_afectada
    test_function(
        "consultar_ruta_afectada",
        consultar_ruta,
        {"truck_id": "1"}
    )
    
    # Test 2: consultar_flota_disponible
    test_function(
        "consultar_flota_disponible",
        consultar_flota,
        {"excluir_fatiga_alta": True}
    )
    
    # Test 3: consultar_inventario_almacen
    test_function(
        "consultar_inventario_almacen",
        consultar_inventario,
        {"skus": ["FAR-001", "MED-002"]}
    )
    
    # Test 4: calcular_distancia
    test_function(
        "calcular_distancia",
        calcular_distancia,
        {
            "origen": {"lat": 19.4326, "lon": -99.1332},
            "destino": {"lat": 19.4345, "lon": -99.1410}
        }
    )
    
    # Test 5: calcular_ruta_optimizada
    test_function(
        "calcular_ruta_optimizada",
        calcular_ruta_optimizada,
        {
            "paradas": [
                {"stop_id": "STOP-1", "latitud": 19.4326, "longitud": -99.1332}
            ],
            "origen": {"lat": 19.4384, "lon": -99.1569}
        }
    )
    
    # Test 6: actualizar_ruta_s3
    test_function(
        "actualizar_ruta_s3",
        actualizar_ruta_s3,
        {
            "truck_id": "1",
            "fecha": "2026-02-17",
            "ruta": {
                "truck_id": "1",
                "fecha_ruta": "2026-02-17",
                "conductor_asignado": "Test Driver",
                "estado_ruta": "Activa",
                "paradas": []
            }
        }
    )
    
    # Test 7: registrar_incidencia
    test_function(
        "registrar_incidencia",
        registrar_incidencia,
        {
            "incidente": {
                "incidente_id": "INC-TEST-001",
                "timestamp": "2026-02-17T14:15:00Z",
                "truck_id": "1",
                "tipo_incidente": "Choque",
                "nivel_gravedad": "Crítico",
                "ubicacion_gps": {"lat": 19.4345, "lon": -99.1410},
                "descripcion_evento": "Test incident"
            }
        }
    )
    
    # Test 8: enviar_notificacion_cliente
    test_function(
        "enviar_notificacion_cliente",
        enviar_notificacion,
        {
            "cliente_id": "CLI-001",
            "telefono": "+525512345678",
            "mensaje": "Test notification",
            "prioridad": "Alta"
        }
    )
    
    print("\n" + "="*60)
    print("PRUEBAS COMPLETADAS")
    print("="*60)
    print("\nResumen:")
    print("- ✅ = Función ejecutada sin errores de sintaxis")
    print("- ⚠️  = Función retornó código de error (esperado sin AWS)")
    print("- ❌ = Error de sintaxis o importación")
    print("\nPara pruebas completas, desplegar en AWS y usar test_event.json")


if __name__ == "__main__":
    main()
