// Dashboard JavaScript functionality for Alpha Sniper Bot

// Global variables
let statusUpdateInterval;
let chartInstance;

// DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    initializeCharts();
});

// Initialize dashboard
function initializeDashboard() {
    console.log('Initializing Alpha Sniper Bot Dashboard');
    
    // Update bot status immediately
    updateBotStatus();
    
    // Start periodic updates
    startPeriodicUpdates();
    
    // Initialize tooltips
    initializeTooltips();
}

// Setup event listeners
function setupEventListeners() {
    // Form submission handlers
    const newAlertForm = document.querySelector('#newAlertModal form');
    if (newAlertForm) {
        newAlertForm.addEventListener('submit', function(e) {
            handleAlertFormSubmission(e, this);
        });
    }
    
    // Auto-refresh controls
    const refreshButton = document.querySelector('[data-action="refresh"]');
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            refreshDashboard();
        });
    }
    
    // Alert action buttons
    document.querySelectorAll('[data-action="send-alert"]').forEach(button => {
        button.addEventListener('click', function() {
            const alertId = this.dataset.alertId;
            sendAlert(alertId);
        });
    });
}

// Update bot status
function updateBotStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            updateStatusIndicator(data);
            updateStatusMetrics(data);
        })
        .catch(error => {
            console.error('Error fetching bot status:', error);
            updateStatusIndicator({ is_online: false });
        });
}

// Update status indicator in navbar
function updateStatusIndicator(status) {
    const statusElement = document.getElementById('bot-status');
    if (!statusElement) return;
    
    const isOnline = status.is_online;
    const statusText = isOnline ? 'Online' : 'Offline';
    const badgeClass = isOnline ? 'bg-success' : 'bg-danger';
    
    statusElement.className = `badge ${badgeClass} me-2`;
    statusElement.innerHTML = `
        <i data-feather="circle" class="me-1"></i>
        ${statusText}
    `;
    
    // Re-initialize feather icons
    feather.replace();
}

// Update status metrics on dashboard
function updateStatusMetrics(status) {
    // Update guild count
    const guildCountElement = document.querySelector('[data-metric="guild-count"]');
    if (guildCountElement) {
        guildCountElement.textContent = status.guild_count || 0;
    }
    
    // Update latency
    const latencyElement = document.querySelector('[data-metric="latency"]');
    if (latencyElement) {
        latencyElement.textContent = `${Math.round(status.latency || 0)}ms`;
    }
    
    // Update uptime
    const uptimeElement = document.querySelector('[data-metric="uptime"]');
    if (uptimeElement && status.uptime) {
        uptimeElement.textContent = formatUptime(status.uptime);
    }
}

// Format uptime string
function formatUptime(uptimeStr) {
    if (!uptimeStr) return 'N/A';
    
    try {
        const parts = uptimeStr.split(',');
        if (parts.length > 1) {
            return parts[0].trim(); // Return days part
        }
        return uptimeStr.split('.')[0]; // Remove microseconds
    } catch (e) {
        return 'N/A';
    }
}

// Handle alert form submission
function handleAlertFormSubmission(event, form) {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = `
        <span class="spinner-border spinner-border-sm me-1" role="status"></span>
        Creating...
    `;
    
    // Validate form
    if (!validateAlertForm(form)) {
        event.preventDefault();
        submitButton.disabled = false;
        submitButton.innerHTML = originalText;
        return;
    }
    
    // Form will submit normally, but we'll reset button state after a delay
    setTimeout(() => {
        submitButton.disabled = false;
        submitButton.innerHTML = originalText;
    }, 2000);
}

// Validate alert form
function validateAlertForm(form) {
    const title = form.querySelector('[name="title"]').value.trim();
    const message = form.querySelector('[name="message"]').value.trim();
    const channelId = form.querySelector('[name="channel_id"]').value.trim();
    
    if (!title || !message || !channelId) {
        showAlert('error', 'Please fill in all required fields.');
        return false;
    }
    
    // Validate channel ID format (should be numbers only)
    if (!/^\d+$/.test(channelId)) {
        showAlert('error', 'Channel ID should contain only numbers.');
        return false;
    }
    
    return true;
}

// Send alert via API
function sendAlert(alertId) {
    const button = document.querySelector(`[data-action="send-alert"][data-alert-id="${alertId}"]`);
    if (!button) return;
    
    const originalText = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `
        <span class="spinner-border spinner-border-sm me-1" role="status"></span>
        Sending...
    `;
    
    // Navigate to send route (since we're using server-side handling)
    window.location.href = `/alerts/${alertId}/send`;
}

// Show alert message
function showAlert(type, message) {
    const alertContainer = document.querySelector('.container');
    if (!alertContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the beginning of the container
    alertContainer.insertBefore(alertElement, alertContainer.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertElement.parentNode) {
            alertElement.remove();
        }
    }, 5000);
}

// Start periodic updates
function startPeriodicUpdates() {
    // Update bot status every 30 seconds
    statusUpdateInterval = setInterval(updateBotStatus, 30000);
    
    // Update pending alerts count every 60 seconds
    setInterval(updatePendingAlertsCount, 60000);
}

// Update pending alerts count
function updatePendingAlertsCount() {
    fetch('/api/alerts/pending')
        .then(response => response.json())
        .then(data => {
            const pendingElement = document.querySelector('[data-metric="pending-alerts"]');
            if (pendingElement) {
                pendingElement.textContent = data.pending_alerts || 0;
            }
        })
        .catch(error => {
            console.error('Error fetching pending alerts:', error);
        });
}

// Refresh dashboard
function refreshDashboard() {
    const refreshButton = document.querySelector('[data-action="refresh"]');
    if (refreshButton) {
        const icon = refreshButton.querySelector('i');
        if (icon) {
            icon.style.animation = 'spin 1s linear infinite';
            setTimeout(() => {
                icon.style.animation = '';
            }, 1000);
        }
    }
    
    // Update all metrics
    updateBotStatus();
    updatePendingAlertsCount();
    
    showAlert('info', 'Dashboard refreshed successfully!');
}

// Initialize tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize charts
function initializeCharts() {
    const chartCanvas = document.getElementById('alertsChart');
    if (!chartCanvas) return;
    
    const ctx = chartCanvas.getContext('2d');
    
    // Sample data - in a real implementation, this would come from an API
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Alerts Sent',
                data: [12, 19, 3, 5, 2, 3, 7],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    }
                }
            }
        }
    });
}

// Utility functions
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 4,
        maximumFractionDigits: 4
    }).format(amount);
}

function timeAgo(date) {
    const now = new Date();
    const past = new Date(date);
    const diffInSeconds = Math.floor((now - past) / 1000);
    
    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
}

// CSS animation for spinning icons
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (statusUpdateInterval) {
        clearInterval(statusUpdateInterval);
    }
    if (chartInstance) {
        chartInstance.destroy();
    }
});

// Global function for updating bot status (called from base template)
window.updateBotStatus = updateBotStatus;
