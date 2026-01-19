/**
 * Railway Visualization System - Circuit & Switch Analysis Global JavaScript
 * Comprehensive script for all Circuit & Switch Analysis interactive features
 * Version: 2.0 (Global)
 * Last Updated: January 19, 2026
 * 
 * Features:
 * - Plot management and visualization
 * - Form handling and validation
 * - Circuit selection interface
 * - Range navigation for plots
 * - CSV download functionality
 * - File upload handling
 * - Toast notifications
 * - UI enhancements and animations
 */

// ==================================================================================================================================================================================
// PLOT MANAGEMENT FUNCTIONS
// ==================================================================================================================================================================================

/**
 * Global tracking of plots to help with cleanup
 */
let activePlots = [];

/**
 * Deletes a plot element with animation
 * @param {string} plotId - DOM ID of plot container to remove
 */
function deletePlot(plotId) {
    const plotElement = document.getElementById(plotId);
    if (plotElement) {
        // Fade out animation before removal
        plotElement.style.transition = 'all 0.3s ease';
        plotElement.style.transform = 'scale(0.95)';
        plotElement.style.opacity = '0';
        
        // Find any Plotly instances inside and properly clean them up
        const plotlyInstances = plotElement.querySelectorAll('.js-plotly-plot');
        plotlyInstances.forEach(plot => {
            if (plot && plot._fullLayout) {
                Plotly.purge(plot); // Properly clean up Plotly
            }
        });
        
        setTimeout(() => {
            plotElement.remove();
            
            // Remove from active plots tracking
            activePlots = activePlots.filter(id => id !== plotId);
        }, 300);
    }
}

/**
 * Resizes all plots to fit their containers using a more efficient approach
 * Only resizes visible plots to improve performance
 */
function resizePlots() {
    // Only resize plots in the currently active tab to save resources
    const activeTabId = document.querySelector('.tab-pane.active').id;
    const plotContainer = document.getElementById(activeTabId);
    
    if (!plotContainer) return;
    
    const plotDivs = plotContainer.querySelectorAll('.js-plotly-plot');
    
    if (plotDivs.length > 0) {
        // Use a progressive approach to resizing to avoid blocking the main thread
        let index = 0;
        
        function resizeNextPlot() {
            if (index >= plotDivs.length) return;
            
            const div = plotDivs[index];
            if (div && div._fullLayout) {
                try {
                    Plotly.relayout(div, {
                        'autosize': true,
                        'width': div.parentElement.offsetWidth
                    });
                } catch (e) {
                    console.warn('Error resizing plot:', e);
                }
            }
            
            index++;
            // Use requestAnimationFrame to process next plot on next frame
            // This prevents blocking the UI thread
            if (index < plotDivs.length) {
                window.requestAnimationFrame(resizeNextPlot);
            }
        }
        
        // Start the progressive resizing
        window.requestAnimationFrame(resizeNextPlot);
    }
}

/**
 * Sets up plot interactions like highlighting on click
 * Uses event delegation to improve performance
 */
function setupPlotInteractions() {
    // Use event delegation instead of attaching to each plot
    document.addEventListener('click', function(event) {
        // Find if the click is in a plot container
        const plotContainer = event.target.closest('.plot-container');
        if (plotContainer) {
            // Remove highlight from all plots
            document.querySelectorAll('.plot-highlight').forEach(div => {
                div.classList.remove('plot-highlight');
            });
            
            // Add highlight to the clicked container
            plotContainer.classList.add('plot-highlight');
        }
    });
}

/**
 * Shows loading state for plots
 * @param {boolean} isLoading - Whether loading is in progress
 */
function toggleLoadingState(isLoading) {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        if (isLoading) {
            loadingOverlay.style.display = 'flex';
        } else {
            loadingOverlay.style.display = 'none';
        }
    }
}

// ===============================================================================================================================
// UI ENHANCEMENT FUNCTIONS
// ===============================================================================================================================

/**
 * Animates counting up for statistics values with improved performance
 */
