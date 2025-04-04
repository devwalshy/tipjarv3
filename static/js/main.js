/**
 * TipJar - Main JavaScript
 * Handles all client-side interactivity for the TipJar web application.
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initApp();
});

/**
 * Initialize the application
 */
function initApp() {
    // Initialize file upload functionality
    initFileUpload();
    
    // Initialize step navigation
    initStepNavigation();
    
    // Initialize manual entry form
    initManualEntryForm();
    
    // Initialize all button actions
    initButtonActions();
    
    // Initialize history toggle
    initHistoryToggle();
    
    // Load any history data
    loadHistory();
}

/**
 * Initialize file upload functionality
 */
function initFileUpload() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    
    // Enable/disable upload button based on file selection
    fileInput.addEventListener('change', function() {
        uploadButton.disabled = !this.files.length;
        
        // Preview image if file is selected
        if (this.files.length) {
            const file = this.files[0];
            const reader = new FileReader();
            
            reader.onload = function(e) {
                const previewImage = document.getElementById('previewImage');
                previewImage.src = e.target.result;
            }
            
            reader.readAsDataURL(file);
        }
    });
    
    // Drag and drop functionality
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('drag-over');
    }
    
    function unhighlight() {
        dropArea.classList.remove('drag-over');
    }
    
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        fileInput.files = files;
        
        // Trigger change event
        const event = new Event('change', { bubbles: true });
        fileInput.dispatchEvent(event);
    }
    
    // Process image when upload button is clicked
    uploadButton.addEventListener('click', processImage);
}

/**
 * Process the uploaded image
 */
