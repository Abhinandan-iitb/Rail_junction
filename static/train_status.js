/**
 * Railway Train Status Visualization
 * Provides interactive visualization of train movements on railway tracks
 */
document.addEventListener('DOMContentLoaded', function() {
    // ===== STATE VARIABLES =====
    // Animation state
    let playing = false;
    let currentFrame = 0;
    let frames = [];
    let timeLabels = [];
    let interval;
    let animationSpeed = 1000;
    let speedMultiplier = 1;
    
    // Data source state
    let useDefaultData = true;
    let selectedRoute = "";
    let selectedNetGroup = ""; 
    let startDateTime = "";
    let endDateTime = "";
    let filteredTrackIds = [];  // Track IDs belonging to filtered intervals
    
    // UI state
    let trainIcons = {};
    let sliderUpdateTimeout = null;
    let lastSliderValue = 0;
    let lastUpdateTime = 0;
    
    // Signal indicator state
    let hasSignalIndicators = false;
    let signalIndicatorsCount = 0;
    
    // ===== DOM ELEMENTS =====
    // Control elements
    const playPauseBtn = document.getElementById('play-pause-btn');
    const resetBtn = document.getElementById('reset-btn');
    const slider = document.getElementById('train-slider');
    const sliderTooltip = document.getElementById('slider-tooltip');
    const timeDisplay = document.getElementById('time-display');
    const speedDecreaseBtn = document.getElementById('speed-decrease-btn');
    const speedIncreaseBtn = document.getElementById('speed-increase-btn');
    const speedDisplay = document.getElementById('speed-display');
    
    // Visualization elements
    const graphContainer = document.getElementById('graph-container');
    // Hide the train legend element as we don't need it anymore
    const trainLegend = document.getElementById('train-legend');
    if (trainLegend) {
        trainLegend.style.display = 'none';
    }
    
    // Statistics elements
    const activeTracksEl = document.getElementById('active-tracks');
    const totalTracksEl = document.getElementById('total-tracks');
    const activeTrainsEl = document.getElementById('active-trains');
    const occupancyRateEl = document.getElementById('occupancy-rate');
    const occupancyBarEl = document.getElementById('occupancy-bar');
    
    // Filter & upload elements
    const fileUploadForm = document.getElementById('fileUploadForm');
    const uploadStatus = document.getElementById('uploadStatus');
    const useDefaultBtn = document.getElementById('useDefaultBtn');
    const routeSelect = document.getElementById('route-select');
    const applyRouteFilterBtn = document.getElementById('apply-route-filter');
    const clearRouteFilterBtn = document.getElementById('clear-route-filter');
    const startDateTimeInput = document.getElementById('start-datetime');
    const endDateTimeInput = document.getElementById('end-datetime');
    const applyDateTimeFilterBtn = document.getElementById('apply-datetime-filter');
    const dateTimeFilterStatus = document.getElementById('datetime-filter-status');
    const clearDateTimeFilterBtn = document.getElementById('clear-datetime-filter');
    const netGroupSelect = document.getElementById('net-group-select');
    const applyNetGroupFilterBtn = document.getElementById('apply-net-group-filter');
    const clearNetGroupFilterBtn = document.getElementById('clear-net-group-filter');
    
    // ===== DEBUG FUNCTIONS =====
    /**
     * Debug function to verify datetime filter is working
     */
    function debugDateTimeFilter() {
        console.log('=== DateTime Filter Debug ===');
        console.log('Start DateTime:', startDateTime);
        console.log('End DateTime:', endDateTime);
        console.log('Total Frames:', frames.length);
        
        if (timeLabels.length > 0) {
            console.log('First Frame Time:', timeLabels[0]);
            console.log('Last Frame Time:', timeLabels[timeLabels.length - 1]);
            
            // Check if filter is actually applied
            if (startDateTime) {
                const filterStart = new Date(startDateTime);
                const dataStart = new Date(timeLabels[0]);
                console.log('Filter Start >= Data Start:', filterStart <= dataStart);
            }
            
            if (endDateTime) {
                const filterEnd = new Date(endDateTime);
                const dataEnd = new Date(timeLabels[timeLabels.length - 1]);
                console.log('Filter End >= Data End:', filterEnd >= dataEnd);
            }
        }
        console.log('========================');
    }

    // ===== DATA LOADING FUNCTIONS =====
    /**
     * Load available routes for dropdown selection
     */
    function loadAvailableRoutes() {
        fetch('/train-movement/get_routes')
            .then(response => response.json())
            .then(data => {
                // Clear existing options except the first one
                while (routeSelect.options.length > 1) {
                    routeSelect.remove(1);
                }
                
                // Add new routes
                data.routes.forEach(route => {
                    const option = document.createElement('option');
                    option.value = route;
                    option.textContent = `Route ${route}`;
                    routeSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading routes:', error);
            });
    }
    
    /**
     * Load available Net Group IDs for dropdown selection
     */
    function loadAvailableNetGroupIDs() {
        fetch('/train-movement/get_net_group_ids')
            .then(response => response.json())
            .then(data => {
                // Clear existing options except the first one
                while (netGroupSelect.options.length > 1) {
                    netGroupSelect.remove(1);
                }
                
                // Add new net group IDs
                data.net_group_ids.forEach(netGroupId => {
                    const option = document.createElement('option');
                    option.value = netGroupId;
                    option.textContent = `Net Group ${netGroupId}`;
                    netGroupSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading net group IDs:', error);
            });
    }
    
    /**
     * Load visualization data from server
     */
    function loadVisualizationData() {
        // Reset data
        frames = [];
        timeLabels = [];
        hasSignalIndicators = false;
        
        // Show loading state
        graphContainer.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin mr-2"></i> Loading train movement visualization...
            </div>`;
        
        // Build API endpoint with filters
        let endpoint = useDefaultData ? 
            '/train-movement/get_track_data' : 
            '/train-movement/get_track_data?use_uploaded=true';
            
        if (selectedRoute) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `route=${selectedRoute}`;
        }
        
        if (selectedNetGroup) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `net_group=${selectedNetGroup}`;
        }
        
        if (startDateTime) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `start_datetime=${encodeURIComponent(startDateTime)}`;
        }
        
        if (endDateTime) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `end_datetime=${encodeURIComponent(endDateTime)}`;
        }
            
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    graphContainer.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                    return;
                }
                
                // Store animation data
                frames = data.frames;
                timeLabels = data.time_labels;
                hasSignalIndicators = data.has_signals || false;
                
                // Store filtered track IDs if provided but don't automatically focus on them
                filteredTrackIds = [];
                
                // Display interval IDs and their status if Net_Group_ID filter was applied
                if (data.filter_info && data.filter_info.interval_ids) {
                    displayIntervalStatus(
                        data.filter_info.net_group_id, 
                        data.filter_info.interval_ids,
                        data.filter_info.interval_statuses || {}
                    );
                    
                    // Store filtered track IDs but don't focus on them
                    if (data.filter_info.filtered_track_ids && data.filter_info.filtered_track_ids.length > 0) {
                        filteredTrackIds = data.filter_info.filtered_track_ids;
                    }
                } else {
                    // Hide the interval status display if no Net_Group_ID filter is applied
                    hideIntervalStatusDisplay();
                    
                    // Clear filtered track IDs
                    filteredTrackIds = [];
                    
                    // Remove any existing filter notifications
                    const existingNotifications = document.querySelectorAll('.filter-notification');
                    existingNotifications.forEach(notification => {
                        notification.parentNode.removeChild(notification);
                    });
                }
                
                // Check if we got any frames
                if (!frames.length) {
                    graphContainer.innerHTML = `<div class="alert alert-warning">
                        <i class="fas fa-exclamation-circle"></i> 
                        No data found for the selected time range. Please try a different time period.
                    </div>`;
                    return;
                }
                
                // Configure slider
                slider.max = frames.length - 1;
                slider.step = frames.length > 500 ? 0.5 : 0.01;
                
                // Create plot from Plotly JSON
                graphContainer.innerHTML = '';
                Plotly.newPlot(graphContainer, data.plotly_data.data, data.plotly_data.layout);
                
                // Store the count of signal indicators for reference during updates
                if (hasSignalIndicators) {
                    signalIndicatorsCount = frames[0].signals ? frames[0].signals.length : 0;
                    console.log(`Found ${signalIndicatorsCount} signal indicators`);
                }
                
                // Create container for train icons
                createTrainContainer();
                
                // Enhance track labels
                enhanceTrackLabels();
                
                // REMOVED: Automatic focus on filtered tracks
                // Instead, always show all tracks
                setTimeout(() => {
                    showAllTracks();
                }, 500);
                
                // Update to first frame
                if (frames.length > 0) {
                    updateFrame(0);
                }
            })
            .catch(error => {
                console.error('Error fetching track data:', error);
                graphContainer.innerHTML = `<div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> 
                    Error loading visualization data. Please try again later.
                </div>`;
            });
    }
    
    /**
     * Create container for train icons if it doesn't exist
     */
    function createTrainContainer() {
        if (!document.getElementById('train-container')) {
            const container = document.createElement('div');
            container.id = 'train-container';
            container.style.position = 'absolute';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100%';
            container.style.height = '100%';
            container.style.pointerEvents = 'none';
            graphContainer.appendChild(container);
        }
    }
    
    /**
     * Display interval IDs and their running status
     */
    function displayIntervalStatus(netGroupId, intervalIds, statusData) {
        // Create or update interval status display area
        let intervalStatusDisplay = document.getElementById('interval-status-display');
        if (!intervalStatusDisplay) {
            intervalStatusDisplay = document.createElement('div');
            intervalStatusDisplay.id = 'interval-status-display';
            intervalStatusDisplay.className = 'interval-status-panel mt-3';
            
            // Find a good place to insert it (after the net group section or graph container)
            const netGroupSection = document.getElementById('netGroupSection');
            if (netGroupSection) {
                netGroupSection.parentNode.insertBefore(intervalStatusDisplay, netGroupSection.nextSibling);
            } else {
                const graphContainer = document.getElementById('graph-container');
                if (graphContainer) {
                    graphContainer.parentNode.insertBefore(intervalStatusDisplay, graphContainer);
                }
            }
        }
        
        // Format interval IDs and status for display
        intervalStatusDisplay.style.display = 'block';
        
        // Create header
        let html = `
            <div class="card">
                <div class="card-header bg-info text-white">
                    <h5 class="mb-0"><i class="fas fa-train"></i> Train Running Status for Net Group ${netGroupId}</h5>
                </div>
                <div class="card-body">
        `;
        
        if (intervalIds.length > 0) {
            // Create table for status display
            html += `
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Interval ID</th>
                                <th>Circuit Name</th>
                                <th>Down Time</th>
                                <th>Up Time</th>
                                <th>Duration</th>
                                <th>Switch Status</th>
                                <th>Route</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            // Add row for each interval ID
            intervalIds.forEach(id => {
                const status = statusData[id] || {};
                const routeInfo = status.route_id ? 
                    `${status.route_id} (${status.route_name || 'Unknown'})` : 
                    'Not assigned';
                    
                html += `
                    <tr>
                        <td><strong>${id}</strong></td>
                        <td>${status.circuit_name || 'Unknown'}</td>
                        <td>${formatDateTime(status.down_time)}</td>
                        <td>${formatDateTime(status.up_time)}</td>
                        <td>${status.duration || 'N/A'}</td>
                        <td>${status.switch_status || 'N/A'}</td>
                        <td>${routeInfo}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            html += '<p>No interval IDs found for this Net Group ID.</p>';
        }
        
        html += `
                </div>
            </div>
        `;
        
        intervalStatusDisplay.innerHTML = html;
    }
    
    /**
     * Format datetime for display
     */
    function formatDateTime(dateTimeStr) {
        if (!dateTimeStr) return 'N/A';
        
        try {
            const date = new Date(dateTimeStr);
            return date.toLocaleString();
        } catch (e) {
            return dateTimeStr;
        }
    }
    
    /**
     * Hide the interval status display
     */
    function hideIntervalStatusDisplay() {
        const intervalStatusDisplay = document.getElementById('interval-status-display');
        if (intervalStatusDisplay) {
            intervalStatusDisplay.style.display = 'none';
        }
    }
    
    /**
     * Load available routes for dropdown selection
     */
    function loadAvailableRoutes() {
        fetch('/train-movement/get_routes')
            .then(response => response.json())
            .then(data => {
                // Clear existing options except the first one
                while (routeSelect.options.length > 1) {
                    routeSelect.remove(1);
                }
                
                // Add new routes
                data.routes.forEach(route => {
                    const option = document.createElement('option');
                    option.value = route;
                    option.textContent = `Route ${route}`;
                    routeSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading routes:', error);
            });
    }
    
    /**
     * Load available Net Group IDs for dropdown selection
     */
    function loadAvailableNetGroupIDs() {
        fetch('/train-movement/get_net_group_ids')
            .then(response => response.json())
            .then(data => {
                // Clear existing options except the first one
                while (netGroupSelect.options.length > 1) {
                    netGroupSelect.remove(1);
                }
                
                // Add new net group IDs
                data.net_group_ids.forEach(netGroupId => {
                    const option = document.createElement('option');
                    option.value = netGroupId;
                    option.textContent = `Net Group ${netGroupId}`;
                    netGroupSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Error loading net group IDs:', error);
            });
    }
    
    /**
     * Load visualization data from server
     */
    function loadVisualizationData() {
        // Reset data
        frames = [];
        timeLabels = [];
        hasSignalIndicators = false;
        
        // Show loading state
        graphContainer.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin mr-2"></i> Loading train movement visualization...
            </div>`;
        
        // Build API endpoint with filters
        let endpoint = useDefaultData ? 
            '/train-movement/get_track_data' : 
            '/train-movement/get_track_data?use_uploaded=true';
            
        if (selectedRoute) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `route=${selectedRoute}`;
        }
        
        if (selectedNetGroup) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `net_group=${selectedNetGroup}`;
        }
        
        if (startDateTime) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `start_datetime=${encodeURIComponent(startDateTime)}`;
        }
        
        if (endDateTime) {
            endpoint += (endpoint.includes('?') ? '&' : '?') + `end_datetime=${encodeURIComponent(endDateTime)}`;
        }
            
        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    graphContainer.innerHTML = `<div class="alert alert-danger">Error: ${data.error}</div>`;
                    return;
                }
                
                // Store animation data
                frames = data.frames;
                timeLabels = data.time_labels;
                hasSignalIndicators = data.has_signals || false;
                
                // Store filtered track IDs if provided but don't automatically focus on them
                filteredTrackIds = [];
                
                // Display interval IDs and their status if Net_Group_ID filter was applied
                if (data.filter_info && data.filter_info.interval_ids) {
                    displayIntervalStatus(
                        data.filter_info.net_group_id, 
                        data.filter_info.interval_ids,
                        data.filter_info.interval_statuses || {}
                    );
                    
                    // Store filtered track IDs but don't focus on them
                    if (data.filter_info.filtered_track_ids && data.filter_info.filtered_track_ids.length > 0) {
                        filteredTrackIds = data.filter_info.filtered_track_ids;
                    }
                } else {
                    // Hide the interval status display if no Net_Group_ID filter is applied
                    hideIntervalStatusDisplay();
                    
                    // Clear filtered track IDs
                    filteredTrackIds = [];
                    
                    // Remove any existing filter notifications
                    const existingNotifications = document.querySelectorAll('.filter-notification');
                    existingNotifications.forEach(notification => {
                        notification.parentNode.removeChild(notification);
                    });
                }
                
                // Check if we got any frames
                if (!frames.length) {
                    graphContainer.innerHTML = `<div class="alert alert-warning">
                        <i class="fas fa-exclamation-circle"></i> 
                        No data found for the selected time range. Please try a different time period.
                    </div>`;
                    return;
                }
                
                // Configure slider
                slider.max = frames.length - 1;
                slider.step = frames.length > 500 ? 0.5 : 0.01;
                
                // Create plot from Plotly JSON
                graphContainer.innerHTML = '';
                Plotly.newPlot(graphContainer, data.plotly_data.data, data.plotly_data.layout);
                
                // Store the count of signal indicators for reference during updates
                if (hasSignalIndicators) {
                    signalIndicatorsCount = frames[0].signals ? frames[0].signals.length : 0;
                    console.log(`Found ${signalIndicatorsCount} signal indicators`);
                }
                
                // Create container for train icons
                createTrainContainer();
                
                // Enhance track labels
                enhanceTrackLabels();
                
                // REMOVED: Automatic focus on filtered tracks
                // Instead, always show all tracks
                setTimeout(() => {
                    showAllTracks();
                }, 500);
                
                // Update to first frame
                if (frames.length > 0) {
                    updateFrame(0);
                }
            })
            .catch(error => {
                console.error('Error fetching track data:', error);
                graphContainer.innerHTML = `<div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> 
                    Error loading visualization data. Please try again later.
                </div>`;
            });
    }
    
    /**
     * Create container for train icons if it doesn't exist
     */
    function createTrainContainer() {
        if (!document.getElementById('train-container')) {
            const container = document.createElement('div');
            container.id = 'train-container';
            container.style.position = 'absolute';
            container.style.top = '0';
            container.style.left = '0';
            container.style.width = '100%';
            container.style.height = '100%';
            container.style.pointerEvents = 'none';
            graphContainer.appendChild(container);
        }
    }
    
    /**
     * Display interval IDs and their running status
     */
    function displayIntervalStatus(netGroupId, intervalIds, statusData) {
        // Create or update interval status display area
        let intervalStatusDisplay = document.getElementById('interval-status-display');
        if (!intervalStatusDisplay) {
            intervalStatusDisplay = document.createElement('div');
            intervalStatusDisplay.id = 'interval-status-display';
            intervalStatusDisplay.className = 'interval-status-panel mt-3';
            
            // Find a good place to insert it (after the net group section or graph container)
            const netGroupSection = document.getElementById('netGroupSection');
            if (netGroupSection) {
                netGroupSection.parentNode.insertBefore(intervalStatusDisplay, netGroupSection.nextSibling);
            } else {
                const graphContainer = document.getElementById('graph-container');
                if (graphContainer) {
                    graphContainer.parentNode.insertBefore(intervalStatusDisplay, graphContainer);
                }
            }
        }
        
        // Format interval IDs and status for display
        intervalStatusDisplay.style.display = 'block';
        
        // Create header
        let html = `
            <div class="card">
                <div class="card-header bg-info text-white">
                    <h5 class="mb-0"><i class="fas fa-train"></i> Train Running Status for Net Group ${netGroupId}</h5>
                </div>
                <div class="card-body">
        `;
        
        if (intervalIds.length > 0) {
            // Create table for status display
            html += `
                <div class="table-responsive">
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Interval ID</th>
                                <th>Circuit Name</th>
                                <th>Down Time</th>
                                <th>Up Time</th>
                                <th>Duration</th>
                                <th>Switch Status</th>
                                <th>Route</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            // Add row for each interval ID
            intervalIds.forEach(id => {
                const status = statusData[id] || {};
                const routeInfo = status.route_id ? 
                    `${status.route_id} (${status.route_name || 'Unknown'})` : 
                    'Not assigned';
                    
                html += `
                    <tr>
                        <td><strong>${id}</strong></td>
                        <td>${status.circuit_name || 'Unknown'}</td>
                        <td>${formatDateTime(status.down_time)}</td>
                        <td>${formatDateTime(status.up_time)}</td>
                        <td>${status.duration || 'N/A'}</td>
                        <td>${status.switch_status || 'N/A'}</td>
                        <td>${routeInfo}</td>
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        } else {
            html += '<p>No interval IDs found for this Net Group ID.</p>';
        }
        
        html += `
                </div>
            </div>
        `;
        
        intervalStatusDisplay.innerHTML = html;
    }
    
    /**
     * Format datetime for display
     */
    function formatDateTime(dateTimeStr) {
        if (!dateTimeStr) return 'N/A';
        
        try {
            const date = new Date(dateTimeStr);
            return date.toLocaleString();
        } catch (e) {
            return dateTimeStr;
        }
    }
    
    /**
     * Hide the interval status display
     */
    function hideIntervalStatusDisplay() {
        const intervalStatusDisplay = document.getElementById('interval-status-display');
        if (intervalStatusDisplay) {
            intervalStatusDisplay.style.display = 'none';
        }
    }
    
    // ===== VISUALIZATION FUNCTIONS =====
    /**
     * Update frame to show track and train positions at specified index
     */
    function updateFrame(index) {
        try {
            // Ensure index is within bounds
            index = Math.min(Math.max(0, parseFloat(index)), frames.length - 1);
            const frameIndex = Math.round(index);
            
            currentFrame = frameIndex;
            if (!frames.length) return;
            
            const frame = frames[frameIndex];
            
            // Update plot colors
            const plotDiv = document.getElementById('graph-container');
            if (!plotDiv || !plotDiv.data) return;
            
            // Get colors and widths from frame data
            const colors = frame.colors || frame;
            const widths = frame.widths || Array(colors.length).fill(3);
            
            // Update track visualization
            for (let i = 0; i < colors.length; i++) {
                if (plotDiv.data[i] && plotDiv.data[i].line) {
                    Plotly.restyle(plotDiv, {
                        'line.color': [colors[i]],
                        'line.width': [widths[i]]
                    }, [i]);
                }
            }
            
            // Update signal indicators if they exist
            if (hasSignalIndicators && frame.signals && Array.isArray(frame.signals)) {
                updateSignalIndicators(frame.signals, plotDiv);
            }
            
            // Update train positions if plot is initialized
            if (plotDiv._fullLayout && plotDiv._fullLayout.xaxis) {
                updateTrainPositions(frame, plotDiv);
            }
            
            // Update time display
            timeDisplay.textContent = timeLabels[frameIndex] || `Frame ${frameIndex + 1}`;
            
            // Update slider position (only if not being dragged)
            if (parseFloat(slider.value) !== index) {
                slider.value = index;
                // Update progress indicator
                const progress = (index / (frames.length - 1)) * 100;
                slider.style.setProperty('--progress', `${progress}%`);
            }
            
            // Update statistics
            updateStatistics(frame);
        } catch (error) {
            console.error('Error updating frame:', error);
        }
    }
    
    /**
     * Update signal indicators based on frame data
     */
    function updateSignalIndicators(signalUpdates, plotDiv) {
        try {
            // Calculate the index offset where signal indicators start
            // They come after edge traces and label traces
            let startIndex = 0;
            
            // Find where signal traces start in the data array
            for (let i = 0; i < plotDiv.data.length; i++) {
                if (plotDiv.data[i].mode === 'markers' && 
                    plotDiv.data[i].marker && 
                    plotDiv.data[i].marker.symbol === 'circle') {
                    startIndex = i;
                    break;
                }
            }
            
            // Apply updates to each signal indicator
            signalUpdates.forEach((update, index) => {
                const traceIndex = startIndex + index;
                if (traceIndex < plotDiv.data.length && update) {
                    // Update marker color
                    if (update['marker.color']) {
                        Plotly.restyle(plotDiv, {
                            'marker.color': update['marker.color']
                        }, [traceIndex]);
                    }
                }
            });
        } catch (error) {
            console.error('Error updating signal indicators:', error);
        }
    }
    
    /**
     * Update train positions on the visualization
     */
    function updateTrainPositions(frame, plotDiv) {
        try {
            const trainContainer = document.getElementById('train-container');
            if (!trainContainer) {
                createTrainContainer();
                return;
            }
            
            // Get the train positions from the frame
            const trainPositions = frame.trains || {};
            
            // Remove trains that are no longer active
            for (const trainId in trainIcons) {
                if (!trainPositions[trainId]) {
                    removeTrainIcon(trainId);
                }
            }
            
            // Update or add active trains
            for (const trainId in trainPositions) {
                const positions = trainPositions[trainId];
                if (positions && positions.length > 0) {
                    updateTrainIcon(trainId, positions[0], plotDiv);
                }
            }
        } catch (error) {
            console.error('Error updating train positions:', error);
        }
    }
    
    /**
     * Remove a train icon from the visualization
     */
    function removeTrainIcon(trainId) {
        if (trainIcons[trainId]) {
            if (trainIcons[trainId].element && trainIcons[trainId].element.parentNode) {
                trainIcons[trainId].element.parentNode.removeChild(trainIcons[trainId].element);
            }
            if (trainIcons[trainId].labelElement && trainIcons[trainId].labelElement.parentNode) {
                trainIcons[trainId].labelElement.parentNode.removeChild(trainIcons[trainId].labelElement);
            }
            delete trainIcons[trainId];
        }
    }
    
    /**
     * Update or create a train icon at the specified position
     */
    function updateTrainIcon(trainId, pos, plotDiv) {
        // Make sure we have needed layout info
        if (!plotDiv._fullLayout || !plotDiv._fullLayout.xaxis || !plotDiv._fullLayout.yaxis) {
            console.warn('Plot layout not ready yet');
            return;
        }
        
        const xaxis = plotDiv._fullLayout.xaxis;
        const yaxis = plotDiv._fullLayout.yaxis;
        
        // Make sure we have the coordinate conversion functions
        if (!xaxis || !yaxis || !xaxis.l2p || !yaxis.l2p) {
            console.warn('Axis conversion functions not available');
            return;
        }
        
        // Get margins to adjust position
        const marginLeft = plotDiv._fullLayout.margin.l || 0;
        const marginTop = plotDiv._fullLayout.margin.t || 0;
        
        // Calculate pixel coordinates
        const x = xaxis.l2p(pos.x) + marginLeft;
        const y = yaxis.l2p(pos.y) + marginTop;
        
        // Get the angle if it exists (or default to 0)
        const angle = pos.angle || 0;
        
        // Get train number for display
        const trainNumber = trainId.split('-')[1] || trainId;
        
        // Get train color from position data or use train info
        const trainColor = pos.color || trainInfo[trainId] || '#FF0000';
        
        if (trainIcons[trainId]) {
            // Update existing train icon
            const trainIcon = trainIcons[trainId].element;
            trainIcon.style.left = `${x}px`;
            trainIcon.style.top = `${y}px`;
            trainIcon.style.transform = `rotate(${angle}deg)`;
            trainIcon.style.backgroundColor = trainColor;
            trainIcon.style.setProperty('--train-color', trainColor);
            
            // Update the label position
            if (trainIcons[trainId].labelElement) {
                trainIcons[trainId].labelElement.style.left = `${x}px`;
                trainIcons[trainId].labelElement.style.top = `${y}px`;
            }
        } else {
            // Create new train icon
            const trainIcon = document.createElement('div');
            trainIcon.className = 'train-icon';
            trainIcon.style.left = `${x}px`;
            trainIcon.style.top = `${y}px`;
            trainIcon.style.transform = `rotate(${angle}deg)`;
            trainIcon.style.backgroundColor = trainColor;
            trainIcon.style.setProperty('--train-color', trainColor);
            
            // Create separate element for train number
            const trainLabel = document.createElement('div');
            trainLabel.className = 'train-number';
            trainLabel.textContent = trainNumber;
            trainLabel.style.left = `${x}px`;
            trainLabel.style.top = `${y}px`;
            
            // Store the train icon and label
            trainIcons[trainId] = {
                element: trainIcon,
                labelElement: trainLabel,
                position: pos
            };
            
            // Add to container
            const container = document.getElementById('train-container');
            container.appendChild(trainIcon);
            container.appendChild(trainLabel);
        }
    }
    
    /**
     * Update statistics display with current frame data
     */
    function updateStatistics(frame) {
        if (!frame) return;
        
        // Make sure we're handling the frame format correctly
        const colors = frame.colors || frame;
        
        // Count active tracks (non-blue colors)
        const activeCount = colors.filter(color => color !== '#0066cc').length;
        const totalTracks = colors.length;
        const occupancyRate = Math.round((activeCount / totalTracks) * 100);
        
        // Update statistics if elements exist
        if (activeTracksEl) activeTracksEl.textContent = activeCount;
        if (totalTracksEl) totalTracksEl.textContent = totalTracks;
        if (occupancyRateEl) occupancyRateEl.textContent = `${occupancyRate}%`;
        if (occupancyBarEl) occupancyBarEl.style.width = `${occupancyRate}%`;
        
        // Count active trains if train positions exist
        const trainPositions = frame.trains || {};
        const activeTrains = Object.keys(trainPositions).length;
        if (activeTrainsEl) activeTrainsEl.textContent = activeTrains;
        
        // Count active signals if available
        if (frame.signals && hasSignalIndicators) {
            const activeSignals = frame.signals.filter(signal => 
                signal['marker.color'] && 
                signal['marker.color'][0] !== '#888888'
            ).length;
            
            // If you have signal statistics elements, update them here
            // Example: if (activeSignalsEl) activeSignalsEl.textContent = activeSignals;
        }
    }
    
    /**
     * Enhance track labels after plot is created
     */
    function enhanceTrackLabels() {
        setTimeout(() => {
            const textElements = document.querySelectorAll('.js-plotly-plot .textpoint text');
            textElements.forEach(el => {
                el.classList.add('track-label');
            });
        }, 1000);
    }
    
    // ===== ANIMATION CONTROL FUNCTIONS =====
    /**
     * Start animation with current speed settings
     */
    function startAnimation() {
        if (interval) {
            clearInterval(interval);
        }
        
        // More sophisticated animation timing
        let lastTimestamp = 0;
        const frameDuration = animationSpeed; // ms per frame
        let accumulatedTime = 0;
        
        function animateFrame(timestamp) {
            if (!playing) return;
            
            if (!lastTimestamp) lastTimestamp = timestamp;
            const elapsed = timestamp - lastTimestamp;
            lastTimestamp = timestamp;
            
            accumulatedTime += elapsed;
            
            if (accumulatedTime >= frameDuration) {
                // Calculate how many frames to advance (usually just 1)
                const framesToAdvance = Math.floor(accumulatedTime / frameDuration);
                accumulatedTime %= frameDuration;
                
                // Advance frames smoothly
                currentFrame = (currentFrame + framesToAdvance) % frames.length;
                updateFrame(currentFrame);
            }
            
            requestAnimationFrame(animateFrame);
        }
        
        requestAnimationFrame(animateFrame);
    }
    
    /**
     * Toggle play/pause state of the animation
     */
    function togglePlayPause() {
        playing = !playing;
        
        if (playing) {
            playPauseBtn.innerHTML = '<i class="fas fa-pause"></i> Pause';
            startAnimation();
        } else {
            playPauseBtn.innerHTML = '<i class="fas fa-play"></i> Play';
            clearInterval(interval);
        }
    }
    
    /**
     * Reset animation to first frame
     */
    function resetAnimation() {
        if (playing) {
            togglePlayPause(); // Stop the animation
        }
        updateFrame(0);
    }
    
    /**
     * Increase animation speed
     */
    function increaseSpeed() {
        if (animationSpeed > 100) { // Don't let it get too fast
            animationSpeed = Math.max(100, animationSpeed / 1.5);
            speedMultiplier = Math.round((1000 / animationSpeed) * 10) / 10;
            speedDisplay.textContent = `${speedMultiplier}x`;
            
            if (playing) {
                startAnimation(); // Restart with new speed
            }
        }
    }
    
    /**
     * Decrease animation speed
     */
    function decreaseSpeed() {
        if (animationSpeed < 5000) { // Limit how slow it can get
            animationSpeed = Math.min(5000, animationSpeed * 1.5);
            speedMultiplier = Math.round((1000 / animationSpeed) * 10) / 10;
            speedDisplay.textContent = `${speedMultiplier}x`;
            
            if (playing) {
                startAnimation(); // Restart with new speed
            }
        }
    }
    
    // ===== HELPER FUNCTIONS =====
    /**
     * Utility function for debouncing
     */
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }
    
    // ===== EVENT HANDLERS =====
    /**
     * Handle file upload form submission
     */
    fileUploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Create form data object
        const formData = new FormData(fileUploadForm);
        
        // Check if files are selected
        const nodesFile = document.getElementById('nodesFile').files[0];
        const edgesFile = document.getElementById('edgesFile').files[0];
        const circuitFile = document.getElementById('circuitFile').files[0];
        
        if (!nodesFile || !edgesFile || !circuitFile) {
            uploadStatus.className = 'alert alert-warning upload-status';
            uploadStatus.style.display = 'block';
            uploadStatus.textContent = 'Please select all three required files.';
            return;
        }
        
        // Show loading state
        uploadStatus.className = 'alert alert-info upload-status';
        uploadStatus.style.display = 'block';
        uploadStatus.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading and processing files...';
        
        // Submit files
        fetch('/train-movement/upload_files', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                uploadStatus.className = 'alert alert-success upload-status';
                uploadStatus.innerHTML = '<i class="fas fa-check-circle"></i> Files uploaded successfully! Loading visualization...';
                
                // Set flag to use uploaded files
                useDefaultData = false;
                
                // Load visualization with uploaded data
                setTimeout(() => {
                    loadVisualizationData();
                    // Reload routes as they may have changed
                    loadAvailableRoutes();
                }, 1000);
            } else {
                uploadStatus.className = 'alert alert-danger upload-status';
                uploadStatus.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${data.error}`;
            }
        })
        .catch(error => {
            console.error('Upload error:', error);
            uploadStatus.className = 'alert alert-danger upload-status';
            uploadStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Upload failed. Please try again.';
        });
    });
    
    /**
     * Handle use default data button
     */
    useDefaultBtn.addEventListener('click', function() {
        useDefaultData = true;
        uploadStatus.className = 'alert alert-info upload-status';
        uploadStatus.style.display = 'block';
        uploadStatus.innerHTML = '<i class="fas fa-info-circle"></i> Using default railway data.';
        loadVisualizationData();
        loadAvailableRoutes();
    });
    
    /**
     * Handle route filter application
     */
    applyRouteFilterBtn.addEventListener('click', function() {
        selectedRoute = routeSelect.value;
        if (playing) togglePlayPause();
        loadVisualizationData();
    });
    
    /**
     * Handle route filter clearing
     */
    clearRouteFilterBtn.addEventListener('click', function() {
        routeSelect.value = '';
        selectedRoute = '';
        if (playing) togglePlayPause();
        loadVisualizationData();
    });
    
    /**
     * Handle date-time filter application
     */
    applyDateTimeFilterBtn.addEventListener('click', function() {
        const startValue = startDateTimeInput.value;
        const endValue = endDateTimeInput.value;
        
        // Validate inputs
        if (!startValue && !endValue) {
            // If both empty, clear the filter
            startDateTime = "";
            endDateTime = "";
            dateTimeFilterStatus.style.display = 'block';
            dateTimeFilterStatus.className = 'alert alert-info';
            dateTimeFilterStatus.textContent = 'Date-time filter cleared.';
            clearDateTimeFilterBtn.style.display = 'none';
        } else if (!startValue || !endValue) {
            // Need both start and end times
            dateTimeFilterStatus.style.display = 'block';
            dateTimeFilterStatus.className = 'alert alert-warning';
            dateTimeFilterStatus.textContent = 'Please provide both start and end date-time values.';
            return;
        } else if (new Date(startValue) >= new Date(endValue)) {
            // Start time must be before end time
            dateTimeFilterStatus.style.display = 'block';
            dateTimeFilterStatus.className = 'alert alert-warning';
            dateTimeFilterStatus.textContent = 'Start date-time must be earlier than end date-time.';
            return;
        } else {
            // Valid filter, apply it
            startDateTime = startValue;
            endDateTime = endValue;
            dateTimeFilterStatus.style.display = 'block';
            dateTimeFilterStatus.className = 'alert alert-success';
            dateTimeFilterStatus.innerHTML = `
                <i class="fas fa-filter"></i> 
                Filtering data from <strong>${formatDateTime(startValue)}</strong> to <strong>${formatDateTime(endValue)}</strong>
            `;
            clearDateTimeFilterBtn.style.display = 'inline-block';
        }
        
        // Pause if playing
        if (playing) togglePlayPause();
        
        // Show loading state with filter info
        graphContainer.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin mr-2"></i> 
                Applying date-time filter and loading train movement data...
                <br><small class="text-muted mt-2">
                    ${startDateTime && endDateTime ? 
                        `Filtering from ${formatDateTime(startDateTime)} to ${formatDateTime(endDateTime)}` : 
                        'Loading all available data'
                    }
                </small>
            </div>`;
        
        // Load data with the new filter
        loadVisualizationData();
    });
    
    /**
     * Handle date-time filter clearing
     */
    clearDateTimeFilterBtn.addEventListener('click', function() {
        // Clear filter values
        startDateTimeInput.value = '';
        endDateTimeInput.value = '';
        startDateTime = '';
        endDateTime = '';
        
        // Update UI
        dateTimeFilterStatus.style.display = 'block';
        dateTimeFilterStatus.className = 'alert alert-info';
        dateTimeFilterStatus.textContent = 'Date-time filter cleared.';
        clearDateTimeFilterBtn.style.display = 'none';
        
        // Reload data without filters
        if (playing) togglePlayPause();
        loadVisualizationData();
    });
    
    /**
     * Handle net group filter application
     */
    applyNetGroupFilterBtn.addEventListener('click', function() {
        selectedNetGroup = netGroupSelect.value;
        if (playing) togglePlayPause();
        loadVisualizationData();
    });
    
    /**
     * Handle net group filter clearing
     */
    clearNetGroupFilterBtn.addEventListener('click', function() {
        netGroupSelect.value = '';
        selectedNetGroup = '';
        if (playing) togglePlayPause();
        hideIntervalStatusDisplay();  // Hide interval status display when clearing filter
        
        // Reset filtered track IDs
        filteredTrackIds = [];
        
        // Show all tracks when clearing filter
        showAllTracks();
        
        // Remove any existing filter notifications
        const existingNotifications = document.querySelectorAll('.filter-notification');
        existingNotifications.forEach(notification => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
        
        loadVisualizationData();
    });
    
    // Animation control event listeners
    playPauseBtn.addEventListener('click', togglePlayPause);
    resetBtn.addEventListener('click', resetAnimation);
    speedIncreaseBtn.addEventListener('click', increaseSpeed);
    speedDecreaseBtn.addEventListener('click', decreaseSpeed);
    
    // Add smooth slider change event for better performance
    slider.addEventListener('change', function() {
        const value = parseFloat(this.value);
        updateFrame(value);
        lastSliderValue = value;
        lastUpdateTime = Date.now();
    });
    
    /**
     * Handle slider input events
     */
    slider.addEventListener('input', function() {
        // Cancel any pending update
        clearTimeout(sliderUpdateTimeout);
        
        // Get the current value
        const value = parseFloat(this.value);
        
        // Update the tooltip position and content
        const sliderWidth = slider.offsetWidth;
        const thumbPosition = (value / (frames.length - 1)) * sliderWidth;
        sliderTooltip.style.left = `${thumbPosition}px`;
        
        // Show the frame time in the tooltip
        const frameIndex = Math.round(value);
        if (timeLabels[frameIndex]) {
            sliderTooltip.textContent = timeLabels[frameIndex];
            sliderTooltip.style.display = 'block';
        }
        
        // Immediate update for smoother experience
        updateFrame(value);
        lastSliderValue = value;
        lastUpdateTime = Date.now();
        
        // If playing, pause
        if (playing) togglePlayPause();
    });
    
    // Slider tooltip mouse events
    slider.addEventListener('mousemove', function(e) {
        if (frames.length === 0) return;
        
        // Calculate position
        const sliderRect = slider.getBoundingClientRect();
        const position = (e.clientX - sliderRect.left) / sliderRect.width;
        const framePosition = position * (frames.length - 1);
        const frameIndex = Math.min(Math.max(0, Math.round(framePosition)), frames.length - 1);
        
        // Position the tooltip
        sliderTooltip.style.left = `${(e.clientX - sliderRect.left)}px`;
        
        // Show the frame time in the tooltip
        if (timeLabels[frameIndex]) {
            sliderTooltip.textContent = timeLabels[frameIndex];
            sliderTooltip.style.display = 'block';
        }
    });
    
    slider.addEventListener('mouseenter', function() {
        if (frames.length > 0) {
            sliderTooltip.style.display = 'block';
        }
    });
    
    slider.addEventListener('mouseleave', function() {
        sliderTooltip.style.display = 'none';
    });
    
    // Touch events for mobile
    slider.addEventListener('touchstart', function(e) {
        if (frames.length === 0) return;
        sliderTooltip.style.display = 'block';
        
        // If playing, pause
        if (playing) togglePlayPause();
    });
    
    slider.addEventListener('touchend', function() {
        sliderTooltip.style.display = 'none';
    });
    
    // Keyboard controls for slider (left/right arrow keys)
    document.addEventListener('keydown', function(e) {
        // Only handle arrow keys when not typing in input fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            return;
        }
        
        if (frames.length === 0) return;
        
        let currentValue = parseFloat(slider.value);
        let newValue = currentValue;
        
        switch(e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                // Hold Shift for faster navigation (jump by 10 frames)
                newValue = Math.max(0, currentValue - (e.shiftKey ? 10 : 1));
                break;
            case 'ArrowRight':
                e.preventDefault();
                // Hold Shift for faster navigation (jump by 10 frames)
                newValue = Math.min(frames.length - 1, currentValue + (e.shiftKey ? 10 : 1));
                break;
            case 'Home':
                e.preventDefault();
                newValue = 0; // Go to beginning
                break;
            case 'End':
                e.preventDefault();
                newValue = frames.length - 1; // Go to end
                break;
            case ' ': // Spacebar for play/pause
                e.preventDefault();
                togglePlayPause();
                return;
            case 'r': // R key for reset
            case 'R':
                e.preventDefault();
                resetAnimation();
                return;
            default:
                return;
        }
        
        // Update slider and frame
        slider.value = newValue;
        updateFrame(newValue);
        
        // Show tooltip briefly
        const frameIndex = Math.round(newValue);
        if (timeLabels[frameIndex]) {
            sliderTooltip.textContent = timeLabels[frameIndex];
            sliderTooltip.style.display = 'block';
            
            // Hide tooltip after 1 second
            setTimeout(() => {
                sliderTooltip.style.display = 'none';
            }, 1000);
        }
        
        // Pause animation if playing
        if (playing && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
            togglePlayPause();
        }
    });
    
    /**
     * Update track visibility based on filter focus toggle
     */
    function updateTrackVisibility() {
        if (!focusOnFilteredTracks || filteredTrackIds.length === 0) {
            // Show all tracks
            showAllTracks();
        } else {
            // Only show filtered tracks
            focusOnTracks(filteredTrackIds);
        }
    }
    
    /**
     * Show all tracks and reset view
     */
    function showAllTracks() {
        const plotDiv = document.getElementById('graph-container');
        if (!plotDiv || !plotDiv.data) return;
        
        // Remove highlight class from graph container
        plotDiv.classList.remove('filtered-view');
        
        // Reset all tracks to visible
        for (let i = 0; i < plotDiv.data.length; i++) {
            Plotly.restyle(plotDiv, {
                'visible': true
            }, [i]);
        }
        
        // Reset the zoom/pan
        Plotly.relayout(plotDiv, {
            'xaxis.autorange': true,
            'yaxis.autorange': true
        });
    }
    
    /**
     * Focus view on specific track IDs
     * @param {Array} trackIds - List of track IDs to focus on
     */
    function focusOnTracks(trackIds) {
        const plotDiv = document.getElementById('graph-container');
        if (!plotDiv || !plotDiv.data) return;
        
        // Add highlight class to the graph container to indicate focused state
        plotDiv.classList.add('filtered-view');
        
        // Count of filtered traces for debugging
        let filteredCount = 0;
        let totalCount = plotDiv.data.length;
        
        // Set visibility based on whether the trace is for a filtered track
        for (let i = 0; i < plotDiv.data.length; i++) {
            const trace = plotDiv.data[i];
            // If this trace has text (and is a label trace), check if it's a filtered track
            if (trace.text && trace.text.length > 0) {
                const trackId = trace.text[0];
                const isFiltered = trackIds.includes(trackId);
                
                if (isFiltered) filteredCount++;
                
                // If it's a label trace, make it visible if it's filtered
                if (trace.mode === 'text') {
                    Plotly.restyle(plotDiv, {
                        'visible': isFiltered
                    }, [i]);
                }
                // If it's a track line, make it visible if it's filtered
                else if (trace.mode === 'lines') {
                    Plotly.restyle(plotDiv, {
                        'visible': isFiltered
                    }, [i]);
                }
            }
            // Signal indicators should always be visible
            else if (trace.mode === 'markers' && trace.marker && trace.marker.symbol === 'circle') {
                // Keep signals visible
                Plotly.restyle(plotDiv, {
                    'visible': true
                }, [i]);
            }
        }
        
        console.log(`Focused view: showing ${filteredCount} out of ${totalCount} traces`);
        
        // Autoscale to show all visible traces
        Plotly.relayout(plotDiv, {
            'xaxis.autorange': true,
            'yaxis.autorange': true
        });
    }
    
    // ===== INITIALIZATION =====
    // Initial data load
    loadAvailableNetGroupIDs();
    loadAvailableRoutes();
    loadVisualizationData();
});
