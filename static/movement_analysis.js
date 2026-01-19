/**
 * Railway Movement Analysis System
 * JavaScript functionality for movement analysis interface
 * 
 * This script manages interactive features including:
 * - File uploads
 * - Route visualization
 * - Movement time analysis
 * - Interactive charts with Plotly
 */

// Application configuration
const config = {
    apiPrefix: '/movement_analysis',  // API endpoint prefix
    toast: {
        duration: 3000,    // Display time in ms
        animationDuration: 300  // Fade animation time in ms
    },
    rangeSlider: {
        keyboardNavigation: {
            enabled: true,
            shiftPercentage: 15  // How much to shift the range when arrow keys are pressed (in %)
        }
    }
};

/**
 * UI NOTIFICATION SYSTEM
 */

/**
 * Display a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast: 'success', 'warning', or 'danger'
 */
function showToast(message, type) {
    // Remove any existing toasts first
    $('.toast-notification').remove();
    
    // Create appropriate icon based on type
    const iconClass = type === 'success' ? 'check-circle' : 
                     type === 'warning' ? 'exclamation-triangle' : 
                     'times-circle';
    
    // Create toast HTML
    const toast = `<div class="toast-notification toast-${type}">
        <div class="toast-icon"><i class="fas fa-${iconClass}"></i></div>
        <div class="toast-message">${message}</div>
    </div>`;
    
    // Add to DOM and animate in
    $('body').append(toast);
    setTimeout(() => $('.toast-notification').addClass('show'), 100);
    
    // Set timeout to remove after display duration
    setTimeout(() => {
        $('.toast-notification').removeClass('show');
        setTimeout(() => {
            $('.toast-notification').remove();
        }, config.toast.animationDuration);
    }, config.toast.duration);
}

/**
 * FORM & DATA HANDLING
 */

/**
 * Set default date values - One day range ending at current time
 */
function setDefaultDates() {
    const today = new Date();
    const formattedToday = today.toISOString().slice(0,10);
    
    // Create yesterday's date
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const formattedYesterday = yesterday.toISOString().slice(0,10);
    
    // Set form field values
    $('#from_date').val(formattedYesterday + 'T00:00');
    $('#to_date').val(formattedToday + 'T23:59');
    
    console.log("Default date range set");
}

/**
 * Load available routes from the API
 */
function loadRoutes() {
    console.log("Fetching available routes...");
    
    $.getJSON(`${config.apiPrefix}/routes`)
        .done(function(data) {
            if (data.routes && data.routes.length > 0) {
                // Update stats counter
                $('#totalRoutes').text(data.routes.length);
                
                // Build select options
                let options = '<option value="">Select a route...</option>';
                data.routes.forEach(route => {
                    options += `<option value="${route}">${route}</option>`;
                });
                
                // Update dropdown
                $("#route").html(options);
                console.log(`Loaded ${data.routes.length} routes`);
            } else {
                handleEmptyRoutes();
            }
        })
        .fail(function(jqXHR, textStatus, errorThrown) {
            console.error("Error fetching routes:", textStatus, errorThrown);
            handleRouteFetchError(textStatus);
        });
}

/**
 * Handle case when no routes are available
 */
function handleEmptyRoutes() {
    $("#route").html('<option value="">No routes available</option>');
    $('#visualization').html('<div class="alert alert-warning">' + 
        '<i class="fas fa-exclamation-triangle"></i> No routes found in the system.</div>');
    console.warn("No routes found in API response");
}

/**
 * Handle error when fetching routes
 * @param {string} errorText - Error message
 */
function handleRouteFetchError(errorText) {
    $("#route").html('<option value="">Error loading routes</option>');
    $('#visualization').html(`<div class="alert alert-danger">` + 
        `<i class="fas fa-exclamation-triangle"></i> Error loading routes: ${errorText}</div>`);
}

/**
 * VISUALIZATION GENERATION
 */

/**
 * Generate visualization based on form parameters
 * @param {Array} routes - Array of selected route names
 * @param {string} fromTime - Start time in ISO format
 * @param {string} toTime - End time in ISO format
 */