function processImage() {
    const fileInput = document.getElementById('fileInput');
    
    if (!fileInput.files.length) {
        showNotification('Please select an image to upload', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    // Show loading overlay
    showLoading('Processing image...');
    
    // Make AJAX request to process the image
    fetch('/process_image', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // Update the OCR result display
            const ocrResult = document.getElementById('ocrResult');
            ocrResult.innerHTML = '';
            
            // Create pre element for the OCR text
            const pre = document.createElement('pre');
            pre.textContent = data.ocr_result;
            ocrResult.appendChild(pre);
            
            // Update image preview if needed
            const previewImage = document.getElementById('previewImage');
            if (data.image_path) {
                previewImage.src = data.image_path;
            }
            
            // Move to the next step
            goToStep('extract');
            
            // Setup download OCR button
            setupDownloadOcrButton();
            
            showNotification('Image processed successfully!', 'success');
        } else {
            showNotification(data.error || 'Error processing image', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while processing the image. Please try again.', 'error');
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Set up the download OCR button
 */
function setupDownloadOcrButton() {
    const downloadOcrButton = document.getElementById('downloadOcrButton');
    downloadOcrButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        fetch('/download_ocr')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Create and trigger download
                    const link = document.createElement('a');
                    link.href = `data:text/plain;base64,${data.b64data}`;
                    link.download = data.filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                } else {
                    showNotification(data.error || 'Download failed', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Failed to download OCR text', 'error');
            });
    });
}

/**
 * Initialize step navigation
 */
function initStepNavigation() {
    // Event delegation for step clicks
    const stepIndicator = document.querySelector('.step-indicator');
    stepIndicator.addEventListener('click', function(e) {
        // Find the closest step element
        const step = e.target.closest('.step');
        if (step && step.classList.contains('completed')) {
            const targetStep = step.getAttribute('data-step');
            goToStep(targetStep);
        }
    });
    
    // Initialize "proceed to" buttons
    document.getElementById('proceedToCalculation').addEventListener('click', function() {
        goToStep('calculate');
    });
}

/**
 * Go to a specific step in the process
 */
function goToStep(stepId) {
    // Update step indicators
    const steps = document.querySelectorAll('.step');
    const targetStepIndex = Array.from(steps).findIndex(step => step.getAttribute('data-step') === stepId);
    
    if (targetStepIndex === -1) return;
    
    // Mark previous steps as completed and current step as active
    steps.forEach((step, index) => {
        step.classList.remove('active');
        if (index < targetStepIndex) {
            step.classList.add('completed');
        } else if (index === targetStepIndex) {
            step.classList.add('active');
        } else {
            step.classList.remove('completed');
        }
    });
    
    // Show the corresponding content
    const contents = document.querySelectorAll('.step-content');
    contents.forEach(content => content.classList.remove('active'));
    
    const targetContent = document.getElementById(`${stepId}-step`);
    if (targetContent) {
        // Add fade out/in animation
        targetContent.style.animation = 'none';
        targetContent.offsetHeight; // Trigger reflow
        targetContent.style.animation = 'fadeIn 0.5s ease-in-out';
        targetContent.classList.add('active');
        
        // Scroll to top of the step
        targetContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Initialize manual entry form
 */
function initManualEntryForm() {
    const manualEntryToggle = document.getElementById('manualEntryToggle');
    const manualEntryForm = document.getElementById('manualEntryForm');
    const partnerCountInput = document.getElementById('partnerCount');
    const updatePartnerCountButton = document.getElementById('updatePartnerCount');
    const partnersContainer = document.getElementById('partnersContainer');
    const saveManualDataButton = document.getElementById('saveManualData');
    
    // Toggle form visibility
    manualEntryToggle.addEventListener('click', function() {
        manualEntryForm.classList.toggle('hidden');
        if (!manualEntryForm.classList.contains('hidden')) {
            // Generate partner inputs
            generatePartnerInputs(parseInt(partnerCountInput.value, 10));
        }
    });
    
    // Update partner count
    updatePartnerCountButton.addEventListener('click', function() {
        const count = parseInt(partnerCountInput.value, 10);
        if (count > 0 && count <= 20) {
            generatePartnerInputs(count);
        } else {
            showNotification('Please enter a valid number between 1 and 20', 'warning');
        }
    });
    
    // Save manual data
    saveManualDataButton.addEventListener('click', function() {
        const partnerData = collectManualPartnerData();
        if (partnerData.length > 0) {
            saveManualPartnerData(partnerData);
        } else {
            showNotification('Please enter at least one partner with a name and hours', 'warning');
        }
    });
    
    // Generate initial inputs
    generatePartnerInputs(3);
}

/**
 * Generate partner input fields
 */
function generatePartnerInputs(count) {
    const partnersContainer = document.getElementById('partnersContainer');
    partnersContainer.innerHTML = '';
    
    for (let i = 0; i < count; i++) {
        const partnerGroup = document.createElement('div');
        partnerGroup.className = 'partner-input-group';
        partnerGroup.innerHTML = `
            <h4>Partner ${i + 1}</h4>
            <div class="form-group">
                <label for="partnerName${i}">Name:</label>
                <input type="text" id="partnerName${i}" class="form-control" placeholder="Enter partner name">
            </div>
            <div class="form-group">
                <label for="partnerHours${i}">Hours:</label>
                <input type="number" id="partnerHours${i}" class="form-control" placeholder="0" min="0" step="0.25">
            </div>
        `;
        
        partnersContainer.appendChild(partnerGroup);
    }
}

/**
 * Collect manual partner data
 */
function collectManualPartnerData() {
    const partnerData = [];
    const partnerGroups = document.querySelectorAll('.partner-input-group');
    
    partnerGroups.forEach((group, index) => {
        const nameInput = group.querySelector(`#partnerName${index}`);
        const hoursInput = group.querySelector(`#partnerHours${index}`);
        
        if (nameInput && hoursInput && nameInput.value.trim()) {
            partnerData.push({
                name: nameInput.value.trim(),
                hours: parseFloat(hoursInput.value) || 0,
                number: index + 1
            });
        }
    });
    
    return partnerData;
}

/**
 * Save manual partner data
 */
function saveManualPartnerData(partnerData) {
    showLoading('Saving partner data...');
    
    fetch('/manual_partner_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ partnerData: partnerData })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display the partner data
            displayPartnerData(data.partner_data, data.total_hours);
            
            // Hide the manual entry form
            document.getElementById('manualEntryForm').classList.add('hidden');
            
            showNotification('Partner data saved successfully!', 'success');
        } else {
            showNotification(data.error || 'Error saving partner data', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while saving partner data', 'error');
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Initialize button actions
 */
function initButtonActions() {
    // Extract Data Button
    const extractDataButton = document.getElementById('extractDataButton');
    extractDataButton.addEventListener('click', extractPartnerData);
    
    // Calculate Tips Button
    const calculateTipsButton = document.getElementById('calculateTipsButton');
    calculateTipsButton.addEventListener('click', calculateTips);
    
    // Save to History Button
    const saveToHistoryButton = document.getElementById('saveToHistoryButton');
    saveToHistoryButton.addEventListener('click', saveToHistory);
    
    // Download HTML Button
    const downloadHtmlButton = document.getElementById('downloadHtmlButton');
    downloadHtmlButton.addEventListener('click', downloadHtmlTable);
    
    // Copy Results Button
    const copyResultsButton = document.getElementById('copyResultsButton');
    copyResultsButton.addEventListener('click', copyResults);
}

/**
 * Extract partner data from OCR result
 */
function extractPartnerData() {
    showLoading('Extracting partner data...');
    
    fetch('/extract_partner_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display the partner data
            displayPartnerData(data.partner_data, data.total_hours);
            showNotification('Partner data extracted successfully!', 'success');
        } else {
            showNotification(data.error || 'Error extracting partner data', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while extracting partner data', 'error');
    })
    .finally(() => {
        hideLoading();
    });
}
/**
 * Display partner data in a table
 */
function displayPartnerData(partnerData, totalHours) {
    const partnerDataCard = document.getElementById('partnerDataCard');
    const partnerDataTable = document.getElementById('partnerDataTable');
    const totalHoursDisplay = document.getElementById('totalHoursDisplay');
    
    // Show the partner data card
    partnerDataCard.classList.remove('hidden');
    
    // Set total hours
    totalHoursDisplay.textContent = `Total Hours: ${totalHours.toFixed(2)}`;
    
    // Create the table
    partnerDataTable.innerHTML = '';
    
    // Create table element
    const table = document.createElement('table');
    
    // Create table header
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    
    ['#', 'Name', 'Hours'].forEach(text => {
        const th = document.createElement('th');
        th.textContent = text;
        headerRow.appendChild(th);
    });
    
    thead.appendChild(headerRow);
    table.appendChild(thead);
    
    // Create table body
    const tbody = document.createElement('tbody');
    
    partnerData.forEach(partner => {
        const row = document.createElement('tr');
        
        // Partner number
        const numberCell = document.createElement('td');
        numberCell.textContent = partner.number;
        row.appendChild(numberCell);
        
        // Partner name
        const nameCell = document.createElement('td');
        nameCell.textContent = partner.name;
        row.appendChild(nameCell);
        
        // Partner hours
        const hoursCell = document.createElement('td');
        hoursCell.textContent = partner.hours;
        row.appendChild(hoursCell);
        
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    partnerDataTable.appendChild(table);
    
    // Add animation to each row
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row, index) => {
        row.style.animation = `slideIn 0.3s ease-out ${index * 0.1}s both`;
    });
}

/**
 * Calculate tips based on partner data
 */
function calculateTips() {
    const totalTipAmount = document.getElementById('totalTipAmount').value;
    
    if (!totalTipAmount || isNaN(totalTipAmount) || parseFloat(totalTipAmount) <= 0) {
        showNotification('Please enter a valid tip amount', 'warning');
        return;
    }
    
    showLoading('Calculating tip distribution...');
    
    fetch('/calculate_tips', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ totalTipAmount: parseFloat(totalTipAmount) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Display calculation information
            document.getElementById('hourlyRate').textContent = `$${data.hourly_rate.toFixed(2)}`;
            document.getElementById('tipAmountDisplay').textContent = data.total_tip_amount.toFixed(2);
            document.getElementById('hoursAmountDisplay').textContent = data.total_hours.toFixed(2);
            document.getElementById('rateDisplay').textContent = data.hourly_rate.toFixed(2);
            
            document.getElementById('calculationInfo').classList.remove('hidden');
            
            // Display the distribution results
            displayDistributionResults(data.partner_data, data.hourly_rate);
            
            // Move to the distribution step
            goToStep('distribute');
            
            showNotification('Tips calculated successfully!', 'success');
        } else {
            showNotification(data.error || 'Error calculating tips', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while calculating tips', 'error');
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Display tip distribution results
 */
function displayDistributionResults(partnerData, hourlyRate) {
    const distributionResults = document.getElementById('distributionResults');
    distributionResults.innerHTML = '';
    
    partnerData.forEach((partner, index) => {
        const card = document.createElement('div');
        card.className = 'distribution-card';
        card.style.animationDelay = `${index * 0.1}s`;
        
        const partnerNumber = document.createElement('div');
        partnerNumber.className = 'partner-number';
        partnerNumber.textContent = partner.number;
        
        const partnerInfo = document.createElement('div');
        partnerInfo.className = 'partner-info';
        
        const partnerName = document.createElement('div');
        partnerName.className = 'partner-name';
        partnerName.textContent = partner.name;
        
        const partnerHours = document.createElement('div');
        partnerHours.className = 'partner-detail';
        partnerHours.textContent = `${partner.hours} hours`;
        
        const partnerCalculation = document.createElement('div');
        partnerCalculation.className = 'partner-detail';
        partnerCalculation.textContent = `${partner.hours} × $${hourlyRate.toFixed(2)} = $${partner.exact_tip_amount.toFixed(2)} → $${partner.tip_amount}`;
        
        const partnerBills = document.createElement('div');
        partnerBills.className = 'partner-detail';
        partnerBills.textContent = `Bills: ${partner.bills_text}`;
        
        partnerInfo.appendChild(partnerName);
        partnerInfo.appendChild(partnerHours);
        partnerInfo.appendChild(partnerCalculation);
        partnerInfo.appendChild(partnerBills);
        
        const partnerAmount = document.createElement('div');
        partnerAmount.className = 'partner-amount';
        partnerAmount.textContent = `$${partner.tip_amount}`;
        
        card.appendChild(partnerNumber);
        card.appendChild(partnerInfo);
        card.appendChild(partnerAmount);
        
        distributionResults.appendChild(card);
    });
    
    // Setup download and copy buttons
    setupDownloadHtmlButton();
}

/**
 * Save the current distribution to history
 */
function saveToHistory() {
    showLoading('Saving to history...');
    
    fetch('/save_to_history', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Refresh history
            displayHistory(data.history);
            
            // Show history section
            document.getElementById('historyContent').classList.remove('hidden');
            
            showNotification('Distribution saved to history!', 'success');
        } else {
            showNotification(data.error || 'Error saving to history', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred while saving to history', 'error');
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Download the HTML table of results
 */
function downloadHtmlTable() {
    fetch('/download_html')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Create and trigger download
                const link = document.createElement('a');
                link.href = `data:text/html;base64,${data.b64data}`;
                link.download = data.filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                showNotification(data.error || 'Download failed', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Failed to download HTML table', 'error');
        });
}

/**
 * Setup the download HTML button
 */
function setupDownloadHtmlButton() {
    const downloadHtmlButton = document.getElementById('downloadHtmlButton');
    downloadHtmlButton.addEventListener('click', downloadHtmlTable);
}

/**
 * Copy results to clipboard
 */
function copyResults() {
    const distributionResults = document.getElementById('distributionResults');
    
    // Create a formatted text version of the results
    const cards = distributionResults.querySelectorAll('.distribution-card');
    let text = '';
    
    cards.forEach(card => {
        const number = card.querySelector('.partner-number').textContent;
        const name = card.querySelector('.partner-name').textContent;
        const details = card.querySelectorAll('.partner-detail');
        const hours = details[0].textContent;
        const bills = details[2].textContent;
        const amount = card.querySelector('.partner-amount').textContent;
        
        text += `Partner ${number}: ${name} | ${hours} | ${amount} | ${bills}\n`;
    });
    
    // Copy to clipboard
    navigator.clipboard.writeText(text)
        .then(() => {
            showNotification('Results copied to clipboard!', 'success');
        })
        .catch(err => {
            console.error('Error copying to clipboard:', err);
            showNotification('Failed to copy results', 'error');
        });
}

/**
 * Initialize history toggle
 */
function initHistoryToggle() {
    const historyToggle = document.getElementById('historyToggle');
    const historyContent = document.getElementById('historyContent');
    
    historyToggle.addEventListener('click', function() {
        historyContent.classList.toggle('hidden');
        
        // Toggle chevron icon
        const chevron = historyToggle.querySelector('.fa-chevron-down');
        if (historyContent.classList.contains('hidden')) {
            chevron.classList.remove('fa-chevron-up');
            chevron.classList.add('fa-chevron-down');
        } else {
            chevron.classList.remove('fa-chevron-down');
            chevron.classList.add('fa-chevron-up');
        }
    });
}

/**
 * Load history data
 */
function loadHistory() {
    fetch('/get_history')
        .then(response => response.json())
        .then(data => {
            if (data.history && data.history.length > 0) {
                displayHistory(data.history);
            }
        })
        .catch(error => {
            console.error('Error loading history:', error);
        });
}

/**
 * Display history data
 */
function displayHistory(history) {
    const historyContainer = document.getElementById('historyContainer');
    const historyPlaceholder = document.getElementById('historyPlaceholder');
    
    if (history && history.length > 0) {
        historyContainer.innerHTML = '';
        historyPlaceholder.classList.add('hidden');
        
        history.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';
            
            const historyHeader = document.createElement('div');
            historyHeader.className = 'history-header';
            
            const historyTitle = document.createElement('div');
            historyTitle.className = 'history-title';
            historyTitle.textContent = `Week ${item.week}`;
            
            const historyDetails = document.createElement('div');
            historyDetails.className = 'history-details';
            historyDetails.textContent = `Total: $${item.total_amount.toFixed(2)} for ${item.total_hours.toFixed(2)} hours`;
            
            historyHeader.appendChild(historyTitle);
            historyHeader.appendChild(historyDetails);
            
            const historyPartnerList = document.createElement('div');
            historyPartnerList.className = 'history-partner-list';
            item.partners.forEach(partner => {
                const partnerItem = document.createElement('div');
                partnerItem.className = 'history-partner-item';
                partnerItem.textContent = `${partner.name}: $${partner.tip_amount} (${partner.hours} hours)`;
                historyPartnerList.appendChild(partnerItem);
            });
            
            historyItem.appendChild(historyHeader);
            historyItem.appendChild(historyPartnerList);
            historyContainer.appendChild(historyItem);
        });
    } else {
        historyPlaceholder.classList.remove('hidden');
    }
}

/**
 * Show a notification to the user
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    const notificationContainer = document.getElementById('notification-container');
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // Add message
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    notification.appendChild(messageSpan);
    
    // Add close button
    const closeButton = document.createElement('button');
    closeButton.className = 'notification-close';
    closeButton.innerHTML = '&times;';
    closeButton.addEventListener('click', () => {
        hideNotification(notification);
    });
    notification.appendChild(closeButton);
    
    // Add to container
    notificationContainer.appendChild(notification);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            hideNotification(notification);
        }
    }, 5000);
}

/**
 * Hide a specific notification
 * @param {HTMLElement} notification - The notification element to hide
 */
function hideNotification(notification) {
    // Add fadeOut animation
    notification.style.animation = 'fadeOut 0.3s ease-in forwards';
    
    // Remove after animation completes
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
}

/**
 * Show the loading overlay
 * @param {string} message - The loading message to display
 */
function showLoading(message = 'Loading...') {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    
    loadingText.textContent = message;
    loadingOverlay.classList.remove('hidden');
    
    // Disable scrolling on body
    document.body.style.overflow = 'hidden';
}

/**
 * Hide the loading overlay
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    
    // Add fadeOut animation
    loadingOverlay.style.animation = 'fadeOut 0.3s ease-in forwards';
    
    // Add hidden class and reset animation after animation completes
    setTimeout(() => {
        loadingOverlay.classList.add('hidden');
        loadingOverlay.style.animation = 'fadeIn 0.3s ease-in-out';
        
        // Re-enable scrolling on body
        document.body.style.overflow = '';
    }, 300);
}

/**
 * Format a number as currency
 * @param {number} value - The number to format
 * @returns {string} The formatted currency string
 */
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(value);
}

/**
 * Format a number as decimal
 * @param {number} value - The number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} The formatted decimal string
 */
function formatDecimal(value, decimals = 2) {
    return Number(value).toFixed(decimals);
}
