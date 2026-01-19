/**
 * Debug utility functions for the Railway Visualization System
 * This file contains functions to help diagnose and fix issues
 */

/**
 * Logs performance metrics about plot rendering
 * Call this function after plots are rendered to get timing info
 */
function logPlotPerformance() {
    // Get all plot elements
    const plots = document.querySelectorAll('.js-plotly-plot');
    
    console.log(`Plots found: ${plots.length}`);
    
    // Log memory usage if supported by the browser
    if (window.performance && window.performance.memory) {
        console.log('Memory usage:', {
            totalJSHeapSize: Math.round(window.performance.memory.totalJSHeapSize / (1024 * 1024)) + ' MB',
            usedJSHeapSize: Math.round(window.performance.memory.usedJSHeapSize / (1024 * 1024)) + ' MB',
            jsHeapSizeLimit: Math.round(window.performance.memory.jsHeapSizeLimit / (1024 * 1024)) + ' MB'
        });
    }
}

/**
 * Tests network connectivity to key resources
 * This helps diagnose if network issues are causing problems
 */
function testConnectivity() {
    // Test connectivity to Plotly CDN
    fetch('https://cdn.plot.ly/plotly-latest.min.js', { method: 'HEAD' })
        .then(response => {
            console.log('Plotly CDN connectivity:', response.ok ? 'OK' : 'Failed');
        })
        .catch(error => {
            console.error('Plotly CDN connectivity error:', error);
        });
        
    // Test connectivity to Bootstrap CDN
    fetch('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css', { method: 'HEAD' })
        .then(response => {
            console.log('Bootstrap CDN connectivity:', response.ok ? 'OK' : 'Failed');
        })
        .catch(error => {
            console.error('Bootstrap CDN connectivity error:', error);
        });
}

// Execute tests when directly included
if (document.readyState === 'complete') {
    console.log('Debug utilities loaded. Use logPlotPerformance() or testConnectivity() to run diagnostics.');
} else {
    window.addEventListener('load', function() {
        console.log('Debug utilities loaded. Use logPlotPerformance() or testConnectivity() to run diagnostics.');
    });
}