function generateVisualization(routes, fromTime, toTime) {
    // Show loading state
    $('#loading').fadeIn();
    $('#visualization').html('');
    
    // Update button state
    $('#generateBtn')
        .prop('disabled', true)
        .html('<i class="fas fa-spinner fa-spin"></i> Generating...');
    
    console.log(`Requesting visualization for routes: ${routes.join(", ")} (${fromTime} to ${toTime})`);
    
    // Make API request
    $.ajax({
        url: `${config.apiPrefix}/plot`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            routes: routes,
            from_time: fromTime,
            to_time: toTime
        }),
        success: handleVisualizationSuccess,
        error: handleVisualizationError
    });
}

/**
 * Handle successful visualization response
 * @param {Object} response - API response data
 */
function handleVisualizationSuccess(response) {
    // Hide loading indicator and reset button
    $('#loading').fadeOut();
    $('#generateBtn')
        .prop('disabled', false)
        .html('<i class="fas fa-chart-area"></i> Generate Visualization');
    
    if (response.plot) {
        // Display visualization
        $('#visualization').html(response.plot);
        $('#downloadBtn').prop('disabled', false);
        
        // Initialize keyboard navigation after plot is rendered
        setTimeout(function() {
            initKeyboardNavigation();
        }, 500);
        
        // Update statistics if provided
        if (response.stats) {
            $('#dataPoints').text(response.stats.dataPoints || '0');
        }
        
        // Update movement counts by route
        if (response.movementCounts) {
            updateMovementCountsByRoute(response.movementCounts, response.selectedRoutes || []);
        }
        
        showToast('Visualization generated successfully!', 'success');
    } else {
        // Handle empty response
        $('#visualization').html('<div class="alert alert-info">' + 
            '<i class="fas fa-info-circle"></i> No data available for the selected parameters.</div>');
        
        // Clear movement counts
        clearMovementCountsDisplay();
    }
}

/**
 * Update the movement counts display by route
 * @param {Object} movementCounts - Object mapping route IDs to movement counts
 * @param {Array} selectedRoutes - Array of all selected route IDs
 */
function updateMovementCountsByRoute(movementCounts, selectedRoutes) {
    const container = $('#routeMovementsContainer');
    container.empty();
    
    // Get the colors array used for routes
    const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'];
    
    // Create a complete list of routes
    const allRoutes = [...new Set([...Object.keys(movementCounts), ...selectedRoutes])];
    
    if (allRoutes.length === 0) {
        container.html('<p class="no-routes-message">No movement data available for selected routes.</p>');
        return;
    }
    
    // Sort routes alphabetically
    const sortedRoutes = allRoutes.sort();
    
    // Create a card for each route
    sortedRoutes.forEach((routeId, index) => {
        const count = movementCounts[routeId] || 0;
        const color = colors[index % colors.length];
        
        const card = $(`<div class="route-movement-card clickable-card" 
                            data-route="${routeId}" 
                            style="border-left-color: ${color}">
            <h5>Route ${routeId}</h5>
            <div>
                <span class="route-movement-count">${count}</span>
                <span class="route-movement-label">Movements</span>
            </div>
        </div>`);
        
        // Add click handler to filter movement times
        card.on('click', function() {
            filterMovementTimesByRoute(routeId);
            $('.route-movement-card').removeClass('active');
            $(this).addClass('active');
            
            // Scroll to movement times section
            $('html, body').animate({
                scrollTop: $("#movementTimesContainer").offset().top - 100
            }, 500);
        });
        
        container.append(card);
    });
    
    // Add an "All Routes" card
    const allRoutesCard = $(`<div class="route-movement-card clickable-card all-routes-card"
                               data-route="all">
        <h5>All Routes</h5>
        <div>
            <span class="route-movement-count">${sortedRoutes.length}</span>
            <span class="route-movement-label">Total</span>
        </div>
    </div>`);
    
    allRoutesCard.on('click', function() {
        filterMovementTimesByRoute('all');
        $('.route-movement-card').removeClass('active');
        $(this).addClass('active');
    });
    
    container.append(allRoutesCard);
}

/**
 * Filter the movement times table to show only a specific route
 * @param {string} routeId - The route ID to filter by, or 'all' for all routes
 */
function filterMovementTimesByRoute(routeId) {
    if (routeId === 'all') {
        $('.movement-row').show();
        $('#movementTimesHeader').text('Movement Times Summary');
    } else {
        $('.movement-row').hide();
        $(`.movement-row[data-route="${routeId}"]`).show();
        $('#movementTimesHeader').text(`Movement Times for Route ${routeId}`);
    }
}

