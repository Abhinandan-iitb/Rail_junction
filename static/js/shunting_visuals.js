/**
 * Shunting Visuals JavaScript
 * Handles file upload, data processing, and visualization with default data
 */

class ShuntingVisuals {
    constructor() {
        this.chainSeqData = null;
        this.intervalData = null;
        this.availableNetIds = [];
        this.abortController = null;  // Add abort controller
        this.initializeEventListeners();
        this.addDebugLogging();
        this.loadDefaultData();
        this.initializeCollapsibleSections();
    }

    addDebugLogging() {
        // Debug console is hidden from users - only log to browser console
        this.debugLog('Shunting Visuals initialized...');
    }

    debugLog(message) {
        // Only log to browser console, not visible debug console
        console.log(`[ShuntingVisuals] ${message}`);
    }

    initializeEventListeners() {
        // File upload button
        document.getElementById('uploadBtn').addEventListener('click', (e) => {
            e.preventDefault();
            this.handleFileUpload();
        });

        // Load default data button
        document.getElementById('loadDefaultBtn').addEventListener('click', () => {
            this.debugLog('Load Default Data button clicked!');
            this.loadDefaultDataManually();
        });

        // Generate plot button
        document.getElementById('generatePlotBtn').addEventListener('click', () => {
            this.generatePlot();
        });

        // Download plot button
        document.getElementById('downloadPlotBtn').addEventListener('click', () => {
            this.downloadPlot();
        });

        // Remove Fullscreen button event listener

        // Net ID input enter key
        document.getElementById('netIdInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.generatePlot();
            }
        });
    }

    async handleFileUpload() {
        const chainSeqFile = document.getElementById('chainSeqFile').files[0];
        const intervalFile = document.getElementById('intervalFile').files[0];

        if (!chainSeqFile || !intervalFile) {
            this.showAlert('Please select both CSV files', 'warning');
            this.debugLog('File upload: Missing files');
            return;
        }

        // Show loading
        this.showUploadStatus(true);
        this.debugLog('File upload: Starting upload process...');
        
        try {
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('chainSeqFile', chainSeqFile);
            formData.append('intervalFile', intervalFile);
            
            this.debugLog('File upload: Files prepared, sending to server...');
            
            // Send files to backend
            const response = await fetch('/shunting-visuals/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            this.debugLog(`File upload: Server response: ${result.status}`);

            if (result.status === 'success') {
                // Store the uploaded data
                this.chainSeqData = result.data.chain_seq;
                this.intervalData = result.data.interval;
                this.availableNetIds = result.available_net_ids || [];

                this.debugLog(`File upload: Data processed - Chains: ${this.chainSeqData.length}, Intervals: ${this.intervalData.length}`);

                // Update available networks list
                this.updateAvailableNetworksList();

                // Show analysis section
                this.showAnalysisSection();
                
                // Show only data summary (not raw data)
                this.showDataSummary('uploaded', result.summary);
                
                this.showAlert('Files uploaded and processed successfully!', 'success');
                
            } else {
                this.debugLog(`File upload: Error - ${result.message}`);
                this.showAlert('Error processing files: ' + result.message, 'danger');
            }
            
        } catch (error) {
            this.debugLog(`File upload: Exception - ${error.message}`);
            console.error('Error processing files:', error);
            this.showAlert('Error processing files: ' + error.message, 'danger');
        } finally {
            this.showUploadStatus(false);
        }
    }

    parseCSV(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const csv = e.target.result;
                    const lines = csv.split('\n');
                    const headers = lines[0].split(',').map(h => h.trim());
                    
                    const data = [];
                    for (let i = 1; i < lines.length; i++) {
                        if (lines[i].trim()) {
                            const values = lines[i].split(',').map(v => v.trim());
                            const row = {};
                            headers.forEach((header, index) => {
                                row[header] = values[index] || '';
                            });
                            data.push(row);
                        }
                    }
                    resolve(data);
                } catch (error) {
                    reject(error);
                }
            };
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    processTimestamps() {
        // Convert timestamp strings to Date objects
        this.intervalData.forEach(row => {
            if (row.Down_timestamp) {
                row.Down_timestamp = new Date(row.Down_timestamp);
            }
            if (row.Up_timestamp) {
                row.Up_timestamp = new Date(row.Up_timestamp);
            }
        });
    }

    extractAvailableNetIds() {
        const netIds = [...new Set(this.chainSeqData.map(row => parseInt(row.Net_id)))];
        this.availableNetIds = netIds.filter(id => !isNaN(id)).sort((a, b) => a - b);
        
        // Display available Net IDs
        this.displayAvailableNetIds();
    }

    updateAvailableNetworksList() {
        const availableNetworksElement = document.getElementById('availableNetworksList');
        if (availableNetworksElement && this.availableNetIds.length > 0) {
            availableNetworksElement.textContent = this.availableNetIds.join(', ');
        }
        
        // Remove this line - no longer updating visual display
        // this.displayAvailableNetIds();
    }

    async generatePlot() {
        const netId = document.getElementById('netIdInput').value;
        const spacing = 20; // Fixed spacing value

        if (!netId) {
            this.showAlert('Please enter a Network ID', 'warning');
            return;
        }

        if (!this.chainSeqData || !this.intervalData) {
            this.showAlert('No data available. Please load data first.', 'warning');
            return;
        }

        // Show loading
        this.showPlotLoading(true);

        // Prepare data for the API
        const requestData = {
            net_id: parseInt(netId),
            spacing: spacing,
            chain_seq_data: this.chainSeqData,
            interval_data: this.intervalData
        };

        // Cancel previous request if exists
        if (this.abortController) {
            this.abortController.abort();
        }
        this.abortController = new AbortController();
        
        try {
            const response = await fetch('/shunting-visuals/api/generate-plot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData),
                signal: this.abortController.signal  // Add signal
            });
            
            const result = await response.json();
            if (result.status === 'success') {
                this.renderPlot(result.plot_data);
                this.showStatistics(result.statistics);
                this.showAlert(`Timeline plot generated for Network ID ${netId}!`, 'success');
            } else {
                this.showAlert('Error generating plot: ' + result.message, 'danger');
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request cancelled');
                return;
            }
            console.error('Error generating plot:', error);
            this.showAlert('Error generating plot: ' + error.message, 'danger');
        } finally {
            this.showPlotLoading(false);
        }
    }

    showPlotLoading(show) {
        const plotContainer = document.getElementById('plotContainer');
        const plotControls = document.getElementById('plotControls');
        const generateBtn = document.getElementById('generatePlotBtn');
        
        if (show) {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating Plot...';
            plotContainer.style.display = 'none';
            plotControls.style.display = 'none';
        } else {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-chart-line me-2"></i>Generate Timeline Plot';
        }
    }

    renderPlot(plotData) {
        if (!plotData || plotData.length === 0) {
            this.showAlert('No plot data to render', 'warning');
            return;
        }

        const plotContainer = document.getElementById('plotContainer');
        const plotControls = document.getElementById('plotControls');
        
        plotContainer.style.display = 'block';
        plotControls.style.display = 'block';

        // Extract data for plotting
        const netId = plotData[0]?.Net_id || 'Unknown';
        const totalIntervals = plotData.length;
        const spacing = 20;
        const dynamicHeight = Math.max(600, (totalIntervals + 2) * spacing);
        
        // Color palette for different chains
        const colors = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ];

        const traces = [];
        const chainIds = [...new Set(plotData.map(row => row.Chain_id))];
        
        chainIds.forEach((chainId, colorIndex) => {
            const chainData = plotData.filter(row => row.Chain_id === chainId);
            const color = colors[colorIndex % colors.length];
            
            chainData.forEach((row, index) => {
                const downTime = new Date(row.Down_timestamp);
                const upTime = new Date(row.Up_timestamp);
                
                const hoverText = [
                    `Interval: ${row.Interval_id}`,
                    `Circuit: ${row.Circuit_Name || 'N/A'}`,
                    `Chain ID: ${row.Chain_id}`,
                    `Net ID: ${row.Net_id}`,
                    `Down Time: ${downTime.toLocaleString()}`,
                    `Up Time: ${upTime.toLocaleString()}`,
                    `Duration: ${this.formatDuration(row.Duration)}`
                ].join('<br>');

                // Interval line
                traces.push({
                    x: [downTime, upTime],
                    y: [row.Row, row.Row],
                    mode: 'lines+markers',
                    line: { color: color, width: 3 },
                    marker: { size: 6 },
                    hovertext: hoverText,
                    hoverinfo: 'text',
                    name: `Chain ${chainId}`,
                    showlegend: index === 0,
                    legendgroup: `chain_${chainId}`
                });

                // Interval label
                const midTime = new Date((downTime.getTime() + upTime.getTime()) / 2);
                traces.push({
                    x: [midTime],
                    y: [row.Row + (spacing * 0.2)],
                    mode: 'text',
                    text: [row.Interval_id],
                    textposition: 'top center',
                    textfont: { size: 10, color: color },
                    showlegend: false,
                    hoverinfo: 'skip'
                });
            });
        });

        const layout = {
            height: dynamicHeight,
            title: {
                text: `Shunting Timeline for Network ID ${netId}`,
                font: { size: 18, color: '#2c3e50' }
            },
            xaxis: {
                title: 'Date & Time',
                showgrid: true,
                gridcolor: 'lightgray',
                tickformat: '%Y-%m-%d %H:%M',
                rangeslider: { visible: true },
                rangeselector: {
                    buttons: [
                        { count: 1, label: '1h', step: 'hour', stepmode: 'backward' },
                        { count: 6, label: '6h', step: 'hour', stepmode: 'backward' },
                        { count: 1, label: '1d', step: 'day', stepmode: 'backward' },
                        { step: 'all' }
                    ]
                }
            },
            yaxis: {
                title: '',
                range: [0, (totalIntervals + 1) * spacing],
                showgrid: true,
                dtick: spacing,
                gridcolor: 'lightgray',
                zeroline: false,
                showticklabels: false
            },
            plot_bgcolor: 'white',
            paper_bgcolor: 'white',
            legend: {
                orientation: 'h',
                yanchor: 'bottom',
                y: 1.02,
                xanchor: 'center',
                x: 0.5
            },
            margin: { l: 50, r: 50, t: 100, b: 50 },
            
            // Explicitly set individual hover mode (shows one interval at a time)
            hovermode: 'closest'  // Individual hover - NOT unified
        };

        // Simplified plot configuration - focused on plotting only
        const config = {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: [
                'autoScale2d', 
                'lasso2d', 
                'select2d',
                'toggleSpikelines',
                'hoverCompareCartesian',
                'hoverClosestCartesian',
                'zoom2d',
                'pan2d',
                'zoomIn2d',
                'zoomOut2d',
                'autoScale2d',
                'resetScale2d'
            ],
            displaylogo: false,
            modeBarButtonsToAdd: [],
            toImageButtonOptions: {
                format: 'png',
                filename: `railway_shunting_timeline_net_${netId}`,
                height: dynamicHeight,
                width: 1400,
                scale: 2
            },
            // Remove fullscreen and other interactive features
            scrollZoom: false,
            doubleClick: 'reset',
            showTips: false
        };

        Plotly.newPlot('plotContainer', traces, layout, config);
    }

    showStatistics(statistics) {
        const statisticsContainer = document.getElementById('statisticsContainer');
        
        if (!statistics || Object.keys(statistics).length === 0) {
            statisticsContainer.style.display = 'none';
            return;
        }

        statisticsContainer.style.display = 'block';
        
        // Update statistics
        document.getElementById('totalChains').textContent = statistics.total_chains || '-';
        document.getElementById('totalIntervals').textContent = statistics.total_intervals || '-';
        document.getElementById('avgDuration').textContent = statistics.avg_duration || '-';
    }

    mergeIntervalData(orderList) {
        const merged = [];
        
        orderList.forEach(orderRow => {
            const intervalRow = this.intervalData.find(row => 
                row.Interval_id && row.Interval_id.trim() === orderRow.Interval_id
            );
            
            if (intervalRow) {
                merged.push({
                    ...orderRow,
                    ...intervalRow,
                    Down_timestamp: intervalRow.Down_timestamp,
                    Up_timestamp: intervalRow.Up_timestamp
                });
            }
        });
        
        return merged;
    }

    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    downloadPlot() {
        const plotElement = document.getElementById('plotContainer');
        if (plotElement) {
            Plotly.downloadImage(plotElement, {
                format: 'png',
                width: 1200,
                height: 800,
                filename: 'shunting_timeline'
            });
        }
    }

    showAnalysisSection() {
        document.getElementById('analysisSection').style.display = 'block';
        document.getElementById('analysisSection').classList.add('fade-in-up');
    }

    showDataSummary(dataType, summaryData = null) {
        const summarySection = document.getElementById('dataSummary');
        
        this.debugLog(`Displaying dataset summary - Source: ${dataType}`);
        
        if (!summarySection) {
            this.debugLog('ERROR: Data summary section not found in DOM');
            return;
        }
        
        const summaryChains = document.getElementById('summaryChains');
        const summaryIntervals = document.getElementById('summaryIntervals');
        const summaryNetIds = document.getElementById('summaryNetIds');
        const summaryNetList = document.getElementById('summaryNetList');
        const summarySource = document.getElementById('summarySource');
        const summaryTimeRange = document.getElementById('summaryTimeRange');
        
        // Show the summary section
        summarySection.style.display = 'block';
        
        // Update statistics using backend summary data if available
        if (summaryData) {
            const chains = summaryData.chain_seq_records || summaryData.chain_seq_count || this.chainSeqData?.length || 0;
            const intervals = summaryData.interval_records || summaryData.interval_count || this.intervalData?.length || 0;
            const netCount = summaryData.net_ids?.length || this.availableNetIds.length || 0;
            const netList = (summaryData.net_ids || this.availableNetIds).join(', ') || 'None';
            
            if (summaryChains) summaryChains.textContent = chains;
            if (summaryIntervals) summaryIntervals.textContent = intervals;
            if (summaryNetIds) summaryNetIds.textContent = netCount;
            if (summaryNetList) summaryNetList.textContent = netList;
            
            // Handle time range from backend
            if (summaryData.time_range && summaryTimeRange) {
                if (summaryData.time_range.start && summaryData.time_range.end) {
                    const startDate = new Date(summaryData.time_range.start);
                    const endDate = new Date(summaryData.time_range.end);
                    const diffDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
                    summaryTimeRange.textContent = `${diffDays} days`;
                } else {
                    summaryTimeRange.textContent = 'Available';
                }
            } else if (summaryTimeRange) {
                summaryTimeRange.textContent = 'N/A';
            }
        } else {
            // Fallback to local calculation
            const chains = this.chainSeqData?.length || 0;
            const intervals = this.intervalData?.length || 0;
            const netCount = this.availableNetIds.length || 0;
            const netList = this.availableNetIds.join(', ') || 'None';
            
            if (summaryChains) summaryChains.textContent = chains;
            if (summaryIntervals) summaryIntervals.textContent = intervals;
            if (summaryNetIds) summaryNetIds.textContent = netCount;
            if (summaryNetList) summaryNetList.textContent = netList;
        }
        
        // Set source
        if (summarySource) {
            summarySource.textContent = dataType === 'default' ? 'Default CSV Files' : 'User Upload';
        }
        
        this.debugLog('Dataset summary displayed successfully');
    }

    showUploadStatus(show) {
        const status = document.getElementById('uploadStatus');
        const button = document.getElementById('uploadBtn');
        
        if (show) {
            status.style.display = 'block';
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
        } else {
            status.style.display = 'none';
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-upload me-2"></i>Upload Files';
        }
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert alert - try uploadForm first, fallback to uploadSection
        const uploadForm = document.getElementById('uploadForm');
        const uploadSection = document.querySelector('.upload-section');
        
        if (uploadForm && uploadForm.parentNode) {
            uploadForm.parentNode.insertBefore(alert, uploadForm.nextSibling);
        } else if (uploadSection) {
            uploadSection.insertBefore(alert, uploadSection.firstChild);
        } else {
            // Last resort - prepend to content wrapper
            const contentWrapper = document.querySelector('.content-wrapper .container-fluid');
            if (contentWrapper) {
                contentWrapper.insertBefore(alert, contentWrapper.firstChild);
            }
        }

        // Auto dismiss after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    async loadDefaultDataManually() {
        try {
            // Show loading status
            this.showDefaultLoadingStatus(true);
            this.debugLog('Manual load: Starting to load default data...');
            
            // Call the same API endpoint as automatic loading
            const response = await fetch('/shunting-visuals/api/data');
            this.debugLog(`Manual load: API response status: ${response.status}`);
            
            const result = await response.json();
            this.debugLog(`Manual load: API response: ${JSON.stringify(result.status)}`);
            
            if (result.status === 'success') {
                // Store the data
                this.chainSeqData = result.data.chain_seq;
                this.intervalData = result.data.interval;
                this.availableNetIds = result.available_net_ids || [];
                
                this.debugLog(`Manual load: Data stored successfully`);
                this.debugLog(`Manual load: Chains: ${this.chainSeqData.length}, Intervals: ${this.intervalData.length}`);
                this.debugLog(`Manual load: Net IDs: [${this.availableNetIds.join(', ')}]`);
                
                // Update available networks list
                this.updateAvailableNetworksList();
                
                // Show analysis section
                this.showAnalysisSection();
                
                // Show only data summary (not raw data)
                this.showDataSummary('default', result.summary);
                
                this.showAlert('Default railway shunting data loaded successfully! Ready to analyze shunting patterns.', 'success');
                
                this.debugLog('Manual load: Complete - summary shown');
                
            } else {
                this.debugLog(`Manual load: Error - ${result.message}`);
                this.showAlert('Failed to load default data: ' + result.message, 'danger');
            }
            
        } catch (error) {
            this.debugLog(`Manual load: Exception - ${error.message}`);
            console.error('Error loading default data manually:', error);
            this.showAlert('Failed to load default data: ' + error.message, 'danger');
        } finally {
            this.showDefaultLoadingStatus(false);
        }
    }

    showDefaultLoadingStatus(show) {
        const button = document.getElementById('loadDefaultBtn');
        
        if (show) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading Default Data...';
        } else {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-database me-2"></i>Load Default Data';
        }
    }

    parseCSVString(csvString) {
        const lines = csvString.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim());
        
        const data = [];
        for (let i = 1; i < lines.length; i++) {
            if (lines[i].trim()) {
                const values = lines[i].split(',').map(v => v.trim());
                const row = {};
                headers.forEach((header, index) => {
                    row[header] = values[index] || '';
                });
                data.push(row);
            }
        }
        return data;
    }

    async loadDefaultData() {
        try {
            this.debugLog('Starting to load default railway data...');
            
            // Call backend API to get default data
            const response = await fetch('/shunting-visuals/api/data');
            this.debugLog(`API response status: ${response.status}`);
            
            const result = await response.json();
            this.debugLog(`API response received - Status: ${result.status}`);
            
            if (result.status === 'success') {
                this.chainSeqData = result.data.chain_seq;
                this.intervalData = result.data.interval;
                this.availableNetIds = result.available_net_ids || [];
                
                this.debugLog(`Data loaded successfully:`);
                this.debugLog(`- Chain sequences: ${this.chainSeqData.length} records`);
                this.debugLog(`- Circuit intervals: ${this.intervalData.length} records`);
                this.debugLog(`- Available Net IDs: [${this.availableNetIds.join(', ')}]`);
                
                // Update available networks list
                this.updateAvailableNetworksList();
                
                // Show analysis section
                this.showAnalysisSection();
                
                // Show data summary
                this.showDataSummary('default', result.summary);
                
                this.showAlert('Default railway shunting data loaded successfully! Ready to analyze shunting patterns.', 'success');
                
            } else {
                this.debugLog(`Error loading data: ${result.message}`);
                console.error('Failed to load default data:', result);
                throw new Error(result.message || 'Failed to load data');
            }
            
        } catch (error) {
            this.debugLog(`Exception during data loading: ${error.message}`);
            console.error('Error loading default data:', error);
            this.showAlert('Failed to load default data: ' + error.message, 'danger');
        }
    }

    initializeCollapsibleSections() {
        // Initialize collapse functionality for professional UI
        const collapseElements = document.querySelectorAll('[data-bs-toggle="collapse"]');
        
        collapseElements.forEach(element => {
            element.addEventListener('click', function() {
                const target = document.querySelector(this.getAttribute('data-bs-target'));
                const icon = this.querySelector('.collapse-icon');
                
                if (target && icon) {
                    // Add smooth transition
                    setTimeout(() => {
                        if (target.classList.contains('show')) {
                            icon.style.transform = 'rotate(0deg)';
                            this.setAttribute('aria-expanded', 'false');
                        } else {
                            icon.style.transform = 'rotate(180deg)';
                            this.setAttribute('aria-expanded', 'true');
                        }
                    }, 50);
                }
            });
        });
        
        // Set initial states
        document.querySelectorAll('.collapse.show').forEach(element => {
            const trigger = document.querySelector(`[data-bs-target="#${element.id}"]`);
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'true');
                const icon = trigger.querySelector('.collapse-icon');
                if (icon) {
                    icon.style.transform = 'rotate(180deg)';
                }
            }
        });
    }
}

// Initialize when DOM is loaded - Single initialization point
document.addEventListener('DOMContentLoaded', function() {
    try {
        const shuntingVisuals = new ShuntingVisuals();
        console.log('Shunting Visuals application initialized successfully');
    } catch (error) {
        console.error('Error initializing Shunting Visuals:', error);
    }
});