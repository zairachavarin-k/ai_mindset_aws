from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from typing import List, Dict, Optional, Any
import os
import logging
import sys
from datetime import datetime, timedelta
import json
from pathlib import Path
import csv

# Add mtsp module to path
sys.path.append(os.path.dirname(__file__))
from mtsp.index import solve_mtsp_from_coordinates

# Import truck simulator
from agents.truck_simulator import simulator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Route Optimizer API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load inventory data for pricing
INVENTORY_PRICES = {}
INVENTORY_FILE = Path("inventary/3_inventario_almacen.csv")

def load_inventory_prices():
    """Load inventory prices from CSV file"""
    global INVENTORY_PRICES
    try:
        if INVENTORY_FILE.exists():
            with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    product_name = row['nombre_producto']
                    price = float(row['valor_unitario_usd'])
                    INVENTORY_PRICES[product_name] = price
            logger.info(f"Loaded {len(INVENTORY_PRICES)} inventory items with prices")
        else:
            logger.warning(f"Inventory file not found: {INVENTORY_FILE}")
    except Exception as e:
        logger.error(f"Error loading inventory prices: {e}")

# Load inventory on startup
load_inventory_prices()

def calculate_items_value(items: List[str]) -> float:
    """Calculate total value of items based on inventory prices"""
    total = 0.0
    for item in items:
        # Try exact match first
        if item in INVENTORY_PRICES:
            total += INVENTORY_PRICES[item]
        else:
            # Try partial match (in case of quantity suffixes)
            base_item = item.split('(')[0].strip() if '(' in item else item
            if base_item in INVENTORY_PRICES:
                total += INVENTORY_PRICES[base_item]
            else:
                # Try matching by first 2-3 words (ignoring color suffix)
                # Example: "Cámara Smart Mediumaquamarine" -> match "Cámara Smart"
                words = base_item.split()
                if len(words) >= 2:
                    # Try matching first 2 words
                    prefix_2 = ' '.join(words[:2])
                    matched = False
                    for inv_item, price in INVENTORY_PRICES.items():
                        if inv_item.startswith(prefix_2):
                            total += price
                            matched = True
                            break
                    
                    if not matched and len(words) >= 3:
                        # Try matching first 3 words
                        prefix_3 = ' '.join(words[:3])
                        for inv_item, price in INVENTORY_PRICES.items():
                            if inv_item.startswith(prefix_3):
                                total += price
                                matched = True
                                break
                    
                    if not matched:
                        logger.warning(f"Item not found in inventory: {item}")
                else:
                    logger.warning(f"Item not found in inventory: {item}")
    return total

# Create data directory if it doesn't exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# Initialize AWS Location Service clients
try:
    # New geo-routes service for optimize_waypoints
    geo_routes_client = boto3.client('geo-routes', region_name='us-east-1')
    logger.info("AWS geo-routes client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize geo-routes client: {e}")
    geo_routes_client = None

try:
    # Legacy location service for calculate_route_matrix (if needed)
    location_client = boto3.client('location', region_name='us-east-1')
    logger.info("AWS location client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize location client: {e}")
    location_client = None

class Coordinate(BaseModel):
    lng: float
    lat: float

class OptimizeRequest(BaseModel):
    origin: List[float]
    destination: List[float]
    waypoints: List[List[float]]

class RouteMatrixRequest(BaseModel):
    origins: List[List[float]]
    destinations: List[List[float]]

class CalculateRouteRequest(BaseModel):
    origin: List[float]
    destination: List[float]
    waypoints: List[List[float]] = []

class MTSPRequest(BaseModel):
    num_trucks: int
    depot: List[float]
    destinations: List[List[float]]

class RouteExportRequest(BaseModel):
    truck_id: int
    waypoints: List[Dict]  # List of {coords, id, name, items}
    distance: float
    duration: float
    route_geometry: List[List[float]] = None

