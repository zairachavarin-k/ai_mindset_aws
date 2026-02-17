"""
Script de prueba para el sistema LangGraph
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from agents.langgraph_system import process_message

def test_system():
    print("=" * 80)
    print("PRUEBA DEL SISTEMA LANGGRAPH")
    print("=" * 80)
    print()
    
    # Test 1: Saludo
    print("Test 1: Saludo")
    print("-" * 80)
    response = process_message("Hola, ¿cómo estás?")
    print(f"Usuario: Hola, ¿cómo estás?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response']}")
    print()
    
    # Test 2: Pregunta técnica
    print("Test 2: Pregunta técnica")
    print("-" * 80)
    response = process_message("¿Dónde están los camiones?")
    print(f"Usuario: ¿Dónde están los camiones?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response'][:200]}...")
    print()
    
    print("=" * 80)
    print("PRUEBAS COMPLETADAS")
    print("=" * 80)

if __name__ == "__main__":
    test_system()
