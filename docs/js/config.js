const CONFIG = {
    API_BASE_URL: 'http://10.0.0.181:5000',

    REFRESH_INTERVALS: { // (ms)
        liveData: 5000,      // 5 seconds
        nodeStats: 10000,    // 10 seconds
        decisions: 8000,     // 8 seconds
        map: 15000,          // 15 seconds
        charts: 30000        // 30 seconds
    },

    CHART_COLORS: {
        temperature: 'rgba(239, 68, 68, 1)',      // Red
        humidity: 'rgba(59, 130, 246, 1)',        // Blue
        soil_moisture: 'rgba(16, 185, 129, 1)',   // Green
        sunlight: 'rgba(245, 158, 11, 1)',        // Orange
        battery: 'rgba(124, 58, 237, 1)'          // Purple
    },

    CHART_COLORS_ALPHA: {
        temperature: 'rgba(239, 68, 68, 0.2)',
        humidity: 'rgba(59, 130, 246, 0.2)',
        soil_moisture: 'rgba(16, 185, 129, 0.2)',
        sunlight: 'rgba(245, 158, 11, 0.2)',
        battery: 'rgba(124, 58, 237, 0.2)'
    },

    MAP: {
        defaultCenter: [39.6837, -75.7497],  // UPDATE!
        defaultZoom: 15,
        tileLayer: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    },

    FEATURES: {
        realTimeUpdates: true,
        serverSentEvents: true,
        heatMap: true,
        autoRefresh: true
    }
};