function animateCounter(element, start, end, duration) {
    if (!element) return;
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

/**
 * Initializes all UI enhancements - stat counters, card effects, etc
 */
function initUIEnhancements() {
    // Statistics counter animations
    const statValues = document.querySelectorAll('.stats-value');
    statValues.forEach(stat => {
        if (!isNaN(stat.textContent) && stat.textContent !== '-') {
            const finalValue = parseInt(stat.textContent);
            animateCounter(stat, 0, finalValue, 1000);
        }
    });
}

// ===============================================================================================================================
// FORM HANDLING
// ===============================================================================================================================

/**
 * Set up form submission with progressive enhancement
 * Falls back to traditional form submission if AJAX is not supported
 */
function setupFormHandling() {
    const analysisForm = document.querySelector('form[action*="plot"]');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(e) {
            // Show loading state immediately
            toggleLoadingState(true);
            
            // Don't prevent default form submission
            // This ensures the form will work even if our AJAX approach fails
            // e.preventDefault(); - REMOVED to allow traditional form submission
            
            // Let the form submit normally, which is the most reliable approach
            // The loading overlay will show while the page reloads
        });
    }
}

// ===============================================================================================================================
// CIRCUIT SELECTION HANDLING
// ===============================================================================================================================

/**
 * Initialize the ordered circuit selection interface
 */
function initCircuitSelector() {
    const addButton = document.getElementById('add_circuit_btn');
    const circuitSelector = document.getElementById('circuit_selector');
    const selectedList = document.getElementById('selected_circuits_list');
    const noCircuitsMsg = document.getElementById('no_circuits_message');
    const primaryCircuitSelect = document.getElementById('circuit_name');
    const hiddenContainer = document.getElementById('hidden_circuits_container');
    
    // Skip if any of these elements are missing
    if (!addButton || !circuitSelector || !selectedList || !noCircuitsMsg || !primaryCircuitSelect || !hiddenContainer) {
        return;
    }
    
    // Function to update the hidden inputs for form submission
    function updateHiddenInputs() {
        // Clear existing hidden inputs
        hiddenContainer.innerHTML = '';
        
        // Get all selected circuits from the list
        const listItems = selectedList.querySelectorAll('.circuit-item');
        
        // Create hidden inputs for each circuit
        listItems.forEach(item => {
            const circuitName = item.dataset.circuit;
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'additional_circuits';
            hiddenInput.value = circuitName;
            hiddenContainer.appendChild(hiddenInput);
        });
        
        // Toggle visibility of the "no circuits" message
        if (listItems.length > 0) {
            noCircuitsMsg.style.display = 'none';
        } else {
            noCircuitsMsg.style.display = 'block';
        }
    }
    
    // Add circuit button click handler
    addButton.addEventListener('click', function() {
        const selectedCircuit = circuitSelector.value;
        const primaryCircuit = primaryCircuitSelect.value;
        
        // Don't add if nothing selected or same as primary circuit
        if (!selectedCircuit || selectedCircuit === primaryCircuit) {
            if (selectedCircuit === primaryCircuit) {
                showAlert('Primary circuit cannot be added as additional circuit', 'warning');
            }
            return;
        }
        
        // Check if the circuit is already in the list
        const exists = Array.from(selectedList.children).some(
            item => item.dataset.circuit === selectedCircuit
        );
        
        if (exists) {
            showAlert('This circuit is already added', 'info');
            return;
        }
        
        // Create a new list item
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item d-flex justify-content-between align-items-center p-2 circuit-item';
        listItem.dataset.circuit = selectedCircuit;
        
        // Add drag handle for reordering
        listItem.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="drag-handle me-2" title="Drag to reorder">
                    <i class="fas fa-grip-lines"></i>
                </span>
                <span class="circuit-name">${selectedCircuit}</span>
            </div>
            <div class="btn-group btn-group-sm" role="group">
                <button type="button" class="btn btn-outline-secondary btn-move-up" title="Move up">
                    <i class="fas fa-chevron-up"></i>
                </button>
                <button type="button" class="btn btn-outline-secondary btn-move-down" title="Move down">
                    <i class="fas fa-chevron-down"></i>
                </button>
                <button type="button" class="btn btn-outline-danger btn-remove" title="Remove">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add the item to the list
        selectedList.appendChild(listItem);
        
        // Add event listeners for the buttons
        const removeBtn = listItem.querySelector('.btn-remove');
        removeBtn.addEventListener('click', function() {
            listItem.remove();
            updateHiddenInputs();
        });
        
        const moveUpBtn = listItem.querySelector('.btn-move-up');
        moveUpBtn.addEventListener('click', function() {
            if (listItem.previousElementSibling) {
                listItem.parentNode.insertBefore(listItem, listItem.previousElementSibling);
                updateHiddenInputs();
            }
        });
        
        const moveDownBtn = listItem.querySelector('.btn-move-down');
        moveDownBtn.addEventListener('click', function() {
            if (listItem.nextElementSibling) {
                listItem.parentNode.insertBefore(listItem.nextElementSibling, listItem);
                updateHiddenInputs();
            }
        });
        
        // Reset the selector
        circuitSelector.selectedIndex = 0;
        
        // Update hidden inputs
        updateHiddenInputs();
    });
    
    // Make the list sortable (if available)
    if (typeof Sortable !== 'undefined') {
        new Sortable(selectedList, {
            animation: 150,
            handle: '.drag-handle',
            onEnd: function() {
                updateHiddenInputs();
            }
        });
    }
    
    // Also handle primary circuit changes to ensure no duplicates
    primaryCircuitSelect.addEventListener('change', function() {
        const primaryCircuit = this.value;
        
        // Check if the new primary circuit is in the additional list
        const listItems = selectedList.querySelectorAll('.circuit-item');
        listItems.forEach(item => {
            if (item.dataset.circuit === primaryCircuit) {
                item.remove();
                showAlert('Removed duplicate circuit from additional selection', 'info');
            }
        });
        
        updateHiddenInputs();
    });
}

