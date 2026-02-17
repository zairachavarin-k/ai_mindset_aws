"""
Script de prueba para verificar que los agentes responden naturalmente con Claude
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from agents.orchestrator import LogisticsOrchestrator


def test_natural_responses():
    """
    Prueba que los agentes respondan de forma natural, no con mensajes predefinidos
    """
    orchestrator = LogisticsOrchestrator()
    
    print("=" * 80)
    print("PRUEBA DE RESPUESTAS NATURALES CON CLAUDE")
    print("=" * 80)
    print()
    
    # Test 1: Saludo casual
    print("Test 1: Saludo casual")
    print("-" * 80)
    response = orchestrator.process_message("Hola, ¿cómo estás?")
    print(f"Usuario: Hola, ¿cómo estás?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response']}")
    print()
    
    # Test 2: Pregunta sobre nombre
    print("Test 2: Pregunta sobre nombre")
    print("-" * 80)
    response = orchestrator.process_message("¿Cómo te llamas?")
    print(f"Usuario: ¿Cómo te llamas?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response']}")
    print()
    
    # Test 3: Pregunta sobre capacidades
    print("Test 3: Pregunta sobre capacidades")
    print("-" * 80)
    response = orchestrator.process_message("¿Qué puedes hacer por mí?")
    print(f"Usuario: ¿Qué puedes hacer por mí?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response']}")
    print()
    
    # Test 4: Pregunta técnica (debe delegar)
    print("Test 4: Pregunta técnica - debe delegar a Route Planner")
    print("-" * 80)
    response = orchestrator.process_message("¿Dónde están los camiones?")
    print(f"Usuario: ¿Dónde están los camiones?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response'][:200]}...")
    print()
    
    # Test 5: Pregunta casual sobre el sistema
    print("Test 5: Pregunta casual sobre el sistema")
    print("-" * 80)
    response = orchestrator.process_message("¿Eres un robot?")
    print(f"Usuario: ¿Eres un robot?")
    print(f"Agente: {response['agent']}")
    print(f"Respuesta: {response['response']}")
    print()
    
    print("=" * 80)
    print("PRUEBAS COMPLETADAS")
    print("=" * 80)
    print()
    print("✅ Si ves respuestas naturales y variadas (no siempre iguales), ¡funciona!")
    print("✅ El agente debe responder de forma conversacional, no con listas predefinidas")
    print()


if __name__ == "__main__":
    test_natural_responses()
