// Main application initialization

document.addEventListener('DOMContentLoaded', () => {
  // Initialize map
  initializeMap();
  
  // Initialize charts
  initCharts();
  
  // Set up event listeners
  document.getElementById('optimizeBtn').addEventListener('click', optimizeAllRoutes);
  document.getElementById('viewExportsBtn').addEventListener('click', viewSavedExports);
  document.getElementById('startSimBtn').addEventListener('click', () => simulation.start());
  document.getElementById('stopSimBtn').addEventListener('click', () => simulation.stop());
  
  // Redirect buttons
  document.getElementById('redirectAllToDepotBtn').addEventListener('click', async () => {
    if (confirm('¿Redirigir todos los camiones al almacén/depósito?')) {
      await simulation.redirectAllToDepot();
    }
  });
  
  document.getElementById('redirectCustomBtn').addEventListener('click', async () => {
    const lng = prompt('Ingresa la longitud (ej: -99.15):');
    const lat = prompt('Ingresa la latitud (ej: 19.42):');
    
    if (lng && lat) {
      const coords = [parseFloat(lng), parseFloat(lat)];
      const name = prompt('Nombre de la ubicación (opcional):', 'Ubicación personalizada');
      
      if (confirm(`¿Redirigir todos los camiones a [${coords[0]}, ${coords[1]}]?`)) {
        await simulation.redirectAllTrucks(coords, name || 'Ubicación personalizada');
      }
    }
  });
  
  // Redirect individual truck selector
  document.getElementById('redirectTruckSelector').addEventListener('change', async (e) => {
    const truckId = parseInt(e.target.value);
    if (!isNaN(truckId)) {
      if (confirm(`¿Redirigir Camión ${truckId + 1} al almacén/depósito?`)) {
        await simulation.redirectToDepot(truckId);
      }
      // Reset selector
      e.target.value = '';
    }
  });
  
  console.log('Route Optimizer Dashboard initialized');
});