/**
 * Display a simple alert message
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Find a good place to show the alert
    const container = document.querySelector('.page-container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 300);
        }, 3000);
    }
}

// ===============================================================================================================================
// RANGESLIDER NAVIGATION
// ===============================================================================================================================

/**
 * Controls the rangeslider navigation for plots
 * @param {string} direction - Either 'left' or 'right'
 * @param {number} stepPercentage - How much to move as a percentage of the current view (default 25%)
 */
function moveRangeslider(direction, stepPercentage = 25) {
    // Get the currently active tab
    const activeTabId = document.querySelector('.tab-pane.active').id;
    const plotContainer = document.getElementById(activeTabId);
    
    if (!plotContainer) return;
    
    // Find all Plotly plots in the active tab
    const plotDivs = plotContainer.querySelectorAll('.js-plotly-plot');
    
    // Process each plot
    plotDivs.forEach(plotDiv => {
        if (!plotDiv || !plotDiv._fullLayout || !plotDiv._fullLayout.xaxis) return;
        
        // Get current axis range
        const xAxis = plotDiv._fullLayout.xaxis;
        const currentRange = xAxis.range;
        
        // Skip if there's no valid range
        if (!currentRange || currentRange.length !== 2) return;
        
        // Convert string dates to timestamps if needed
        const range0 = typeof currentRange[0] === 'string' ? new Date(currentRange[0]).getTime() : currentRange[0];
        const range1 = typeof currentRange[1] === 'string' ? new Date(currentRange[1]).getTime() : currentRange[1];
        
        // Calculate the current range width
        const rangeWidth = Math.abs(range1 - range0);
        
        // Calculate the step size based on the percentage
        const stepSize = (rangeWidth * stepPercentage) / 100;
        
        // Calculate new range based on direction
        let newRange;
        if (direction === 'left') {
            newRange = [range0 - stepSize, range1 - stepSize];
        } else { // right
            newRange = [range0 + stepSize, range1 + stepSize];
        }
        
        // Update the range
        Plotly.relayout(plotDiv, {'xaxis.range': newRange});
    });
}

/**
 * Setup rangeslider navigation buttons
 */
function setupRangesliderNavigation() {
    // Find navigation buttons
    const leftBtn = document.getElementById('range-nav-left');
    const rightBtn = document.getElementById('range-nav-right');
    
    if (leftBtn) {
        leftBtn.addEventListener('click', function(e) {
            e.preventDefault();
            moveRangeslider('left');
        });
    }
    
    if (rightBtn) {
        rightBtn.addEventListener('click', function(e) {
            e.preventDefault();
            moveRangeslider('right');
        });
    }
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Only process if we're not in an input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
            return;
        }
        
        if (e.key === 'ArrowLeft') {
            moveRangeslider('left');
        } else if (e.key === 'ArrowRight') {
            moveRangeslider('right');
        }
    });
}

// ===============================================================================================================================
// CSV DOWNLOAD FUNCTIONS
// ===============================================================================================================================

/**
 * Handle CSV download button clicks by making an AJAX request to the server
 * @param {string} dataType - Type of data to download ('circuits', 'switches', etc.)
 */
