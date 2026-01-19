/**
 * Toggle visibility of sample data containers
 * @param {string} containerId - ID of the container to toggle
 */
function toggleSampleData(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        if (container.style.display === 'block') {
            container.style.display = 'none';
        } else {
            container.style.display = 'block';
        }
    }
}

/**
 * Railway Data Visuals - JavaScript
 * Handles data analysis, file uploads, and displaying results
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Railway Data Visuals module loaded");
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // DOM Elements
    const fileUploadForm = document.getElementById('fileUploadForm');
    const mainFile = document.getElementById('mainFile');
    const jsonFile = document.getElementById('jsonFile');
    const uploadBtn = document.getElementById('uploadBtn');
    const useDefaultBtn = document.getElementById('useDefaultBtn');
    const uploadStatus = document.getElementById('uploadStatus');
    const dataSummarySection = document.getElementById('dataSummarySection');
    const mainDataSummary = document.getElementById('mainDataSummary');
    const jsonDataSummary = document.getElementById('jsonDataSummary');
    const analysisOptionsSection = document.getElementById('analysisOptionsSection');
    const jumpToAnalysis = document.getElementById('jumpToAnalysis');
    const jumpToBtn = document.getElementById('jumpToBtn');
    
    // Initialize all analysis sections immediately (don't wait for data upload)
    setupDirectAnalysisButtons();
    setupJumpToAnalysis();
    
    // Track the current state
    let filesUploaded = false;
    let currentResults = null;
    let usingDefaultData = false;
    
    // Add highlight to file upload section initially
    const fileUploadCard = document.querySelector('#fileUploadForm').closest('.card');
    if (fileUploadCard) {
        fileUploadCard.classList.add('no-data-highlight');
    }

    // Event Listeners
    if (fileUploadForm) {
        fileUploadForm.addEventListener('submit', handleFileUpload);
    }
    
    // Add event listener for the "Use Default Data" button
    if (useDefaultBtn) {
        useDefaultBtn.addEventListener('click', handleUseDefaultData);
    }
    
    // Add event listeners for export buttons
    document.querySelectorAll('.export-btn').forEach(button => {
        button.addEventListener('click', function() {
            const sectionId = this.getAttribute('data-section');
            exportSectionResults(sectionId);
        });
    });

    /**
     * Handle file upload form submission
     */
    function handleFileUpload(event) {
        event.preventDefault();
        
        // Check if required files are selected
        if (!mainFile.files.length || !jsonFile.files.length) {
            showUploadStatus('error', 'Please select both Main Dataset, Chain Dataset and  Start-End Data (CSV) files');
            return;
        }
        
        // Create FormData
        const formData = new FormData();
        formData.append('main_file', mainFile.files[0]);
        formData.append('json_file', jsonFile.files[0]);
        
        // Add start-end file if selected
        const startEndFile = document.getElementById('startEndFile');
        if (startEndFile && startEndFile.files.length) {
            formData.append('start_end_file', startEndFile.files[0]);
        }
        
        // Show loading status
        showUploadStatus('loading', 'Uploading and processing files...');
        
        // Disable upload button during upload
        uploadBtn.disabled = true;
        
        // Upload files
        fetch('/railway-data-visuals/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Re-enable upload button
            uploadBtn.disabled = false;
            
            if (data.status === 'success') {
                // Show success message
                showUploadStatus('success', 'Files uploaded and processed successfully!');
                
                // Update UI based on data summary
                if (data.data_summary) {
                    displayDataSummary(data.data_summary);
                }
                
                // Show analysis options
                showAnalysisSection();
                
                // Remove highlight from file upload section
                const fileUploadCard = document.querySelector('#fileUploadForm').closest('.card');
                if (fileUploadCard) {
                    fileUploadCard.classList.remove('no-data-highlight');
                }
            } else {
                // Show error message
                showUploadStatus('error', data.message || 'Error processing files');
            }
        })
        .catch(error => {
            // Re-enable upload button
            uploadBtn.disabled = false;
            
            // Show error message
            showUploadStatus('error', 'Error uploading files: ' + error.message);
            console.error('Upload error:', error);
        });
    }
    
    /**
     * Show upload status message
     */
    function showUploadStatus(type, message) {
        let alertClass = '';
        let icon = '';
        
        switch (type) {
            case 'success':
                alertClass = 'alert-success';
                icon = 'fa-check-circle';
                break;
            case 'warning':
                alertClass = 'alert-warning';
                icon = 'fa-exclamation-triangle';
                break;
            case 'error':
                alertClass = 'alert-danger';
                icon = 'fa-exclamation-circle';
                break;
            case 'loading':
                alertClass = 'alert-info';
                icon = 'fa-spinner fa-spin';
                break;
            case 'default':
                alertClass = 'alert-secondary';
                icon = 'fa-database';
                break;
            default:
                alertClass = 'alert-info';
                icon = 'fa-info-circle';
        }
        
        uploadStatus.innerHTML = `
            <div class="alert ${alertClass}">
                <i class="fas ${icon} me-2"></i>${message}
            </div>
        `;
    }
    
    /**
     * Display data summary
     */
    function displayDataSummary(summary) {
        if (!summary) return;
        
        // Show data summary section
        const dataSummarySection = document.getElementById('dataSummarySection');
        if (dataSummarySection) {
            dataSummarySection.style.display = 'block';
        }
        
        // Display the shunting summary
        displayShuntingSummary(summary);
    }
    
    // New function to display shunting summary
    function displayShuntingSummary(summary) {
        // Get the data summary section
        const dataSummarySection = document.getElementById('dataSummarySection');
        if (!dataSummarySection) return;
        
        // Clear previous content
        dataSummarySection.innerHTML = '';
        
        // Create header
        const header = document.createElement('div');
        header.className = 'card mb-4';
        header.innerHTML = `
            <div class="card-header">
                <h5><i class="fas fa-chart-bar me-2"></i>Shunting Data Summary</h5>
            </div>
        `;
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        
        // Check if shunting summary is available
        if (summary && summary.shunting_summary) {
            const shuntingData = summary.shunting_summary;
            
            // Create summary cards
            const summaryRow = document.createElement('div');
            summaryRow.className = 'row mb-4';
            
            // Total records card
            summaryRow.innerHTML = `
                <div class="col-md-4">
                    <div class="card h-100">
                        <div class="card-header bg-primary text-white">
                            Total Shunting Records
                        </div>
                        <div class="card-body d-flex align-items-center justify-content-center">
                            <h3>${shuntingData.total_records}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card h-100">
                        <div class="card-header bg-success text-white">
                            Unique Net-id with Shunting
                        </div>
                        <div class="card-body d-flex align-items-center justify-content-center">
                            <h3>${shuntingData.unique_net_ids.length}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card h-100">
                        <div class="card-header bg-info text-white">
                            Unique Chain-id with Shunting
                        </div>
                        <div class="card-body d-flex align-items-center justify-content-center">
                            <h3>${shuntingData.unique_chain_ids.length}</h3>
                        </div>
                    </div>
                </div>
            `;
            
            cardBody.appendChild(summaryRow);
            
            // Create Net-id to Chain-id mapping table
            if (shuntingData.net_id_to_chain_mapping && Object.keys(shuntingData.net_id_to_chain_mapping).length > 0) {
                const mappingSection = document.createElement('div');
                mappingSection.className = 'mt-4';
                mappingSection.innerHTML = `
                    <h5 class="mb-3">Net-id to Chain-id Mapping (Shunting Records)</h5>
                    <div class="table-responsive">
                        <table class="table table-striped table-hover">
                            <thead>
                                <tr>
                                    <th>Net-id</th>
                                    <th>Associated Chain-id</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${Object.entries(shuntingData.net_id_to_chain_mapping).map(([netId, chains]) => `
                                    <tr>
                                        <td>${netId}</td>
                                        <td>${chains.join(', ')}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
                cardBody.appendChild(mappingSection);
            }
        } else {
            // Display a message if no shunting data is available
            cardBody.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    No shunting data available or shunting status not found in dataset.
                </div>
            `;
        }
        
        // Append card body to header
        header.appendChild(cardBody);
        
        // Append to the summary section
        dataSummarySection.appendChild(header);
        
        // Make sure the section is visible
        dataSummarySection.style.display = 'block';
    }
    
    /**
     * Show analysis sections after data upload
     */
    function showAnalysisSection() {
        // Show data summary section
        if (dataSummarySection) {
            dataSummarySection.style.display = 'block';
        }
        
        // Update UI to reflect that files are now uploaded
        filesUploaded = true;
        
        // Clear any previous "no data" messages in result sections
        document.querySelectorAll('.results-container').forEach(container => {
            if (container.querySelector('.alert-info')) {
                container.innerHTML = '';
            }
        });
    }
    
    // Featured analysis functions have been removed
    
    /**
     * Setup direct analysis buttons for each method
     */
    function setupDirectAnalysisButtons() {
        // Net ID Analysis Buttons
        document.getElementById('getRecordsByNetIdBtn').addEventListener('click', function() {
            runDirectNetIdAnalysis('get_records_by_netid', document.getElementById('getRecordsNetIdInput').value);
        });
        
        document.getElementById('getUniqueChainsByNetIdBtn').addEventListener('click', function() {
            runDirectNetIdAnalysis('get_unique_chains_by_netid', document.getElementById('uniqueChainsNetIdInput').value);
        });
        
        document.getElementById('getUniqueCircuitsByNetIdBtn').addEventListener('click', function() {
            runDirectNetIdAnalysis('get_unique_circuits_by_netid', document.getElementById('uniqueCircuitsNetIdInput').value);
        });
        
        document.getElementById('getChainsByNetIdBtn').addEventListener('click', function() {
            runDirectNetIdAnalysis('get_chains_by_netid', document.getElementById('chainsNetIdInput').value);
        });
        
        // Chain ID Analysis Buttons
        document.getElementById('showStartEndChainBtn').addEventListener('click', function() {
            runDirectChainIdAnalysis('show_start_end_chain', document.getElementById('startEndChainIdInput').value);
        });
        
        document.getElementById('getChainSequenceLengthBtn').addEventListener('click', function() {
            runDirectChainIdAnalysis('get_chain_sequence_length', document.getElementById('chainSequenceLengthIdInput').value);
        });
        
        document.getElementById('getChainCircuitSequenceBtn').addEventListener('click', function() {
            runDirectChainIdAnalysis('get_chain_circuit_sequence', document.getElementById('circuitSequenceChainIdInput').value);
        });
    }
    
    /**
     * Setup jump to analysis dropdown
     */
    function setupJumpToAnalysis() {
        // Handle dropdown change
        jumpToBtn.addEventListener('click', function() {
            const selectedValue = jumpToAnalysis.value;
            if (selectedValue) {
                const element = document.getElementById(selectedValue);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth' });
                    // Highlight the selected section
                    element.classList.add('highlight-section');
                    setTimeout(() => {
                        element.classList.remove('highlight-section');
                    }, 2000);
                }
            }
        });
    }
    
    /**
     * Run direct Net ID analysis from a specific input
     */
    function runDirectNetIdAnalysis(analysisType, netId) {
        // Get the input card for this analysis type
        const buttonMap = {
            'get_records_by_netid': 'getRecordsByNetIdBtn',
            'get_unique_chains_by_netid': 'getUniqueChainsByNetIdBtn',
            'get_unique_circuits_by_netid': 'getUniqueCircuitsByNetIdBtn',
            'get_chains_by_netid': 'getChainsByNetIdBtn'
        };
        
        const buttonId = buttonMap[analysisType];
        const button = document.getElementById(buttonId);
        if (!button) return;
        
        // Find the parent card of this button
        const card = button.closest('.analysis-input-card');
        if (!card) return;
        
        // Check if an inline results container already exists
        let resultsContainer = card.nextElementSibling;
        if (!resultsContainer || !resultsContainer.classList.contains('inline-results-container')) {
            // Create a new results container
            resultsContainer = document.createElement('div');
            resultsContainer.className = 'card mb-4 inline-results-container';
            resultsContainer.id = `inline-${analysisType}-results`;
            
            // Insert after the input card
            if (card.nextElementSibling) {
                card.parentNode.insertBefore(resultsContainer, card.nextElementSibling);
            } else {
                card.parentNode.appendChild(resultsContainer);
            }
        }

        if (!filesUploaded) {
            // Show message about needing to upload data
            resultsContainer.innerHTML = `
                <div class="card-header d-flex justify-content-between align-items-center bg-warning bg-opacity-10">
                    <h5 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Data Required</h5>
                    <button type="button" class="btn-close" aria-label="Close"></button>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>No Data Available:</strong> Please upload the required data files using the "Upload Data Files" section above before running this analysis.
                    </div>
                    <div class="text-center my-3">
                        <button class="btn btn-primary" onclick="document.getElementById('mainFile').scrollIntoView({behavior: 'smooth'})">
                            <i class="fas fa-upload me-2"></i>Go to File Upload
                        </button>
                    </div>
                </div>
            `;
            
            // Add event listener for close button
            const closeBtn = resultsContainer.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    resultsContainer.style.display = 'none';
                });
            }
            
            // Show the results container
            resultsContainer.style.display = 'block';
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            return;
        }
        
        if (!netId) {
            alert('Please enter a Net ID');
            return;
        }
        
        // Show loading in the inline results container
        resultsContainer.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center bg-info bg-opacity-10">
                <h5 class="mb-0"><i class="fas fa-spinner fa-spin me-2"></i>Loading Results</h5>
            </div>
            <div class="card-body text-center">
                <div class="spinner-border text-primary my-4" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Processing ${analysisType.replace(/_/g, ' ')} for Net ID: ${netId}...</p>
            </div>
        `;
        
        // Show the results container
        resultsContainer.style.display = 'block';
        
        // Make API request
        fetch(`/railway-data-visuals/api/net-analysis?analysis_type=${analysisType}&net_id=${netId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show results in the inline container
                    let title;
                    switch(analysisType) {
                        case 'get_records_by_netid': 
                            title = `Records for Net ID: ${netId}`; break;
                        case 'get_unique_chains_by_netid': 
                            title = `Unique Chain IDs for Net ID: ${netId}`; break;
                        case 'get_unique_circuits_by_netid': 
                            title = `Unique Circuit Names for Net ID: ${netId}`; break;
                        case 'get_chains_by_netid': 
                            title = `Chains & Sub-Chains for Net ID: ${netId}`; break;
                        default: 
                            title = `Results for ${analysisType.replace(/_/g, ' ')}`;
                    }
                    
                    resultsContainer.innerHTML = `
                        <div class="card-header d-flex justify-content-between align-items-center bg-light">
                            <h5 class="mb-0"><i class="fas fa-table me-2"></i>${title}</h5>
                            <div>
                                <button class="btn btn-sm btn-outline-secondary export-btn me-2" data-analysis="${analysisType}" data-id="${netId}">
                                    <i class="fas fa-download me-1"></i>Export
                                </button>
                                <button type="button" class="btn-close" aria-label="Close"></button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="results-container table-responsive">
                                ${data.result_html}
                            </div>
                        </div>
                        <div class="card-footer">
                            <small class="text-muted">Found ${data.row_count} records</small>
                        </div>
                    `;
                    
                    // Store current results for export
                    currentResults = {
                        title: data.title || title,
                        html: data.result_html,
                        type: 'net',
                        netId: netId,
                        analysisType: analysisType
                    };
                    
                    // Add event listeners for export and close buttons
                    const exportBtn = resultsContainer.querySelector('.export-btn');
                    if (exportBtn) {
                        exportBtn.addEventListener('click', () => {
                            exportResults(currentResults, `${analysisType}_${netId}`);
                        });
                    }
                    
                    const closeBtn = resultsContainer.querySelector('.btn-close');
                    if (closeBtn) {
                        closeBtn.addEventListener('click', () => {
                            resultsContainer.style.display = 'none';
                        });
                    }
                } else {
                    // Show error
                    resultsContainer.innerHTML = `
                        <div class="card-header d-flex justify-content-between align-items-center bg-danger bg-opacity-10">
                            <h5 class="mb-0"><i class="fas fa-exclamation-circle me-2"></i>Error</h5>
                            <button type="button" class="btn-close" aria-label="Close"></button>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                ${data.message || 'Unknown error occurred'}
                            </div>
                        </div>
                    `;
                    
                    // Add event listener for close button
                    const closeBtn = resultsContainer.querySelector('.btn-close');
                    if (closeBtn) {
                        closeBtn.addEventListener('click', () => {
                            resultsContainer.style.display = 'none';
                        });
                    }
                }
                
                // Scroll to the results container
                resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            })
            .catch(error => {
                // Show error
                resultsContainer.innerHTML = `
                    <div class="card-header d-flex justify-content-between align-items-center bg-danger bg-opacity-10">
                        <h5 class="mb-0"><i class="fas fa-exclamation-circle me-2"></i>Error</h5>
                        <button type="button" class="btn-close" aria-label="Close"></button>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>${error.message}
                        </div>
                    </div>
                `;
                
                // Add event listener for close button
                const closeBtn = resultsContainer.querySelector('.btn-close');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        resultsContainer.style.display = 'none';
                    });
                }
                
                console.error('Analysis error:', error);
            });
    }
    
    /**
     * Run direct Chain ID analysis from a specific input
     */
    function runDirectChainIdAnalysis(analysisType, chainId) {
        // Get the input card for this analysis type
        const buttonMap = {
            'show_start_end_chain': 'showStartEndChainBtn',
            'get_chain_sequence_length': 'getChainSequenceLengthBtn',
            'get_chain_circuit_sequence': 'getChainCircuitSequenceBtn'
        };
        
        const buttonId = buttonMap[analysisType];
        const button = document.getElementById(buttonId);
        if (!button) return;
        
        // Find the parent card of this button
        const card = button.closest('.analysis-input-card');
        if (!card) return;
        
        // Check if an inline results container already exists
        let resultsContainer = card.nextElementSibling;
        if (!resultsContainer || !resultsContainer.classList.contains('inline-results-container')) {
            // Create a new results container
            resultsContainer = document.createElement('div');
            resultsContainer.className = 'card mb-4 inline-results-container';
            resultsContainer.id = `inline-${analysisType}-results`;
            
            // Insert after the input card
            if (card.nextElementSibling) {
                card.parentNode.insertBefore(resultsContainer, card.nextElementSibling);
            } else {
                card.parentNode.appendChild(resultsContainer);
            }
        }
        
        if (!filesUploaded) {
            // Show message about needing to upload data
            resultsContainer.innerHTML = `
                <div class="card-header d-flex justify-content-between align-items-center bg-warning bg-opacity-10">
                    <h5 class="mb-0"><i class="fas fa-exclamation-triangle me-2"></i>Data Required</h5>
                    <button type="button" class="btn-close" aria-label="Close"></button>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>No Data Available:</strong> Please upload the required data files using the "Upload Data Files" section above before running this analysis.
                    </div>
                    <div class="text-center my-3">
                        <button class="btn btn-primary" onclick="document.getElementById('mainFile').scrollIntoView({behavior: 'smooth'})">
                            <i class="fas fa-upload me-2"></i>Go to File Upload
                        </button>
                    </div>
                </div>
            `;
            
            // Add event listener for close button
            const closeBtn = resultsContainer.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    resultsContainer.style.display = 'none';
                });
            }
            
            // Show the results container
            resultsContainer.style.display = 'block';
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            return;
        }
        
        if (!chainId) {
            alert('Please enter a Chain ID');
            return;
        }
        
        // Show loading in the inline results container
        resultsContainer.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center bg-info bg-opacity-10">
                <h5 class="mb-0"><i class="fas fa-spinner fa-spin me-2"></i>Loading Results</h5>
            </div>
            <div class="card-body text-center">
                <div class="spinner-border text-primary my-4" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">Processing ${analysisType.replace(/_/g, ' ')} for Chain ID: ${chainId}...</p>
            </div>
        `;
        
        // Show the results container
        resultsContainer.style.display = 'block';
        
        // Make API request
        fetch(`/railway-data-visuals/api/net-analysis?analysis_type=${analysisType}&chain_id=${chainId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Show results in the inline container
                    let title;
                    switch(analysisType) {
                        case 'show_start_end_chain': 
                            title = `Start-End of Chain ID: ${chainId}`; break;
                        case 'get_chain_sequence_length': 
                            title = `Sequence Length for Chain ID: ${chainId}`; break;
                        case 'get_chain_circuit_sequence': 
                            title = `Circuit Sequence for Chain ID: ${chainId}`; break;
                        default: 
                            title = `Results for ${analysisType.replace(/_/g, ' ')}`;
                    }
                    
                    resultsContainer.innerHTML = `
                        <div class="card-header d-flex justify-content-between align-items-center bg-light">
                            <h5 class="mb-0"><i class="fas fa-table me-2"></i>${title}</h5>
                            <div>
                                <button class="btn btn-sm btn-outline-secondary export-btn me-2" data-analysis="${analysisType}" data-id="${chainId}">
                                    <i class="fas fa-download me-1"></i>Export
                                </button>
                                <button type="button" class="btn-close" aria-label="Close"></button>
                            </div>
                        </div>
                        <div class="card-body">
                            <div class="results-container table-responsive">
                                ${data.result_html}
                            </div>
                        </div>
                        <div class="card-footer">
                            <small class="text-muted">Found ${data.row_count} records</small>
                        </div>
                    `;
                    
                    // Store current results for export
                    currentResults = {
                        title: data.title || title,
                        html: data.result_html,
                        type: 'chain',
                        chainId: chainId,
                        analysisType: analysisType
                    };
                    
                    // Add event listeners for export and close buttons
                    const exportBtn = resultsContainer.querySelector('.export-btn');
                    if (exportBtn) {
                        exportBtn.addEventListener('click', () => {
                            exportResults(currentResults, `${analysisType}_${chainId}`);
                        });
                    }
                    
                    const closeBtn = resultsContainer.querySelector('.btn-close');
                    if (closeBtn) {
                        closeBtn.addEventListener('click', () => {
                            resultsContainer.style.display = 'none';
                        });
                    }
                } else {
                    // Show error
                    resultsContainer.innerHTML = `
                        <div class="card-header d-flex justify-content-between align-items-center bg-danger bg-opacity-10">
                            <h5 class="mb-0"><i class="fas fa-exclamation-circle me-2"></i>Error</h5>
                            <button type="button" class="btn-close" aria-label="Close"></button>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-danger">
                                ${data.message || 'Unknown error occurred'}
                            </div>
                        </div>
                    `;
                    
                    // Add event listener for close button
                    const closeBtn = resultsContainer.querySelector('.btn-close');
                    if (closeBtn) {
                        closeBtn.addEventListener('click', () => {
                            resultsContainer.style.display = 'none';
                        });
                    }
                }
                
                // Scroll to the results container
                resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            })
            .catch(error => {
                // Show error
                resultsContainer.innerHTML = `
                    <div class="card-header d-flex justify-content-between align-items-center bg-danger bg-opacity-10">
                        <h5 class="mb-0"><i class="fas fa-exclamation-circle me-2"></i>Error</h5>
                        <button type="button" class="btn-close" aria-label="Close"></button>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>${error.message}
                        </div>
                    </div>
                `;
                
                // Add event listener for close button
                const closeBtn = resultsContainer.querySelector('.btn-close');
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        resultsContainer.style.display = 'none';
                    });
                }
                
                console.error('Analysis error:', error);
            });
    }

    /**
     * Show loading state in appropriate result section
     */
    function showLoadingInSection(analysisType, id) {
        // Map analysis type to section ID
        const sectionMap = {
            'get_records_by_netid': 'getRecordsByNetIdSection',
            'get_unique_chains_by_netid': 'getUniqueChainsByNetIdSection',
            'get_unique_circuits_by_netid': 'getUniqueCircuitsByNetIdSection',
            'get_chains_by_netid': 'getChainsByNetIdSection',
            'show_start_end_chain': 'showStartEndChainSection',
            'get_chain_sequence_length': 'getChainSequenceLengthSection',
            'get_chain_circuit_sequence': 'getChainCircuitSequenceSection'
        };
        
        // Get the section ID
        const sectionId = sectionMap[analysisType];
        
        if (sectionId) {
            // Show the section
            const section = document.getElementById(sectionId);
            if (section) {
                section.style.display = 'block';
                
                // Get the results container
                const resultsContainer = section.querySelector('.results-container');
                if (resultsContainer) {
                    // Show loading indicator
                    resultsContainer.innerHTML = `
                        <div class="d-flex justify-content-center align-items-center p-5">
                            <div class="spinner-border text-primary" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <span class="ms-3">Loading results...</span>
                        </div>
                    `;
                }
                
                // Update info text
                const infoElement = section.querySelector('.results-info');
                if (infoElement) {
                    infoElement.textContent = `Processing ${analysisType.replace(/_/g, ' ')} for ID: ${id}...`;
                }
                
                // Scroll to the section
                section.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }
    
    /**
     * Display results in appropriate section
     */
    function displayResultsInSection(analysisType, data, id) {
        // Map analysis type to section ID and results container ID
        const sectionMap = {
            'get_records_by_netid': {
                section: 'getRecordsByNetIdSection',
                container: 'getRecordsByNetIdResults',
                info: 'getRecordsByNetIdInfo'
            },
            'get_unique_chains_by_netid': {
                section: 'getUniqueChainsByNetIdSection',
                container: 'getUniqueChainsByNetIdResults',
                info: 'getUniqueChainsByNetIdInfo'
            },
            'get_unique_circuits_by_netid': {
                section: 'getUniqueCircuitsByNetIdSection',
                container: 'getUniqueCircuitsByNetIdResults',
                info: 'getUniqueCircuitsByNetIdInfo'
            },
            'get_chains_by_netid': {
                section: 'getChainsByNetIdSection',
                container: 'getChainsByNetIdResults',
                info: 'getChainsByNetIdInfo'
            },
            'show_start_end_chain': {
                section: 'showStartEndChainSection',
                container: 'showStartEndChainResults',
                info: 'showStartEndChainInfo'
            },
            'get_chain_sequence_length': {
                section: 'getChainSequenceLengthSection',
                container: 'getChainSequenceLengthResults',
                info: 'getChainSequenceLengthInfo'
            },
            'get_chain_circuit_sequence': {
                section: 'getChainCircuitSequenceSection',
                container: 'getChainCircuitSequenceResults',
                info: 'getChainCircuitSequenceInfo'
            }
        };
        
        const mapping = sectionMap[analysisType];
        
        if (mapping) {
            // Get the section
            const section = document.getElementById(mapping.section);
            if (section) {
                // Ensure section is visible
                section.style.display = 'block';
                
                // Get the results container
                const resultsContainer = document.getElementById(mapping.container);
                if (resultsContainer) {
                    // Display results
                    resultsContainer.innerHTML = data.result_html;
                }
                
                // Update info text
                const infoElement = document.getElementById(mapping.info);
                if (infoElement) {
                    infoElement.textContent = `Found ${data.row_count} records for ${analysisType.replace(/_/g, ' ')} with ID: ${id}`;
                }
                
                // Scroll to the section
                section.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }
    
    /**
     * Show error in appropriate section
     */
    function showErrorInSection(analysisType, errorMessage) {
        // Map analysis type to section ID and results container ID
        const sectionMap = {
            'get_records_by_netid': {
                section: 'getRecordsByNetIdSection',
                container: 'getRecordsByNetIdResults'
            },
            'get_unique_chains_by_netid': {
                section: 'getUniqueChainsByNetIdSection',
                container: 'getUniqueChainsByNetIdResults'
            },
            'get_unique_circuits_by_netid': {
                section: 'getUniqueCircuitsByNetIdSection',
                container: 'getUniqueCircuitsByNetIdResults'
            },
            'get_chains_by_netid': {
                section: 'getChainsByNetIdSection',
                container: 'getChainsByNetIdResults'
            },
            'show_start_end_chain': {
                section: 'showStartEndChainSection',
                container: 'showStartEndChainResults'
            },
            'get_chain_sequence_length': {
                section: 'getChainSequenceLengthSection',
                container: 'getChainSequenceLengthResults'
            },
            'get_chain_circuit_sequence': {
                section: 'getChainCircuitSequenceSection',
                container: 'getChainCircuitSequenceResults'
            }
        };
        
        const mapping = sectionMap[analysisType];
        
        if (mapping) {
            // Get the section
            const section = document.getElementById(mapping.section);
            if (section) {
                // Ensure section is visible
                section.style.display = 'block';
                
                // Get the results container
                const resultsContainer = document.getElementById(mapping.container);
                if (resultsContainer) {
                    // Display error
                    resultsContainer.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>${errorMessage}
                        </div>
                    `;
                }
                
                // Scroll to the section
                section.scrollIntoView({ behavior: 'smooth' });
            }
        }
    }
    
    /**
     * Export results from a specific section
     */
    function exportSectionResults(sectionId) {
        // Map section ID to result container ID
        const containerMap = {
            'getRecordsByNetId': 'getRecordsByNetIdResults',
            'getUniqueChainsByNetId': 'getUniqueChainsByNetIdResults',
            'startEndTable': 'startEndTableResults',
            'getUniqueCircuitsByNetId': 'getUniqueCircuitsByNetIdResults',
            'getChainsByNetId': 'getChainsByNetIdResults',
            'showStartEndChain': 'showStartEndChainResults',
            'getChainSequenceLength': 'getChainSequenceLengthResults',
            'getChainCircuitSequence': 'getChainCircuitSequenceResults'
        };
        
        const containerId = containerMap[sectionId];
        if (!containerId) {
            alert('Invalid section ID');
            return;
        }
        
        const container = document.getElementById(containerId);
        if (!container || !container.innerHTML.trim()) {
            alert('No results to export in this section');
            return;
        }
        
        // In a real application, you would make an API call to get CSV data
        // For now, we'll just create a simple export notification
        
        let filename = `railway_data_${sectionId}_export.csv`;
        
        // Create a temporary link to trigger download
        const a = document.createElement('a');
        a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent('Exported data would be here in a real application');
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        alert(`In a real application, this would download the results from the "${sectionId}" section as a properly formatted CSV file`);
    }
    
    /**
     * Handle "Use Default Data" button click
     */
    function handleUseDefaultData(event) {
        // Show loading status
        showUploadStatus('loading', 'Loading default datasets...');
        
        // Show spinner and disable buttons
        const btnText = document.getElementById('defaultBtnText');
        const btnSpinner = document.getElementById('defaultBtnSpinner');
        if (btnText) btnText.textContent = 'Loading...';
        if (btnSpinner) btnSpinner.classList.remove('d-none');
        
        // Disable buttons during loading
        uploadBtn.disabled = true;
        useDefaultBtn.disabled = true;
        
        console.log("Requesting default data...");
        
        // Make a request to the server to use default data
        fetch('/railway-data-visuals/api/use-default-data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            cache: 'no-cache' // Prevent caching issues
        })
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                return response.json().then(errData => {
                    throw new Error(errData.message || `Server returned ${response.status}: ${response.statusText}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log("Received data:", data);
            uploadBtn.disabled = false;
            useDefaultBtn.disabled = false;
            
            // Hide spinner and restore button text
            const btnText = document.getElementById('defaultBtnText');
            const btnSpinner = document.getElementById('defaultBtnSpinner');
            if (btnText) btnText.textContent = 'Use Default Data';
            if (btnSpinner) btnSpinner.classList.add('d-none');
            
            if (data.status === 'success') {
                filesUploaded = true;
                usingDefaultData = true;
                showUploadStatus('default', 'Using default datasets for analysis');
                
                // Ensure data_summary exists before trying to display it
                if (data.data_summary) {
                    try {
                        displayDataSummary(data.data_summary);
                        showAnalysisSection();
                    } catch (displayError) {
                        console.error("Error displaying data summary:", displayError);
                        showUploadStatus('warning', 'Default datasets loaded but there was an error displaying the summary');
                    }
                } else {
                    console.error("Data summary missing in response");
                    showUploadStatus('warning', 'Default datasets loaded but summary information is missing');
                }
                
                // Remove highlight from file upload section
                const fileUploadCard = document.querySelector('#fileUploadForm').closest('.card');
                if (fileUploadCard) {
                    fileUploadCard.classList.remove('no-data-highlight');
                }
                
                // Show a tooltip or hint about using default data
                const uploadStatus = document.getElementById('uploadStatus');
                if (uploadStatus) {
                    // Remove existing notes if any
                    const existingNote = uploadStatus.querySelector('.default-data-note');
                    if (existingNote) {
                        existingNote.remove();
                    }
                    
                    const defaultDataNote = document.createElement('div');
                    defaultDataNote.className = 'mt-2 small text-muted default-data-note';
                    defaultDataNote.innerHTML = '<i class="fas fa-database me-1"></i> Using built-in default datasets. You can still upload your own files if needed.';
                    uploadStatus.appendChild(defaultDataNote);
                }
                
                // Scroll to the analysis section
                document.getElementById('analysisOptionsSection').scrollIntoView({ behavior: 'smooth' });
                
            } else {
                showUploadStatus('error', 'Error loading default datasets: ' + (data.message || 'Unknown error'));
            }
        })
        .catch(error => {
            uploadBtn.disabled = false;
            useDefaultBtn.disabled = false;
            
            // Hide spinner and restore button text
            const btnText = document.getElementById('defaultBtnText');
            const btnSpinner = document.getElementById('defaultBtnSpinner');
            if (btnText) btnText.textContent = 'Use Default Data';
            if (btnSpinner) btnSpinner.classList.add('d-none');
            
            showUploadStatus('error', 'Error loading default data: ' + error.message);
            console.error('Default data load error:', error);
        });
    }
    
    /**
     * Check if default data is available on page load
     */
    function checkDefaultDataAvailability() {
        fetch('/railway-data-visuals/api/check-default-data', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Update UI based on data availability
                const useDefaultBtn = document.getElementById('useDefaultBtn');
                
                if (data.all_available) {
                    if (useDefaultBtn) {
                        useDefaultBtn.disabled = false;
                        useDefaultBtn.title = "Use default datasets without uploading files";
                        
                        // Add a note to the upload status section
                        const uploadStatus = document.getElementById('uploadStatus');
                        if (uploadStatus) {
                            uploadStatus.innerHTML = `
                                <div class="alert alert-info">
                                    <i class="fas fa-info-circle me-2"></i>Default datasets are available. Click "Use Default Data" to load them.
                                </div>
                                <div class="small text-muted mt-2">
                                    <i class="fas fa-lightbulb me-1"></i> <strong>Tip:</strong> Default data includes start-end data file for railway analysis
                                </div>
                            `;
                        }
                    }
                } else {
                    const missingFiles = data.missing || [];
                    
                    if (useDefaultBtn) {
                        useDefaultBtn.disabled = true;
                        useDefaultBtn.title = `Missing required files: ${missingFiles.join(', ')}`;
                    }
                    
                    const uploadStatus = document.getElementById('uploadStatus');
                    if (uploadStatus) {
                        uploadStatus.innerHTML = `
                            <div class="alert alert-warning">
                                <i class="fas fa-exclamation-triangle me-2"></i>Some default datasets are missing. Please upload files manually.
                            </div>
                            <div class="small text-muted mt-2">
                                <i class="fas fa-folder-open me-1"></i> <strong>Missing files:</strong> ${missingFiles.join(', ')}
                            </div>
                        `;
                    }
                }
            } else {
                console.error('Error checking default data:', data.message);
            }
        })
        .catch(error => {
            console.error('Error checking default data availability:', error);
        });
    }
    
    // Check default data availability on page load
    checkDefaultDataAvailability();
    
    /**
     * Display analysis results in a dedicated section or inline
     */
    function displayAnalysisResults(sectionId, data, targetElementId = null) {
        // If targetElementId is provided, display results after that element
        // Otherwise use the standard results section
        let resultSection;
        
        if (targetElementId) {
            // Check if a results container already exists after this element
            const targetElement = document.getElementById(targetElementId);
            if (!targetElement) {
                console.error(`Target element ${targetElementId} not found`);
                return;
            }
            
            // Look for an existing results container or create one
            let resultsContainer = targetElement.nextElementSibling;
            if (!resultsContainer || !resultsContainer.classList.contains('inline-results-container')) {
                resultsContainer = document.createElement('div');
                resultsContainer.className = 'card mt-3 mb-4 inline-results-container';
                resultsContainer.id = `inline-results-${targetElementId}`;
                
                // Insert after the target element
                targetElement.parentNode.insertBefore(resultsContainer, targetElement.nextSibling);
            }
            
            resultSection = resultsContainer;
        } else {
            // Use the standard results section
            resultSection = document.getElementById(`${sectionId}Results`);
            if (!resultSection) {
                console.error(`Results section for ${sectionId} not found`);
                return;
            }
        }
        
        // Show the results section
        resultSection.style.display = 'block';
        
        // Clear any existing results
        resultSection.innerHTML = '';
        
        // Add results header
        const resultHeader = document.createElement('h5');
        resultHeader.className = 'mb-3 card-header bg-light';
        resultHeader.innerHTML = `<i class="fas fa-chart-bar me-2"></i>Analysis Results`;
        resultSection.appendChild(resultHeader);
        
        // Create a card body for the content
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';
        resultSection.appendChild(cardBody);
        
        // Process and display the results
        if (data.html) {
            // If HTML content is provided, use it directly
            const contentDiv = document.createElement('div');
            contentDiv.className = 'table-responsive';
            contentDiv.innerHTML = data.html;
            cardBody.appendChild(contentDiv);
        } else if (data.tables) {
            // Handle multiple tables
            for (const [tableId, tableHtml] of Object.entries(data.tables)) {
                const tableSection = document.createElement('div');
                tableSection.className = 'mb-4';
                
                const tableTitle = document.createElement('h6');
                tableTitle.className = 'text-muted mb-2';
                tableTitle.textContent = formatTableId(tableId);
                
                const tableContainer = document.createElement('div');
                tableContainer.className = 'table-responsive';
                tableContainer.innerHTML = tableHtml;
                
                tableSection.appendChild(tableTitle);
                tableSection.appendChild(tableContainer);
                cardBody.appendChild(tableSection);
            }
        } else if (data.message) {
            // If just a message is provided
            const messageDiv = document.createElement('div');
            messageDiv.className = 'alert alert-info';
            messageDiv.textContent = data.message;
            cardBody.appendChild(messageDiv);
        } else {
            // Fallback for unexpected data format
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-warning';
            errorDiv.textContent = 'No results data available';
            cardBody.appendChild(errorDiv);
        }
        
        // Add close button and export button
        const buttonRow = document.createElement('div');
        buttonRow.className = 'card-footer d-flex justify-content-between';
        
        // Add export button if results are available
        if (data.html || data.tables) {
            const exportButton = document.createElement('button');
            exportButton.className = 'btn btn-sm btn-outline-secondary export-btn';
            exportButton.setAttribute('data-section', sectionId);
            exportButton.innerHTML = '<i class="fas fa-download me-1"></i>Export Results';
            exportButton.addEventListener('click', function() {
                exportSectionResults(sectionId);
            });
            buttonRow.appendChild(exportButton);
        }
        
        // Add close button only for inline results
        if (targetElementId) {
            const closeButton = document.createElement('button');
            closeButton.className = 'btn btn-sm btn-outline-danger ms-auto';
            closeButton.innerHTML = '<i class="fas fa-times me-1"></i>Close';
            closeButton.addEventListener('click', function() {
                resultSection.style.display = 'none';
            });
            buttonRow.appendChild(closeButton);
        }
        
        resultSection.appendChild(buttonRow);
        
        // Scroll to the results
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    /**
     * Process form submission for analysis and show results inline after the input fields
     * @param {HTMLFormElement} form - The form element being submitted
     * @param {string} sectionId - The section ID for API endpoint
     */
    function processAnalysisFormWithInlineResults(form, sectionId) {
        const netIdInput = form.querySelector('input[name="net_id"]');
        const chainIdInput = form.querySelector('input[name="chain_id"]');
        
        // Determine which input we're working with
        let targetInput = null;
        if (netIdInput && netIdInput.value) {
            targetInput = netIdInput;
        } else if (chainIdInput && chainIdInput.value) {
            targetInput = chainIdInput;
        }
        
        if (!targetInput) {
            alert("Please enter a valid ID");
            return;
        }
        
        // Find the parent container of the input for result placement
        const inputGroup = targetInput.closest('.form-group') || targetInput.closest('.input-group') || targetInput.parentElement;
        
        // Check if there's already a results container
        let resultsContainer = document.getElementById(`inline-results-${targetInput.id}`);
        
        // If no results container exists, create one
        if (!resultsContainer) {
            resultsContainer = document.createElement('div');
            resultsContainer.id = `inline-results-${targetInput.id}`;
            resultsContainer.className = 'card mt-3 mb-3 inline-results';
            
            // Insert after the input group
            if (inputGroup.nextElementSibling) {
                inputGroup.parentNode.insertBefore(resultsContainer, inputGroup.nextElementSibling);
            } else {
                inputGroup.parentNode.appendChild(resultsContainer);
            }
        }
        
        // Show loading indicator
        resultsContainer.innerHTML = `
            <div class="card-body text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2">Processing data for ${targetInput.name.replace('_', ' ')} ${targetInput.value}...</p>
            </div>
        `;
        resultsContainer.style.display = 'block';
        
        // Get form data
        const formData = new FormData(form);
        const formDataObj = {};
        formData.forEach((value, key) => {
            formDataObj[key] = value;
        });
        
        // Make API request
        fetch(`/railway-data-visuals/api/${sectionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formDataObj),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Error: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                // Create a container for the results
                resultsContainer.innerHTML = '';
                
                // Add header
                const header = document.createElement('div');
                header.className = 'card-header d-flex justify-content-between align-items-center bg-light';
                header.innerHTML = `
                    <h5 class="mb-0">
                        <i class="fas fa-chart-bar me-2"></i>
                        Results for ${targetInput.name.replace('_', ' ')} ${targetInput.value}
                    </h5>
                    <button type="button" class="btn-close" aria-label="Close"></button>
                `;
                resultsContainer.appendChild(header);
                
                // Add close button functionality
                header.querySelector('.btn-close').addEventListener('click', () => {
                    resultsContainer.style.display = 'none';
                });
                
                // Add content
                const content = document.createElement('div');
                content.className = 'card-body';
                
                if (data.results.html) {
                    content.innerHTML = data.results.html;
                } else if (data.results.tables) {
                    // Process multiple tables
                    for (const [tableId, tableHtml] of Object.entries(data.results.tables)) {
                        const tableSection = document.createElement('div');
                        tableSection.className = 'mb-4';
                        
                        const tableTitle = document.createElement('h6');
                        tableTitle.className = 'text-muted mb-2';
                        tableTitle.textContent = tableId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                        
                        const tableContent = document.createElement('div');
                        tableContent.className = 'table-responsive';
                        tableContent.innerHTML = tableHtml;
                        
                        tableSection.appendChild(tableTitle);
                        tableSection.appendChild(tableContent);
                        content.appendChild(tableSection);
                    }
                } else {
                    content.innerHTML = '<div class="alert alert-info">No data available</div>';
                }
                
                resultsContainer.appendChild(content);
                
                // Add footer with export button
                const footer = document.createElement('div');
                footer.className = 'card-footer';
                footer.innerHTML = `
                    <button class="btn btn-sm btn-outline-secondary">
                        <i class="fas fa-download me-1"></i>Export Results
                    </button>
                `;
                resultsContainer.appendChild(footer);
                
                // Attach export functionality
                footer.querySelector('button').addEventListener('click', () => {
                    exportResults(data.results, `${sectionId}_${targetInput.value}`);
                });
                
                // Scroll to the results
                resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                // Show error
                resultsContainer.innerHTML = `
                    <div class="card-body">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            ${data.message || 'Error processing request'}
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultsContainer.innerHTML = `
                <div class="card-body">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        An error occurred while processing the request: ${error.message}
                    </div>
                </div>
            `;
        });
    }

    /**
     * Export results to CSV/Excel
     */
    function exportResults(results, fileName) {
        // Create a temporary element to hold the HTML
        const tempDiv = document.createElement('div');
        
        if (results.html) {
            tempDiv.innerHTML = results.html;
        } else if (results.tables) {
            // Combine all tables
            for (const tableHtml of Object.values(results.tables)) {
                tempDiv.innerHTML += tableHtml;
            }
        } else {
            alert('No data available for export');
            return;
        }
        
        // Get all tables
        const tables = tempDiv.querySelectorAll('table');
        
        if (tables.length === 0) {
            alert('No table data to export');
            return;
        }
        
        // Process first table for now (we can enhance to handle multiple tables later)
        const table = tables[0];
        const rows = table.querySelectorAll('tr');
        const csvContent = [];
        
        // Process each row
        rows.forEach(row => {
            const rowData = [];
            // Get cells (either th or td)
            const cells = row.querySelectorAll('th, td');
            
            cells.forEach(cell => {
                // Replace commas and quotes for proper CSV formatting
                let cellText = cell.textContent.trim().replace(/"/g, '""');
                rowData.push(`"${cellText}"`);
            });
            
            csvContent.push(rowData.join(','));
        });
        
        // Create CSV content
        const csvData = csvContent.join('\n');
        
        // Create download link
        const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.setAttribute('href', url);
        link.setAttribute('download', `${fileName}.csv`);
        link.style.display = 'none';
        
        // Append to document, click, and remove
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    // Add event listeners to forms that should show inline results
    function setupInlineResultsForms() {
        // Forms that contain net_id or chain_id inputs should show inline results
        const formsWithIds = [
            'netDetailForm',
            'chainDetailForm',
            'netChainForm',
            'netCircuitForm',
            'startEndTableForm',
            'chainSequenceForm'
        ];
        
        formsWithIds.forEach(formId => {
            const form = document.getElementById(formId);
            if (form) {
                // Remove existing event listeners
                const newForm = form.cloneNode(true);
                form.parentNode.replaceChild(newForm, form);
                
                // Add new event listener
                newForm.addEventListener('submit', function(event) {
                    event.preventDefault();
                    // Get the section ID from the form ID by removing 'Form'
                    const sectionId = formId.replace('Form', '');
                    processAnalysisFormWithInlineResults(this, sectionId);
                });
            }
        });
    }

    // Initialize the inline results functionality when the page loads
    document.addEventListener('DOMContentLoaded', function() {
        setupInlineResultsForms();
    });
    
    // Update the section that fetches data summary to use our new function
    document.addEventListener('DOMContentLoaded', function() {
        // Find the existing display data summary function call and update it
        const originalDisplayDataSummary = displayDataSummary;
        
        // Override the displayDataSummary function to use our new displayShuntingSummary
        displayDataSummary = function(data) {
            // Show the data summary section
            const dataSummarySection = document.getElementById('dataSummarySection');
            if (dataSummarySection) {
                dataSummarySection.style.display = 'block';
            }
            
            // Use the new shunting summary display function
            displayShuntingSummary(data);
        };
        
        // When the data is loaded via API or default data, it will now use our new function
    });
    
    // Setup event handlers for the start-end feature
    const getStartEndDataBtn = document.getElementById('getStartEndDataBtn');
    if (getStartEndDataBtn) {
        getStartEndDataBtn.addEventListener('click', function() {
            const netIdInput = document.getElementById('startEndNetIdInput');
            const netId = netIdInput ? netIdInput.value : '';
            getStartEndData(netId);
        });
    }

    // Function to get start-end data
    function getStartEndData(netId) {
        if (!filesUploaded) {
            alert('Please upload data files or use default data first');
            return;
        }
        
        // Show loading in the start-end results section
        const resultsSection = document.getElementById('featureStartEndSection');
        const resultsContainer = document.getElementById('featureStartEndResults');
        
        if (resultsSection && resultsContainer) {
            // Make section visible
            resultsSection.style.display = 'block';
            
            // Show loading indicator
            resultsContainer.innerHTML = `
                <div class="text-center my-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">Loading start-end data...</p>
                </div>
            `;
            
            // Fetch data from server
            fetch(`/railway-data-visuals/api/feature-start-end?net_id=${netId || ''}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Update section header
                        const sectionHeader = resultsSection.querySelector('.card-header h5');
                        if (sectionHeader) {
                            sectionHeader.innerHTML = `<i class="fas fa-route me-2"></i>${data.title || 'Start-End Data Results'}`;
                        }
                        
                        // Update results container
                        resultsContainer.innerHTML = data.result_html || '<div class="alert alert-info">No data available</div>';
                        
                        // Update info text
                        const infoText = document.getElementById('featureStartEndInfo');
                        if (infoText) {
                            infoText.textContent = `Found ${data.row_count || 0} records`;
                        }
                        
                        // Scroll to results
                        resultsSection.scrollIntoView({ behavior: 'smooth' });
                    } else {
                        resultsContainer.innerHTML = `
                            <div class="alert alert-danger">
                                <i class="fas fa-exclamation-circle me-2"></i>${data.message || 'Error fetching data'}
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    resultsContainer.innerHTML = `
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>Error: ${error.message}
                        </div>
                    `;
                });
        }
    }
});