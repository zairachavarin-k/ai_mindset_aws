import numpy as np
from typing import List, Dict, Tuple
import json
import random


def haversine_distance(coord1, coord2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in km
    lat1, lon1 = np.radians(coord1[1]), np.radians(coord1[0])
    lat2, lon2 = np.radians(coord2[1]), np.radians(coord2[0])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


class MTSPAntColony:
    def __init__(self, num_trucks, distance_matrix, depot_index=0):
        self.num_trucks = num_trucks
        self.distance_matrix = np.array(distance_matrix)
        self.depot_index = depot_index
        self.num_locations = len(distance_matrix)
        self.num_destinations = self.num_locations - 1
        
        # ACO parameters
        self.num_ants = 100
        self.num_iterations = 100
        self.alpha = 1.0  # Pheromone importance
        self.beta = 3.0   # Distance importance
        self.evaporation_rate = 0.1
        self.pheromone_deposit = 100.0
        self.initial_pheromone = 1.0
        
        # Initialize pheromone matrix
        self.pheromones = np.ones((self.num_locations, self.num_locations)) * self.initial_pheromone
        
        # Heuristic information (inverse of distance)
        self.heuristic = np.zeros_like(self.distance_matrix)
        for i in range(self.num_locations):
            for j in range(self.num_locations):
                if i != j and self.distance_matrix[i][j] > 0:
                    self.heuristic[i][j] = 1.0 / self.distance_matrix[i][j]
    
    def construct_solution(self):
        """
        Construct a solution using ant colony approach
        Each ant builds routes for all trucks
        """
        # Track unvisited destinations
        unvisited = set(range(1, self.num_locations))
        routes = [[] for _ in range(self.num_trucks)]
        current_positions = [self.depot_index] * self.num_trucks
        
        # Distribute destinations among trucks
        while unvisited:
            for truck_id in range(self.num_trucks):
                if not unvisited:
                    break
                
                current = current_positions[truck_id]
                
                # Calculate probabilities for next destination
                probabilities = []
                destinations = list(unvisited)
                
                for dest in destinations:
                    pheromone = self.pheromones[current][dest] ** self.alpha
                    heuristic = self.heuristic[current][dest] ** self.beta
                    probabilities.append(pheromone * heuristic)
                
                # Normalize probabilities
                total = sum(probabilities)
                if total > 0:
                    probabilities = [p / total for p in probabilities]
                else:
                    probabilities = [1.0 / len(destinations)] * len(destinations)
                
                # Select next destination
                next_dest = np.random.choice(destinations, p=probabilities)
                
                routes[truck_id].append(next_dest)
                unvisited.remove(next_dest)
                current_positions[truck_id] = next_dest
        
        # Convert to full routes (depot -> destinations -> depot)
        full_routes = []
        for route in routes:
            if route:
                full_routes.append([self.depot_index] + route + [self.depot_index])
            else:
                full_routes.append([self.depot_index, self.depot_index])
        
        return full_routes
    
    def calculate_route_distance(self, route):
        """Calculate total distance for a single route"""
        distance = 0
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i + 1]]
        return distance
    
    def calculate_total_distance(self, routes):
        """Calculate total distance for all routes"""
        return sum(self.calculate_route_distance(route) for route in routes)
    
    def update_pheromones(self, all_routes, all_distances):
        """Update pheromone levels based on ant solutions"""
        # Evaporation
        self.pheromones *= (1 - self.evaporation_rate)
        
        # Add new pheromones
        for routes, total_distance in zip(all_routes, all_distances):
            if total_distance > 0:
                deposit = self.pheromone_deposit / total_distance
                
                for route in routes:
                    for i in range(len(route) - 1):
                        self.pheromones[route[i]][route[i + 1]] += deposit
                        self.pheromones[route[i + 1]][route[i]] += deposit  # Symmetric
    
    def local_search_2opt(self, route):
        """Apply 2-opt local search to improve a single route"""
        if len(route) <= 3:  # Too short for 2-opt
            return route
        
        improved = True
        best_route = route[:]
        best_distance = self.calculate_route_distance(best_route)
        
        while improved:
            improved = False
            for i in range(1, len(best_route) - 2):
                for j in range(i + 1, len(best_route) - 1):
                    # Try reversing segment [i:j+1]
                    new_route = best_route[:i] + best_route[i:j+1][::-1] + best_route[j+1:]
                    new_distance = self.calculate_route_distance(new_route)
                    
                    if new_distance < best_distance:
                        best_route = new_route
                        best_distance = new_distance
                        improved = True
                        break
                if improved:
                    break
        
        return best_route
    
    def optimize(self):
        """Run the ant colony optimization algorithm"""
        best_routes = None
        best_distance = float('inf')
        distance_history = []
        
        for iteration in range(self.num_iterations):
            # Construct solutions for all ants
            all_routes = []
            all_distances = []
            
            for ant in range(self.num_ants):
                routes = self.construct_solution()
                
                # Apply local search to each route
                routes = [self.local_search_2opt(route) for route in routes]
                
                total_distance = self.calculate_total_distance(routes)
                
                all_routes.append(routes)
                all_distances.append(total_distance)
                
                # Update best solution
                if total_distance < best_distance:
                    best_distance = total_distance
                    best_routes = routes
            
            # Update pheromones
            self.update_pheromones(all_routes, all_distances)
            
            distance_history.append(best_distance)
            
            # Print progress
            if (iteration + 1) % 20 == 0:
                print(f"Iteration {iteration + 1}/{self.num_iterations}: Best distance = {best_distance:.2f} km")
        
        return best_routes, best_distance, distance_history