function downloadCSVData(dataType) {
    // Show spinner or indicator
    const downloadButton = document.getElementById(`download-${dataType}-csv`);
    if (!downloadButton) {
        console.error(`Download button for ${dataType} not found`);
        return;
    }

    const originalText = downloadButton.innerHTML;
    downloadButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Preparing Download...';
    downloadButton.disabled = true;
    
    // Get parameters from the page
    const params = new URLSearchParams();
    
    // Try to get parameters from form elements first
    const circuitName = document.getElementById('circuit_name')?.value;
    const fromTime = document.getElementById('from_time')?.value;
    const toTime = document.getElementById('to_time')?.value;
    const minDuration = document.getElementById('min_duration')?.value;
    const maxDuration = document.getElementById('max_duration')?.value;
    
    // Add parameters to the request
    if (circuitName) params.append('circuit_name', circuitName);
    if (fromTime) params.append('from_time', fromTime);
    if (toTime) params.append('to_time', toTime);
    if (minDuration) params.append('min_duration', minDuration);
    if (maxDuration) params.append('max_duration', maxDuration);
    
    // Get additional circuits from hidden inputs
    const additionalCircuitInputs = document.querySelectorAll('#hidden_circuits_container input[name="additional_circuits"]');
    additionalCircuitInputs.forEach(input => {
        params.append('additional_circuits', input.value);
    });
    
    // If form elements are not available, try to get from stored values
    if (!circuitName && window.selectedCircuitName) {
        params.append('circuit_name', window.selectedCircuitName);
    }
    
    if (!fromTime && window.selectedFromTime) {
        params.append('from_time', window.selectedFromTime);
    }
    
    if (!toTime && window.selectedToTime) {
        params.append('to_time', window.selectedToTime);
    }
    
    if (!minDuration && window.selectedMinDuration) {
        params.append('min_duration', window.selectedMinDuration);
    }
    
    if (!maxDuration && window.selectedMaxDuration) {
        params.append('max_duration', window.selectedMaxDuration);
    }
    
    // Add additional circuits if available but not already added
    if (additionalCircuitInputs.length === 0 && window.selectedAdditionalCircuits && Array.isArray(window.selectedAdditionalCircuits)) {
        window.selectedAdditionalCircuits.forEach(circuit => {
            params.append('additional_circuits', circuit);
        });
    }
    
    // Create a timestamp for the filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    
    // Create a hidden download link
    const downloadLink = document.createElement('a');
    downloadLink.style.display = 'none';
    document.body.appendChild(downloadLink);
    
    console.log(`Fetching CSV data for ${dataType} with params:`, params.toString());
    
    // Show user feedback toast
    showToast(`Preparing ${dataType} data for download...`, 'info');
    
    // Make AJAX request to the server
    fetch(`/circuit-switch-analysis/download_csv/${dataType}?${params.toString()}`)
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    try {
                        const errorJson = JSON.parse(text);
                        throw new Error(errorJson.error || `HTTP error! Status: ${response.status}`);
                    } catch (e) {
                        throw new Error(`HTTP error! Status: ${response.status}, Details: ${text.substring(0, 100)}...`);
                    }
                });
            }
            return response.blob();
        })
        .then(blob => {
            console.log("Download blob received:", blob);
            
            // Create a URL for the blob
            const url = window.URL.createObjectURL(blob);
            
            // Set up the download link
            downloadLink.href = url;
            downloadLink.download = `railway_${dataType}_data_${timestamp}.csv`;
            
            // Trigger download
            downloadLink.click();
            
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(downloadLink);
            
            // Restore button state
            downloadButton.innerHTML = originalText;
            downloadButton.disabled = false;
            
            // Show success toast
            showToast('Download complete!', 'success');
        })
        .catch(error => {
            console.error('Download error:', error);
            showAlert(`Error downloading data: ${error.message}`, 'danger');
            
            // Restore button state
            downloadButton.innerHTML = originalText;
            downloadButton.disabled = false;
        });
}

/**
 * Display a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (info, success, warning, danger)
 */
