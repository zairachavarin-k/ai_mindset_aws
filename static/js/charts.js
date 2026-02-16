// Chart initialization and management

let completedGaugeChart, moneyPieChart, priorityChart;

function initCharts() {
  // Chart 1: Completed Assignments Gauge (Doughnut)
  const gaugeCtx = document.getElementById('completedGauge').getContext('2d');
  completedGaugeChart = new Chart(gaugeCtx, {
    type: 'doughnut',
    data: {
      labels: ['Completed', 'Remaining'],
      datasets: [{
        data: [0, 100],
        backgroundColor: ['#4caf50', '#333'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '75%',
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      }
    },
    plugins: [{
      id: 'centerText',
      afterDraw: (chart) => {
        const ctx = chart.ctx;
        const width = chart.width;
        const height = chart.height;
        const percentage = chart.data.datasets[0].data[0];
        
        ctx.restore();
        ctx.font = 'bold 32px Arial';
        ctx.fillStyle = '#4caf50';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(percentage + '%', width / 2, height / 2);
        ctx.save();
      }
    }]
  });

  // Chart 2: Money Collection Status (Pie Chart)
  const moneyCtx = document.getElementById('assignmentChart').getContext('2d');
  moneyPieChart = new Chart(moneyCtx, {
    type: 'pie',
    data: {
      labels: ['Collected Money', 'Missing Money'],
      datasets: [{
        data: [0, 100],
        backgroundColor: ['#4caf50', '#ff9800'],
        borderWidth: 2,
        borderColor: '#1a1a1a'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: '#aaa',
            font: { size: 11 },
            padding: 15
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.parsed || 0;
              return label + ': $' + value.toFixed(2);
            }
          }
        }
      }
    }
  });

  // Chart 3: Assignment Priority (Bar)
  const priorityCtx = document.getElementById('priorityChart').getContext('2d');
  priorityChart = new Chart(priorityCtx, {
    type: 'bar',
    data: {
      labels: ['Truck 1', 'Truck 2', 'Truck 3', 'Truck 4', 'Truck 5'],
      datasets: [{
        label: 'Distance (km)',
        data: [0, 0, 0, 0, 0],
        backgroundColor: '#5dade2',
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#aaa' }
        },
        y: {
          beginAtZero: true,
          grid: { color: '#333' },
          ticks: { color: '#aaa' }
        }
      }
    }
  });
}

function updateCharts(optimizedRoutes) {
  const destinationCounts = [0, 0, 0, 0, 0];
  const distances = [0, 0, 0, 0, 0];
  let totalDestinations = 0;
  let completedDestinations = 0;

  optimizedRoutes.forEach(route => {
    destinationCounts[route.truckId] = route.waypoints.length;
    distances[route.truckId] = parseFloat((route.distance / 1000).toFixed(2));
    totalDestinations += route.waypoints.length;
  });

  // Update Money Pie Chart (initially all missing, will update during simulation)
  updateMoneyPieChart(0, 100);

  // Update Priority Chart (using distances)
  priorityChart.data.datasets[0].data = distances;
  priorityChart.update();

  // Update Completed Gauge (initially 0%, will update during simulation)
  updateCompletedGauge(0);
  
  // Update Delivery Status bars
  updateDeliveryStatus(0, 0, totalDestinations);
}

function updateCompletedGauge(percentage) {
  completedGaugeChart.data.datasets[0].data = [percentage, 100 - percentage];
  completedGaugeChart.update();
}

function updateMoneyPieChart(collectedMoney, missingMoney) {
  moneyPieChart.data.datasets[0].data = [collectedMoney, missingMoney];
  moneyPieChart.update();
}

function updateDeliveryStatus(completed, inProgress, pending) {
  const total = completed + inProgress + pending;
  
  if (total === 0) {
    document.querySelector('.status-bar-fill.completed').style.width = '0%';
    document.querySelector('.status-bar-fill.in-progress').style.width = '0%';
    document.querySelector('.status-bar-fill.pending').style.width = '0%';
    document.querySelectorAll('.status-value')[0].textContent = '0';
    document.querySelectorAll('.status-value')[1].textContent = '0';
    document.querySelectorAll('.status-value')[2].textContent = '0';
    return;
  }
  
  const completedPercent = (completed / total) * 100;
  const inProgressPercent = (inProgress / total) * 100;
  const pendingPercent = (pending / total) * 100;
  
  document.querySelector('.status-bar-fill.completed').style.width = completedPercent + '%';
  document.querySelector('.status-bar-fill.in-progress').style.width = inProgressPercent + '%';
  document.querySelector('.status-bar-fill.pending').style.width = pendingPercent + '%';
  
  document.querySelectorAll('.status-value')[0].textContent = completed;
  document.querySelectorAll('.status-value')[1].textContent = inProgress;
  document.querySelectorAll('.status-value')[2].textContent = pending;
}