/**
 * Clear the movement counts display
 */
function clearMovementCountsDisplay() {
    const container = $('#routeMovementsContainer');
    container.html('<p class="text-muted">Select routes to view movement counts</p>');
}

/**
 * Handle visualization error
 * @param {Object} error - Error response
 */
function handleVisualizationError(error) {
    $('#loading').fadeOut();
    $('#generateBtn')
        .prop('disabled', false)
        .html('<i class="fas fa-chart-area"></i> Generate Visualization');
    
    console.error("Error generating visualization:", error);
    $('#visualization').html(`<div class="alert alert-danger">` +
        `<i class="fas fa-exclamation-triangle"></i> Error: ${error.responseText || 'Could not generate visualization'}</div>`);
    
    clearMovementCountsDisplay();
    showToast('Error generating visualization', 'danger');
}

/**
 * EVENT HANDLERS
 */

/**
 * Set up form submission handler
 */
function setupFormSubmission() {
    $('#visualizationForm').on('submit', function(e) {
        e.preventDefault();
        
        // Get form values
        const routes = $('#route').val();
        const fromTime = $('#from_date').val();
        const toTime = $('#to_date').val();
        
        // Validate form
        if (!routes || routes.length === 0 || !fromTime || !toTime) {
            showToast('Please select at least one route and time range.', 'warning');
            return;
        }
        
        // Calculate time difference for display
        const from = new Date(fromTime);
        const to = new Date(toTime);
        const diffHours = Math.round((to - from) / (1000 * 60 * 60));
        $('#timePeriod').text(diffHours + ' hrs');
        
        // Generate visualization
        generateVisualization(routes, fromTime, toTime);
        
        // Fetch movement times
        fetchMovementTimes(routes, fromTime, toTime);
    });
    
    // Update selected routes display when selection changes
    $('#route').on('change', function() {
        updateSelectedRoutesDisplay($(this).val());
    });
}

/**
 * Display selected routes as tags
 * @param {Array} selectedRoutes - Array of selected route names
 */
function updateSelectedRoutesDisplay(selectedRoutes) {
    const container = $('#selectedRoutes');
    container.empty();
    
    if (selectedRoutes && selectedRoutes.length > 0) {
        selectedRoutes.forEach(route => {
            const routeTag = $(`<span class="route-tag">${route} <i class="fas fa-times remove-route" data-route="${route}"></i></span>`);
            container.append(routeTag);
        });
    }
    
    // Add click handler for removing routes
    $('.remove-route').on('click', function() {
        const routeToRemove = $(this).data('route');
        const currentSelection = $('#route').val();
        const updatedSelection = currentSelection.filter(r => r !== routeToRemove);
        $('#route').val(updatedSelection);
        updateSelectedRoutesDisplay(updatedSelection);
    });
}

/**
 * Set up UI control handlers
 */
function setupUIControls() {
    setupRangeSliderKeyboardNavigation();
}

/**
 * Debounce function to limit how often a function is called
 * @param {Function} func - Function to debounce
 * @param {number} wait - Milliseconds to wait
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Set up keyboard navigation for the Plotly rangeslider
 */
function setupRangeSliderKeyboardNavigation() {
    if (!config.rangeSlider.keyboardNavigation.enabled) return;
    
    console.log("Setting up keyboard navigation for rangeslider");
    
    // Listen for document-level keydown events
    $(document).off('keydown.rangeslider').on('keydown.rangeslider', function(e) {
        const key = e.which || e.keyCode;
        const isInputFocused = $('input:focus, select:focus, textarea:focus').length > 0;
        
        if (isInputFocused) return;
        
        // Left arrow: 37, Right arrow: 39
        if (key === 37 || key === 39) {
            const gd = document.querySelector('#visualization .js-plotly-plot');
            
            if (!gd || !gd._fullLayout || !gd._fullLayout.xaxis) {
                return;
            }
            
            e.preventDefault();
            const direction = (key === 37) ? -1 : 1;
            shiftRangesliderView(direction, config.rangeSlider.keyboardNavigation.shiftPercentage / 100);
        }
    });
    
    // Listen for the custom event from the plot
    document.removeEventListener('plotly_rendered', initKeyboardNavigation);
    document.addEventListener('plotly_rendered', initKeyboardNavigation);
}

