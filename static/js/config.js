// Configuration and constants

// IMPORTANT: Before deploying, set your API key in config.local.js
// Copy config.local.example.js to config.local.js and add your key
var CONFIG = {
  apiKey: "v1.public.eyJqdGkiOiI4MWJkNzI1Ni04ZDYyLTQ1MzQtOTRhOS04NDA0OWNlMGFmOGIifUb3xUrPxp_yMl_ffrQkLNyj2zcg29N06kkds_aTmiSHlqpVkS-ZmYGiK-Eo5P1VrFf8_o48uSC_5yO0-51LEnvye94J79FTYvruBHEQKhM77-YxfDXngUms5AbYQU_Ok8-qu_j_6cd4mbUD66TM92tjsob98WKnACm1XxW03ipXspQvJld4rHo83QD1u6bUJVODKE0MHPrwYRbxXbnyjS-Wb359ZGsQMIpRiIXzcKsuApJn6_sYu4_tkcfzU1xxB1-QvQ7NL3mIB3t8dULQvm1mljGMFklNtaC1yNF_Vm2RXlty-BGa_RGHSEUfIfIn0NLwi9ZQSrYHYpYSu1HaxfU.ZWU0ZWIzMTktMWRhNi00Mzg0LTllMzYtNzlmMDU3MjRmYTkx",
  region: "us-east-1",
  style: "Monochrome",
  colorScheme: "Dark",
  apiUrl: window.API_URL || "http://localhost:8000"
};

// Truck depot: Located in Polanco, CDMX
// format: [longitude, latitude]
var depot = [-99.1908, 19.4336];

// 14 destinations across Mexico City (CDMX) and Metropolitan Area
// Each destination includes: [longitude, latitude, location name, items to deliver]
var destinationsData = [
  { coords: [-99.1332, 19.4326], name: "Centro Histórico", items: ["Laptop Gaming X1 Ultra", "Monitor Médico 4K", "Tablet Smart Yellow"] },
  { coords: [-99.1696, 19.4141], name: "Roma Norte", items: ["Vacunas COVID (Lote A)", "Mesa Metal Indianred", "Sofá Madera Lightgray"] },
  { coords: [-99.2736, 19.3629], name: "Santa Fe", items: ["Motor Eléctrico Industrial", "Hub Air Lightslategray", "Sensor Smart Gold"] },
  { coords: [-99.1774, 19.3601], name: "Coyoacán Centro", items: ["Toner Bond Limegreen", "Carpetas Pack Navy", "Papel Bond Darkblue"] },
  { coords: [-99.1866, 19.3894], name: "Nápoles / WTC", items: ["Monitor Médico 4K", "Vacunas COVID (Lote A)", "Cámara Smart Mediumaquamarine"] },
  { coords: [-99.2045, 19.4034], name: "Lomas de Chapultepec", items: ["Mesa Metal Purple", "Silla Metal Darkolivegreen", "Lámpara Madera Chocolate"] },
  { coords: [-99.1245, 19.4000], name: "Iztacalco", items: ["Filtro V8 Mediumblue", "Bujía Cerámico Darkorchid", "Aceite Cerámico Darkslategray"] },
  { coords: [-99.0745, 19.4361], name: "Near AICM Airport", items: ["Drone Pro Bisque", "Tablet Air Darkblue", "Reloj Mini Lightsteelblue"] },
  { coords: [-99.2358, 19.5042], name: "Satélite / Naucalpan", items: ["Mesa Eco Peru", "Estante Confort Mediumseagreen", "Lámpara Eco Bisque"] },
  { coords: [-99.1500, 19.4500], name: "Tlatelolco", items: ["Toner Ejecutivo Darkslategray", "Bolígrafos Ejecutivo Slateblue", "Papel Ejecutivo Pink"] },
  { coords: [-99.1812, 19.4225], name: "Condesa", items: ["Sofá Madera Springgreen", "Mesa Madera Chocolate", "Silla Metal Darkolivegreen"] },
  { coords: [-99.1122, 19.3555], name: "Iztapalapa Norte", items: ["Batería V8 Chocolate", "Frenos Hidráulico Olivedrab", "Filtro Cerámico Skyblue"] },
  { coords: [-99.2201, 19.3245], name: "San Ángel / Altavista", items: ["Cámara Smart Mediumaquamarine", "Sensor Smart Darkcyan", "Hub Air Lightslategray"] },
  { coords: [-99.1415, 19.4712], name: "Lindavista", items: ["Motor Eléctrico Industrial", "Laptop Gaming X1 Ultra", "Drone Pro Bisque"] }
];

// Extract just coordinates for backward compatibility
var destinations = destinationsData.map(d => d.coords);

// Colors for each truck
var truckColors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'];

// Inventory prices (from CSV)
var inventoryPrices = {
  "Vacunas COVID (Lote A)": 5000,
  "Laptop Gaming X1 Ultra": 2500,
  "Motor Eléctrico Industrial": 3000,
  "Monitor Médico 4K": 1200,
  "Cámara Smart Mediumaquamarine": 1457,
  "Silla Metal Darkolivegreen": 226,
  "Mesa Metal Indianred": 322,
  "Mesa Metal Purple": 340,
  "Toner Bond Limegreen": 89,
  "Carpetas Pack Navy": 66,
  "Papel Bond Darkblue": 70,
  "Filtro V8 Mediumblue": 227,
  "Bujía Cerámico Darkorchid": 61,
  "Aceite Cerámico Darkslategray": 256,
  "Hub Air Lightslategray": 774,
  "Tablet Smart Yellow": 532,
  "Drone Pro Bisque": 1363,
  "Tablet Air Darkblue": 370,
  "Reloj Mini Lightsteelblue": 959,
  "Mesa Eco Peru": 321,
  "Estante Confort Mediumseagreen": 65,
  "Lámpara Eco Bisque": 387,
  "Lámpara Madera Chocolate": 156,
  "Toner Ejecutivo Darkslategray": 68,
  "Bolígrafos Ejecutivo Slateblue": 49,
  "Papel Ejecutivo Pink": 72,
  "Sofá Madera Springgreen": 219,
  "Mesa Madera Chocolate": 123,
  "Sofá Madera Lightgray": 72,
  "Batería V8 Chocolate": 272,
  "Frenos Hidráulico Olivedrab": 109,
  "Filtro Cerámico Skyblue": 33,
  "Sensor Smart Darkcyan": 168,
  "Sensor Smart Gold": 413
};

function calculateItemsValue(items) {
  let total = 0;
  items.forEach(item => {
    if (inventoryPrices[item]) {
      total += inventoryPrices[item];
    }
  });
  return total;
}

// Debug: Verify variables are loaded
console.log('Config loaded:', {
  CONFIG: typeof CONFIG,
  depot: typeof depot,
  destinationsData: typeof destinationsData,
  destinations: typeof destinations,
  truckColors: typeof truckColors,
  inventoryPrices: typeof inventoryPrices
});
