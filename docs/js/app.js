// Main Application Logic
class DashboardApp {
    constructor() {
        this.charts = {};
        this.map = null;
        this.heatLayer = null;
        this.markers = [];
        this.eventSource = null;
        this.isConnected = false;

        this.init();
    }

    async init() {
        console.log('Initializing Dashboard...');

        // Initialize components
        this.initMap();
        this.initCharts();

        // Start data fetching
        await this.fetchAllData();

        // Setup real-time updates
        if (CONFIG.FEATURES.serverSentEvents) {
            this.initSSE();
        }

        // Setup periodic refresh
        if (CONFIG.FEATURES.autoRefresh) {
            this.setupAutoRefresh();
        }

        // Setup event listeners
        this.setupEventListeners();
    }

    // ==================== Data Fetching ====================

    async fetchAPI(endpoint) {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/api${endpoint}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            this.updateConnectionStatus(false);
            return null;
        }
    }

    async fetchAllData() {
        console.log('Fetching all data...');
        await Promise.all([
            this.fetchLiveData(),
            this.fetchNodeStats(),
            this.fetchDecisions(),
            this.fetchNodeLocations(),
            this.fetchTimeSeriesData()
        ]);
        this.updateConnectionStatus(true);
    }

    async fetchLiveData() {
        const data = await this.fetchAPI('/latest?limit=10');
        if (data) this.updateLiveDataFeed(data);
    }

    async fetchNodeStats() {
        const data = await this.fetchAPI('/nodes');
        if (data) this.updateNodeStats(data);
    }

    async fetchDecisions() {
        const data = await this.fetchAPI('/decisions');
        if (data) this.updateDecisions(data);
    }

    async fetchNodeLocations() {
        const data = await this.fetchAPI('/nodes/locations');
        if (data) this.updateMap(data);
    }

    async fetchTimeSeriesData() {
        const hours = document.getElementById('timeRange').value;
        const data = await this.fetchAPI(`/timeseries?hours=${hours}`);
        if (data) this.updateCharts(data);
    }

    // ==================== Server-Sent Events ====================

    initSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        try {
            this.eventSource = new EventSource(`${CONFIG.API_BASE_URL}/api/stream`);

            this.eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('SSE Update:', data);
                this.handleRealtimeUpdate(data);
                this.updateConnectionStatus(true);
            };

            this.eventSource.onerror = (error) => {
                console.error('SSE Error:', error);
                this.updateConnectionStatus(false);
            };
        } catch (error) {
            console.error('Failed to initialize SSE:', error);
        }
    }

    handleRealtimeUpdate(data) {
        // Add to live feed
        this.addToLiveDataFeed(data);

        // Update last update time
        this.updateLastUpdateTime();

        // Optionally refresh other components
        this.fetchNodeStats();
        this.fetchDecisions();
    }

    // ==================== UI Updates ====================

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connectionStatus');

        if (connected) {
            statusElement.textContent = '🟢 Connected';
            statusElement.classList.remove('disconnected');
        } else {
            statusElement.textContent = '🔴 Disconnected';
            statusElement.classList.add('disconnected');
        }
    }

    updateLastUpdateTime() {
        const now = new Date();
        document.getElementById('lastUpdate').textContent = now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
    }

    updateLiveDataFeed(dataArray) {
        const container = document.getElementById('liveDataContainer');

        if (!dataArray || dataArray.length === 0) {
            container.innerHTML = '<p class="loading">No data available</p>';
            return;
        }

        container.innerHTML = '';

        dataArray.forEach(data => {
            container.appendChild(this.createDataItem(data));
        });

        this.updateLastUpdateTime();
    }

    addToLiveDataFeed(data) {
        const container = document.getElementById('liveDataContainer');

        // Remove loading message if present
        const loading = container.querySelector('.loading');
        if (loading) loading.remove();

        // Create new data item
        const dataItem = this.createDataItem(data);

        // Add to top
        container.insertBefore(dataItem, container.firstChild);

        // Keep only latest 10 items
        while (container.children.length > 10) {
            container.removeChild(container.lastChild);
        }
    }

    createDataItem(data) {
        const item = document.createElement('div');
        item.className = 'data-item';

        const timestamp = new Date(data.timestamp).toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        item.innerHTML = `
            <div class="data-item-header">
                <span class="node-id">${data.node_id}</span>
                <span class="timestamp">${timestamp}</span>
            </div>
            <div class="sensor-readings">
                <div class="sensor-value">
                    <span class="sensor-label">Temperature</span>
                    <span class="sensor-number">${this.formatValue(data.temperature, '°C')}</span>
                </div>
                <div class="sensor-value">
                    <span class="sensor-label">Humidity</span>
                    <span class="sensor-number">${this.formatValue(data.relative_humidity, '%')}</span>
                </div>
                <div class="sensor-value">
                    <span class="sensor-label">Soil Moisture</span>
                    <span class="sensor-number">${this.formatValue(data.soil_moisture, '')}</span>
                </div>
                <div class="sensor-value">
                    <span class="sensor-label">Light</span>
                    <span class="sensor-number">${this.formatValue(data.lux, ' lux')}</span>
                </div>
                <div class="sensor-value">
                    <span class="sensor-label">Voltage</span>
                    <span class="sensor-number">${this.formatValue(data.voltage, 'V')}</span>
                </div>
            </div>
        `;

        return item;
    }

    formatValue(value, unit) {
        if (value === null || value === undefined) return 'N/A';
        return `${value.toFixed(1)}${unit}`;
    }

    updateNodeStats(statsArray) {
        const container = document.getElementById('nodeStatsContainer');

        if (!statsArray || statsArray.length === 0) {
            container.innerHTML = '<p class="loading">No nodes found</p>';
            return;
        }

        container.innerHTML = '';

        statsArray.forEach(stat => {
            const card = document.createElement('div');
            card.className = 'node-stat-card';

            const lastSeen = new Date(stat.last_seen).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            card.innerHTML = `
                <div class="node-stat-header">
                    <span class="node-stat-name">${stat.node_id}</span>
                    <span class="node-stat-readings">${stat.reading_count} readings</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-muted);">
                    Last seen: ${lastSeen}
                </div>
                <div class="node-averages">
                    <div class="avg-value">
                        <div class="avg-label">Avg Temp</div>
                        <div class="avg-number">${this.formatValue(stat.avg_temp, '°C')}</div>
                    </div>
                    <div class="avg-value">
                        <div class="avg-label">Avg Humidity</div>
                        <div class="avg-number">${this.formatValue(stat.avg_humidity, '%')}</div>
                    </div>
                    <div class="avg-value">
                        <div class="avg-label">Avg Voltage</div>
                        <div class="avg-number">${this.formatValue(stat.avg_voltage, 'V')}</div>
                    </div>
                </div>
            `;

            container.appendChild(card);
        });
    }

    updateDecisions(decisionsArray) {
        const container = document.getElementById('decisionsContainer');

        if (!decisionsArray || decisionsArray.length === 0) {
            container.innerHTML = '<p class="loading">No decisions available</p>';
            return;
        }

        container.innerHTML = '';

        decisionsArray.forEach(decision => {
            const card = document.createElement('div');
            let cardClass = 'decision-card';

            // Set color based on action
            if (decision.action !== 'none') {
                cardClass += decision.action.includes('warning') || decision.action.includes('battery')
                    ? ' warning'
                    : ' alert';
            }

            card.className = cardClass;

            const timestamp = new Date(decision.timestamp).toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });

            card.innerHTML = `
                <div class="decision-header">
                    <span class="decision-node">${decision.node_id}</span>
                    <span class="decision-confidence">${(decision.confidence * 100).toFixed(0)}%</span>
                </div>
                <div class="decision-text">${decision.decision}</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 8px;">
                    ${timestamp}
                </div>
                <span class="decision-action">Action: ${decision.action.replace('_', ' ')}</span>
            `;

            container.appendChild(card);
        });
    }

    // ==================== Map ====================

    initMap() {
        this.map = L.map('map').setView(CONFIG.MAP.defaultCenter, CONFIG.MAP.defaultZoom);

        L.tileLayer(CONFIG.MAP.tileLayer, {
            attribution: CONFIG.MAP.attribution,
            maxZoom: 19
        }).addTo(this.map);

        console.log('Map initialized');
    }

    updateMap(nodesData) {
        // Clear existing markers
        this.markers.forEach(marker => this.map.removeLayer(marker));
        this.markers = [];

        // Clear existing heat layer
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
        }

        if (!nodesData || nodesData.length === 0) return;

        // Add markers for each node
        const heatData = [];

        nodesData.forEach(node => {
            const marker = L.marker([node.lat, node.lon]).addTo(this.map);

            const popupContent = `
                <strong>${node.name || node.node_id}</strong><br>
                Temp: ${this.formatValue(node.avg_temp, '°C')}<br>
                Humidity: ${this.formatValue(node.avg_humidity, '%')}<br>
                Soil: ${this.formatValue(node.avg_soil_moisture, '')}<br>
                Light: ${this.formatValue(node.avg_lux, ' lux')}<br>
                Voltage: ${this.formatValue(node.avg_voltage, 'V')}
            `;

            marker.bindPopup(popupContent);
            this.markers.push(marker);

            // Add to heat map data
            const metric = document.getElementById('heatmapMetric').value;
            let intensity = 0;

            switch(metric) {
                case 'temperature':
                    intensity = node.avg_temp || 0;
                    break;
                case 'humidity':
                    intensity = node.avg_humidity || 0;
                    break;
                case 'soil_moisture':
                    intensity = node.avg_soil_moisture || 0;
                    break;
                case 'lux':
                    intensity = node.avg_lux || 0;
                    break;
            }

            heatData.push([node.lat, node.lon, intensity / 100]);
        });

        // Add heat layer
        if (CONFIG.FEATURES.heatMap && heatData.length > 0) {
            this.heatLayer = L.heatLayer(heatData, {
                radius: 25,
                blur: 15,
                maxZoom: 17,
            }).addTo(this.map);
        }

        // Fit map to markers
        if (this.markers.length > 0) {
            const group = L.featureGroup(this.markers);
            this.map.fitBounds(group.getBounds().pad(0.1));
        }
    }

    // ==================== Charts ====================

    initCharts() {
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: { color: '#e2e8f0' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                },
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(148, 163, 184, 0.1)' }
                }
            }
        };

        // Temperature & Humidity Chart
        this.charts.tempHumidity = new Chart(
            document.getElementById('tempHumidityChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: chartOptions
            }
        );

        // Soil & Sunlight Chart
        this.charts.soilSun = new Chart(
            document.getElementById('soilSunChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: chartOptions
            }
        );

        // Battery Chart
        this.charts.battery = new Chart(
            document.getElementById('batteryChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: chartOptions
            }
        );

        console.log('Charts initialized');
    }

    updateCharts(timeSeriesData) {
        if (!timeSeriesData || timeSeriesData.length === 0) return;

        // Group data by node
        const nodeData = {};

        timeSeriesData.forEach(point => {
            if (!nodeData[point.node_id]) {
                nodeData[point.node_id] = [];
            }
            nodeData[point.node_id].push(point);
        });

        const labels = timeSeriesData
            .map(d => new Date(d.timestamp).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }))
            .filter((v, i, a) => a.indexOf(v) === i);

        // Update Temperature & Humidity Chart
        const tempHumidityDatasets = [];
        Object.keys(nodeData).forEach((nodeId, index) => {
            const colors = Object.values(CONFIG.CHART_COLORS);
            const color = colors[index % colors.length];

            tempHumidityDatasets.push({
                label: `${nodeId} - Temp`,
                data: nodeData[nodeId].map(d => d.avg_temp),
                borderColor: color,
                backgroundColor: color.replace('1)', '0.1)'),
                tension: 0.4
            });

            tempHumidityDatasets.push({
                label: `${nodeId} - Humidity`,
                data: nodeData[nodeId].map(d => d.avg_humidity),
                borderColor: CONFIG.CHART_COLORS.humidity,
                backgroundColor: CONFIG.CHART_COLORS_ALPHA.humidity,
                tension: 0.4
            });
        });

        this.charts.tempHumidity.data.labels = labels;
        this.charts.tempHumidity.data.datasets = tempHumidityDatasets;
        this.charts.tempHumidity.update();

        // Update Soil & Light Chart
        const soilSunDatasets = [];
        Object.keys(nodeData).forEach(nodeId => {
            soilSunDatasets.push({
                label: `${nodeId} - Soil Moisture`,
                data: nodeData[nodeId].map(d => d.avg_soil_moisture),
                borderColor: CONFIG.CHART_COLORS.soil_moisture,
                backgroundColor: CONFIG.CHART_COLORS_ALPHA.soil_moisture,
                tension: 0.4
            });

            soilSunDatasets.push({
                label: `${nodeId} - Light`,
                data: nodeData[nodeId].map(d => d.avg_lux),
                borderColor: CONFIG.CHART_COLORS.lux,
                backgroundColor: CONFIG.CHART_COLORS_ALPHA.lux,
                tension: 0.4
            });
        });

        this.charts.soilSun.data.labels = labels;
        this.charts.soilSun.data.datasets = soilSunDatasets;
        this.charts.soilSun.update();

        // Update Voltage Chart
        const voltageDatasets = [];
        Object.keys(nodeData).forEach(nodeId => {
            voltageDatasets.push({
                label: `${nodeId} - Voltage`,
                data: nodeData[nodeId].map(d => d.avg_voltage),
                borderColor: CONFIG.CHART_COLORS.voltage,
                backgroundColor: CONFIG.CHART_COLORS_ALPHA.voltage,
                tension: 0.4,
                fill: true
            });
        });

        this.charts.battery.data.labels = labels;
        this.charts.battery.data.datasets = voltageDatasets;
        this.charts.battery.update();
    }

    // ==================== Auto Refresh ====================

    setupAutoRefresh() {
        setInterval(() => this.fetchLiveData(), CONFIG.REFRESH_INTERVALS.liveData);
        setInterval(() => this.fetchNodeStats(), CONFIG.REFRESH_INTERVALS.nodeStats);
        setInterval(() => this.fetchDecisions(), CONFIG.REFRESH_INTERVALS.decisions);
        setInterval(() => this.fetchNodeLocations(), CONFIG.REFRESH_INTERVALS.map);
        setInterval(() => this.fetchTimeSeriesData(), CONFIG.REFRESH_INTERVALS.charts);

        console.log('Auto-refresh enabled');
    }

    // ==================== Event Listeners ====================

    setupEventListeners() {
        // Time range selector
        document.getElementById('timeRange').addEventListener('change', () => {
            this.fetchTimeSeriesData();
        });

        // Heat map metric selector
        document.getElementById('heatmapMetric').addEventListener('change', () => {
            this.fetchNodeLocations();
        });
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardApp = new DashboardApp();
});