/**
 * Shift the rangeslider view left or right
 * @param {number} direction - Direction to shift: -1 for left, 1 for right
 * @param {number} percentage - Percentage of the current view to shift by (0-1)
 */
function shiftRangesliderView(direction, percentage) {
    const gd = document.querySelector('#visualization .js-plotly-plot');
    
    if (!gd || !gd._fullLayout || !gd._fullLayout.xaxis) {
        return;
    }
    
    const xaxis = gd._fullLayout.xaxis;
    
    if (!Array.isArray(xaxis.range) || xaxis.range.length !== 2) {
        return;
    }
    
    const currentRange = xaxis.range.map(r => new Date(r));
    const timeSpan = currentRange[1] - currentRange[0];
    
    if (!timeSpan || isNaN(timeSpan)) {
        return;
    }
    
    const shiftAmount = timeSpan * percentage * direction;
    const newRange = [
        new Date(currentRange[0].getTime() + shiftAmount),
        new Date(currentRange[1].getTime() + shiftAmount)
    ];
    
    Plotly.relayout(gd, {
        'xaxis.range': newRange
    }).then(() => {
        showViewShiftIndicator(direction);
    }).catch(err => {
        console.error('Error shifting rangeslider view:', err);
    });
}

/**
 * Show a visual indicator that the view has shifted
 * @param {number} direction - Direction of shift: -1 for left, 1 for right
 */
function showViewShiftIndicator(direction) {
    $('.range-shift-indicator').remove();
    
    const indicator = $('<div class="range-shift-indicator"></div>');
    
    if (direction < 0) {
        indicator.addClass('range-shift-left').html('<i class="fas fa-chevron-left"></i>');
    } else {
        indicator.addClass('range-shift-right').html('<i class="fas fa-chevron-right"></i>');
    }
    
    $('#visualization').append(indicator);
    
    setTimeout(() => {
        indicator.remove();
    }, 500);
}

/**
 * Initialize keyboard navigation - called after plot is rendered
 */
function initKeyboardNavigation() {
    console.log('Initializing keyboard navigation for timeline');
    
    const vizContainer = document.getElementById('visualization');
    if (vizContainer && !vizContainer.hasAttribute('tabindex')) {
        vizContainer.setAttribute('tabindex', '0');
    }
    
    setupRangeSliderKeyboardNavigation();
    addTimelineNavigationButtons();
    
    if (!$('input:focus, select:focus, textarea:focus').length) {
        setTimeout(() => {
            if (vizContainer) {
                vizContainer.focus({preventScroll: true});
                showKeyboardNavigationHint();
            }
        }, 500);
    }
}

/**
 * Add timeline navigation buttons to the visualization container
 */
function addTimelineNavigationButtons() {
    $('.timeline-nav-button').remove();
    
    const vizContainer = document.getElementById('visualization');
    if (!vizContainer) {
        return;
    }
    
    const leftButton = $(`<button class="timeline-nav-button timeline-nav-left" aria-label="Navigate timeline left">
        <i class="fas fa-chevron-left"></i>
    </button>`);
    
    const rightButton = $(`<button class="timeline-nav-button timeline-nav-right" aria-label="Navigate timeline right">
        <i class="fas fa-chevron-right"></i>
    </button>`);
    
    $(vizContainer).append(leftButton);
    $(vizContainer).append(rightButton);
    
    leftButton.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        shiftRangesliderView(-1, config.rangeSlider.keyboardNavigation.shiftPercentage / 100);
    });
    
    rightButton.on('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        shiftRangesliderView(1, config.rangeSlider.keyboardNavigation.shiftPercentage / 100);
    });
    
    setTimeout(() => {
        leftButton.addClass('visible');
        rightButton.addClass('visible');
    }, 500);
}

/**
 * Show a hint about keyboard navigation
 */
function showKeyboardNavigationHint() {
    $('.keyboard-nav-hint').remove();
    
    const hint = $('<div class="keyboard-nav-hint"><i class="fas fa-keyboard"></i> Use ← → keys to navigate timeline</div>');
    $('#visualization').append(hint);
    
    setTimeout(() => {
        hint.addClass('show');
        
        setTimeout(() => {
            hint.removeClass('show');
            setTimeout(() => hint.remove(), 1000);
        }, 3000);
    }, 100);
}

/**
 * Set up download button functionality
 */
