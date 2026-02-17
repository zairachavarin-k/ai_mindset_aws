# Guía de Redirección de Camiones

## Descripción
Sistema para cambiar dinámicamente las rutas de los camiones durante la simulación en el frontend.

## Uso desde la Interfaz (Botones)

### 1. Botón "🏠 All to Depot"
- Redirige TODOS los camiones al almacén/depósito
- Coordenadas del depósito: [-99.1908, 19.4336]
- Solo funciona cuando la simulación está corriendo

### 2. Botón "📍 Custom Location"
- Redirige TODOS los camiones a una ubicación personalizada
- Te pedirá ingresar:
  - Longitud (ej: -99.15)
  - Latitud (ej: 19.42)
  - Nombre de la ubicación (opcional)

## Uso desde la Consola del Navegador

Abre la consola del navegador (F12) y usa estas funciones:

### Redirigir todos los camiones al depósito
```javascript
redirectAllToDepot();
```

### Redirigir un camión específico al depósito
```javascript
redirectTruckToDepot(0);  // Camión 1 (ID 0)
redirectTruckToDepot(2);  // Camión 3 (ID 2)
```

### Redirigir todos los camiones a una ubicación personalizada
```javascript
// Sintaxis: redirectAllTrucks(longitud, latitud, nombre)
redirectAllTrucks(-99.15, 19.42, "Centro de la ciudad");
```

### Redirigir un camión específico a una ubicación
```javascript
// Sintaxis: redirectTruck(truckId, longitud, latitud, nombre)
redirectTruck(0, -99.15, 19.42, "Emergencia");
redirectTruck(3, -99.20, 19.45, "Nueva ubicación");
```

## Uso desde Python (Backend)

También puedes usar el endpoint del backend:

```python
import requests

# Redirigir todos al depósito
response = requests.post('http://localhost:8000/redirect-trucks', json={
    "target_location": "depot"
})

# Redirigir todos a ubicación personalizada
response = requests.post('http://localhost:8000/redirect-trucks', json={
    "target_location": "custom",
    "custom_coords": [-99.15, 19.42]
})

# Redirigir un camión específico
response = requests.post('http://localhost:8000/redirect-trucks', json={
    "truck_id": 0,
    "target_location": "depot"
})
```

## Características

- ✅ Los camiones cambian su ruta inmediatamente
- ✅ Se cancelan todas las entregas pendientes
- ✅ El marcador del camión cambia a color naranja (🟠) para indicar redirección
- ✅ Los camiones con incidentes NO pueden ser redirigidos
- ✅ Solo funciona cuando la simulación está corriendo

## Ejemplos de Coordenadas en CDMX

```javascript
// Zócalo
redirectAllTrucks(-99.1332, 19.4326, "Zócalo");

// Aeropuerto
redirectAllTrucks(-99.0721, 19.4363, "Aeropuerto AICM");

// Santa Fe
redirectAllTrucks(-99.2677, 19.3595, "Santa Fe");

// Polanco
redirectAllTrucks(-99.1944, 19.4338, "Polanco");
```

## Notas Importantes

1. La simulación DEBE estar corriendo para poder redirigir camiones
2. Los camiones con incidentes reportados NO pueden ser redirigidos
3. Al redirigir, se pierden todas las entregas pendientes del camión
4. La nueva ruta se calcula automáticamente desde la posición actual
5. El color naranja indica que el camión fue redirigido manualmente