function showToast(message, type = 'info') {
    // Check if toast container exists, if not create it
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center border-0 bg-${type}`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Toast content
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body text-white">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();
    
    // Remove after hiding
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

// Store selected parameters in window object for later use in downloads
function storeSelectedParameters() {
    // These values will be used by the download functions
    const circuitName = document.getElementById('circuit_name');
    const fromTime = document.getElementById('from_time');
    const toTime = document.getElementById('to_time');
    const minDuration = document.getElementById('min_duration');
    const maxDuration = document.getElementById('max_duration');
    
    // Get values from form elements if available
    if (circuitName && circuitName.value) window.selectedCircuitName = circuitName.value;
    if (fromTime && fromTime.value) window.selectedFromTime = fromTime.value;
    if (toTime && toTime.value) window.selectedToTime = toTime.value;
    if (minDuration && minDuration.value) window.selectedMinDuration = minDuration.value;
    if (maxDuration && maxDuration.value) window.selectedMaxDuration = maxDuration.value;
    
    // If values are not available from form elements, try to find them in the selected details section
    if (!window.selectedCircuitName) {
        const circuitDetail = document.querySelector('.bg-light.p-2.rounded:not(.small)');
        if (circuitDetail) window.selectedCircuitName = circuitDetail.textContent.trim();
    }
    
    // Get additional circuits
    const hiddenInputs = document.querySelectorAll('#hidden_circuits_container input');
    window.selectedAdditionalCircuits = Array.from(hiddenInputs).map(input => input.value);
    
    // If no additional circuits from hidden inputs, try to get them from badges
    if (!window.selectedAdditionalCircuits.length) {
        const circuitBadges = document.querySelectorAll('.badge.bg-primary');
        window.selectedAdditionalCircuits = Array.from(circuitBadges).map(badge => badge.textContent.trim());
    }
    
    // Log the collected parameters for debugging
    console.log("Stored parameters for download:", {
        circuit: window.selectedCircuitName,
        from: window.selectedFromTime,
        to: window.selectedToTime,
        minDuration: window.selectedMinDuration,
        maxDuration: window.selectedMaxDuration,
        additionalCircuits: window.selectedAdditionalCircuits
    });
}

// ===============================================================================================================================
// INITIALIZATION
// ===============================================================================================================================

// Main initialization when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add loading overlay to DOM if not present
    if (!document.getElementById('loading-overlay')) {
        const loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'loading-overlay';
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Generating plots...</p>
        `;
        document.body.appendChild(loadingOverlay);
    }
    
    // Set default date values for the datetime pickers
    const today = new Date();
    const formattedDate = today.toISOString().slice(0, 16);
    const fromTimeEl = document.getElementById('from_time');
    const toTimeEl = document.getElementById('to_time');
    if (fromTimeEl && toTimeEl) {
        fromTimeEl.value = formattedDate;
        toTimeEl.value = formattedDate;
    }
    
    // Initialize tooltips
    const tooltipTriggers = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggers.forEach(trigger => {
        new bootstrap.Tooltip(trigger);
    });
    
    // Set up plot interactions using event delegation
    setupPlotInteractions();
    
    // Initialize UI enhancements
    initUIEnhancements();
    
    // Setup form handling with loading state
    setupFormHandling();
    
    // Resize plots for initial layout with small delay to ensure DOM is ready
    setTimeout(resizePlots, 300);
    
    // Add window resize handler with improved debouncing
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        // Use a longer delay to prevent excessive recalculations
        resizeTimer = setTimeout(resizePlots, 500);
    });
    
    // Use a more selective mutation observer focused only on plot containers
    const plotsContainer = document.getElementById('plots-container');
    const switchPlotsContainer = document.getElementById('switch-plots-container');
    
    if (plotsContainer || switchPlotsContainer) {
        const observer = new MutationObserver(function(mutations) {
            let needsResize = false;
            
            mutations.forEach(mutation => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    // Check if any added nodes are plot containers
                    mutation.addedNodes.forEach(node => {
                        if (node.classList && node.classList.contains('plot-container')) {
                            needsResize = true;
                        }
                    });
                }
            });
            
            // Only call resize if plot containers were added
            if (needsResize) {
                // Delay to ensure plots are fully rendered
                setTimeout(resizePlots, 200);
            }
        });
        
        // Observe both plot containers
        if (plotsContainer) {
            observer.observe(plotsContainer, { childList: true });
        }
        if (switchPlotsContainer) {
            observer.observe(switchPlotsContainer, { childList: true });
        }
    }
    
    // Handle tab switching to ensure plots resize when tabs change
    const plotTabs = document.querySelectorAll('button[data-bs-toggle="tab"]');
    plotTabs.forEach(tab => {
        tab.addEventListener('shown.bs.tab', function(e) {
            // Allow a moment for the tab content to display
            setTimeout(resizePlots, 100);
        });
    });
    
    // Hide loading overlay if it's visible when page loads
    // (in case of a page reload after form submission)
    setTimeout(() => toggleLoadingState(false), 500);
    
    // Initialize our new circuit selector
    initCircuitSelector();
    
    // Set up rangeslider navigation
    setupRangesliderNavigation();

    // Set up download buttons
    const downloadButtons = {
        'circuits': document.getElementById('download-circuits-csv'),
        'switches': document.getElementById('download-switches-csv'),
        'short_duration': document.getElementById('download-short-duration-csv'),
        'short_duration_switches': document.getElementById('download-short-duration-switch-csv'),
        'unknown_circuits': document.getElementById('download-unknown-circuits-csv')
    };
    
    // Add click handlers to all download buttons
    for (const [dataType, button] of Object.entries(downloadButtons)) {
        if (button) {
            button.addEventListener('click', function() {
                console.log(`Download ${dataType} data requested`);
                storeSelectedParameters(); // Make sure we have the latest parameters
                downloadCSVData(dataType);
            });
        }
    }
    
    // Add a special handler for the "all unknown circuits" button to show loading feedback
    const downloadAllUnknownBtn = document.getElementById('download-all-unknown-circuits');
    if (downloadAllUnknownBtn) {
        downloadAllUnknownBtn.addEventListener('click', function(e) {
            // Don't prevent default - let the link work naturally
            // Just add visual feedback
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Preparing Download...';
            
            // Restore text after 3 seconds
            setTimeout(() => {
                this.innerHTML = originalText;
            }, 3000);
            
            // Show a toast notification
            showToast('Downloading all unknown circuit data...', 'info');
        });
    }
    
    // Store form parameters when form is submitted
    const analysisForm = document.querySelector('form[action*="plot"]');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function() {
            storeSelectedParameters();
        });
    }
    
    // Also store parameters from existing selections if available
    storeSelectedParameters();

    // Add this to your event listeners in the DOMContentLoaded section
    const unknownCircuitsFilterBtn = document.querySelector('.btn-outline-info[href*="unknown_circuits_download"]');
    if (unknownCircuitsFilterBtn) {
        unknownCircuitsFilterBtn.addEventListener('click', function(e) {
            // If we have date ranges in the current analysis, populate them in the filter page
            if (window.selectedFromTime && window.selectedToTime) {
                e.preventDefault();
                const url = new URL(this.href);
                url.searchParams.append('from_time', window.selectedFromTime);
                url.searchParams.append('to_time', window.selectedToTime);
                window.location.href = url.toString();
            }
        });
    }
    
    // Initialize download buttons
    initializeDownloadButtons();
});

