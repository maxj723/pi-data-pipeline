const CONFIG = {
    API_BASE_URL: 'https://mirror-nuke-lcd-ethical.trycloudflare.com', // cloudflare url for https tunneling

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
        lux: 'rgba(245, 158, 11, 1)',             // Orange
        voltage: 'rgba(124, 58, 237, 1)'          // Purple
    },

    CHART_COLORS_ALPHA: {
        temperature: 'rgba(239, 68, 68, 0.2)',
        humidity: 'rgba(59, 130, 246, 0.2)',
        soil_moisture: 'rgba(16, 185, 129, 0.2)',
        lux: 'rgba(245, 158, 11, 0.2)',
        voltage: 'rgba(124, 58, 237, 0.2)'
    },

    MAP: {
        defaultCenter: [41.7052, -86.2352],
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
