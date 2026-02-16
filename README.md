# Route Optimizer Dashboard

A real-time route optimization system for delivery trucks using AWS Location Services, ACO (Ant Colony Optimization), and interactive visualization.

## Features

- 🚚 Multi-truck route optimization using ACO + AWS
- 🗺️ Interactive map with real-time truck tracking
- 📊 Live KPI dashboard with charts and metrics
- 💰 Monetary value tracking for deliveries
- 🎯 Individual truck route filtering
- 💬 Chat interface for assistance
- 📱 Responsive dark-themed UI

## Prerequisites

- Python 3.8+
- AWS Account with Location Services enabled
- AWS credentials configured

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd hackathon_aws
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

Create or update `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

### 4. Configure AWS Location API Key

Copy the example config file:

```bash
cp static/js/config.local.example.js static/js/config.local.js
```

Edit `static/js/config.local.js` and add your AWS Location Service API key:

```javascript
window.AWS_LOCATION_API_KEY = "your_actual_api_key_here";
```

**Note:** Never commit `config.local.js` to version control!

### 5. Run the Backend

```bash
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run the Frontend

Open `index.html` in your browser or serve it with:

```bash
python3 -m http.server 8080
```

Then visit `http://localhost:8080`

## Usage

1. Click **"Optimize Routes"** to calculate optimal delivery routes
2. Click **"▶ Start Sim"** to begin the simulation
3. Watch trucks deliver items in real-time
4. Use the **"View Truck"** selector to focus on individual trucks
5. Click the **💬 button** to open the chat assistant

## Project Structure

```
hackathon_aws/
├── main.py                 # FastAPI backend
├── requirements.txt        # Python dependencies
├── index.html             # Main frontend page
├── static/
│   ├── css/
│   │   └── styles.css     # Styling
│   └── js/
│       ├── config.js      # Configuration (safe for GitHub)
│       ├── config.local.js # Local config (gitignored)
│       ├── map.js         # Map functionality
│       ├── charts.js      # Chart management
│       ├── cards.js       # KPI cards
│       ├── simulation.js  # Truck simulation
│       ├── optimizer.js   # Route optimization
│       ├── export.js      # Data export
│       └── chat.js        # Chat interface
├── mtsp/
│   └── index.py           # MTSP solver
├── inventary/
│   └── 3_inventario_almacen.csv  # Inventory data
└── data/                  # Generated route plans (gitignored)
```

## API Endpoints

- `GET /` - Health check
- `POST /optimize-waypoints` - Optimize waypoint order
- `POST /calculate-route-matrix` - Calculate route matrix
- `POST /calculate-route` - Calculate single route with geometry
- `POST /solve-mtsp` - Solve multi-truck assignment
- `POST /export-routes` - Export route plans to JSON
- `GET /list-exports` - List saved route plans
- `POST /update-delivery-status` - Update delivery status
- `POST /report-incident` - Report truck incident
- `POST /chat` - Chat message endpoint

## Technologies

- **Backend:** FastAPI, Python, Boto3 (AWS SDK)
- **Frontend:** Vanilla JavaScript, MapLibre GL JS, Chart.js
- **Optimization:** PuLP (MILP solver), Custom ACO implementation
- **AWS Services:** Location Service (Routes, Geocoding)

## Security Notes

- Never commit API keys or AWS credentials
- Use environment variables or local config files
- Keep `.gitignore` updated
- Rotate keys regularly

## License

MIT License

## Contributing

Pull requests are welcome! Please ensure you don't commit sensitive credentials.
