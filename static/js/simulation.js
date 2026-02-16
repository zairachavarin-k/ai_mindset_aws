// Route simulation - animate trucks moving along their routes

class TruckSimulation {
  constructor() {
    this.trucks = [];
    this.isRunning = false;
    this.animationFrameId = null;
    this.startTime = null;
    this.markers = [];
    this.incidentTrucks = new Set(); // Track trucks with incidents
    this.deliveryStatus = {}; // Track delivery status
    this.exportFilename = null; // Track the export filename for JSON updates
  }

  initialize(optimizedRoutes, exportFilename = null) {
    this.stop(); // Stop any existing simulation
    this.trucks = [];
    this.deliveryStatus = {}; // Track delivery status for each truck
    this.exportFilename = exportFilename; // Store the filename for updates
    this.totalMoneyValue = 0; // Track total money to collect
    this.collectedMoney = 0; // Track collected money
    
    // Create truck data for simulation
    optimizedRoutes.forEach(route => {
      if (route.waypoints.length > 0) {
        // Use actual route geometry if available, otherwise fall back to waypoints
        let pathCoordinates;
        
        if (route.routeGeometry && route.routeGeometry.length > 0) {
          // Use the actual road geometry from AWS
          pathCoordinates = route.routeGeometry;
          console.log(`Truck ${route.truckId}: Using ${pathCoordinates.length} geometry points from AWS`);
        } else {
          // Fallback to simple waypoint path
          pathCoordinates = [
            depot,
            ...route.waypoints.map(w => w.coords),
            depot
          ];
          console.log(`Truck ${route.truckId}: Using ${pathCoordinates.length} waypoint path (fallback)`);
        }
        
        // Duration in seconds (1 minute = 1 second in simulation)
        const durationSeconds = route.duration*3 / 60;
        
        // Calculate delivery stop times (5 seconds = 5 minutes in simulation)
        const deliveryStops = route.waypoints.map((wp, idx) => {
          const destInfo = destinationsData[wp.id];
          if (!destInfo) {
            console.error(`No destination info for waypoint id ${wp.id}`);
            return {
              waypointIndex: idx,
              waypointId: wp.id,
              coords: wp.coords,
              name: `Destination ${wp.id + 1}`,
              items: [],
              itemsValue: 0,
              delivered: false,
              stopNumber: idx + 1
            };
          }
          const itemsValue = calculateItemsValue(destInfo.items);
          this.totalMoneyValue += itemsValue;
          
          return {
            waypointIndex: idx,
            waypointId: wp.id,
            coords: wp.coords,
            name: destInfo.name,
            items: destInfo.items,
            itemsValue: itemsValue,
            delivered: false,
            stopNumber: idx + 1 // Stop number for JSON update (1-based)
          };
        });
        
        this.trucks.push({
          id: route.truckId,
          path: pathCoordinates,
          waypoints: route.waypoints,
          color: truckColors[route.truckId],
          duration: durationSeconds,
          currentPosition: pathCoordinates[0],
          progress: 0,
          marker: null,
          deliveryStops: deliveryStops,
          currentStop: null,
          stopStartTime: null,
          isAtStop: false
        });
        
        // Initialize delivery status
        this.deliveryStatus[route.truckId] = {
          total: deliveryStops.length,
          delivered: 0,
          stops: deliveryStops
        };
      }
    });
    
    console.log(`Initialized simulation with ${this.trucks.length} trucks`);
  }

  createTruckMarker(truck) {
    // Create truck icon
    const el = document.createElement('div');
    el.style.width = '24px';
    el.style.height = '24px';
    el.style.backgroundColor = truck.color;
    el.style.border = '3px solid white';
    el.style.borderRadius = '50%';
    el.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';
    el.style.cursor = 'pointer';
    el.innerHTML = `<div style="color:white;font-size:10px;font-weight:bold;text-align:center;line-height:18px;">${truck.id + 1}</div>`;
    
    // Create popup with incident button
    const popup = new maplibregl.Popup({ offset: 25 })
      .setHTML(`
        <div style="padding:5px;">
          <strong>Truck ${truck.id + 1}</strong><br>
          <button id="incident-btn-${truck.id}" style="margin-top:8px; padding:5px 10px; background:#dc3545; color:white; border:none; border-radius:4px; cursor:pointer; font-size:11px;">
            🚨 Report Incident
          </button>
        </div>
      `);
    
    const marker = new maplibregl.Marker({ element: el })
      .setLngLat(truck.currentPosition)
      .setPopup(popup)
      .addTo(map);
    
    // Add incident button click handler
    popup.on('open', () => {
      const incidentBtn = document.getElementById(`incident-btn-${truck.id}`);
      if (incidentBtn) {
        incidentBtn.onclick = () => this.reportIncident(truck.id);
      }
    });
    
    return marker;
  }

