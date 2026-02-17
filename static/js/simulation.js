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
      // INMEDIATAMENTE detener TODOS los camiones
      console.log('🚨 Deteniendo todos los camiones...');
      
      // Pausar la animación
      const wasRunning = this.isRunning;
      if (wasRunning) {
        this.isRunning = false;
        if (this.animationFrameId) {
          cancelAnimationFrame(this.animationFrameId);
        }
      }
      
      // Marcar el camión con incidente
      this.incidentTrucks.add(truckId);
      
      // Marcar visualmente el camión con incidente
      const incidentTruck = this.trucks.find(t => t.id === truckId);
      if (incidentTruck && incidentTruck.marker) {
        const el = incidentTruck.marker.getElement();
        el.style.backgroundColor = '#dc3545';
        el.style.border = '3px solid #ff0000';
        el.innerHTML = `<div style="color:white;font-size:10px;font-weight:bold;text-align:center;line-height:18px;">⚠️</div>`;
      }
      
      // Recopilar posiciones actuales de todos los camiones
      const truckPositions = {};
      this.trucks.forEach(truck => {
        truckPositions[truck.id] = {
          lat: truck.currentPosition[1],
          lng: truck.currentPosition[0],
          currentStop: truck.currentStop || 0,
          status: truck.id === truckId ? 'incident' : 'paused',
          progress: Math.round(truck.progress * 100)
        };
      });
      
      console.log('📍 Posiciones de camiones:', truckPositions);
      
      // Mostrar mensaje de procesamiento
      const processingMsg = document.createElement('div');
      processingMsg.id = 'incident-processing';
      processingMsg.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.9);
        color: white;
        padding: 20px 40px;
        border-radius: 8px;
        z-index: 10000;
        text-align: center;
        font-size: 14px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      `;
      processingMsg.innerHTML = `
        <div style="margin-bottom: 10px; font-size: 16px;">🚨 Incidente Reportado</div>
        <div style="font-size: 12px; color: #aaa;">Todos los camiones detenidos</div>
        <div style="margin-top: 15px; font-size: 12px;">
          <div class="spinner" style="border: 3px solid #333; border-top: 3px solid #fff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 10px auto;"></div>
          <div style="margin-top: 10px;">Analizando situación...</div>
          <div style="margin-top: 5px; color: #888; font-size: 11px;">Buscando camión más cercano</div>
        </div>
      `;
      document.body.appendChild(processingMsg);
      
      // Agregar animación de spinner
      const style = document.createElement('style');
      style.textContent = '@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
      document.head.appendChild(style);
      
      // Close the popup
      if (incidentTruck && incidentTruck.marker) {
        incidentTruck.marker.getPopup().remove();
      }
      
      // Llamar al backend con las posiciones actuales
      const response = await fetch(`${CONFIG.apiUrl}/report-incident`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          truck_id: truckId,
          truck_positions: truckPositions
        })
      });
      
      // Remover mensaje de procesamiento
      const msg = document.getElementById('incident-processing');
      if (msg) msg.remove();
      
      if (response.ok) {
        const result = await response.json();
        const orchestration = result.orchestration;
        
        console.log('📊 Resultado de orquestación:', orchestration);
        
        if (orchestration && orchestration.success) {
          const newRoute = orchestration.new_route;
          const selectedTruckId = newRoute.truck_id;
          const incidentAnalysis = orchestration.solution.incident_analysis;
          const validation = orchestration.validation;
          
          if (newRoute && newRoute.summary) {
            // Calcular métricas de impacto
            const pendingValue = incidentAnalysis.pending_value_usd || 0;
            const additionalDistance = newRoute.summary.total_distance_km;
            const additionalTime = newRoute.summary.total_duration_minutes;
            const availableItems = orchestration.solution.inventory_check.available_items || 0;
            const totalItems = orchestration.solution.inventory_check.total_items_checked || 0;
            const unavailableItems = validation.unavailable_items || [];
            
            // Calcular valor recuperable (proporción de items disponibles)
            const recoverableValue = (availableItems / totalItems) * pendingValue;
            const lostValue = pendingValue - recoverableValue;
            
            // Mostrar modal con métricas
            this.showIncidentSolutionModal({
              incidentTruckId: truckId,
              selectedTruckId: selectedTruckId,
              selectedTruckName: newRoute.truck_name,
              incidentTruckName: incidentAnalysis.truck_name,
              totalDestinations: newRoute.summary.total_destinations,
              additionalDistance: additionalDistance,
              additionalTime: additionalTime,
              pendingValue: pendingValue,
              recoverableValue: recoverableValue,
              lostValue: lostValue,
              availableItems: availableItems,
              totalItems: totalItems,
              unavailableItems: unavailableItems,
              partialDelivery: validation.partial_delivery,
              confidence: validation.confidence,
              // Datos completos para explicación LLM
              fullOrchestration: orchestration
            }, (accepted) => {
              if (accepted) {
                // Aplicar la solución
                this.applyIncidentSolution(selectedTruckId, newRoute, wasRunning);
              } else {
                // Usuario rechazó la solución
                console.log('❌ Usuario rechazó la solución propuesta');
                
                // Reanudar simulación sin cambios
                if (wasRunning) {
                  this.isRunning = true;
                  this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
                  console.log('▶️ Simulación reanudada sin cambios');
                }
              }
            });
          }
        } else {
          let message = `❌ No se pudo encontrar solución automática\n`;
          if (orchestration && orchestration.error) {
            message += `Razón: ${orchestration.error}`;
          }
          
          alert(message);
          
          // Reanudar simulación sin cambios
          if (wasRunning) {
            this.isRunning = true;
            this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
          }
        }
      } else {
        alert('Failed to report incident');
        // Reanudar simulación en caso de error
        if (wasRunning) {
          this.isRunning = true;
          this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
        }
      }
    } catch (error) {
      // Remover mensaje de procesamiento en caso de error
      const msg = document.getElementById('incident-processing');
      if (msg) msg.remove();
      
      console.error('Error reporting incident:', error);
      alert('Error reporting incident: ' + error.message);
      
      // Reanudar simulación en caso de error
      if (this.isRunning === false) {
        this.isRunning = true;
        this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
      }
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
    
    // Validar que start y end existen
    if (!start || !end || !Array.isArray(start) || !Array.isArray(end)) {
      console.error(`Segmento inválido para camión ${truck.id}: segment=${currentSegment}, path length=${truck.path.length}`);
      console.error(`start:`, start, `end:`, end);
      return truck.currentPosition || truck.path[0] || depot;
    }
    
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
      let position;
      
      // Manejar camiones redirigidos de manera especial
      if (truck.wasRedirected && truck.redirectedAt) {
        // Verificar si está en una parada de entrega
        if (truck.isAtStop && truck.stopStartTime !== null) {
          const stopDuration = (timestamp - truck.stopStartTime) / 1000;
          if (stopDuration < 5) { // 5 segundos = 5 minutos
            // Todavía en la parada, no mover
            position = truck.currentPosition;
          } else {
            // Parada completada, marcar entrega
            if (truck.currentStop !== null) {
              const stop = truck.deliveryStops[truck.currentStop];
              if (!stop.delivered) {
                stop.delivered = true;
                this.deliveryStatus[truck.id].delivered++;
                this.collectedMoney += stop.itemsValue || 0;
                console.log(`✓ Truck ${truck.id + 1} completed delivery at stop ${truck.currentStop + 1}`);
                
                // Update JSON if we have a filename
                this.updateDeliveryInJSON(truck.id, stop.stopNumber);
              }
            }
            truck.isAtStop = false;
            truck.currentStop = null;
            truck.stopStartTime = null;
          }
        }
        
        if (!truck.isAtStop) {
          // Calcular tiempo desde la redirección
          const timeSinceRedirect = (timestamp - truck.redirectedAt) / 1000;
          
          // Calcular progreso de la redirección (0 a 1)
          const redirectProgress = Math.min(timeSinceRedirect / truck.duration, 1);
          truck.redirectProgress = redirectProgress;
          
          // Log para debugging
          if (redirectProgress < 0.05 || (redirectProgress > 0 && redirectProgress < 1 && Math.random() < 0.01)) {
            console.log(`🚗 Camión ${truck.id + 1} redirigido:`);
            console.log(`   progress=${(redirectProgress*100).toFixed(1)}%`);
            console.log(`   time=${timeSinceRedirect.toFixed(1)}s / ${truck.duration.toFixed(1)}s`);
            console.log(`   path length=${truck.path.length}`);
          }
          
          // Interpolar desde la posición de inicio de redirección hasta el destino
          if (redirectProgress >= 1) {
            // Llegó al destino
            position = truck.path[truck.path.length - 1];
            truck.progress = 1;
          } else {
            // Calcular posición en el path de redirección
            const totalSegments = truck.path.length - 1;
            const segmentProgress = redirectProgress * totalSegments;
            const currentSegment = Math.floor(segmentProgress);
            const segmentFraction = segmentProgress - currentSegment;
            
            if (currentSegment >= totalSegments) {
              position = truck.path[truck.path.length - 1];
            } else {
              const start = truck.path[currentSegment];
              const end = truck.path[currentSegment + 1];
              
              if (start && end && Array.isArray(start) && Array.isArray(end)) {
                position = this.interpolatePosition(start, end, segmentFraction);
              } else {
                position = truck.currentPosition || truck.path[0];
              }
            }
            
            truck.progress = redirectProgress;
            
            // Verificar si llegó a una parada de entrega
            if (!truck.isAtStop) {
              for (let i = 0; i < truck.deliveryStops.length; i++) {
                const stop = truck.deliveryStops[i];
                if (!stop.delivered) {
                  const distance = this.calculateDistance(position, stop.coords);
                  if (distance < 0.0005) { // Cerca del waypoint (~50 metros)
                    // Iniciar parada de entrega
                    truck.isAtStop = true;
                    truck.currentStop = i;
                    truck.stopStartTime = timestamp;
                    console.log(`🚚 Truck ${truck.id + 1} arrived at delivery stop ${i + 1} (${stop.location})`);
                    break;
                  }
                }
              }
            }
          }
        }
      } else {
        // Camión normal (no redirigido)
        const effectiveElapsedSeconds = elapsedSeconds;
        position = this.getPositionAtTime(truck, effectiveElapsedSeconds);
      }
      
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
    const redirectDepotBtn = document.getElementById('redirectAllToDepotBtn');
    const redirectCustomBtn = document.getElementById('redirectCustomBtn');
    const redirectSelector = document.getElementById('redirectTruckSelector');
    
    if (startBtn) startBtn.disabled = true;
    if (stopBtn) stopBtn.disabled = false;
    if (redirectDepotBtn) redirectDepotBtn.disabled = false;
    if (redirectCustomBtn) redirectCustomBtn.disabled = false;
    if (redirectSelector) redirectSelector.disabled = false;
    
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
    const redirectDepotBtn = document.getElementById('redirectAllToDepotBtn');
    const redirectCustomBtn = document.getElementById('redirectCustomBtn');
    const redirectSelector = document.getElementById('redirectTruckSelector');
    
    if (startBtn) startBtn.disabled = false;
    if (stopBtn) stopBtn.disabled = true;
    if (redirectDepotBtn) redirectDepotBtn.disabled = true;
    if (redirectCustomBtn) redirectCustomBtn.disabled = true;
    if (redirectSelector) redirectSelector.disabled = true;
    
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
  
  getCurrentPositions() {
    /**
     * Retorna las posiciones actuales de todos los camiones
     * Para uso del chat y otros componentes
     */
    const positions = {};
    
    this.trucks.forEach(truck => {
      const currentPos = truck.currentPosition;
      
      // Encontrar la parada actual (última entrega completada)
      let currentStop = 0;
      if (truck.deliveryStops) {
        for (let i = 0; i < truck.deliveryStops.length; i++) {
          if (truck.deliveryStops[i].delivered) {
            currentStop = truck.deliveryStops[i].stopNumber;
          }
        }
      }
      
      positions[truck.id] = {
        lat: currentPos[1],  // latitude
        lng: currentPos[0],  // longitude
        currentStop: currentStop,
        status: truck.isAtStop ? 'delivering' : 'in_transit',
        progress: Math.round(truck.progress * 100)
      };
    });
    
    return positions;
  }
  
  /**
   * Redirige todos los camiones a una ubicación específica
   * @param {Array} targetCoords - [lng, lat] de destino
   * @param {String} targetName - Nombre del destino (ej: "Almacén", "Depósito")
   */
  async redirectAllTrucks(targetCoords, targetName = "Almacén") {
    if (!this.isRunning) {
      alert('La simulación debe estar corriendo para redirigir camiones');
      return;
    }
    
    console.log(`Redirigiendo todos los camiones a ${targetName} [${targetCoords}]`);
    
    // Redirigir cada camión secuencialmente
    for (const truck of this.trucks) {
      await this.redirectTruck(truck.id, targetCoords, targetName);
    }
    
    alert(`✓ Todos los camiones han sido redirigidos a ${targetName}`);
  }
  
  /**
   * Redirige un camión específico a una ubicación
   * @param {Number} truckId - ID del camión
   * @param {Array} targetCoords - [lng, lat] de destino
   * @param {String} targetName - Nombre del destino
   */
  async redirectTruck(truckId, targetCoords, targetName = "Nueva ubicación") {
    const truck = this.trucks.find(t => t.id === truckId);
    if (!truck) {
      console.error(`Camión ${truckId} no encontrado`);
      return;
    }
    
    // Validar targetCoords
    if (!targetCoords || !Array.isArray(targetCoords) || targetCoords.length !== 2) {
      console.error(`Coordenadas inválidas:`, targetCoords);
      alert('Error: Coordenadas inválidas');
      return;
    }
    
    // Si el camión tiene un incidente, no redirigir
    if (this.incidentTrucks.has(truckId)) {
      console.log(`Camión ${truckId} tiene un incidente, no se puede redirigir`);
      alert(`Camión ${truckId + 1} tiene un incidente y no puede ser redirigido`);
      return;
    }
    
    // Obtener posición actual del camión
    const currentPos = truck.currentPosition;
    
    // Validar currentPos
    if (!currentPos || !Array.isArray(currentPos) || currentPos.length !== 2) {
      console.error(`Posición actual inválida:`, currentPos);
      alert('Error: Posición actual del camión inválida');
      return;
    }
    
    // Guardar la posición original antes de cualquier cambio
    const originalPosition = [currentPos[0], currentPos[1]];
    
    console.log(`🔄 Calculando ruta de redirección para Camión ${truckId + 1}...`);
    
    try {
      // Llamar al backend para calcular la ruta real con AWS
      const response = await fetch(`${CONFIG.apiUrl}/calculate-redirect-route`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin: currentPos,
          destination: targetCoords
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const routeData = await response.json();
      
      console.log(`✓ Ruta calculada: ${routeData.geometry.length} puntos, ${routeData.distance_km} km, ${routeData.duration_minutes} min`);
      
      // Verificar que la geometría empiece cerca de la posición actual
      if (routeData.geometry && routeData.geometry.length > 0) {
        const firstPoint = routeData.geometry[0];
        const distToFirst = this.calculateDistance(currentPos, firstPoint);
        console.log(`  Distancia a primer punto de geometría: ${distToFirst.toFixed(6)}`);
        console.log(`  Posición actual: [${currentPos[0].toFixed(6)}, ${currentPos[1].toFixed(6)}]`);
        console.log(`  Primer punto geometría: [${firstPoint[0].toFixed(6)}, ${firstPoint[1].toFixed(6)}]`);
      }
      
      // Usar la geometría real de AWS o fallback a línea recta
      let newPath;
      let duration;
      
      if (routeData.geometry && routeData.geometry.length > 0) {
        // Filtrar puntos inválidos (null, undefined, o no arrays)
        const validGeometry = routeData.geometry.filter(point => {
          if (!point || !Array.isArray(point) || point.length !== 2) {
            console.warn('Punto inválido en geometría:', point);
            return false;
          }
          if (point[0] === null || point[1] === null || 
              typeof point[0] !== 'number' || typeof point[1] !== 'number') {
            console.warn('Coordenadas inválidas en punto:', point);
            return false;
          }
          return true;
        });
        
        console.log(`  Geometría filtrada: ${validGeometry.length} de ${routeData.geometry.length} puntos válidos`);
        
        if (validGeometry.length >= 2) {
          // Usar geometría real de AWS
          newPath = validGeometry;
          // Duración basada en el tiempo real de AWS (convertido a segundos de simulación)
          // Asegurar que la duración sea razonable (mínimo 15 segundos)
          const awsDuration = routeData.duration_seconds / 20;
          duration = Math.max(awsDuration, 15);
          
          console.log(`  Duración AWS: ${routeData.duration_seconds}s real -> ${awsDuration.toFixed(1)}s simulación -> ${duration.toFixed(1)}s final`);
        } else {
          // No hay suficientes puntos válidos, usar línea recta
          console.warn('Geometría insuficiente, usando línea recta');
          newPath = [
            [currentPos[0], currentPos[1]],
            [targetCoords[0], targetCoords[1]]
          ];
          const distance = this.calculateDistance(currentPos, targetCoords);
          duration = Math.max(distance * 5000, 15);
        }
      } else {
        // Fallback a línea recta
        console.warn('No se obtuvo geometría, usando línea recta');
        newPath = [
          [currentPos[0], currentPos[1]],
          [targetCoords[0], targetCoords[1]]
        ];
        const distance = this.calculateDistance(currentPos, targetCoords);
        duration = Math.max(distance * 5000, 15);
      }
      
      console.log(`  Path tiene ${newPath.length} puntos`);
      console.log(`  Duración: ${duration.toFixed(1)}s`);
      
      // IMPORTANTE: NO resetear progress a 0
      // El camión debe continuar desde donde está, no desde el inicio del path
      
      // Actualizar el camión
      truck.path = newPath;
      truck.duration = duration;
      // NO resetear progress aquí - se manejará en getPositionAtTime
      truck.isAtStop = false;
      truck.currentStop = null;
      truck.stopStartTime = null;
      
      // Guardar la posición actual antes de la redirección
      truck.redirectStartPosition = originalPosition;
      
      // Marcar el timestamp actual para calcular el tiempo desde la redirección
      truck.redirectedAt = performance.now();
      truck.wasRedirected = true;
      truck.redirectProgress = 0; // Progreso específico para la redirección
      
      console.log(`  redirectedAt: ${truck.redirectedAt}`);
      console.log(`  wasRedirected: ${truck.wasRedirected}`);
      
      // Limpiar entregas pendientes (ya no va a esos destinos)
      truck.deliveryStops = [{
        waypointIndex: 0,
        coords: [targetCoords[0], targetCoords[1]],
        name: targetName,
        items: [],
        itemsValue: 0,
        delivered: false,
        stopNumber: 1
      }];
      
      // Actualizar el estado de entregas
      this.deliveryStatus[truckId] = {
        total: 1,
        delivered: 0,
        stops: truck.deliveryStops
      };
      
      console.log(`✓ Camión ${truckId + 1} redirigido a ${targetName}`);
      console.log(`  Posición actual: [${currentPos[0].toFixed(4)}, ${currentPos[1].toFixed(4)}]`);
      console.log(`  Destino: [${targetCoords[0].toFixed(4)}, ${targetCoords[1].toFixed(4)}]`);
      console.log(`  Puntos de ruta: ${newPath.length}`);
      console.log(`  Duración estimada: ${duration.toFixed(1)}s`);
      console.log(`  Primer punto del path: [${newPath[0][0].toFixed(4)}, ${newPath[0][1].toFixed(4)}]`);
      console.log(`  Último punto del path: [${newPath[newPath.length-1][0].toFixed(4)}, ${newPath[newPath.length-1][1].toFixed(4)}]`);
      
      // Actualizar el marcador visualmente
      if (truck.marker) {
        const el = truck.marker.getElement();
        el.style.backgroundColor = '#FFA500'; // Color naranja para indicar redirección
        el.style.border = '3px solid #FF8C00';
        
        // IMPORTANTE: Forzar que el marcador se quede en la posición actual
        truck.marker.setLngLat(originalPosition);
      }
      
      // Forzar que currentPosition sea la posición original
      truck.currentPosition = originalPosition;
      
      // Opcional: Dibujar la nueva ruta en el mapa
      this.drawRedirectRoute(truckId, newPath);
      
    } catch (error) {
      console.error('Error calculando ruta de redirección:', error);
      alert(`Error al calcular ruta: ${error.message}\nUsando ruta directa como fallback.`);
      
      // Fallback a línea recta si falla la API
      const newPath = [
        [currentPos[0], currentPos[1]],
        [targetCoords[0], targetCoords[1]]
      ];
      const distance = this.calculateDistance(currentPos, targetCoords);
      const duration = Math.max(distance * 5000, 15);
      
      const originalPosition = [truck.currentPosition[0], truck.currentPosition[1]];
      
      truck.path = newPath;
      truck.duration = duration;
      truck.isAtStop = false;
      truck.currentStop = null;
      truck.stopStartTime = null;
      
      truck.redirectStartPosition = originalPosition;
      truck.redirectedAt = performance.now();
      truck.wasRedirected = true;
      truck.redirectProgress = 0;
      
      truck.deliveryStops = [{
        waypointIndex: 0,
        coords: [targetCoords[0], targetCoords[1]],
        name: targetName,
        items: [],
        itemsValue: 0,
        delivered: false,
        stopNumber: 1
      }];
      
      this.deliveryStatus[truckId] = {
        total: 1,
        delivered: 0,
        stops: truck.deliveryStops
      };
      
      if (truck.marker) {
        const el = truck.marker.getElement();
        el.style.backgroundColor = '#FFA500';
        el.style.border = '3px solid #FF8C00';
      }
    }
  }
  
  /**
   * Muestra modal con análisis de impacto de la solución
   */
  showIncidentSolutionModal(metrics, callback) {
    // Crear modal
    const modal = document.createElement('div');
    modal.id = 'incident-solution-modal';
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.8);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
    `;
    
    const recoveryRate = (metrics.recoverableValue / metrics.pendingValue * 100).toFixed(0);
    const itemsRate = (metrics.availableItems / metrics.totalItems * 100).toFixed(0);
    
    modal.innerHTML = `
      <div style="background: #1a1a1a; border-radius: 12px; padding: 30px; max-width: 600px; width: 90%; color: white; box-shadow: 0 10px 40px rgba(0,0,0,0.5);">
        <h2 style="margin: 0 0 20px 0; font-size: 24px; color: #fff;">🚨 Solución de Incidente</h2>
        
        <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
          <div style="font-size: 14px; color: #aaa; margin-bottom: 10px;">Incidente en:</div>
          <div style="font-size: 18px; font-weight: bold;">${metrics.incidentTruckName}</div>
        </div>
        
        <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
          <div style="font-size: 14px; color: #aaa; margin-bottom: 10px;">Solución propuesta:</div>
          <div style="font-size: 16px; font-weight: bold; color: #00ff00;">${metrics.selectedTruckName} asumirá las entregas</div>
          <div style="font-size: 12px; color: #888; margin-top: 5px;">
            ${metrics.totalDestinations} destinos • ${metrics.additionalDistance.toFixed(1)} km • ${metrics.additionalTime.toFixed(0)} min
          </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
          <div style="background: #2a2a2a; padding: 15px; border-radius: 8px;">
            <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">💰 Valor en Riesgo</div>
            <div style="font-size: 24px; font-weight: bold; color: #ff6b6b;">$${metrics.pendingValue.toFixed(0)}</div>
          </div>
          
          <div style="background: #2a2a2a; padding: 15px; border-radius: 8px;">
            <div style="font-size: 12px; color: #aaa; margin-bottom: 5px;">✅ Valor Recuperable</div>
            <div style="font-size: 24px; font-weight: bold; color: #51cf66;">$${metrics.recoverableValue.toFixed(0)}</div>
            <div style="font-size: 11px; color: #888;">${recoveryRate}% del total</div>
          </div>
        </div>
        
        <div style="background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
          <div style="font-size: 12px; color: #aaa; margin-bottom: 10px;">📦 Disponibilidad de Items</div>
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
            <div style="flex: 1; background: #1a1a1a; height: 20px; border-radius: 10px; overflow: hidden;">
              <div style="background: linear-gradient(90deg, #51cf66, #40c057); height: 100%; width: ${itemsRate}%; transition: width 0.3s;"></div>
            </div>
            <div style="font-size: 14px; font-weight: bold;">${itemsRate}%</div>
          </div>
          <div style="font-size: 12px; color: #888;">
            ${metrics.availableItems} de ${metrics.totalItems} items disponibles
          </div>
          ${metrics.unavailableItems.length > 0 ? `
            <div style="margin-top: 10px; padding: 10px; background: #3a2a2a; border-radius: 6px; border-left: 3px solid #ff6b6b;">
              <div style="font-size: 11px; color: #ff6b6b; margin-bottom: 5px;">⚠️ Items no disponibles (${metrics.unavailableItems.length}):</div>
              <div style="font-size: 10px; color: #aaa;">
                ${metrics.unavailableItems.slice(0, 3).join(', ')}${metrics.unavailableItems.length > 3 ? ` y ${metrics.unavailableItems.length - 3} más` : ''}
              </div>
            </div>
          ` : ''}
        </div>
        
        ${metrics.lostValue > 0 ? `
          <div style="background: #3a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 3px solid #ff6b6b;">
            <div style="font-size: 12px; color: #ff6b6b; margin-bottom: 5px;">⚠️ Impacto de NO aceptar:</div>
            <div style="font-size: 14px; color: #fff;">
              • Pérdida de <strong>$${metrics.lostValue.toFixed(0)}</strong> en entregas no disponibles<br>
              • Pérdida de <strong>$${metrics.recoverableValue.toFixed(0)}</strong> en entregas disponibles<br>
              • Total: <strong style="color: #ff6b6b;">$${metrics.pendingValue.toFixed(0)}</strong>
            </div>
          </div>
        ` : ''}
        
        <div style="background: #2a4a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 3px solid #51cf66;">
          <div style="font-size: 12px; color: #51cf66; margin-bottom: 5px;">✅ Beneficios de aceptar:</div>
          <div style="font-size: 14px; color: #fff;">
            • Recuperar <strong>$${metrics.recoverableValue.toFixed(0)}</strong> (${recoveryRate}%)<br>
            • Completar ${metrics.availableItems} entregas<br>
            • Tiempo adicional: solo ${metrics.additionalTime.toFixed(0)} min
          </div>
        </div>
        
        <div style="display: flex; gap: 10px; margin-top: 20px;">
          <button id="explain-solution-btn" style="flex: 0.5; padding: 12px; background: #4a90e2; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: bold; cursor: pointer;">
            💡 Explicar
          </button>
          <button id="reject-solution-btn" style="flex: 1; padding: 12px; background: #dc3545; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer;">
            ❌ Rechazar
          </button>
          <button id="accept-solution-btn" style="flex: 1; padding: 12px; background: #28a745; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer;">
            ✅ Aceptar Solución
          </button>
        </div>
        
        <div id="explanation-container" style="display: none; margin-top: 15px; padding: 15px; background: #2a3a4a; border-radius: 8px; border-left: 3px solid #4a90e2;">
          <div style="font-size: 12px; color: #4a90e2; margin-bottom: 10px;">💡 Explicación del Sistema:</div>
          <div id="explanation-text" style="font-size: 13px; color: #ddd; line-height: 1.6;">
            <div style="text-align: center; padding: 20px;">
              <div class="spinner" style="border: 3px solid #333; border-top: 3px solid #4a90e2; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
              <div style="margin-top: 10px; color: #888;">Generando explicación...</div>
            </div>
          </div>
        </div>
        
        <div style="margin-top: 15px; text-align: center; font-size: 11px; color: #666;">
          Confianza del sistema: ${metrics.confidence}%
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Event listeners
    document.getElementById('accept-solution-btn').onclick = () => {
      document.body.removeChild(modal);
      callback(true);
    };
    
    document.getElementById('reject-solution-btn').onclick = () => {
      document.body.removeChild(modal);
      callback(false);
    };
    
    // Botón de explicación
    document.getElementById('explain-solution-btn').onclick = async () => {
      const explainBtn = document.getElementById('explain-solution-btn');
      const explanationContainer = document.getElementById('explanation-container');
      const explanationText = document.getElementById('explanation-text');
      
      // Mostrar contenedor
      explanationContainer.style.display = 'block';
      explainBtn.disabled = true;
      explainBtn.style.opacity = '0.5';
      
      try {
        // Llamar al backend para generar explicación
        const response = await fetch(`${CONFIG.apiUrl}/explain-incident-solution`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            orchestration: metrics.fullOrchestration,
            metrics: {
              pendingValue: metrics.pendingValue,
              recoverableValue: metrics.recoverableValue,
              availableItems: metrics.availableItems,
              totalItems: metrics.totalItems,
              additionalTime: metrics.additionalTime,
              additionalDistance: metrics.additionalDistance
            }
          })
        });
        
        if (response.ok) {
          const result = await response.json();
          explanationText.innerHTML = result.explanation.replace(/\n/g, '<br>');
        } else {
          explanationText.innerHTML = '<span style="color: #ff6b6b;">Error al generar explicación. Por favor intenta de nuevo.</span>';
        }
      } catch (error) {
        console.error('Error getting explanation:', error);
        explanationText.innerHTML = '<span style="color: #ff6b6b;">Error de conexión. Por favor intenta de nuevo.</span>';
      }
      
      explainBtn.disabled = false;
      explainBtn.style.opacity = '1';
    };
  }
  
  /**
   * Aplica la solución de incidente al camión seleccionado
   */
  applyIncidentSolution(selectedTruckId, newRoute, wasRunning) {
    console.log(`🚀 Aplicando nueva ruta al Camión ${selectedTruckId + 1}...`);
    
    // Encontrar el camión seleccionado
    const selectedTruck = this.trucks.find(t => t.id === selectedTruckId);
    
    if (selectedTruck && newRoute.waypoints && newRoute.waypoints.length > 0) {
      // Actualizar la ruta del camión seleccionado
      const newWaypoints = newRoute.waypoints.map(wp => ({
        coords: wp.coords,
        location: wp.location,
        items: wp.items || [],
        itemsValue: 0,
        delivered: false,
        stopNumber: wp.stop_number
      }));
      
      selectedTruck.deliveryStops = newWaypoints;
      
      this.deliveryStatus[selectedTruckId] = {
        total: newWaypoints.length,
        delivered: 0,
        stops: newWaypoints
      };
      
      // Usar geometría AWS
      if (newRoute.geometry && newRoute.geometry.length > 0) {
        selectedTruck.path = newRoute.geometry;
        console.log(`  ✓ Usando geometría AWS: ${newRoute.geometry.length} puntos`);
      } else {
        const currentPos = selectedTruck.currentPosition;
        const depotCoords = [-99.1908, 19.4336];
        selectedTruck.path = [currentPos, ...newWaypoints.map(wp => wp.coords), depotCoords];
        console.log(`  ✓ Usando path simple: ${selectedTruck.path.length} puntos`);
      }
      
      // Actualizar duración
      const durationMinutes = newRoute.summary.total_duration_minutes || 30;
      selectedTruck.duration = durationMinutes * 3;
      
      console.log(`  📊 Duración: ${durationMinutes.toFixed(1)} min (${selectedTruck.duration.toFixed(1)}s simulación)`);
      
      // Marcar como redirigido
      selectedTruck.wasRedirected = true;
      selectedTruck.redirectedAt = performance.now();
      selectedTruck.redirectProgress = 0;
      selectedTruck.redirectStartPosition = [selectedTruck.currentPosition[0], selectedTruck.currentPosition[1]];
      selectedTruck.isAtStop = false;
      selectedTruck.currentStop = null;
      selectedTruck.stopStartTime = null;
      
      // Cambiar color a verde
      if (selectedTruck.marker) {
        const el = selectedTruck.marker.getElement();
        el.style.backgroundColor = '#00FF00';
        el.style.border = '3px solid #00AA00';
      }
      
      console.log(`  ✓ Nueva ruta aplicada`);
      
      // Dibujar ruta en mapa
      this.drawRedirectRoute(selectedTruckId, selectedTruck.path);
      
      // Reanudar simulación
      if (wasRunning) {
        this.isRunning = true;
        this.animationFrameId = requestAnimationFrame((ts) => this.animate(ts));
        console.log('▶️ Simulación reanudada con nueva ruta');
      }
    } else {
      console.error('No se pudo aplicar la ruta');
      alert('Error: No se pudo aplicar la nueva ruta');
    }
  }

  /**
   * Dibuja la ruta de redirección en el mapa
   */
  drawRedirectRoute(truckId, routeGeometry) {
    // Remover ruta anterior si existe
    const layerId = `redirect-route-${truckId}`;
    const sourceId = `redirect-route-source-${truckId}`;
    
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }
    
    // Agregar nueva ruta
    map.addSource(sourceId, {
      type: 'geojson',
      data: {
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: routeGeometry
        }
      }
    });
    
    map.addLayer({
      id: layerId,
      type: 'line',
      source: sourceId,
      layout: {
        'line-join': 'round',
        'line-cap': 'round'
      },
      paint: {
        'line-color': '#FFA500',
        'line-width': 3,
        'line-dasharray': [2, 2]
      }
    });
    
    console.log(`✓ Ruta de redirección dibujada en el mapa (${routeGeometry.length} puntos)`);
  }
  
  /**
   * Redirige todos los camiones al almacén/depósito
   */
  redirectAllToDepot() {
    const depotCoords = [-99.1908, 19.4336]; // Coordenadas del almacén
    this.redirectAllTrucks(depotCoords, "Almacén/Depósito");
  }
  
  /**
   * Redirige un camión específico al almacén
   * @param {Number} truckId - ID del camión
   */
  redirectToDepot(truckId) {
    const depotCoords = [-99.1908, 19.4336];
    this.redirectTruck(truckId, depotCoords, "Almacén/Depósito");
  }
}

// Global simulation instance
const simulation = new TruckSimulation();

// Expose globally for chat
window.simulation = simulation;

// Funciones globales de utilidad para redirección
window.redirectAllToDepot = async function() {
  await simulation.redirectAllToDepot();
};

window.redirectTruckToDepot = async function(truckId) {
  await simulation.redirectToDepot(truckId);
};

window.redirectAllTrucks = async function(lng, lat, name = "Ubicación personalizada") {
  await simulation.redirectAllTrucks([lng, lat], name);
};

window.redirectTruck = async function(truckId, lng, lat, name = "Nueva ubicación") {
  await simulation.redirectTruck(truckId, [lng, lat], name);
};
