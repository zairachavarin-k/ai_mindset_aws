from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from typing import List, Dict, Optional
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
        if geo_routes_client is None:
            raise HTTPException(status_code=500, detail="AWS geo-routes client not initialized. Check credentials.")
        
        logger.info(f"Optimizing route with {len(request.waypoints)} waypoints")
        logger.info(f"Origin: {request.origin}, Destination: {request.destination}")
        
        response = geo_routes_client.optimize_waypoints(
            Origin=request.origin,
            Destination=request.destination,
            Waypoints=[{"Position": wp} for wp in request.waypoints],
            TravelMode='Car',
            OptimizeSequencingFor='FastestRoute'  # Changed from OptimizeFor
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

class UpdateDeliveryRequest(BaseModel):
    filename: str
    truck_id: int
    stop_number: int
    status: str = "completed"

class ChatMessage(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(chat: ChatMessage):
    """Handle chat messages from the frontend"""
    try:
        logger.info(f"User: {chat.message}")
        print(f"User: {chat.message}")
        
        return {
            "status": "success",
            "message": "Message received",
            "user_message": chat.message
        }
    except Exception as e:
        logger.error(f"Chat error: {type(e).__name__}: {e}")
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
    """Report an incident for a specific truck"""
    try:
        truck_num = report.truck_id + 1  # Convert 0-based to 1-based
        logger.info(f"Incident in truck {truck_num}")
        
        return {
            "status": "success",
            "message": f"Incident in truck {truck_num}",
            "truck_id": report.truck_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Incident report error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