/**
 * Initialize download buttons for CSV data
 */
function initializeDownloadButtons() {
    // Map button IDs to data types
    const buttonMap = {
        'download-circuits-csv': 'circuits',
        'download-switches-csv': 'switches',
        'download-short-duration-csv': 'short_duration',
        'download-short-duration-switch-csv': 'short_duration_switches'
    };
    
    // Add click handlers to all download buttons
    for (const [buttonId, dataType] of Object.entries(buttonMap)) {
        const button = document.getElementById(buttonId);
        if (button) {
            button.addEventListener('click', function() {
                console.log(`Download button clicked for ${dataType}`);
                downloadCSVData(dataType);
            });
        }
    }
}

/**
 * Download CSV data for the specified type
 * @param {string} dataType - Type of data to download ('circuits', 'switches', etc.)
 */
function downloadCSVData(dataType) {
    console.log(`Starting download for ${dataType} data`);
    
    // Show loading state on button
    const downloadButton = document.getElementById(`download-${dataType.replace('_', '-')}-csv`);
    if (downloadButton) {
        const originalText = downloadButton.innerHTML;
        downloadButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Downloading...';
        downloadButton.disabled = true;
        
        // Reset button after timeout (as a fallback)
        setTimeout(() => {
            downloadButton.innerHTML = originalText;
            downloadButton.disabled = false;
        }, 10000);
    }

    try {
        // Create a form to submit the download request
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/circuit-switch-analysis/download_csv';
        
        // Add hidden input for data type
        const dataTypeInput = document.createElement('input');
        dataTypeInput.type = 'hidden';
        dataTypeInput.name = 'data_type';
        dataTypeInput.value = dataType;
        form.appendChild(dataTypeInput);
        
        // Add to document, submit form, then remove it
        document.body.appendChild(form);
        console.log(`Submitting form to download ${dataType} data`);
        form.submit();
        
        // Remove form after submission
        setTimeout(() => {
            document.body.removeChild(form);
            
            // Reset button after successful submission
            if (downloadButton) {
                downloadButton.innerHTML = originalText;
                downloadButton.disabled = false;
            }
        }, 1000);
        
        // Show toast notification
        showToast(`Downloading ${dataType.replace('_', ' ')} data...`, 'info');
    } catch (error) {
        console.error('Error during CSV download:', error);
        showToast(`Error downloading data: ${error.message}`, 'danger');
        
        // Reset button on error
        if (downloadButton) {
            downloadButton.innerHTML = originalText;
            downloadButton.disabled = false;
        }
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Create toast container if it doesn't exist
    if (!document.querySelector('.toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${type === 'info' ? 'info-circle' : type === 'success' ? 'check-circle' : 'exclamation-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    // Add toast to container
    document.querySelector('.toast-container').appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        this.remove();
    });
}

/**
 * File Upload Handling
 */
function initializeFileUpload() {
    const uploadForm = document.getElementById('uploadDataForm');
    const uploadBtn = document.getElementById('uploadBtn');
    const resetBtn = document.getElementById('resetToDefault');
    const circuitFileInput = document.getElementById('circuit_file');
    const switchFileInput = document.getElementById('switch_file');
    
    // Skip if elements don't exist
    if (!uploadForm || !uploadBtn) return;
    
    // Update file label when file is selected
    if (circuitFileInput) {
        circuitFileInput.addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'No file selected';
            const fileSize = this.files[0] ? (this.files[0].size / 1024 / 1024).toFixed(2) + ' MB' : '';
            const fileLabel = this.parentElement.querySelector('.form-text');
            fileLabel.innerHTML = `Selected: <strong>${fileName}</strong> ${fileSize}`;
        });
    }
    
    if (switchFileInput) {
        switchFileInput.addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'No file selected';
            const fileSize = this.files[0] ? (this.files[0].size / 1024 / 1024).toFixed(2) + ' MB' : '';
            const fileLabel = this.parentElement.querySelector('.form-text');
            fileLabel.innerHTML = `Selected: <strong>${fileName}</strong> ${fileSize}`;
        });
    }
    
    // Handle form submission with loading state
    if (uploadForm) {
        uploadForm.addEventListener('submit', function() {
            uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i> Uploading...';
            uploadBtn.disabled = true;
        });
    }
    
    // Handle reset button
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            window.location.href = '/circuit-switch-analysis/reset_to_default_data';
        });
    }
}