@app.post("/optimize-waypoints")
async def optimize_waypoints(request: OptimizeRequest):
    """Optimize waypoint sequence using AWS Location Service"""
    try:
        print("Oprsd")
        if geo_routes_client is None:
            raise HTTPException(status_code=500, detail="AWS geo-routes client not initialized. Check credentials.")
        
        logger.info(f"Optimizing route with {len(request.waypoints)} waypoints")
        logger.info(f"Origin: {request.origin}, Destination: {request.destination}")
        
        response = geo_routes_client.optimize_waypoints(
            Origin=request.origin,
            Destination=request.destination,
            Waypoints=[{"Position": wp} for wp in request.waypoints],
            TravelMode='Car',
            OptimizeSequencingFor='FastestRoute'
        )
        
        logger.info("Route optimization successful")
        return response
        
    except geo_routes_client.exceptions.ValidationException as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except geo_routes_client.exceptions.AccessDeniedException as e:
        logger.error(f"Access denied: {e}")
        raise HTTPException(status_code=403, detail="AWS credentials don't have required permissions")
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/calculate-route-matrix")
async def calculate_route_matrix(request: RouteMatrixRequest):
    """Calculate route matrix using AWS Location Service"""
    try:
        if geo_routes_client is None:
            raise HTTPException(status_code=500, detail="AWS geo-routes client not initialized. Check credentials.")
        
        logger.info(f"Calculating route matrix: {len(request.origins)} origins, {len(request.destinations)} destinations")
        
        response = geo_routes_client.calculate_route_matrix(
            Origins=[{"Position": origin} for origin in request.origins],
            Destinations=[{"Position": dest} for dest in request.destinations],
            TravelMode='Car'
        )
        
        logger.info("Route matrix calculation successful")
        return response
        
    except Exception as e:
        logger.error(f"Route matrix error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/calculate-route")