function setupDownloadButton() {
    $('#downloadBtn').click(function() {
        if (window.Plotly && document.querySelector('.js-plotly-plot')) {
            Plotly.downloadImage(
                document.querySelector('.js-plotly-plot'), 
                {
                    format: 'png', 
                    width: 1200, 
                    height: 800, 
                    filename: 'railway_movement_analysis'
                }
            );
        } else {
            showToast('No visualization to download', 'warning');
        }
    });
}

/**
 * Set up tooltip for route details
 */
function setupRouteTooltip() {
    $('#routesStatsCard').on('click', function() {
        showAllRoutesTooltip();
    });
    
    $(document).on('click', '.tooltip-close-btn', function(e) {
        e.stopPropagation();
        closeRouteTooltip();
    });
    
    $(document).on('click', '.tooltip-backdrop', function() {
        closeRouteTooltip();
    });
    
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $('#routeTooltip').is(':visible')) {
            closeRouteTooltip();
        }
    });
}

/**
 * Show tooltip with all routes
 */
function showAllRoutesTooltip() {
    $.getJSON(`${config.apiPrefix}/routes`)
        .done(function(data) {
            if (data.routes && data.routes.length > 0) {
                $('body').append('<div class="tooltip-backdrop"></div>');
                
                fetch(`${config.apiPrefix}/route_circuits`)
                    .then(response => {
                        if (!response.ok) throw new Error('Failed to load route circuits');
                        return response.json();
                    })
                    .then(routeData => {
                        fetch(`${config.apiPrefix}/route_details`)
                            .then(response => response.json())
                            .then(routeDetails => {
                                $('#tooltipRouteId').text('Available Routes');
                                
                                let routesHtml = '';
                                data.routes.forEach(routeId => {
                                    const circuit = routeData[routeId] || 'Circuit path not available';
                                    const routeName = routeDetails[routeId] ? routeDetails[routeId].Route_name : '';
                                    
                                    const routeDisplayName = routeName ? 
                                        `<div class="route-id">${routeId}</div><div class="route-name-prominent">${routeName}</div>` : 
                                        `<div class="route-id">${routeId}</div>`;
                                    
                                    routesHtml += `<div class="route-item mb-3">
                                        <h6 class="route-item-title">${routeDisplayName}</h6>
                                        <div class="circuit-path">${formatCircuitPath(circuit)}</div>
                                    </div>`;
                                });
                                
                                $('#tooltipCircuitPath').html(routesHtml);
                                $('#routeTooltip').show();
                            })
                            .catch(error => {
                                console.error('Error loading route details:', error);
                                showTooltipWithoutRouteNames(data.routes, routeData);
                            });
                    })
                    .catch(error => {
                        console.error('Error loading route circuits:', error);
                        $('#tooltipRouteId').text('Available Routes');
                        $('#tooltipCircuitPath').html(`<div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle"></i> Error loading route circuits: ${error.message}
                        </div>`);
                        $('#routeTooltip').show();
                    });
            }
        })
        .fail(function(jqXHR, textStatus, errorThrown) {
            console.error("Error fetching routes:", textStatus, errorThrown);
            showToast('Error loading routes', 'danger');
        });
}

/**
 * Display tooltip without route names as a fallback
 * @param {Array} routes - Array of route IDs
 * @param {Object} routeData - Object containing route circuit data
 */
function showTooltipWithoutRouteNames(routes, routeData) {
    $('#tooltipRouteId').text('Available Routes');
    
    let routesHtml = '';
    routes.forEach(routeId => {
        const circuit = routeData[routeId] || 'Circuit path not available';
        routesHtml += `<div class="route-item mb-3">
            <h6 class="route-item-title">Route: ${routeId}</h6>
            <div class="circuit-path">${formatCircuitPath(circuit)}</div>
        </div>`;
    });
    
    $('#tooltipCircuitPath').html(routesHtml);
    $('#routeTooltip').show();
}

/**
 * Format circuit path for display
 * @param {string} circuitPath - Circuit path string
 * @returns {string} Formatted HTML
 */
function formatCircuitPath(circuitPath) {
    if (!circuitPath) return '<span class="text-muted">No circuit path available</span>';
    
    const segments = circuitPath.split('-');
    let formattedPath = '';
    
    segments.forEach((segment, index) => {
        formattedPath += `<span class="circuit-segment">${segment.trim()}</span>`;
        if (index < segments.length - 1) {
            formattedPath += '<span class="circuit-arrow">→</span>';
        }
    });
    
    return formattedPath;
}