// Add this to the DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', function() {
    // ...existing code...
    
    // Initialize file upload UI
    initializeFileUpload();
    
    // ...existing code...
});

// ============================================================================
// STATISTICS CALCULATION AND DISPLAY
// ============================================================================

/**
 * Calculate and display analysis statistics
 * This function loads statistics from the backend and displays them
 */
function loadAnalysisStatistics() {
    // Load database stats via AJAX
    fetch('/circuit-switch-analysis/debug_load')
        .then(response => response.json())
        .then(data => {
            const switchCountEl = document.getElementById('switch-count');
            const dateRangeEl = document.getElementById('date-range');
            
            if (switchCountEl) {
                switchCountEl.textContent = data.switch_df_rows || "N/A";
            }
            
            if (dateRangeEl) {
                if (data.circuit_df_rows > 0) {
                    dateRangeEl.textContent = "Full database";
                } else {
                    dateRangeEl.textContent = "N/A";
                }
            }
        })
        .catch(error => {
            console.error('Error fetching database stats:', error);
            const switchCountEl = document.getElementById('switch-count');
            const dateRangeEl = document.getElementById('date-range');
            
            if (switchCountEl) switchCountEl.textContent = "Error";
            if (dateRangeEl) dateRangeEl.textContent = "Error";
        });
}

/**
 * Calculate time duration from selected details
 */
function calculateAnalysisDuration(fromTime, toTime) {
    try {
        const from = new Date(fromTime);
        const to = new Date(toTime);
        const diffHours = Math.round((to - from) / (1000 * 60 * 60) * 10) / 10;
        
        const durationEl = document.getElementById('analysis-duration');
        if (durationEl) {
            durationEl.textContent = diffHours;
        }
    } catch (error) {
        console.error('Error calculating duration:', error);
    }
}