async def calculate_route(request: CalculateRouteRequest):
    """Calculate a single route with geometry using AWS Location Service"""
    try:
        if geo_routes_client is None:
            raise HTTPException(status_code=500, detail="AWS geo-routes client not initialized. Check credentials.")
        
        logger.info(f"Calculating route from {request.origin} to {request.destination} with {len(request.waypoints)} waypoints")
        
        # Build the route request
        route_params = {
            'Origin': request.origin,
            'Destination': request.destination,
            'TravelMode': 'Car',
            'LegGeometryFormat': 'Simple'  # Request geometry in response
        }
        
        # Add waypoints if provided
        if request.waypoints:
            route_params['Waypoints'] = [{"Position": wp} for wp in request.waypoints]
        
        response = geo_routes_client.calculate_routes(
            **route_params
        )
        
        logger.info(f"Route calculation successful. Response keys: {response.keys() if response else 'None'}")
        if response and 'Routes' in response and len(response['Routes']) > 0:
            logger.info(f"First route has {len(response['Routes'][0].get('Legs', []))} legs")
        return response
        
    except AttributeError as e:
        logger.error(f"Method not found: {e}")
        raise HTTPException(status_code=500, detail=f"API method error: {str(e)}")
    except Exception as e:
        logger.error(f"Route calculation error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Route Optimizer API",
        "status": "running",
        "geo_routes_client": "initialized" if geo_routes_client else "not initialized",
        "location_client": "initialized" if location_client else "not initialized"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Test AWS credentials
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        return {
            "status": "healthy",
            "aws_account": identity.get('Account'),
            "aws_user": identity.get('Arn')
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/solve-mtsp")
async def solve_mtsp_endpoint(request: MTSPRequest):
    """
    Solve the Multiple Traveling Salesman Problem using MILP
    Returns optimal assignment of destinations to trucks and routes
    """
    try:
        logger.info(f"Solving mTSP for {request.num_trucks} trucks and {len(request.destinations)} destinations")
        
        result = solve_mtsp_from_coordinates(
            num_trucks=request.num_trucks,
            depot=request.depot,
            destinations=request.destinations
        )
        
        logger.info(f"mTSP solved: Status={result['status']}, Total distance={result.get('total_distance', 'N/A')}")
        
        return result
        
    except Exception as e:
        logger.error(f"mTSP solver error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/export-routes")
async def export_routes(routes: List[RouteExportRequest]):
    """
    Generate comprehensive route information JSON for all trucks
    Includes: truck_id, date, stops, arrival_time, direction, status
    """
    try:
        logger.info(f"Generating route export for {len(routes)} trucks")
        
        # Log first route for debugging
        if routes:
            logger.info(f"Sample route data: truck_id={routes[0].truck_id}, waypoints={len(routes[0].waypoints)}")
            if routes[0].waypoints:
                logger.info(f"Sample waypoint: {routes[0].waypoints[0]}")
        
        # Current date and time as starting point
        start_datetime = datetime.now()
        
        route_data = {
            "export_date": start_datetime.isoformat(),
            "total_trucks": len(routes),
            "routes": []
        }
        
        for route in routes:
            if not route.waypoints or len(route.waypoints) == 0:
                continue
            
            # Get depot coordinates (first waypoint's coords or use a default)
            depot_coords = route.waypoints[0]['coords'] if route.waypoints else [0, 0]
            
            # Calculate arrival times for each stop based on actual AWS route data
            stops = []
            current_time = start_datetime
            
            # Add depot as first stop
            stops.append({
                "stop_number": 0,
                "location": "Depot",
                "coordinates": {
                    "longitude": float(depot_coords[0]),
                    "latitude": float(depot_coords[1])
                },
                "arrival_time": current_time.isoformat(),
                "departure_time": current_time.isoformat(),
                "status": "completed"
            })
            
            # Total travel time in minutes (from AWS)
            total_travel_minutes = route.duration / 60
            
            # Estimate time per segment (travel time divided by number of segments)
            # Segments = depot -> dest1 -> dest2 -> ... -> destN -> depot
            num_segments = len(route.waypoints) + 1  # +1 for return to depot
            time_per_segment = total_travel_minutes / num_segments if num_segments > 0 else 0
            
            # Add each destination stop
            for idx, waypoint in enumerate(route.waypoints):
                # Add travel time to get to this stop
                current_time += timedelta(minutes=time_per_segment)
                arrival_time = current_time
                
                # Add service time (assume 5 minutes per stop)
                service_time = 5
                departure_time = current_time + timedelta(minutes=service_time)
                current_time = departure_time
                
                # Safely get waypoint ID
                try:
                    waypoint_id = int(waypoint.get('id', idx))
                except (ValueError, TypeError):
                    waypoint_id = idx
                
                # Get destination name and items if available
                dest_name = waypoint.get('name', f"Destination {waypoint_id + 1}")
                dest_items = waypoint.get('items', [])
                
                # Calculate value of items at this stop
                stop_value = calculate_items_value(dest_items) if dest_items else 0.0
                
                stop_data = {
                    "stop_number": idx + 1,
                    "location": dest_name,
                    "destination_id": waypoint_id,
                    "coordinates": {
                        "longitude": float(waypoint['coords'][0]),
                        "latitude": float(waypoint['coords'][1])
                    },
                    "arrival_time": arrival_time.isoformat(),
                    "departure_time": departure_time.isoformat(),
                    "service_time_minutes": service_time,
                    "status": "pending"
                }
                
                # Add items and value if available
                if dest_items:
                    stop_data["items"] = dest_items
                    stop_data["items_value_usd"] = round(stop_value, 2)
                
                stops.append(stop_data)
            
            # Add return to depot
            current_time += timedelta(minutes=time_per_segment)
            stops.append({
                "stop_number": len(route.waypoints) + 1,
                "location": "Depot (Return)",
                "coordinates": stops[0]["coordinates"],
                "arrival_time": current_time.isoformat(),
                "departure_time": current_time.isoformat(),
                "status": "pending"
            })
            
            # Calculate total time including service time
            total_time_with_service = total_travel_minutes + (len(route.waypoints) * service_time)
            estimated_end = start_datetime + timedelta(minutes=total_time_with_service)
            
            # Calculate total value of items in this route
            all_items = []
            for waypoint in route.waypoints:
                all_items.extend(waypoint.get('items', []))
            total_value_usd = calculate_items_value(all_items)
            
            # Build route summary
            route_info = {
                "truck_id": int(route.truck_id),
                "truck_name": f"Truck {int(route.truck_id) + 1}",
                "date": start_datetime.date().isoformat(),
                "start_time": start_datetime.isoformat(),
                "estimated_end_time": estimated_end.isoformat(),
                "total_distance_km": round(route.distance / 1000, 2),
                "total_duration_minutes": round(total_time_with_service, 2),
                "travel_time_minutes": round(total_travel_minutes, 2),
                "service_time_minutes": len(route.waypoints) * service_time,
                "total_stops": len(route.waypoints),
                "total_value_usd": round(total_value_usd, 2),
                "status": "planned",
                "stops": stops,
                "route_summary": {
                    "origin": "Depot",
                    "destination": "Depot",
                    "waypoints": [
                        {
                            "id": int(wp.get('id', i)) if isinstance(wp.get('id'), (int, float)) else i,
                            "name": wp.get('name', f"Destination {int(wp.get('id', i)) + 1 if isinstance(wp.get('id'), (int, float)) else i + 1}"),
                            "items": wp.get('items', [])
                        }
                        for i, wp in enumerate(route.waypoints)
                    ]
                }
            }
            
            route_data["routes"].append(route_info)
        
        # Add summary statistics
        route_data["summary"] = {
            "total_distance_km": sum(r["total_distance_km"] for r in route_data["routes"]),
            "total_duration_minutes": sum(r["total_duration_minutes"] for r in route_data["routes"]),
            "total_stops": sum(r["total_stops"] for r in route_data["routes"]),
            "total_value_usd": sum(r["total_value_usd"] for r in route_data["routes"]),
            "trucks_in_use": len([r for r in route_data["routes"] if r["total_stops"] > 0])
        }
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"route_plan_{timestamp}.json"
        filepath = DATA_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(route_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Route export saved to {filepath}")
        
        # Return data with file info
        route_data["file_info"] = {
            "filename": filename,
            "filepath": str(filepath),
            "saved_at": datetime.now().isoformat()
        }
        
        return route_data
        
    except Exception as e:
        logger.error(f"Route export error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/list-exports")
async def list_exports():
    """List all saved route export files"""
    try:
        files = []
        for filepath in DATA_DIR.glob("route_plan_*.json"):
            stat = filepath.stat()
            files.append({
                "filename": filepath.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Sort by creation time, newest first
        files.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "total_files": len(files),
            "files": files
        }
    except Exception as e:
        logger.error(f"List exports error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

class IncidentReport(BaseModel):
    truck_id: int
    truck_positions: Optional[Dict[str, Dict]] = None  # Posiciones actuales de todos los camiones

class UpdateDeliveryRequest(BaseModel):
    filename: str
    truck_id: int
    stop_number: int
    status: str = "completed"

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"
    truck_positions: dict = None  # Posiciones actuales del frontend

# Initialize multi-agent system with AgentCore (con memoria)
from agents.agentcore_system import process_message as agentcore_process_message

class ExplainSolutionRequest(BaseModel):
    orchestration: Dict[str, Any]
    metrics: Dict[str, Any]

@app.post("/explain-incident-solution")
async def explain_incident_solution(request: ExplainSolutionRequest):
    """Generate LLM explanation for incident solution"""
    try:
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        orch = request.orchestration
        metrics = request.metrics
        
        # Extraer información relevante
        selected_truck = orch['solution']['selected_truck']
        incident_analysis = orch['solution']['incident_analysis']
        inventory_check = orch['solution']['inventory_check']
        selector_result = orch['steps'][2]['result']
        alternatives = selector_result.get('alternatives', [])
        evaluation_method = selector_result.get('evaluation_method', 'distance')
        
        # Construir información de alternativas
        alternatives_text = ""
        if alternatives:
            for i, alt in enumerate(alternatives[:2], 1):
                time_diff = alt.get('total_time_with_service_minutes', 0) - selected_truck.get('total_time_with_service_minutes', 0)
                alternatives_text += f"\n{i}. {alt['truck_name']}: "
                if alt.get('route_calculated'):
                    alternatives_text += f"{alt['total_distance_km']:.1f} km, {alt['total_time_with_service_minutes']:.0f} min total ({time_diff:.0f} min más lento)"
                else:
                    alternatives_text += f"~{alt['total_time_with_service_minutes']:.0f} min estimados"
        
        prompt = f"""Eres un experto en logística y optimización de rutas. Explica de manera clara y concisa por qué esta es la mejor solución para el incidente.

SITUACIÓN:
- Camión con incidente: {incident_analysis['truck_name']}
- Entregas pendientes: {incident_analysis['pending_deliveries']}
- Valor en riesgo: ${metrics['pendingValue']:.0f} USD

MÉTODO DE SELECCIÓN:
El sistema evaluó TODOS los camiones disponibles calculando la ruta completa (incluyendo sus entregas actuales + las del incidente) y eligió el que minimiza el TIEMPO TOTAL de operación.

SOLUCIÓN PROPUESTA:
- Camión seleccionado: {selected_truck['truck_name']}
- Tiempo total estimado: {selected_truck.get('total_time_with_service_minutes', metrics['additionalTime']):.0f} minutos
- Distancia total: {selected_truck.get('total_distance_km', metrics['additionalDistance']):.1f} km
- Destinos totales: {selected_truck.get('total_destinations', 'N/A')}
- Entregas actuales del camión: {selected_truck.get('pending_deliveries', 0)}

INVENTARIO:
- Items disponibles: {metrics['availableItems']}/{metrics['totalItems']}
- Valor recuperable: ${metrics['recoverableValue']:.0f} USD ({metrics['recoverableValue']/metrics['pendingValue']*100:.0f}%)

ALTERNATIVAS EVALUADAS:{alternatives_text if alternatives_text else "\n(No hay alternativas disponibles)"}

IMPORTANTE: El sistema NO eligió simplemente el camión más cercano al depósito, sino que calculó la ruta completa para cada camión (incluyendo todas sus entregas pendientes + las del incidente) y seleccionó el que completa TODO en el menor tiempo.

Genera una explicación en español de 3-4 párrafos que:
1. Explique que se evaluaron TODOS los camiones calculando rutas completas
2. Justifique por qué este camión específicamente minimiza el tiempo total
3. Compare con las alternativas mostrando cuánto tiempo se ahorraría
4. Mencione los beneficios de aceptar (valor recuperable) vs rechazar (pérdida total)

Usa un tono profesional pero accesible. Enfócate en los números clave y el ahorro de tiempo."""

        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "Eres un experto en logística que explica decisiones de optimización de manera clara y convincente."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        explanation = response.choices[0].message.content.strip()
        
        logger.info(f"Generated explanation for incident solution")
        
        return {
            "status": "success",
            "explanation": explanation
        }
        
    except Exception as e:
        logger.error(f"Explain solution error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/chat")
async def chat_endpoint(chat: ChatMessage):
    """Handle chat messages using OpenAI multi-agent system with memory"""
    try:
        logger.info(f"[Session: {chat.session_id}] User: {chat.message}")
        
        # Si el frontend envía posiciones actuales, actualizar el JSON
        if chat.truck_positions:
            update_route_json_with_positions(chat.truck_positions)
        
        # Process message through AgentCore with memory
        response = agentcore_process_message(chat.message, chat.session_id)
        
        logger.info(f"Agent: {response.get('agent', 'Unknown')}")
        logger.info(f"Response: {response.get('response', 'No response')[:100]}...")
        
        return {
            "status": "success",
            "agent": response.get('agent'),
            "response": response.get('response'),
            "data": response.get('data'),
            "user_message": chat.message,
            "session_id": chat.session_id
        }
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def update_route_json_with_positions(truck_positions: dict):
    """
    Actualiza el JSON de rutas con las posiciones actuales del frontend
    
    Args:
        truck_positions: Dict con formato {truck_id: {lat, lng, currentStop, status, progress}}
    """
    try:
        if not truck_positions:
            logger.info("No truck positions provided, skipping update")
            return
            
        route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
        if not route_files:
            logger.warning("No route files found to update")
            return
        
        latest_route = route_files[0]
        with open(latest_route, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        updated = False
        
        for route in route_data.get('routes', []):
            truck_id = str(route['truck_id'])
            
            if truck_id in truck_positions:
                frontend_data = truck_positions[truck_id]
                current_stop_num = frontend_data.get('currentStop', 0)
                
                logger.info(f"Updating {route['truck_name']}: currentStop={current_stop_num}")
                
                # Actualizar el estado de las paradas según la posición actual
                stops = route.get('stops', [])
                for stop in stops:
                    # Marcar como completadas todas las paradas hasta la actual
                    if stop['stop_number'] <= current_stop_num and stop['stop_number'] > 0:
                        if stop['status'] != 'completed':
                            stop['status'] = 'completed'
                            stop['actual_delivery_time'] = datetime.now().isoformat()
                            updated = True
                            logger.info(f"  ✓ Marked as completed: Stop {stop['stop_number']} - {stop['location']}")
        
        # Guardar cambios
        if updated:
            with open(latest_route, 'w', encoding='utf-8') as f:
                json.dump(route_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Route JSON updated with {len(truck_positions)} truck positions")
        else:
            logger.info(f"No changes needed for route JSON")
        
    except Exception as e:
        logger.error(f"Error updating route JSON: {e}")
        import traceback
        traceback.print_exc()

@app.post("/chat/clear-session")
async def clear_chat_session(session_id: str = "default"):
    """Clear conversation memory for a session"""
    try:
        from agents.agentcore_system import clear_session
        clear_session(session_id)
        logger.info(f"Cleared session: {session_id}")
        return {
            "status": "success",
            "message": f"Session {session_id} cleared",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Clear session error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str = "default"):
    """Get conversation history for a session"""
    try:
        from agents.agentcore_system import get_session_history
        history = get_session_history(session_id)
        return {
            "status": "success",
            "session_id": session_id,
            "message_count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"Get history error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/simulator/start")
async def start_simulator():
    """Start the truck position simulator"""
    try:
        if simulator.running:
            return {
                "status": "already_running",
                "message": "Simulator is already running"
            }
        
        success = simulator.start()
        if success:
            return {
                "status": "success",
                "message": "Simulator started successfully",
                "update_interval_seconds": simulator.update_interval,
                "speed_kmh": simulator.speed_kmh
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to start simulator")
    except Exception as e:
        logger.error(f"Start simulator error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/simulator/stop")
async def stop_simulator():
    """Stop the truck position simulator"""
    try:
        simulator.stop()
        return {
            "status": "success",
            "message": "Simulator stopped"
        }
    except Exception as e:
        logger.error(f"Stop simulator error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/simulator/reset")
async def reset_simulator():
    """Reset simulator with latest route data"""
    try:
        success = simulator.reset()
        if success:
            return {
                "status": "success",
                "message": "Simulator reset successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reset simulator")
    except Exception as e:
        logger.error(f"Reset simulator error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/simulator/status")
async def get_simulator_status():
    """Get simulator status and current positions"""
    try:
        return {
            "status": "success",
            "simulator_running": simulator.running,
            "update_interval_seconds": simulator.update_interval,
            "speed_kmh": simulator.speed_kmh,
            "last_update": simulator.last_update.isoformat() if simulator.last_update else None,
            "truck_count": len(simulator.current_positions),
            "positions": simulator.get_current_positions() if simulator.running else {}
        }
    except Exception as e:
        logger.error(f"Get simulator status error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/trucks/positions")
async def get_truck_positions_endpoint():
    """Get current truck positions (real-time if simulator is running)"""
    try:
        from agents.tools import get_truck_positions
        positions = get_truck_positions()
        return {
            "status": "success",
            "simulator_active": simulator.running,
            "timestamp": datetime.now().isoformat(),
            "truck_count": len(positions),
            "positions": positions
        }
    except Exception as e:
        logger.error(f"Get positions error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

class RedirectRequest(BaseModel):
    target_location: str = "depot"  # "depot" o "custom"
    custom_coords: Optional[List[float]] = None  # [lon, lat] si es custom
    truck_id: Optional[int] = None  # Si se especifica, solo redirige ese camión

@app.post("/redirect-trucks")
async def redirect_trucks(request: RedirectRequest):
    """
    Redirige camiones a una ubicación específica
    
    Ejemplos:
    - Todos al almacén: {"target_location": "depot"}
    - Todos a ubicación custom: {"target_location": "custom", "custom_coords": [-99.15, 19.42]}
    - Un camión específico: {"truck_id": 0, "target_location": "depot"}
    """
    try:
        if not simulator.route_data:
            raise HTTPException(status_code=400, detail="No hay datos de ruta cargados. Inicia el simulador primero.")
        
        # Redirigir un camión específico
        if request.truck_id is not None:
            if request.target_location == "depot":
                result = simulator.redirect_single_truck(
                    truck_id=request.truck_id,
                    target_coords=[-99.1908, 19.4336],
                    target_name="Depósito/Almacén"
                )
            elif request.target_location == "custom" and request.custom_coords:
                result = simulator.redirect_single_truck(
                    truck_id=request.truck_id,
                    target_coords=request.custom_coords,
                    target_name=f"Ubicación personalizada"
                )
            else:
                raise HTTPException(status_code=400, detail="Ubicación objetivo no válida")
        
        # Redirigir todos los camiones
        else:
            result = simulator.redirect_all_trucks(
                target_location=request.target_location,
                custom_coords=request.custom_coords
            )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "Error en la redirección"))
        
        logger.info(f"✓ Redirección exitosa: {result.get('message')}")
        
        return {
            "status": "success",
            **result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redirect trucks error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

class RedirectRouteRequest(BaseModel):
    origin: List[float]
    destination: List[float]

@app.post("/calculate-redirect-route")
async def calculate_redirect_route(request: RedirectRouteRequest):
    """
    Calcula una ruta de redirección con geometría real usando AWS Location Service
    
    Args:
        origin: [lng, lat] posición actual del camión
        destination: [lng, lat] destino de redirección
    
    Returns:
        Geometría de la ruta, distancia y duración
    """
    try:
        if geo_routes_client is None:
            raise HTTPException(status_code=500, detail="AWS geo-routes client not initialized")
        
        logger.info(f"Calculating redirect route from {request.origin} to {request.destination}")
        
        response = geo_routes_client.calculate_routes(
            Origin=request.origin,
            Destination=request.destination,
            TravelMode='Car',
            LegGeometryFormat='Simple'
        )
        
        if not response or 'Routes' not in response or len(response['Routes']) == 0:
            raise HTTPException(status_code=500, detail="No route found")
        
        route = response['Routes'][0]
        
        # Extraer geometría de todos los legs
        geometry = []
        total_distance = 0
        total_duration = 0
        
        for leg in route.get('Legs', []):
            total_distance += leg.get('Distance', 0)
            total_duration += leg.get('DurationSeconds', 0)
            
            # Extraer puntos de geometría
            leg_geometry = leg.get('Geometry', {})
            if 'LineString' in leg_geometry:
                for point in leg_geometry['LineString']:
                    geometry.append(point)
        
        logger.info(f"Route calculated: {len(geometry)} points, {total_distance}m, {total_duration}s")
        
        return {
            "status": "success",
            "geometry": geometry,
            "distance_meters": total_distance,
            "duration_seconds": total_duration,
            "distance_km": round(total_distance / 1000, 2),
            "duration_minutes": round(total_duration / 60, 2)
        }
        
    except Exception as e:
        logger.error(f"Calculate redirect route error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/update-delivery-status")
async def update_delivery_status(update: UpdateDeliveryRequest):
    """Update the delivery status of a specific stop in the route plan JSON"""
    try:
        filepath = DATA_DIR / update.filename
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"File {update.filename} not found")
        
        # Read the current JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        # Find the truck and update the stop status
        truck_found = False
        stop_found = False
        
        for route in route_data.get('routes', []):
            if route['truck_id'] == update.truck_id:
                truck_found = True
                for stop in route.get('stops', []):
                    if stop['stop_number'] == update.stop_number:
                        stop['status'] = update.status
                        stop['actual_delivery_time'] = datetime.now().isoformat()
                        stop_found = True
                        logger.info(f"Updated delivery status: Truck {update.truck_id + 1}, Stop {update.stop_number} -> {update.status}")
                        break
                break
        
        if not truck_found:
            raise HTTPException(status_code=404, detail=f"Truck {update.truck_id} not found in route plan")
        
        if not stop_found:
            raise HTTPException(status_code=404, detail=f"Stop {update.stop_number} not found for truck {update.truck_id}")
        
        # Save the updated JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(route_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Route plan {update.filename} updated successfully")
        
        return {
            "status": "success",
            "message": f"Delivery status updated for Truck {update.truck_id + 1}, Stop {update.stop_number}",
            "filename": update.filename,
            "updated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Update delivery status error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/report-incident")
async def report_incident(report: IncidentReport):
    """Report an incident for a specific truck and orchestrate solution"""
    try:
        truck_num = report.truck_id + 1  # Convert 0-based to 1-based
        logger.info(f"🚨 Incident reported for truck {truck_num}")
        
        # Generate incident report using tools
        from agents.tools import generate_incident_report, get_truck_positions
        
        # Get current positions (from frontend if provided, otherwise from tools)
        if report.truck_positions:
            logger.info(f"📍 Using truck positions from frontend: {len(report.truck_positions)} trucks")
            # Actualizar el JSON con las posiciones del frontend
            update_route_json_with_positions(report.truck_positions)
        
        truck_positions = get_truck_positions()
        location_coords = None
        if report.truck_id in truck_positions:
            location_coords = truck_positions[report.truck_id]['position']
        
        # Generate detailed incident report
        incident_data = generate_incident_report(
            truck_id=report.truck_id,
            incident_type='accident',
            description=f"Incident reported for truck {truck_num}",
            location=location_coords
        )
        
        # Update route JSON to mark truck as having incident
        update_route_json_with_incident(report.truck_id, incident_data)
        
        logger.info(f"✓ Incident report created: {incident_data.get('incident_id', 'N/A')}")
        
        # 🚨 Activar orquestador de incidentes
        logger.info(f"🚨 Activating incident orchestrator...")
        from agents.incident_orchestrator import orchestrate_incident_response
        
        orchestration_result = orchestrate_incident_response(incident_data)
        
        logger.info(f"✓ Orchestration completed: {'SUCCESS' if orchestration_result.get('success') else 'FAILED'}")
        
        return {
            "status": "success",
            "message": f"Incident reported for truck {truck_num}",
            "truck_id": report.truck_id,
            "incident_id": incident_data.get('incident_id'),
            "timestamp": datetime.now().isoformat(),
            "incident_data": incident_data,
            "orchestration": orchestration_result
        }
    except Exception as e:
        logger.error(f"Incident report error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


def update_route_json_with_incident(truck_id: int, incident_data: dict):
    """
    Actualiza el JSON de rutas para marcar un camión con incidente
    """
    try:
        route_files = sorted(DATA_DIR.glob("route_plan_*.json"), reverse=True)
        if not route_files:
            logger.warning("No route files found to update")
            return
        
        latest_route = route_files[0]
        with open(latest_route, 'r', encoding='utf-8') as f:
            route_data = json.load(f)
        
        # Encontrar la ruta del camión y marcarla con incidente
        for route in route_data.get('routes', []):
            if route['truck_id'] == truck_id:
                route['status'] = 'incident'
                route['incident'] = {
                    'incident_id': incident_data.get('incident_id'),
                    'type': incident_data.get('incident_type'),
                    'description': incident_data.get('description'),
                    'timestamp': incident_data.get('timestamp'),
                    'location': incident_data.get('location'),
                    'recovery_time_minutes': incident_data.get('incident_summary', {}).get('recovery_time_minutes', 13)
                }
                logger.info(f"✓ Marked {route['truck_name']} with incident status")
                break
        
        # Guardar cambios
        with open(latest_route, 'w', encoding='utf-8') as f:
            json.dump(route_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Route JSON updated with incident for truck {truck_id}")
        
    except Exception as e:
        logger.error(f"Error updating route JSON with incident: {e}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
