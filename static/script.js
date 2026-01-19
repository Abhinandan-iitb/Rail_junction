// Common script file for both phases

// Function to handle date-time inputs
function setDefaultDates() {
    // Set default dates for datetime inputs if they exist
    const dateInputs = document.querySelectorAll('input[type="datetime-local"]');
    if (dateInputs.length > 0) {
        const now = new Date();
        // Format date as YYYY-MM-DDThh:mm
        const formattedDate = now.toISOString().slice(0, 16);
        
        dateInputs.forEach(input => {
            if (!input.value) {
                input.value = formattedDate;
            }
        });
    }
}

// Handle fullscreen functionality
function setupFullscreenButtons() {
    const fullscreenButtons = document.querySelectorAll('#fullscreenBtn');
    
    fullscreenButtons.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', function() {
                const vizCard = btn.closest('.viz-card');
                if (vizCard) {
                    vizCard.classList.toggle('fullscreen');
                    const icon = btn.querySelector('i');
                    if (icon) {
                        icon.classList.toggle('fa-expand');
                        icon.classList.toggle('fa-compress');
                    }
                }
            });
        }
    });
}

// Function for back navigation
function navigateBack() {
    window.location.href = "/";  // Navigate back to dashboard
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("Script loaded successfully");
    setDefaultDates();
    setupFullscreenButtons();
    
    // Add back navigation buttons if they exist
    const backButtons = document.querySelectorAll('.back-btn');
    backButtons.forEach(btn => {
        btn.addEventListener('click', navigateBack);
    });
});