  async reportIncident(truckId) {
    try {
      const response = await fetch(`${CONFIG.apiUrl}/report-incident`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ truck_id: truckId })
      });
      
      if (response.ok) {
        // Mark truck as having an incident
        this.incidentTrucks.add(truckId);
        
        // Find the truck and mark it visually
        const truck = this.trucks.find(t => t.id === truckId);
        if (truck && truck.marker) {
          const el = truck.marker.getElement();
          el.style.backgroundColor = '#dc3545'; // Red color for incident
          el.style.border = '3px solid #ff0000';
          el.innerHTML = `<div style="color:white;font-size:10px;font-weight:bold;text-align:center;line-height:18px;">⚠️</div>`;
        }
        
        alert(`Incident reported for Truck ${truckId + 1}\nTruck has stopped.`);
        
        // Close the popup
        if (truck && truck.marker) {
          truck.marker.getPopup().remove();
        }
      } else {
        alert('Failed to report incident');
      }
    } catch (error) {
      console.error('Error reporting incident:', error);
      alert('Error reporting incident');
    }
  }

  interpolatePosition(start, end, progress) {
    // Linear interpolation between two coordinates
    return [
      start[0] + (end[0] - start[0]) * progress,
      start[1] + (end[1] - start[1]) * progress
    ];
  }

  getPositionAtTime(truck, elapsedSeconds) {
    // If truck has an incident, freeze at current position
    if (this.incidentTrucks.has(truck.id)) {
      return truck.currentPosition;
    }
    
    // Check if truck is at a delivery stop
    if (truck.isAtStop && truck.stopStartTime !== null) {
      const stopDuration = elapsedSeconds - truck.stopStartTime;
      if (stopDuration < 5) { // 5 seconds = 5 minutes
        // Still at stop, don't move
        return truck.currentPosition;
      } else {
        // Stop complete, mark delivery as done
        if (truck.currentStop !== null) {
          const stop = truck.deliveryStops[truck.currentStop];
          if (!stop.delivered) {
            stop.delivered = true;
            this.deliveryStatus[truck.id].delivered++;
            this.collectedMoney += stop.itemsValue || 0; // Add money collected
            console.log(`Truck ${truck.id + 1} completed delivery at stop ${truck.currentStop + 1} - Collected $${stop.itemsValue}`);
            
            // Update the JSON file if we have a filename
            this.updateDeliveryInJSON(truck.id, stop.stopNumber);
          }
        }
        truck.isAtStop = false;
        truck.currentStop = null;
        truck.stopStartTime = null;
      }
    }
    
    if (elapsedSeconds >= truck.duration) {
      // Truck has finished
      truck.progress = 1;
      return truck.path[truck.path.length - 1];
    }
    
    // Calculate progress (0 to 1)
    const overallProgress = elapsedSeconds / truck.duration;
    truck.progress = overallProgress;
    
    // Find which segment of the path we're on
    const totalSegments = truck.path.length - 1;
    const segmentProgress = overallProgress * totalSegments;
    const currentSegment = Math.floor(segmentProgress);
    const segmentFraction = segmentProgress - currentSegment;
    
    if (currentSegment >= totalSegments) {
      return truck.path[truck.path.length - 1];
    }
    
    // Interpolate position within current segment
    const start = truck.path[currentSegment];
    const end = truck.path[currentSegment + 1];
    
    const newPosition = this.interpolatePosition(start, end, segmentFraction);
    
    // Check if truck reached a delivery waypoint
    if (!truck.isAtStop) {
      for (let i = 0; i < truck.deliveryStops.length; i++) {
        const stop = truck.deliveryStops[i];
        if (!stop.delivered) {
          const distance = this.calculateDistance(newPosition, stop.coords);
          if (distance < 0.0005) { // Close enough to waypoint (about 50 meters)
            // Start delivery stop
            truck.isAtStop = true;
            truck.currentStop = i;
            truck.stopStartTime = elapsedSeconds;
            console.log(`Truck ${truck.id + 1} arrived at delivery stop ${i + 1}`);
            break;
          }
        }
      }
    }
    
    return newPosition;
  }
  
  async updateDeliveryInJSON(truckId, stopNumber) {
    if (!this.exportFilename) {
      console.log('No export filename available, skipping JSON update');
      return;
    }
    
    try {
      const response = await fetch(`${CONFIG.apiUrl}/update-delivery-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: this.exportFilename,
          truck_id: truckId,
          stop_number: stopNumber,
          status: 'completed'
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log(`✓ JSON updated: ${result.message}`);
      } else {
        console.error('Failed to update JSON:', response.status);
      }
    } catch (error) {
      console.error('Error updating JSON:', error);
    }
  }
  
  calculateDistance(coord1, coord2) {
    // Simple Euclidean distance for proximity check
    const dx = coord1[0] - coord2[0];
    const dy = coord1[1] - coord2[1];
    return Math.sqrt(dx * dx + dy * dy);
  }

  animate(timestamp) {
    if (!this.isRunning) return;
    
    if (!this.startTime) {
      this.startTime = timestamp;
    }
    
    const elapsedSeconds = (timestamp - this.startTime) / 1000;
    
    let allFinished = true;
    let trucksStillOut = 0;
    
    // Update each truck position
    this.trucks.forEach(truck => {
      const position = this.getPositionAtTime(truck, elapsedSeconds);
      truck.currentPosition = position;
      
      if (truck.marker) {
        truck.marker.setLngLat(position);
      }
      
      if (truck.progress < 1) {
        allFinished = false;
        trucksStillOut++;
      }
    });
    
    // Update truck count cards in real-time
    if (typeof updateTrucksOut === 'function') {
      updateTrucksOut(trucksStillOut);
    }
    if (typeof updateTrucksInDepot === 'function') {
      updateTrucksInDepot(5 - trucksStillOut);
    }
    
    // Update progress display
    this.updateProgressDisplay(elapsedSeconds);
    
    if (allFinished) {
      this.stop();
      this.showCompletionMessage();
    } else {
      this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
    }
  }

  updateProgressDisplay(elapsedSeconds) {
    const progressDiv = document.getElementById('simulationProgress');
    if (!progressDiv) return;
    
    let html = '<div style="margin-top:10px; padding:8px; background:rgba(255, 243, 205, 0.2); border-radius:4px; font-size:10px; border: 1px solid rgba(255, 243, 205, 0.3);">';
    html += '<strong>Simulation Running...</strong><br>';
    html += `Time: ${elapsedSeconds.toFixed(1)}s<br><br>`;
    
    let totalDelivered = 0;
    let totalDestinations = 0;
    let inProgress = 0;
    
    this.trucks.forEach(truck => {
      const hasIncident = this.incidentTrucks.has(truck.id);
      const percentage = (truck.progress * 100).toFixed(0);
      const barColor = hasIncident ? '#dc3545' : truck.color;
      
      let status;
      let extraInfo = '';
      if (hasIncident) {
        status = '⚠️ INCIDENT';
      } else if (truck.isAtStop) {
        const stopDuration = elapsedSeconds - truck.stopStartTime;
        const remaining = Math.max(0, 5 - stopDuration).toFixed(1);
        const currentStop = truck.deliveryStops[truck.currentStop];
        status = `🚚 Delivering...`;
        extraInfo = `<div style="font-size:9px; color:#aaa; margin-left:20px; margin-top:2px;">
          📍 ${currentStop.name}<br>
          📦 ${currentStop.items.slice(0, 2).join(', ')}${currentStop.items.length > 2 ? '...' : ''}<br>
          ⏱️ ${remaining}s remaining
        </div>`;
        inProgress++;
      } else {
        status = `${percentage}%`;
      }
      
      const deliveryInfo = this.deliveryStatus[truck.id];
      const deliveryText = `${deliveryInfo.delivered}/${deliveryInfo.total} delivered`;
      totalDelivered += deliveryInfo.delivered;
      totalDestinations += deliveryInfo.total;
      
      html += `<div style="margin:4px 0;">`;
      html += `<span class="truck-color" style="background:${barColor}"></span>`;
      html += `Truck ${truck.id + 1}: ${status}`;
      html += extraInfo;
      html += `<div style="font-size:9px; color:#aaa; margin-left:20px;">${deliveryText}</div>`;
      html += `<div style="background:#1a1a1a; height:4px; border-radius:2px; margin-top:2px;">`;
      html += `<div style="background:${barColor}; height:4px; border-radius:2px; width:${percentage}%;"></div>`;
      html += `</div></div>`;
    });
    
    html += '</div>';
    progressDiv.innerHTML = html;
    
    // Update KPI dashboard
    const pending = totalDestinations - totalDelivered - inProgress;
    const completedPercentage = totalDestinations > 0 ? Math.round((totalDelivered / totalDestinations) * 100) : 0;
    
    // Update delivery status bars
    if (typeof updateDeliveryStatus === 'function') {
      updateDeliveryStatus(totalDelivered, inProgress, pending);
    }
    
    // Update completed gauge
    if (typeof updateCompletedGauge === 'function') {
      updateCompletedGauge(completedPercentage);
    }
    
    // Update money pie chart
    const missingMoney = this.totalMoneyValue - this.collectedMoney;
    if (typeof updateMoneyPieChart === 'function') {
      updateMoneyPieChart(this.collectedMoney, missingMoney);
    }
  }

  showCompletionMessage() {
    const progressDiv = document.getElementById('simulationProgress');
    if (progressDiv) {
      progressDiv.innerHTML = `
        <div style="margin-top:10px; padding:8px; background:rgba(76, 175, 80, 0.2); border-radius:4px; font-size:10px; border: 1px solid rgba(76, 175, 80, 0.3);">
          <strong>✓ Simulation Complete!</strong><br>
          All trucks have returned to depot.<br>
          <strong>Total Money Collected: $${this.collectedMoney.toFixed(2)}</strong>
        </div>
      `;
    }
    
    // Update cards - all trucks back in depot
    if (typeof updateTrucksOut === 'function') {
      updateTrucksOut(0);
    }
    if (typeof updateTrucksInDepot === 'function') {
      updateTrucksInDepot(5);
    }
    
    // Final KPI update - all completed
    let totalDestinations = 0;
    this.trucks.forEach(truck => {
      totalDestinations += this.deliveryStatus[truck.id].total;
    });
    
    if (typeof updateDeliveryStatus === 'function') {
      updateDeliveryStatus(totalDestinations, 0, 0);
    }
    
    if (typeof updateCompletedGauge === 'function') {
      updateCompletedGauge(100);
    }
    
    // Final money update - all collected
    if (typeof updateMoneyPieChart === 'function') {
      updateMoneyPieChart(this.totalMoneyValue, 0);
    }
  }

  start() {
    if (this.trucks.length === 0) {
      alert('Please optimize routes first!');
      return;
    }
    
    if (this.isRunning) {
      console.log('Simulation already running');
      return;
    }
    
    console.log('Starting simulation...');
    this.isRunning = true;
    this.startTime = null;
    
    // Update cards - all trucks are now out
    const trucksWithRoutes = this.trucks.length;
    if (typeof updateTrucksOut === 'function') {
      updateTrucksOut(trucksWithRoutes);
    }
    if (typeof updateTrucksInDepot === 'function') {
      updateTrucksInDepot(5 - trucksWithRoutes);
    }
    
    // Create markers for all trucks
    this.trucks.forEach(truck => {
      truck.progress = 0;
      truck.currentPosition = depot;
      truck.marker = this.createTruckMarker(truck);
    });
    
    // Add progress display
    const results = document.getElementById('results');
    if (!document.getElementById('simulationProgress')) {
      const progressDiv = document.createElement('div');
      progressDiv.id = 'simulationProgress';
      results.appendChild(progressDiv);
    }
    
    // Update button states
    const startBtn = document.getElementById('startSimBtn');
    const stopBtn = document.getElementById('stopSimBtn');
    if (startBtn) startBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = false;
    
    // Start animation
    this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
  }

  stop() {
    console.log('Stopping simulation...');
    this.isRunning = false;
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    // Remove truck markers
    this.trucks.forEach(truck => {
      if (truck.marker) {
        truck.marker.remove();
        truck.marker = null;
      }
    });
    
    // Update cards - all trucks back in depot
    if (typeof updateTrucksOut === 'function') {
      updateTrucksOut(0);
    }
    if (typeof updateTrucksInDepot === 'function') {
      updateTrucksInDepot(5);
    }
    
    // Update button states
    const startBtn = document.getElementById('startSimBtn');
    const stopBtn = document.getElementById('stopSimBtn');
    if (startBtn) startBtn.disabled = false;
    if (stopBtn) stopBtn.disabled = true;
    
    // Remove progress display
    const progressDiv = document.getElementById('simulationProgress');
    if (progressDiv) {
      progressDiv.remove();
    }
  }

  reset() {
    this.stop();
    this.trucks = [];
    this.startTime = null;
    this.incidentTrucks.clear();
    this.deliveryStatus = {};
  }
}

// Global simulation instance
const simulation = new TruckSimulation();
