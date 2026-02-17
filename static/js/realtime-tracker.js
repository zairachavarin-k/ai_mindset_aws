/**
 * Real-time Truck Position Tracker
 * Actualiza las posiciones de los camiones automáticamente
 */

class RealtimeTracker {
    constructor(updateIntervalMs = 5000) {
        this.updateInterval = updateIntervalMs;
        this.intervalId = null;
        this.isRunning = false;
        this.lastPositions = {};
        this.callbacks = [];
    }

    /**
     * Inicia el tracking en tiempo real
     */
    async start() {
        if (this.isRunning) {
            console.log('Tracker already running');
            return;
        }

        console.log('🚚 Starting realtime tracker...');

        // Iniciar el simulador en el backend
        try {
            const response = await fetch('/simulator/start', {
                method: 'POST'
            });
            const data = await response.json();
            console.log('Simulator started:', data);
        } catch (error) {
            console.error('Error starting simulator:', error);
        }

        // Iniciar polling de posiciones
        this.isRunning = true;
        this.intervalId = setInterval(() => this.updatePositions(), this.updateInterval);
        
        // Primera actualización inmediata
        await this.updatePositions();
    }

    /**
     * Detiene el tracking
     */
    async stop() {
        if (!this.isRunning) {
            return;
        }

        console.log('🛑 Stopping realtime tracker...');

        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }

        this.isRunning = false;

        // Detener el simulador en el backend
        try {
            await fetch('/simulator/stop', {
                method: 'POST'
            });
            console.log('Simulator stopped');
        } catch (error) {
            console.error('Error stopping simulator:', error);
        }
    }

    /**
     * Obtiene las posiciones actuales del backend
     */
    async updatePositions() {
        try {
            const response = await fetch('/trucks/positions');
            const data = await response.json();

            if (data.status === 'success') {
                const positions = data.positions;
                
                // Detectar cambios
                const changes = this.detectChanges(positions);
                
                // Actualizar posiciones guardadas
                this.lastPositions = positions;

                // Notificar a los callbacks
                this.notifyCallbacks({
                    positions: positions,
                    changes: changes,
                    timestamp: data.timestamp,
                    simulator_active: data.simulator_active
                });

                console.log(`✓ Updated ${Object.keys(positions).length} truck positions`);
            }
        } catch (error) {
            console.error('Error updating positions:', error);
        }
    }

    /**
     * Detecta cambios en las posiciones
     */
    detectChanges(newPositions) {
        const changes = [];

        for (const [truckId, newData] of Object.entries(newPositions)) {
            const oldData = this.lastPositions[truckId];

            if (!oldData) {
                changes.push({
                    truck_id: parseInt(truckId),
                    truck_name: newData.truck_name,
                    type: 'new',
                    data: newData
                });
                continue;
            }

            // Detectar cambio de posición
            const posChanged = 
                oldData.position[0] !== newData.position[0] ||
                oldData.position[1] !== newData.position[1];

            if (posChanged) {
                changes.push({
                    truck_id: parseInt(truckId),
                    truck_name: newData.truck_name,
                    type: 'position_changed',
                    old_position: oldData.position,
                    new_position: newData.position
                });
            }

            // Detectar cambio de parada
            if (oldData.current_stop !== newData.current_stop) {
                changes.push({
                    truck_id: parseInt(truckId),
                    truck_name: newData.truck_name,
                    type: 'stop_completed',
                    old_stop: oldData.current_stop,
                    new_stop: newData.current_stop
                });
            }

            // Detectar cambio de estado
            if (oldData.status !== newData.status) {
                changes.push({
                    truck_id: parseInt(truckId),
                    truck_name: newData.truck_name,
                    type: 'status_changed',
                    old_status: oldData.status,
                    new_status: newData.status
                });
            }
        }

        return changes;
    }

    /**
     * Registra un callback para recibir actualizaciones
     */
    onUpdate(callback) {
        this.callbacks.push(callback);
    }

    /**
     * Notifica a todos los callbacks registrados
     */
    notifyCallbacks(data) {
        this.callbacks.forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('Error in callback:', error);
            }
        });
    }

    /**
     * Obtiene el estado del simulador
     */
    async getStatus() {
        try {
            const response = await fetch('/simulator/status');
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error getting simulator status:', error);
            return null;
        }
    }

    /**
     * Reinicia el simulador con nuevos datos
     */
    async reset() {
        try {
            const response = await fetch('/simulator/reset', {
                method: 'POST'
            });
            const data = await response.json();
            console.log('Simulator reset:', data);
            
            // Actualizar posiciones inmediatamente
            await this.updatePositions();
            
            return data;
        } catch (error) {
            console.error('Error resetting simulator:', error);
            return null;
        }
    }
}

// Instancia global
const realtimeTracker = new RealtimeTracker(5000); // Actualizar cada 5 segundos

// Auto-iniciar cuando se carga la página
window.addEventListener('load', () => {
    console.log('Realtime tracker ready');
    
    // Registrar callback de ejemplo para logs
    realtimeTracker.onUpdate((data) => {
        if (data.changes.length > 0) {
            console.log('📍 Position updates:', data.changes);
        }
    });
});

// Exportar para uso global
window.realtimeTracker = realtimeTracker;
