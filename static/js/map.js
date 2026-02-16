// Map initialization and marker management

let map;

function initializeMap() {
  map = new maplibregl.Map({
    container: "map",
    style: `https://maps.geo.${CONFIG.region}.amazonaws.com/v2/styles/${CONFIG.style}/descriptor?key=${CONFIG.apiKey}&color-scheme=${CONFIG.colorScheme}`,
    center: depot,
    zoom: 11,
  });
  
  map.addControl(new maplibregl.NavigationControl(), "top-left");
  
  map.on('load', () => {
    addMarkers();
  });
}

function addMarkers() {
  // Check if destinationsData is available
  if (typeof destinationsData === 'undefined') {
    console.error('destinationsData is not defined yet. Retrying in 100ms...');
    setTimeout(addMarkers, 100);
    return;
  }
  
  console.log('Adding markers. destinationsData length:', destinationsData.length);
  console.log('destinations length:', destinations.length);
  
  // Depot marker
  const depotEl = document.createElement('div');
  depotEl.style.width = '20px';
  depotEl.style.height = '20px';
  depotEl.style.backgroundColor = '#FFD700';
  depotEl.style.border = '2px solid #000';
  depotEl.style.borderRadius = '50%';
  new maplibregl.Marker({ element: depotEl })
    .setLngLat(depot)
    .setPopup(new maplibregl.Popup().setHTML('<strong>Depot</strong>'))
    .addTo(map);

  // Destination markers
  destinations.forEach((dest, i) => {
    const el = document.createElement('div');
    el.style.width = '18px';
    el.style.height = '18px';
    el.style.backgroundColor = '#fff';
    el.style.border = '2px solid #333';
    el.style.borderRadius = '50%';
    el.style.display = 'flex';
    el.style.alignItems = 'center';
    el.style.justifyContent = 'center';
    el.style.fontSize = '10px';
    el.style.fontWeight = 'bold';
    el.textContent = i + 1;
    
    // Get destination info with safety check
    const destInfo = destinationsData[i];
    if (!destInfo) {
      console.error(`No destination info for index ${i}`);
      // Fallback to simple marker
      new maplibregl.Marker({ element: el })
        .setLngLat(dest)
        .setPopup(new maplibregl.Popup().setHTML(`<strong>Destination ${i + 1}</strong>`))
        .addTo(map);
      return;
    }
    
    const itemsList = destInfo.items.map(item => `• ${item}`).join('<br>');
    
    new maplibregl.Marker({ element: el })
      .setLngLat(dest)
      .setPopup(new maplibregl.Popup().setHTML(`
        <div style="padding: 5px;">
          <strong>Destination ${i + 1}</strong><br>
          <span style="color: #666; font-size: 11px;">${destInfo.name}</span><br>
          <div style="margin-top: 8px; font-size: 10px; color: #444;">
            <strong>Items:</strong><br>
            ${itemsList}
          </div>
        </div>
      `))
      .addTo(map);
  });
  
  console.log('Markers added successfully');
}

async function drawRoute(truckId, waypoints, color) {
  try {
    console.log(`Fetching route geometry for truck ${truckId}...`);
    
    // Call AWS to get actual route geometry
    const response = await fetch(`${CONFIG.apiUrl}/calculate-route`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origin: depot,
        destination: depot,
        waypoints: waypoints.map(w => w.coords)
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Failed to get route geometry for truck ${truckId}: ${response.status} - ${errorText}`);
      drawStraightRoute(truckId, waypoints, color);
      return null; // Return null if failed
    }

    const routeData = await response.json();
    console.log(`Route data for truck ${truckId}:`, routeData);
    
    // Extract geometry from AWS response
    if (routeData.Routes && routeData.Routes.length > 0) {
      const route = routeData.Routes[0];
      let coordinates = [];
      
      if (route.Legs) {
        route.Legs.forEach(leg => {
          if (leg.Geometry && leg.Geometry.LineString) {
            coordinates = coordinates.concat(leg.Geometry.LineString);
          }
        });
      }
      
      console.log(`Extracted ${coordinates.length} coordinates for truck ${truckId}`);
      
      if (coordinates.length === 0) {
        console.warn('No geometry found in route response, using straight lines');
        drawStraightRoute(truckId, waypoints, color);
        return null;
      }

      const sourceId = `route-${truckId}`;
      const layerId = `route-layer-${truckId}`;

      if (map.getSource(sourceId)) {
        map.removeLayer(layerId);
        map.removeSource(sourceId);
      }

      map.addSource(sourceId, {
        type: 'geojson',
        data: {
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: coordinates
          }
        }
      });

      map.addLayer({
        id: layerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': color,
          'line-width': 4,
          'line-opacity': 0.8
        }
      });
      
      console.log(`Successfully drew route for truck ${truckId}`);
      
      // Return the coordinates for simulation
      return coordinates;
    } else {
      console.warn('No routes in response');
      drawStraightRoute(truckId, waypoints, color);
      return null;
    }
  } catch (error) {
    console.error(`Error drawing route for truck ${truckId}:`, error);
    drawStraightRoute(truckId, waypoints, color);
    return null;
  }
}

function drawStraightRoute(truckId, waypoints, color) {
  const coordinates = [depot, ...waypoints.map(w => w.coords), depot];
  
  const sourceId = `route-${truckId}`;
  const layerId = `route-layer-${truckId}`;

  if (map.getSource(sourceId)) {
    map.removeLayer(layerId);
    map.removeSource(sourceId);
  }

  map.addSource(sourceId, {
    type: 'geojson',
    data: {
      type: 'Feature',
      geometry: {
        type: 'LineString',
        coordinates: coordinates
      }
    }
  });

  map.addLayer({
    id: layerId,
    type: 'line',
    source: sourceId,
    paint: {
      'line-color': color,
      'line-width': 3,
      'line-opacity': 0.6,
      'line-dasharray': [2, 2]
    }
  });
}
