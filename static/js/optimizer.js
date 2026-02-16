// Route optimization logic

async function optimizeTruckRoute(truckId, waypointsList) {
  try {
    const response = await fetch(`${CONFIG.apiUrl}/optimize-waypoints`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: depot,
        destination: depot,
        waypoints: waypointsList.map(w => w.coords)
      })
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`Error optimizing truck ${truckId}:`, error);
    throw error;
  }
}

async function optimizeAllRoutes() {
  const btn = document.getElementById('optimizeBtn');
  const results = document.getElementById('results');
  
  btn.disabled = true;
  btn.textContent = 'Optimizing...';
  results.innerHTML = '<p>Step 1: Solving ACO for optimal assignment...</p>';

  try {
    // Step 1: Use ACO to optimally assign destinations to trucks
    const acoResponse = await fetch(`${CONFIG.apiUrl}/solve-mtsp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        num_trucks: 5,
        depot: depot,
        destinations: destinations
      })
    });

    if (!acoResponse.ok) {
      throw new Error(`ACO solver failed: ${acoResponse.status}`);
    }

    const acoResult = await acoResponse.json();
    console.log('ACO Solution:', acoResult);

    if (acoResult.status !== 'Optimal') {
      throw new Error(`ACO solver status: ${acoResult.status}`);
    }

    results.innerHTML = '<p>Step 2: Optimizing each truck route with AWS...</p>';

    // Step 2: Convert ACO routes to assignments format
    const assignments = acoResult.routes.map((route, truckId) => {
      // route is array of indices [0, 3, 5, 0] where 0 is depot
      // Convert to our format, excluding depot
      return route
        .filter(idx => idx !== 0) // Remove depot
        .map(idx => ({
          coords: destinations[idx - 1], // idx-1 because destinations array doesn't include depot
          id: idx - 1 // Original destination ID
        }));
    });

    console.log('Assignments from ACO:', assignments);

    const optimizedRoutes = [];

    // Step 3: For each truck, use AWS to optimize the waypoint order
    for (let i = 0; i < 5; i++) {
      if (assignments[i].length > 0) {
        const result = await optimizeTruckRoute(i, assignments[i]);
        
        console.log(`Truck ${i} result:`, result);
        console.log(`Truck ${i} assignments:`, assignments[i]);
        
        if (result && result.OptimizedWaypoints) {
          // Map optimized waypoints back to original IDs
          const optimizedWaypoints = result.OptimizedWaypoints.map((w, idx) => {
            // AWS returns Id as "Waypoint0", "Waypoint1", etc.
            // Extract the numeric index from the Id string
            let waypointIndex = idx;
            if (w.Id && typeof w.Id === 'string' && w.Id.startsWith('Waypoint')) {
              waypointIndex = parseInt(w.Id.replace('Waypoint', ''));
            } else if (typeof w.Id === 'number') {
              waypointIndex = w.Id;
            }
            
            const originalWaypoint = assignments[i][waypointIndex];
            
            console.log(`Truck ${i} - Waypoint ${idx}: AWS Id=${w.Id}, Parsed index=${waypointIndex}, Original id=${originalWaypoint ? originalWaypoint.id : 'undefined'}`);
            
            return {
              coords: w.Position,
              id: originalWaypoint ? originalWaypoint.id : waypointIndex,
              originalOrder: waypointIndex
            };
          });
          
          // Log to show AWS reordered the waypoints
          const acoOrder = assignments[i].map(w => w.id + 1).join(' → ');
          const awsOrder = optimizedWaypoints.map(w => w.id + 1).join(' → ');
          console.log(`Truck ${i} ACO assignment: ${acoOrder}`);
          console.log(`Truck ${i} AWS optimized:  ${awsOrder}`);
          
          optimizedRoutes.push({
            truckId: i,
            waypoints: optimizedWaypoints,
            distance: result.Distance || 0,
            duration: result.Duration || 0,
            acoOrder: acoOrder,
            awsOrder: awsOrder,
            routeGeometry: null // Will be filled when drawing
          });

          // Draw route and get geometry for simulation
          const routeGeometry = await drawRoute(i, optimizedWaypoints, truckColors[i]);
          optimizedRoutes[optimizedRoutes.length - 1].routeGeometry = routeGeometry;
        }
      } else {
        // Empty route for this truck
        optimizedRoutes.push({
          truckId: i,
          waypoints: [],
          distance: 0,
          duration: 0,
          acoOrder: 'No destinations',
          awsOrder: 'No destinations'
        });
      }
    }

    // Display results
    displayResults(optimizedRoutes);
    
    // Update charts with new data
    updateCharts(optimizedRoutes);
    
    // Update cards with route data
    if (typeof updateCards === 'function') {
      updateCards(optimizedRoutes);
    }
    
    // Store routes for export
    setOptimizedRoutes(optimizedRoutes);
    
    // Automatically export routes to JSON file
    let exportFilename = null;
    try {
      const exportData = await exportRoutesToJSON();
      exportFilename = exportData?.file_info?.filename || null;
    } catch (error) {
      console.error('Auto-export failed:', error);
      // Don't block the UI if export fails
    }
    
    // Initialize simulation with optimized routes and export filename
    simulation.initialize(optimizedRoutes, exportFilename);
    
    // Enable simulation buttons
    const startBtn = document.getElementById('startSimBtn');
    if (startBtn) startBtn.disabled = false;
    
  } catch (error) {
    results.innerHTML = `<p style="color:red;">Error: ${error.message}<br><small>Make sure FastAPI server is running on port 8000</small></p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Optimize Routes';
  }
}

function displayResults(optimizedRoutes) {
  const results = document.getElementById('results');
  let html = '<h4 style="color: #ddd; margin-bottom: 10px;">Optimized Routes:</h4>';
  let totalDistance = 0;
  let totalTime = 0;

  optimizedRoutes.forEach(route => {
    const distanceKm = (route.distance / 1000).toFixed(2);
    const durationMin = (route.duration / 60).toFixed(0);
    
    totalDistance += route.distance;
    totalTime += route.duration;

    if (route.waypoints.length > 0) {
      // Build route with destination names
      const routeStops = route.waypoints.map(w => {
        const destInfo = destinationsData[w.id];
        if (!destInfo) {
          console.error(`No destination info for waypoint id ${w.id}`);
          return `<div style="margin: 3px 0; padding-left: 10px;">
            <strong>${w.id + 1}. Destination ${w.id + 1}</strong>
          </div>`;
        }
        return `<div style="margin: 3px 0; padding-left: 10px;">
          <strong>${w.id + 1}. ${destInfo.name}</strong>
          <div style="font-size: 9px; color: #888; padding-left: 10px;">
            ${destInfo.items.join(', ')}
          </div>
        </div>`;
      }).join('');
      
      html += `
        <div class="truck-info">
          <div><span class="truck-color" style="background:${truckColors[route.truckId]}"></span><strong style="color: #fff;">Truck ${route.truckId + 1}</strong></div>
          <div style="font-size:10px; margin-top:6px; color: #aaa;">
            <strong>Route (${route.waypoints.length} stops):</strong><br>
            ${routeStops}
          </div>
          <div style="margin-top:6px; color: #ddd; border-top: 1px solid #333; padding-top: 6px;">
            <strong>${distanceKm} km</strong> • ${durationMin} min
          </div>
        </div>
      `;
    }
  });

  html += `
    <div style="margin-top:15px; padding:10px; background:rgba(76, 175, 80, 0.2); border-radius:4px; border: 1px solid rgba(76, 175, 80, 0.3);">
      <strong style="color: #4caf50;">Total:</strong><br>
      <span style="color: #ddd;">Distance: ${(totalDistance / 1000).toFixed(2)} km<br>
      Time: ${(totalTime / 60).toFixed(0)} min</span>
    </div>
  `;

  results.innerHTML = html;
}