/**
 * Close the route tooltip
 */
function closeRouteTooltip() {
    $('#routeTooltip').hide();
    $('.tooltip-backdrop').remove();
}

/**
 * MOVEMENT TIMES FUNCTIONALITY
 */

/**
 * Fetch and display movement times for selected routes
 * @param {Array} routes - Array of selected route names
 * @param {string} fromTime - Start time in ISO format
 * @param {string} toTime - End time in ISO format
 */
function fetchMovementTimes(routes, fromTime, toTime) {
    $('#movementTimesContainer').html('<div class="text-center"><i class="fas fa-spinner fa-spin"></i> Loading movement times...</div>');
    
    if (!routes || routes.length === 0) {
        $('#movementTimesContainer').html('<p class="text-muted">Select routes to view movement times</p>');
        return;
    }
    
    console.log(`Fetching movement times for routes: ${routes.join(', ')}`);
    
    $.ajax({
        url: `${config.apiPrefix}/movement_times`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            routes: routes,
            from_time: fromTime,
            to_time: toTime
        }),
        success: function(response) {
            displayMovementTimes(response);
        },
        error: function(error) {
            console.error('Error fetching movement times:', error);
            $('#movementTimesContainer').html(`
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> Error loading movement times: ${error.responseText || 'Unknown error'}
                </div>`);
        }
    });
}

/**
 * Display movement times data in the UI
 * @param {Object} data - Movement times data from API
 */
function displayMovementTimes(data) {
    const container = $('#movementTimesContainer');
    
    if (!data || !data.movement_times || data.movement_times.length === 0) {
        container.html(`<p class="text-muted">No movement time data available for the selected routes</p>`);
        return;
    }
    
    // Sort movements by start time
    const movements = data.movement_times.sort((a, b) => {
        return new Date(a.Start_Time) - new Date(b.Start_Time);
    });
    
    // Count movements per route
    const routeCounts = {};
    const routeIds = new Set();
    movements.forEach(movement => {
        routeCounts[movement.Route_id] = (routeCounts[movement.Route_id] || 0) + 1;
        routeIds.add(movement.Route_id);
    });
    
    // Get color mapping for routes
    const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#7f7f7f', '#bcbd22', '#17becf'];
    const routeColors = {};
    [...routeIds].sort().forEach((routeId, index) => {
        routeColors[routeId] = colors[index % colors.length];
    });
    
    let headerHtml = '<h5 id="movementTimesHeader" class="mb-3">Movement Times Summary</h5>';
    
    let tableHtml = `
        <div class="table-responsive">
            <table class="table table-hover movement-times-table" id="movementTimesTable">
                <thead class="table-light">
                    <tr>
                        <th>Route ID</th>
                        <th>Movement ID</th>
                        <th>Start Time</th>
                        <th>End Time</th>
                        <th>Duration</th>
                        <th>Circuit Count</th>
                    </tr>
                </thead>
                <tbody>`;
    
    movements.forEach(movement => {
        const startDate = new Date(movement.Start_Time);
        const endDate = new Date(movement.End_Time);
        const formattedStartTime = startDate.toLocaleString();
        const formattedEndTime = endDate.toLocaleString();
        
        const durationMinutes = movement.Total_Journey_Time_Minutes;
        const formattedDuration = formatDuration(durationMinutes);
        
        const routeColor = routeColors[movement.Route_id] || '#333';
        
        tableHtml += `
            <tr class="movement-row" data-route="${movement.Route_id}">
                <td>
                    <span class="badge route-badge" style="background-color: ${routeColor}">
                        Route ${movement.Route_id}
                    </span>
                </td>
                <td>${movement.Movement_id}</td>
                <td>${formattedStartTime}</td>
                <td>${formattedEndTime}</td>
                <td>${formattedDuration}</td>
                <td>${movement.Circuit_Count}</td>
            </tr>`;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
        <div class="mt-3">
            <p><small class="text-muted">Total movements across all routes: ${movements.length}</small></p>
        </div>`;
    
    container.html(headerHtml + tableHtml);
    
    // Add click handler for rows
    $('.movement-row').on('click', function() {
        $(this).toggleClass('selected-movement');
    });
}

/**
 * Format duration in minutes to a readable string
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration string
 */
function formatDuration(minutes) {
    const hours = Math.floor(minutes / 60);
    const mins = Math.floor(minutes % 60);
    const secs = Math.floor((minutes * 60) % 60);
    let result = '';
    if (hours > 0) result += `${hours}h `;
    if (mins > 0 || hours > 0) result += `${mins}m `;
    result += `${secs}s`;
    return result;
}

/**
 * FILE UPLOAD HANDLING
 */

/**
 * Set up file upload functionality
 */
function setupFileUpload() {
    $('#uploadFilesBtn').on('click', function() {
        uploadSelectedFiles();
    });
    
    $('#resetFilesBtn').on('click', function() {
        resetFileUploads();
    });
    
    // Visual feedback when files are selected
    $('#routeChartFile, #trackCircuitFile').on('change', function() {
        const fileId = $(this).attr('id');
        const fileName = $(this).val().split('\\').pop();
        let statusId = '';
        
        if (fileId === 'routeChartFile') statusId = 'routeChartStatus';
        else if (fileId === 'trackCircuitFile') statusId = 'trackCircuitStatus';
        
        if (fileName) {
            $(`#${statusId}`).html(`<span class="text-info"><i class="fas fa-check-circle"></i> Selected: ${fileName}</span>`);
        } else {
            $(`#${statusId}`).empty();
        }
    });
    
    // Load file info on page load
    loadFileInfo();
}

