"""
Script de validación de sintaxis para Lambda functions
No requiere boto3 instalado
"""
import py_compile
import os
import sys

def validate_file(filepath):
    """Valida la sintaxis de un archivo Python"""
    try:
        py_compile.compile(filepath, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

def main():
    """Valida todos los archivos Lambda"""
    files = [
        'consultar_ruta_afectada.py',
        'consultar_flota_disponible.py',
        'consultar_inventario_almacen.py',
        'calcular_distancia.py',
        'calcular_ruta_optimizada.py',
        'actualizar_ruta_s3.py',
        'registrar_incidencia.py',
        'enviar_notificacion_cliente.py',
    ]
    
    print("\n" + "="*60)
    print("VALIDACIÓN DE SINTAXIS - LAMBDA FUNCTIONS MCP")
    print("="*60 + "\n")
    
    all_valid = True
    base_dir = os.path.dirname(__file__)
    
    for filename in files:
        filepath = os.path.join(base_dir, filename)
        if not os.path.exists(filepath):
            print(f"❌ {filename} - FILE NOT FOUND")
            all_valid = False
            continue
        
        valid, error = validate_file(filepath)
        if valid:
            print(f"✅ {filename} - Sintaxis válida")
        else:
            print(f"❌ {filename} - Error de sintaxis:")
            print(f"   {error}")
            all_valid = False
    
    print("\n" + "="*60)
    if all_valid:
        print("✅ TODAS LAS FUNCIONES TIENEN SINTAXIS VÁLIDA")
        print("="*60 + "\n")
        return 0
    else:
        print("❌ ALGUNAS FUNCIONES TIENEN ERRORES")
        print("="*60 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