def solve_mtsp_aco(num_trucks: int, distance_matrix: List[List[float]], 
                   depot_index: int = 0) -> Dict:
    """
    Solve mTSP using Ant Colony Optimization
    
    Args:
        num_trucks: Number of trucks/salesmen
        distance_matrix: NxN distance matrix
        depot_index: Index of depot (default: 0)
    
    Returns:
        Dictionary with routes, distances, and optimization info
    """
    aco = MTSPAntColony(num_trucks, distance_matrix, depot_index)
    best_routes, best_distance, history = aco.optimize()
    
    # Calculate individual truck distances
    truck_distances = [aco.calculate_route_distance(route) for route in best_routes]
    
    # Convert numpy types to Python native types for JSON serialization
    routes_native = [[int(x) for x in route] for route in best_routes]
    distances_native = [float(d) for d in truck_distances]
    history_native = [float(h) for h in history]
    
    return {
        'status': 'Optimal',
        'routes': routes_native,
        'total_distance': float(best_distance),
        'truck_distances': distances_native,
        'num_trucks_used': int(sum(1 for r in best_routes if len(r) > 2)),
        'optimization_history': history_native,
        'algorithm': 'Ant Colony Optimization'
    }


def solve_mtsp_from_coordinates(num_trucks: int, depot: List[float], 
                                destinations: List[List[float]]) -> Dict:
    """
    Solve mTSP given coordinates using Ant Colony Optimization
    
    Args:
        num_trucks: Number of trucks
        depot: [longitude, latitude] of depot
        destinations: List of [longitude, latitude] for each destination
    
    Returns:
        Solution with routes and distances
    """
    # Build distance matrix
    all_locations = [depot] + destinations
    n = len(all_locations)
    distance_matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i != j:
                distance_matrix[i][j] = haversine_distance(all_locations[i], all_locations[j])
    
    # Solve using ACO
    result = solve_mtsp_aco(num_trucks, distance_matrix, depot_index=0)
    
    # Add coordinates to result
    result['depot'] = depot
    result['destinations'] = destinations
    result['all_locations'] = all_locations
    
    return result


if __name__ == "__main__":
    # Example usage
    print("Solving mTSP with Ant Colony Optimization...")
    print("="*50)
    
    example_depot = [-99.1908, 19.4336]
    example_destinations = [
        [-99.1332, 19.4326],  # 1
        [-99.1696, 19.4141],  # 2
        [-99.2736, 19.3629],  # 3
        [-99.1774, 19.3601],  # 4
        [-99.1866, 19.3894],  # 5
        [-99.2045, 19.4034],  # 6
        [-99.1245, 19.4000],  # 7
        [-99.0745, 19.4361],  # 8
    ]
    
    result = solve_mtsp_from_coordinates(3, example_depot, example_destinations)
    
    print("\n" + "="*50)
    print("SOLUTION:")
    print("="*50)
    print(f"Algorithm: {result['algorithm']}")
    print(f"Status: {result['status']}")
    print(f"Total Distance: {result['total_distance']:.2f} km")
    print(f"Trucks Used: {result['num_trucks_used']}")
    print("\nRoutes:")
    for i, (route, dist) in enumerate(zip(result['routes'], result['truck_distances'])):
        if len(route) > 2:
            dest_names = ' → '.join([f"D{x}" if x > 0 else "Depot" for x in route])
            print(f"  Truck {i+1}: {dest_names}")
            print(f"           Distance: {dist:.2f} km")