/**
 * Upload the selected CSV files
 */
function uploadSelectedFiles() {
    const routeChartFile = $('#routeChartFile')[0].files[0];
    const trackCircuitFile = $('#trackCircuitFile')[0].files[0];
    
    if (!routeChartFile && !trackCircuitFile) {
        showToast('Please select files to upload', 'warning');
        return;
    }
    
    // Require both files
    if (!routeChartFile || !trackCircuitFile) {
        showToast('Please upload both Route Chart and Circuit Data files', 'warning');
        return;
    }
    
    const formData = new FormData();
    
    if (routeChartFile) {
        formData.append('route_chart_file', routeChartFile);
        $('#routeChartStatus').html('<span class="text-info"><i class="fas fa-spinner fa-spin"></i> Uploading...</span>');
    }
    if (trackCircuitFile) {
        formData.append('circuit_data_file', trackCircuitFile);
        $('#trackCircuitStatus').html('<span class="text-info"><i class="fas fa-spinner fa-spin"></i> Uploading...</span>');
    }
    
    $('#uploadFilesBtn').prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Uploading...');
    $('#uploadStatus').removeClass('d-none');
    
    $.ajax({
        url: `${config.apiPrefix}/upload_files`,
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            handleUploadSuccess(response);
        },
        error: function(xhr) {
            handleUploadError(xhr);
        },
        complete: function() {
            $('#uploadFilesBtn').prop('disabled', false).html('<i class="fas fa-cloud-upload-alt"></i> Upload Files');
            $('#uploadStatus').addClass('d-none');
        }
    });
}

/**
 * Handle successful file upload
 * @param {Object} response - Server response
 */
function handleUploadSuccess(response) {
    if (response.error) {
        showToast(response.error, 'danger');
        return;
    }
    
    showToast('Files uploaded successfully!', 'success');
    
    // Clear file inputs
    $('#routeChartFile, #trackCircuitFile').val('');
    $('#routeChartStatus, #trackCircuitStatus').empty();
    
    // Reload file info and routes
    loadFileInfo();
    setTimeout(loadRoutes, 1000);
}

/**
 * Handle file upload error
 * @param {Object} xhr - XHR object
 */
function handleUploadError(xhr) {
    let errorMsg = 'Error uploading files';
    try {
        const response = JSON.parse(xhr.responseText);
        errorMsg = response.error || errorMsg;
    } catch (e) {
        // Use default error message
    }
    
    $('#routeChartStatus, #trackCircuitStatus').html(
        `<span class="text-danger"><i class="fas fa-exclamation-circle"></i> Upload failed</span>`
    );
    showToast(errorMsg, 'danger');
}

/**
 * Reset the file upload fields
 */
