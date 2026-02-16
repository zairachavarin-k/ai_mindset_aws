// Card management and updates

let currentRouteData = null;
let selectedTruckId = 'all';

function updateCards(optimizedRoutes) {
  if (!optimizedRoutes || optimizedRoutes.length === 0) {
    return;
  }
  
  currentRouteData = optimizedRoutes;
  
  // Update based on current selection
  updateCardValues();
}

function updateCardValues() {
  if (!currentRouteData) return;
  
  if (selectedTruckId === 'all') {
    // Show data for all trucks
    const trucksWithRoutes = currentRouteData.filter(r => r.waypoints.length > 0).length;
    const trucksInDepot = 5 - trucksWithRoutes;
    
    // Calculate total time (max time among all trucks)
    const maxTime = Math.max(...currentRouteData.map(r => r.duration / 60));
    
    // Calculate total value
    let totalValue = 0;
    currentRouteData.forEach(route => {
      route.waypoints.forEach(wp => {
        const destInfo = destinationsData[wp.id];
        if (destInfo && destInfo.items) {
          totalValue += calculateItemsValue(destInfo.items);
        }
      });
    });
    
    // Update card values
    updateTrucksOut(0); // Initially 0, will update during simulation
    updateTrucksInDepot(5); // Initially all in depot
    updateCompletionTime(Math.round(maxTime));
    updateTotalValue(totalValue);
  } else {
    // Show data for selected truck only
    const truckId = parseInt(selectedTruckId);
    const route = currentRouteData[truckId];
    
    if (route && route.waypoints.length > 0) {
      // Calculate time for this truck
      const truckTime = route.duration / 60;
      
      // Calculate value for this truck
      let truckValue = 0;
      route.waypoints.forEach(wp => {
        const destInfo = destinationsData[wp.id];
        if (destInfo && destInfo.items) {
          truckValue += calculateItemsValue(destInfo.items);
        }
      });
      
      // Update card values for single truck
      updateTrucksOut(0); // Will update during simulation
      updateTrucksInDepot(5); // Will update during simulation
      updateCompletionTime(Math.round(truckTime));
      updateTotalValue(truckValue);
    } else {
      // No route for this truck
      updateCompletionTime(0);
      updateTotalValue(0);
    }
  }
}

function updateTrucksOut(count) {
  const element = document.getElementById('trucksOut');
  if (element) {
    element.textContent = count;
  }
}

function updateTrucksInDepot(count) {
  const element = document.getElementById('trucksInDepot');
  if (element) {
    element.textContent = count;
  }
}

function updateCompletionTime(minutes) {
  const element = document.getElementById('completionTime');
  if (element) {
    element.textContent = minutes > 0 ? minutes : '--';
  }
}

function updateTotalValue(value) {
  const element = document.getElementById('totalValue');
  if (element) {
    element.textContent = '$' + value.toFixed(0);
  }
}

// Truck selector functionality
function initTruckSelector() {
  const selector = document.getElementById('truckSelector');
  if (selector) {
    selector.addEventListener('change', (e) => {
      selectedTruckId = e.target.value;
      filterTruckView(selectedTruckId);
      updateCardValues(); // Update cards when selection changes
    });
  }
}

function filterTruckView(truckId) {
  console.log('Filtering view for truck:', truckId);
  
  if (truckId === 'all') {
    // Show all truck routes
    showAllTruckRoutes();
  } else {
    // Show only selected truck route
    showSingleTruckRoute(parseInt(truckId));
  }
}

function showAllTruckRoutes() {
  // Show all route layers on the map
  for (let i = 0; i < 5; i++) {
    const layerId = `route-layer-${i}`;
    if (map && map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, 'visibility', 'visible');
    }
  }
}

function showSingleTruckRoute(truckId) {
  // Hide all routes except the selected one
  for (let i = 0; i < 5; i++) {
    const layerId = `route-layer-${i}`;
    if (map && map.getLayer(layerId)) {
      if (i === truckId) {
        map.setLayoutProperty(layerId, 'visibility', 'visible');
      } else {
        map.setLayoutProperty(layerId, 'visibility', 'none');
      }
    }
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  initTruckSelector();
});