/**
 * Calculate approximate data points
 */
function calculateDataPoints(circuitPlotsCount, switchPlotsCount) {
    const dataPoints = circuitPlotsCount * 120 + switchPlotsCount * 80;
    const dataPointsEl = document.getElementById('data-points');
    
    if (dataPointsEl) {
        dataPointsEl.textContent = dataPoints;
    }
}

// ============================================================================
// RANGE NAVIGATION FUNCTIONS (Global Template)
// ============================================================================

let currentRange = 1;
let totalRanges = 1; // Update dynamically based on data

/**
 * Navigate between data ranges
 */
function navigateRange(direction) {
    if (direction === 'prev' && currentRange > 1) {
        currentRange--;
    } else if (direction === 'next' && currentRange < totalRanges) {
        currentRange++;
    }
    
    updateRangeDisplay();
    loadRangeData(currentRange);
}

/**
 * Update the range display UI
 */
function updateRangeDisplay() {
    const rangeInfoEl = document.getElementById('current-range-info');
    if (rangeInfoEl) {
        rangeInfoEl.textContent = `Range ${currentRange} of ${totalRanges}`;
    }
    
    const prevBtn = document.getElementById('prev-range');
    const nextBtn = document.getElementById('next-range');
    
    if (prevBtn) prevBtn.disabled = currentRange === 1;
    if (nextBtn) nextBtn.disabled = currentRange === totalRanges;
}

/**
 * Load range-specific data
 */
function loadRangeData(range) {
    console.log(`Loading data for range ${range}`);
    // Implement AJAX call to load range-specific data
    // This can be extended based on backend API
}

// ============================================================================
// PLOT DOWNLOAD FUNCTIONS
// ============================================================================

/**
 * Download all plots as images
 */
function downloadAllPlots() {
    const plots = document.querySelectorAll('.plot-container');
    
    if (plots.length === 0) {
        showToast('No plots available to download', 'warning');
        return;
    }
    
    plots.forEach((plot, index) => {
        setTimeout(() => {
            const plotDiv = plot.querySelector('div[id^="circuit-plot"], div[id^="switch-plot"]');
            if (plotDiv && typeof Plotly !== 'undefined') {
                Plotly.downloadImage(plotDiv, {
                    format: 'png',
                    width: 1200,
                    height: 800,
                    filename: `plot_${index + 1}`
                });
            }
        }, index * 500); // Stagger downloads to avoid browser issues
    });
    
    showToast(`Downloading ${plots.length} plots...`, 'info');
}

// ============================================================================
// FORM ENHANCEMENT FUNCTIONS
// ============================================================================

/**
 * Initialize file upload preview functionality
 */
function initFileUploadPreview() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name;
            if (fileName) {
                const label = this.closest('.file-upload');
                if (label) {
                    label.classList.add('has-file');
                    const textEl = label.querySelector('.file-upload-text');
                    if (textEl) {
                        textEl.innerHTML = `<i class="fas fa-check-circle"></i> ${fileName}`;
                    }
                }
            }
        });
    });
}

/**
 * Initialize form validation
 */
function initFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value || field.value.trim() === '') {
                    isValid = false;
                    field.classList.add('is-invalid');
                    
                    // Add red border for better visibility
                    field.style.borderColor = '#dc3545';
                } else {
                    field.classList.remove('is-invalid');
                    field.style.borderColor = '';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                showToast('Please fill in all required fields', 'danger');
            }
        });
        
        // Remove invalid state on input
        const requiredFields = form.querySelectorAll('[required]');
        requiredFields.forEach(field => {
            field.addEventListener('input', function() {
                if (this.value && this.value.trim() !== '') {
                    this.classList.remove('is-invalid');
                    this.style.borderColor = '';
                }
            });
        });
    });
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    
    if (typeof bootstrap !== 'undefined') {
        tooltipTriggerList.forEach(function (tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
}

// ============================================================================
// ENHANCED DOM CONTENT LOADED
// ============================================================================

// Extend the existing DOMContentLoaded listener
document.addEventListener('DOMContentLoaded', function() {
    // Load statistics
    loadAnalysisStatistics();
    
    // Initialize file upload preview
    initFileUploadPreview();
    
    // Initialize form validation
    initFormValidation();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize range navigation display
    const rangeInfoEl = document.getElementById('current-range-info');
    if (rangeInfoEl) {
        updateRangeDisplay();
    }
});