function resetFileUploads() {
    if (!confirm('Are you sure you want to remove all uploaded files?')) {
        return;
    }
    
    $('#resetFilesBtn').prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Resetting...');
    
    $.ajax({
        url: `${config.apiPrefix}/reset_files`,
        type: 'POST',
        success: function() {
            showToast('Files reset successfully', 'success');
            $('#routeChartFile, #trackCircuitFile').val('');
            $('#routeChartStatus, #trackCircuitStatus').empty();
            loadFileInfo();
            setTimeout(loadRoutes, 1000);
        },
        error: function() {
            showToast('Error resetting files', 'danger');
        },
        complete: function() {
            $('#resetFilesBtn').prop('disabled', false).html('<i class="fas fa-undo"></i> Reset');
        }
    });
}

/**
 * Load file info from server
 */
function loadFileInfo() {
    $.ajax({
        url: `${config.apiPrefix}/file_info`,
        type: 'GET',
        success: function(response) {
            if (response.files && response.files.length > 0) {
                $('#fileInfo').removeClass('d-none');
                
                let tableHtml = '<table class="table table-striped table-sm">';
                tableHtml += '<thead><tr><th>File Name</th><th>Type</th><th>Size</th><th>Last Modified</th></tr></thead>';
                tableHtml += '<tbody>';
                
                response.files.forEach(function(file) {
                    const badgeClass = file.type === 'route_chart' ? 'primary' : 
                                      file.type === 'circuit_data' ? 'success' : 'info';
                    tableHtml += '<tr>';
                    tableHtml += '<td>' + file.name + '</td>';
                    tableHtml += '<td><span class="badge bg-' + badgeClass + '">' + file.type + '</span></td>';
                    tableHtml += '<td>' + formatFileSize(file.size) + '</td>';
                    tableHtml += '<td>' + formatDate(file.last_modified) + '</td>';
                    tableHtml += '</tr>';
                });
                
                tableHtml += '</tbody></table>';
                
                const statusClass = response.system_ready ? 'success' : 'warning';
                const statusIcon = response.system_ready ? 'check-circle' : 'exclamation-triangle';
                const statusMessage = response.system_ready ? 'System is ready to use' : response.message;
                
                tableHtml += '<div class="alert alert-' + statusClass + ' mt-3">';
                tableHtml += '<i class="fas fa-' + statusIcon + '"></i> <strong>Status:</strong> ' + statusMessage;
                tableHtml += '</div>';
                
                $('#fileInfoContent').html(tableHtml);
            } else {
                $('#fileInfo').addClass('d-none');
            }
        },
        error: function() {
            $('#fileInfo').addClass('d-none');
        }
    });
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

/**
 * Format timestamp for display
 */
function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

/**
 * Initialize everything when document is ready
 */
$(document).ready(function() {
    console.log("Movement Analysis module initializing...");
    
    // Set up components
    setDefaultDates();
    loadRoutes();
    setupFormSubmission();
    setupUIControls();
    setupDownloadButton();
    setupRouteTooltip();
    setupFileUpload();
    
    // Enhanced Plotly event listeners
    $(document).on('plotly_afterplot', function() {
        console.log('Plotly chart rendered, setting up keyboard navigation');
        initKeyboardNavigation();
    });
    
    // Add inline CSS for keyboard navigation and other dynamic elements
    const styleElement = document.createElement('style');
    styleElement.textContent = `
        .keyboard-nav-hint {
            position: absolute;
            bottom: 10px;
            right: 10px;
            background-color: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.5s;
            z-index: 1000;
        }
        .keyboard-nav-hint.show {
            opacity: 0.9;
        }
        
        .timeline-nav-button {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background-color: rgba(0,0,0,0.6);
            color: white;
            width: 40px;
            height: 40px;
            border: none;
            border-radius: 50%;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
            opacity: 0;
            z-index: 1000;
        }
        .timeline-nav-button:hover {
            background-color: rgba(0,0,0,0.8);
            transform: translateY(-50%) scale(1.1);
        }
        .timeline-nav-button.visible {
            opacity: 0.7;
        }
        .timeline-nav-left {
            left: 10px;
        }
        .timeline-nav-right {
            right: 10px;
        }
        
        .route-name-prominent {
            color: #0d6efd;
            font-weight: 500;
            font-size: 1.1em;
            padding: 3px 0;
            display: block;
            margin-top: 2px;
        }
        
        .route-id {
            display: inline-block;
            background-color: #6c757d;
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: 600;
            margin-right: 8px;
        }
    `;
    document.head.appendChild(styleElement);
    
    console.log("Movement Analysis module initialization complete");
});
