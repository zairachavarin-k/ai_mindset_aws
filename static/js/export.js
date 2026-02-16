// Route export functionality

let currentOptimizedRoutes = null;

function setOptimizedRoutes(routes) {
  currentOptimizedRoutes = routes;
  
  // Enable export button
  const exportBtn = document.getElementById('exportBtn');
  if (exportBtn) {
    exportBtn.disabled = false;
  }
}

async function exportRoutesToJSON() {
  if (!currentOptimizedRoutes || currentOptimizedRoutes.length === 0) {
    alert('Please optimize routes first!');
    return;
  }
  
  try {
    console.log('Exporting routes to JSON...');
    
    // Prepare data for export with destination names and items
    const exportData = currentOptimizedRoutes
      .filter(route => route.waypoints.length > 0)
      .map(route => ({
        truck_id: route.truckId,
        waypoints: route.waypoints.map(wp => {
          const destInfo = destinationsData[wp.id];
          if (!destInfo) {
            console.error(`No destination info for waypoint id ${wp.id}`);
            return {
              coords: wp.coords,
              id: wp.id,
              name: `Destination ${wp.id + 1}`,
              items: []
            };
          }
          return {
            coords: wp.coords,
            id: wp.id,
            name: destInfo.name,
            items: destInfo.items
          };
        }),
        distance: route.distance,
        duration: route.duration,
        route_geometry: route.routeGeometry
      }));
    
    // Call backend to generate and save route data
    const response = await fetch(`${CONFIG.apiUrl}/export-routes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(exportData)
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }
    
    const routeData = await response.json();
    console.log('Route data saved:', routeData);
    
    // Update simulation with the filename so it can update the JSON
    if (routeData.file_info?.filename) {
      simulation.exportFilename = routeData.file_info.filename;
      console.log(`Simulation will update: ${routeData.file_info.filename}`);
    }
    
    // Show success message
    showExportSuccess(routeData);
    
    return routeData;
    
  } catch (error) {
    console.error('Export error:', error);
    throw error;
  }
}

function showExportSuccess(routeData) {
  const results = document.getElementById('results');
  const successMsg = document.createElement('div');
  successMsg.style.cssText = 'margin-top:10px; padding:8px; background:rgba(76, 175, 80, 0.2); border-radius:4px; font-size:10px; border: 1px solid rgba(76, 175, 80, 0.3);';
  successMsg.innerHTML = `
    <strong style="color: #4caf50;">✓ Routes Saved!</strong><br>
    <span style="color: #ddd;">File: ${routeData.file_info?.filename || 'route_plan.json'}<br>
    ${routeData.total_trucks} trucks, ${routeData.summary.total_stops} stops<br>
    Total: ${routeData.summary.total_distance_km.toFixed(2)} km</span>
  `;
  
  results.appendChild(successMsg);
  
  // Remove message after 5 seconds
  setTimeout(() => {
    successMsg.remove();
  }, 5000);
}

async function viewSavedExports() {
  try {
    const response = await fetch(`${CONFIG.apiUrl}/list-exports`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch exports: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('Saved exports:', data);
    
    // Show list in alert or modal
    if (data.total_files === 0) {
      alert('No saved route plans found.');
    } else {
      let message = `Saved Route Plans (${data.total_files}):\n\n`;
      data.files.slice(0, 10).forEach((file, idx) => {
        const date = new Date(file.created_at).toLocaleString();
        const sizeMB = (file.size_bytes / 1024).toFixed(1);
        message += `${idx + 1}. ${file.filename}\n   ${date} (${sizeMB} KB)\n\n`;
      });
      
      if (data.total_files > 10) {
        message += `... and ${data.total_files - 10} more files`;
      }
      
      alert(message);
    }
  } catch (error) {
    console.error('Error fetching exports:', error);
    alert(`Failed to fetch saved exports: ${error.message}`);
  }
}
