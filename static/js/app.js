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
  
  console.log('Route Optimizer Dashboard initialized');
});
