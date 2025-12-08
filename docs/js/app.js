// Main Application Logic
class DashboardApp {
    constructor() {
        this.charts = {};
        this.map = null;
        this.heatLayer = null;
        this.markers = [];
        this.eventSource = null;
        this.isConnected = false;
        this.customTimeRange = { start: null, end: null };
        this.isCustomRange = false;
        this.lastLiveDataTimestamp = null;

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
        if (data && data.length > 0) {
            if (this.lastLiveDataTimestamp === null || data[0].timestamp !== this.lastLiveDataTimestamp) {
                this.lastLiveDataTimestamp = data[0].timestamp;
                this.updateLiveDataFeed(data);
            }
        } else if (data) { // data is an empty array
            this.updateLiveDataFeed(data);
        }
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
        let endpoint;

        if (this.isCustomRange && this.customTimeRange.start && this.customTimeRange.end) {
            // Use custom range - format as local datetime string for backend
            const start = this.customTimeRange.start + ':00'; // Add seconds
            const end = this.customTimeRange.end + ':00';
            endpoint = `/timeseries?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
        } else {
            // Use preset range
            const hours = document.getElementById('timeRange').value;
            if (hours === 'custom') return; // Don't fetch if custom is selected but not applied
            endpoint = `/timeseries?hours=${hours}`;
        }

        const data = await this.fetchAPI(endpoint);
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
                try {
                    const data = JSON.parse(event.data);
                    console.log('SSE Update:', data);

                    // Refresh charts when new data arrives
                    this.fetchTimeSeriesData();

                    this.updateConnectionStatus(true);
                } catch (e) {
                    console.log('SSE keepalive');
                }
            };

            this.eventSource.onerror = () => {
                console.warn('SSE connection error, will retry...');
                this.updateConnectionStatus(false);
            };

            console.log('SSE initialized');
        } catch (error) {
            console.error('Failed to initialize SSE:', error);
        }
    }

    // ==================== UI Updates ====================

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusEl = document.getElementById('connectionStatus');
        const lastUpdateEl = document.getElementById('lastUpdate');

        if (connected) {
            statusEl.classList.remove('disconnected');
            statusEl.innerHTML = '<span class="pulse"></span> Connected';
            statusEl.style.color = 'var(--success-color)';
            lastUpdateEl.textContent = new Date().toLocaleTimeString(undefined, {
                hour: 'numeric',
                minute: '2-digit'
            });
        } else {
            statusEl.classList.add('disconnected');
            statusEl.innerHTML = '<span class="pulse"></span> Disconnected';
            statusEl.style.color = 'var(--danger-color)';
        }
    }

    updateLiveDataFeed(dataArray) {
        const container = document.getElementById('liveDataContainer');

        if (!dataArray || dataArray.length === 0) {
            container.innerHTML = '<p class="loading">No data available</p>';
            return;
        }

        container.innerHTML = '';

        dataArray.slice(0, 10).forEach(data => {
            container.appendChild(this.createLiveDataItem(data));
        });
    }

    createLiveDataItem(data) {
        const item = document.createElement('div');
        item.className = 'live-data-item';

        const time = new Date(data.timestamp).toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit'
        });

        item.innerHTML = `
            <div class="live-data-header">
                <span class="node-badge">${data.node_id}</span>
                <span class="timestamp">${time}</span>
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
                hour: 'numeric',
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

            card.innerHTML = `
                <div class="decision-header">
                    <span class="decision-node">${decision.node_id}</span>
                    <span class="decision-confidence">${(decision.confidence * 100).toFixed(0)}% confident</span>
                </div>
                <div class="decision-text">${decision.decision}</div>
                ${decision.action !== 'none' ? `<div class="decision-action">Action: ${decision.action.replace(/_/g, ' ')}</div>` : ''}
            `;

            container.appendChild(card);
        });
    }

    // ==================== Map Functions ====================

    initMap() {
        this.map = L.map('map').setView(CONFIG.MAP.defaultCenter, CONFIG.MAP.defaultZoom);

        L.tileLayer(CONFIG.MAP.tileLayer, {
            attribution: CONFIG.MAP.attribution,
            maxZoom: 19
        }).addTo(this.map);

        console.log('Map initialized');
    }

    updateMap(locations) {
        if (!locations || locations.length === 0) return;

        // Clear existing markers
        this.markers.forEach(marker => marker.remove());
        this.markers = [];

        // Clear existing heat layer
        if (this.heatLayer) {
            this.map.removeLayer(this.heatLayer);
        }

        const heatMetric = document.getElementById('heatmapMetric').value;
        const heatPoints = [];

        locations.forEach(location => {
            if (!location.lat || !location.lon) return;

            // Create marker
            const marker = L.marker([location.lat, location.lon]).addTo(this.map);

            const popupContent = `
                <b>${location.name || location.node_id}</b><br>
                Temp: ${this.formatValue(location.avg_temp, '°C')}<br>
                Humidity: ${this.formatValue(location.avg_humidity, '%')}<br>
                Soil: ${this.formatValue(location.avg_soil_moisture, '')}<br>
                Light: ${this.formatValue(location.avg_lux, ' lux')}<br>
                Voltage: ${this.formatValue(location.avg_voltage, 'V')}
            `;

            marker.bindPopup(popupContent);
            this.markers.push(marker);

            // Add to heat map data
            const metricValue = location[`avg_${heatMetric}`];
            if (metricValue !== null && metricValue !== undefined) {
                heatPoints.push([location.lat, location.lon, metricValue]);
            }
        });

        // Add heat layer if enabled
        if (CONFIG.FEATURES.heatMap && heatPoints.length > 0) {
            this.heatLayer = L.heatLayer(heatPoints, {
                radius: 25,
                blur: 35,
                maxZoom: 17,
            }).addTo(this.map);
        }
    }

    // ==================== Chart Functions ====================

    initCharts() {
        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    labels: { color: '#e2e8f0' }
                },
                tooltip: {
                    backgroundColor: 'rgba(30, 41, 59, 0.9)',
                    titleColor: '#e2e8f0',
                    bodyColor: '#e2e8f0',
                    borderColor: '#475569',
                    borderWidth: 1
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

        // Soil Moisture Chart
        this.charts.soilMoisture = new Chart(
            document.getElementById('soilMoistureChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            min: 0,
                            max: 60,
                            title: {
                                display: true,
                                text: 'Moisture',
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            }
        );

        // Temperature Chart
        this.charts.temperature = new Chart(
            document.getElementById('temperatureChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            title: {
                                display: true,
                                text: 'Temperature (°C)',
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            }
        );

        // Humidity Chart
        this.charts.humidity = new Chart(
            document.getElementById('humidityChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            min: 0,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Humidity (%)',
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            }
        );

        // Lux Chart
        this.charts.lux = new Chart(
            document.getElementById('luxChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            min: 0,
                            title: {
                                display: true,
                                text: 'Light (lux)',
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            }
        );

        // Voltage Chart
        this.charts.voltage = new Chart(
            document.getElementById('voltageChart'),
            {
                type: 'line',
                data: { labels: [], datasets: [] },
                options: {
                    ...chartOptions,
                    scales: {
                        ...chartOptions.scales,
                        y: {
                            ...chartOptions.scales.y,
                            min: 3.0,
                            max: 4.2,
                            title: {
                                display: true,
                                text: 'Voltage (V)',
                                color: '#94a3b8'
                            }
                        }
                    }
                }
            }
        );

        console.log('Charts initialized');
    }

    updateCharts(timeSeriesData) {
        if (!timeSeriesData || timeSeriesData.length === 0) {
            console.warn('No time series data available');
            return;
        }

        // Group data by node
        const nodeData = {};

        timeSeriesData.forEach(point => {
            if (!nodeData[point.node_id]) {
                nodeData[point.node_id] = [];
            }
            nodeData[point.node_id].push(point);
        });

        // Extract unique timestamps for labels
        const labels = [...new Set(timeSeriesData.map(d => {
            const date = new Date(d.timestamp);
            return date.toLocaleString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
            });
        }))];

        // Generate a color for each node
        const nodeColors = {};
        const colorPalette = [
            'rgba(59, 130, 246, 1)',  // Blue
            'rgba(239, 68, 68, 1)',   // Red
            'rgba(16, 185, 129, 1)',  // Green
            'rgba(245, 158, 11, 1)',  // Orange
            'rgba(124, 58, 237, 1)'   // Purple
        ];

        Object.keys(nodeData).forEach((nodeId, index) => {
            nodeColors[nodeId] = colorPalette[index % colorPalette.length];
        });

        // Update Soil Moisture Chart
        const soilDatasets = Object.keys(nodeData).map(nodeId => ({
            label: nodeId,
            data: nodeData[nodeId].map(d => d.avg_soil_moisture),
            borderColor: nodeColors[nodeId],
            backgroundColor: nodeColors[nodeId].replace('1)', '0.1)'),
            tension: 0.4,
            fill: true
        }));
        this.charts.soilMoisture.data.labels = labels;
        this.charts.soilMoisture.data.datasets = soilDatasets;
        this.charts.soilMoisture.update('none'); // 'none' for no animation on update

        // Update Temperature Chart
        const tempDatasets = Object.keys(nodeData).map(nodeId => ({
            label: nodeId,
            data: nodeData[nodeId].map(d => d.avg_temp),
            borderColor: nodeColors[nodeId],
            backgroundColor: nodeColors[nodeId].replace('1)', '0.1)'),
            tension: 0.4,
            fill: true
        }));
        this.charts.temperature.data.labels = labels;
        this.charts.temperature.data.datasets = tempDatasets;
        this.charts.temperature.update('none');

        // Update Humidity Chart
        const humidityDatasets = Object.keys(nodeData).map(nodeId => ({
            label: nodeId,
            data: nodeData[nodeId].map(d => d.avg_humidity),
            borderColor: nodeColors[nodeId],
            backgroundColor: nodeColors[nodeId].replace('1)', '0.1)'),
            tension: 0.4,
            fill: true
        }));
        this.charts.humidity.data.labels = labels;
        this.charts.humidity.data.datasets = humidityDatasets;
        this.charts.humidity.update('none');

        // Update Lux Chart
        const luxDatasets = Object.keys(nodeData).map(nodeId => ({
            label: nodeId,
            data: nodeData[nodeId].map(d => d.avg_lux),
            borderColor: nodeColors[nodeId],
            backgroundColor: nodeColors[nodeId].replace('1)', '0.1)'),
            tension: 0.4,
            fill: true
        }));
        this.charts.lux.data.labels = labels;
        this.charts.lux.data.datasets = luxDatasets;
        this.charts.lux.update('none');

        // Update Voltage Chart
        const voltageDatasets = Object.keys(nodeData).map(nodeId => ({
            label: nodeId,
            data: nodeData[nodeId].map(d => d.avg_voltage),
            borderColor: nodeColors[nodeId],
            backgroundColor: nodeColors[nodeId].replace('1)', '0.1)'),
            tension: 0.4,
            fill: true
        }));
        this.charts.voltage.data.labels = labels;
        this.charts.voltage.data.datasets = voltageDatasets;
        this.charts.voltage.update('none');

        console.log('Charts updated with', timeSeriesData.length, 'data points');
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
        document.getElementById('timeRange').addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                document.getElementById('customRangeControls').style.display = 'flex';
                this.isCustomRange = true;
            } else {
                document.getElementById('customRangeControls').style.display = 'none';
                this.isCustomRange = false;
                this.fetchTimeSeriesData();
            }
        });

        // Apply custom range
        document.getElementById('applyCustomRange').addEventListener('click', () => {
            const start = document.getElementById('startTime').value;
            const end = document.getElementById('endTime').value;

            if (!start || !end) {
                alert('Please select both start and end times');
                return;
            }

            if (new Date(start) >= new Date(end)) {
                alert('Start time must be before end time');
                return;
            }

            this.customTimeRange = { start, end };
            this.isCustomRange = true;
            this.fetchTimeSeriesData();
        });

        // CSV download button
        document.getElementById('downloadCsvBtn').addEventListener('click', () => {
            this.downloadCSV();
        });

        // Heat map metric selector
        document.getElementById('heatmapMetric').addEventListener('change', () => {
            this.fetchNodeLocations();
        });

        console.log('Event listeners setup complete');
    }

    // ==================== CSV Download ====================

    async downloadCSV() {
        let url = `${CONFIG.API_BASE_URL}/api/export/csv`;
        const params = new URLSearchParams();

        if (this.isCustomRange && this.customTimeRange.start && this.customTimeRange.end) {
            // Use local datetime format
            const start = this.customTimeRange.start + ':00';
            const end = this.customTimeRange.end + ':00';
            params.append('start', start);
            params.append('end', end);
        } else {
            const hours = document.getElementById('timeRange').value;
            if (hours !== 'custom') {
                // For preset ranges, use ISO format (already in UTC)
                const end = new Date().toISOString();
                const start = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
                params.append('start', start);
                params.append('end', end);
            }
        }

        if (params.toString()) {
            url += '?' + params.toString();
        }

        try {
            // Fetch the CSV
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error('Failed to download CSV');
            }

            // Get the blob
            const blob = await response.blob();

            // Create download link
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `sensor_data_${new Date().toISOString().slice(0, 10)}.csv`;
            document.body.appendChild(a);
            a.click();

            // Cleanup
            window.URL.revokeObjectURL(downloadUrl);
            document.body.removeChild(a);

            console.log('CSV downloaded successfully');
        } catch (error) {
            console.error('Failed to download CSV:', error);
            alert('Failed to download CSV. Please try again.');
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new DashboardApp();
});
