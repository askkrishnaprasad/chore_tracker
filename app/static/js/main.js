// Add general performance optimizations, deferred loading, and event handling
'use strict';

// Use event delegation where possible to reduce event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));
    }
    
    // Initialize popovers if Bootstrap is loaded
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'))
        popoverTriggerList.forEach(el => new bootstrap.Popover(el));
    }
    
    // Handle flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    if (flashMessages.length > 0) {
        flashMessages.forEach(message => {
            setTimeout(() => {
                const closeButton = message.querySelector('.btn-close');
                if (closeButton) closeButton.click();
            }, 5000); // Auto-dismiss after 5 seconds
        });
    }
});

// Throttle and debounce functions for performance
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

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Lazy load images if available in the document
function lazyLoadImages() {
    if ('loading' in HTMLImageElement.prototype) {
        // Browser supports native lazy loading
        const images = document.querySelectorAll('img[loading="lazy"]');
        images.forEach(img => {
            img.src = img.dataset.src;
        });
    } else {
        // Fallback for browsers that don't support lazy loading
        const lazyImages = document.querySelectorAll('.lazy-image');
        if (lazyImages.length > 0) {
            const lazyImageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const lazyImage = entry.target;
                        lazyImage.src = lazyImage.dataset.src;
                        lazyImage.classList.remove('lazy-image');
                        lazyImageObserver.unobserve(lazyImage);
                    }
                });
            });
            
            lazyImages.forEach(lazyImage => {
                lazyImageObserver.observe(lazyImage);
            });
        }
    }
}

// Initialize charts if needed
function initCharts() {
    // Main chart initialization function
    // This will be called from pages that need charts
    
    // Use requestAnimationFrame for better performance with charts
    const chartInitializers = {
        weekly: function() {
            const weeklyCtx = document.getElementById('weeklyChart');
            if (!weeklyCtx) return;
            
            // Get the chart data from data attributes
            const chartData = JSON.parse(weeklyCtx.dataset.chartData || '{}');
            
            return new Chart(weeklyCtx, {
                type: 'line',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    animation: {
                        duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1000
                    }
                }
            });
        },
        
        monthly: function() {
            const monthlyCtx = document.getElementById('monthlyChart');
            if (!monthlyCtx) return;
            
            const chartData = JSON.parse(monthlyCtx.dataset.chartData || '{}');
            
            return new Chart(monthlyCtx, {
                type: 'bar',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    animation: {
                        duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1000
                    }
                }
            });
        },
        
        distribution: function() {
            const distributionCtx = document.getElementById('choreDistributionChart');
            if (!distributionCtx) return;
            
            const chartData = JSON.parse(distributionCtx.dataset.chartData || '{}');
            
            return new Chart(distributionCtx, {
                type: 'pie',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                        }
                    },
                    animation: {
                        duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1000
                    }
                }
            });
        },
        
        yearly: function() {
            const yearlyCtx = document.getElementById('yearlyChart');
            if (!yearlyCtx) return;
            
            const chartData = JSON.parse(yearlyCtx.dataset.chartData || '{}');
            
            return new Chart(yearlyCtx, {
                type: 'bar',
                data: chartData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    animation: {
                        duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 1000
                    }
                }
            });
        }
    };
    
    // Initialize charts that exist on the page using requestAnimationFrame
    requestAnimationFrame(() => {
        if (document.getElementById('weeklyChart')) chartInitializers.weekly();
        if (document.getElementById('monthlyChart')) chartInitializers.monthly();
        if (document.getElementById('choreDistributionChart')) chartInitializers.distribution();
        if (document.getElementById('yearlyChart')) chartInitializers.yearly();
        
        // Handle tab switches to properly resize charts
        const tabEls = document.querySelectorAll('button[data-bs-toggle="tab"]');
        tabEls.forEach(tabEl => {
            tabEl.addEventListener('shown.bs.tab', event => {
                // Determine which chart to resize based on the active tab
                const targetId = event.target.getAttribute('data-bs-target');
                if (targetId === '#weekly-chart') {
                    const chartInstance = Chart.getChart('weeklyChart');
                    if (chartInstance) chartInstance.resize();
                } else if (targetId === '#monthly-chart') {
                    const chartInstance = Chart.getChart('monthlyChart');
                    if (chartInstance) chartInstance.resize();
                } else if (targetId === '#distribution-chart') {
                    const chartInstance = Chart.getChart('choreDistributionChart');
                    if (chartInstance) chartInstance.resize();
                } else if (targetId === '#yearly-chart') {
                    const chartInstance = Chart.getChart('yearlyChart');
                    if (chartInstance) chartInstance.resize();
                }
            });
        });
    });
}

// Export functions for use in other scripts
window.choreApp = {
    initCharts: initCharts,
    debounce: debounce,
    throttle: throttle,
    lazyLoadImages: lazyLoadImages
};

// Search functionality - REMOVED TO AVOID CONFLICTS

// Chore sharing toggle
function setupChoreSharing() {
    const sharingToggle = document.getElementById('is_shared');
    if (!sharingToggle) return;
    
    const sharingOptions = document.getElementById('sharingOptions');
    
    sharingToggle.addEventListener('change', function() {
        if (this.checked) {
            sharingOptions.classList.remove('d-none');
        } else {
            sharingOptions.classList.add('d-none');
        }
    });
}

// Initialize dashboard charts using Chart.js
function initCharts() {
    // Common chart options
    Chart.defaults.color = "#6e7687";
    Chart.defaults.font.family = "'Nunito', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
    
    // Create gradient backgrounds for charts
    function createGradient(ctx, colorStart, colorEnd) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        return gradient;
    }
    
    // Fetch user stats data from API
    fetch('/api/user_stats')
        .then(response => response.json())
        .then(data => {
            createWeeklyChart(data);
            createMonthlyChart(data);
            createYearlyChart(data);
        })
        .catch(error => console.error('Error fetching stats:', error));
    
    // Fetch chore stats data for distribution chart
    fetch('/api/chore_stats')
        .then(response => response.json())
        .then(data => {
            createChoreDistributionChart(data);
        })
        .catch(error => console.error('Error fetching chore stats:', error));
    
    function createWeeklyChart(data) {
        const weeklyChartEl = document.getElementById('weeklyChart');
        if (!weeklyChartEl) return;
        
        const ctx = weeklyChartEl.getContext('2d');
        
        // Prepare data
        const weeks = data.weekly_data.map(w => w.week_label);
        const datasets = [];
        
        // Create a dataset for each user
        Object.entries(data.users).forEach(([userId, username], index) => {
            // Create different colors for each user
            const colors = [
                ['rgba(78, 115, 223, 0.8)', 'rgba(78, 115, 223, 0.1)'],
                ['rgba(28, 200, 138, 0.8)', 'rgba(28, 200, 138, 0.1)'],
                ['rgba(54, 185, 204, 0.8)', 'rgba(54, 185, 204, 0.1)'],
                ['rgba(246, 194, 62, 0.8)', 'rgba(246, 194, 62, 0.1)'],
                ['rgba(231, 74, 59, 0.8)', 'rgba(231, 74, 59, 0.1)']
            ];
            
            const colorIndex = index % colors.length;
            
            datasets.push({
                label: username,
                data: data.weekly_data.map(w => w.user_points[userId] || 0),
                backgroundColor: createGradient(ctx, colors[colorIndex][0], colors[colorIndex][1]),
                borderColor: colors[colorIndex][0],
                borderWidth: 2,
                pointBackgroundColor: colors[colorIndex][0],
                pointBorderColor: '#fff',
                pointRadius: 4,
                tension: 0.3
            });
        });
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: weeks,
                datasets: datasets
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        padding: 10,
                        titleFont: {
                            size: 14
                        },
                        bodyFont: {
                            size: 13
                        }
                    }
                },
                animation: {
                    duration: 1500
                }
            }
        });
    }
    
    function createMonthlyChart(data) {
        const monthlyChartEl = document.getElementById('monthlyChart');
        if (!monthlyChartEl) return;
        
        const ctx = monthlyChartEl.getContext('2d');
        
        // Prepare data
        const months = data.monthly_data.map(m => m.month_name);
        const datasets = [];
        
        // Create a dataset for each user
        Object.entries(data.users).forEach(([userId, username], index) => {
            // Create different colors for each user
            const colors = [
                'rgba(78, 115, 223, 0.7)',
                'rgba(28, 200, 138, 0.7)',
                'rgba(54, 185, 204, 0.7)',
                'rgba(246, 194, 62, 0.7)',
                'rgba(231, 74, 59, 0.7)'
            ];
            
            const colorIndex = index % colors.length;
            
            datasets.push({
                label: username,
                data: data.monthly_data.map(m => m.user_points[userId] || 0),
                backgroundColor: colors[colorIndex],
                borderRadius: 4
            });
        });
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: months,
                datasets: datasets
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        padding: 10,
                        titleFont: {
                            size: 14
                        },
                        bodyFont: {
                            size: 13
                        }
                    }
                },
                animation: {
                    duration: 1500
                }
            }
        });
    }
    
    function createChoreDistributionChart(data) {
        const choreDistributionEl = document.getElementById('choreDistributionChart');
        if (!choreDistributionEl) return;
        
        const ctx = choreDistributionEl.getContext('2d');
        
        // Find the chores with the most data
        const topChores = data.chore_stats
            .filter(chore => Object.keys(chore.user_stats).length > 0)
            .sort((a, b) => {
                const totalA = Object.values(a.user_stats).reduce((sum, stat) => sum + stat.count, 0);
                const totalB = Object.values(b.user_stats).reduce((sum, stat) => sum + stat.count, 0);
                return totalB - totalA;
            })
            .slice(0, 5);
        
        // Create datasets per user
        const userDatasets = {};
        const userColors = {};
        
        // Assign colors to users
        Object.keys(data.users).forEach((userId, index) => {
            // Create different colors for each user
            const colors = [
                'rgba(78, 115, 223, 0.7)',
                'rgba(28, 200, 138, 0.7)',
                'rgba(54, 185, 204, 0.7)',
                'rgba(246, 194, 62, 0.7)',
                'rgba(231, 74, 59, 0.7)'
            ];
            
            userColors[userId] = colors[index % colors.length];
            userDatasets[userId] = {
                label: data.users[userId],
                data: [],
                backgroundColor: userColors[userId],
                borderRadius: 4
            };
        });
        
        // Collect data for each chore
        const choreLabels = topChores.map(chore => chore.chore_name);
        
        // Fill datasets with data
        topChores.forEach(chore => {
            // For each user, add their stat for this chore (or 0 if none)
            Object.keys(data.users).forEach(userId => {
                const userStat = chore.user_stats[userId];
                userDatasets[userId].data.push(userStat ? userStat.count : 0);
            });
        });
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: choreLabels,
                datasets: Object.values(userDatasets)
            },
            options: {
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        stacked: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        stacked: true,
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        padding: 10,
                        titleFont: {
                            size: 14
                        },
                        bodyFont: {
                            size: 13
                        }
                    }
                },
                animation: {
                    duration: 1500
                }
            }
        });
    }
    
    function createYearlyChart(data) {
        const yearlyChartEl = document.getElementById('yearlyChart');
        if (!yearlyChartEl) return;
        
        const ctx = yearlyChartEl.getContext('2d');
        
        // Calculate yearly totals per user
        const yearlyTotals = {};
        
        // Get current year
        const currentYear = new Date().getFullYear();
        
        // Initialize totals for each user
        Object.keys(data.users).forEach(userId => {
            yearlyTotals[userId] = 0;
        });
        
        // Sum up monthly data for the year
        data.monthly_data.forEach(month => {
            Object.entries(month.user_points).forEach(([userId, points]) => {
                yearlyTotals[userId] += points;
            });
        });
        
        // Create dataset for the yearly chart
        const chartData = {
            labels: Object.values(data.users),
            datasets: [{
                label: `Total Points (${currentYear})`,
                data: Object.keys(data.users).map(userId => yearlyTotals[userId].toFixed(1)),
                backgroundColor: [
                    'rgba(78, 115, 223, 0.8)',
                    'rgba(28, 200, 138, 0.8)',
                    'rgba(54, 185, 204, 0.8)',
                    'rgba(246, 194, 62, 0.8)',
                    'rgba(231, 74, 59, 0.8)'
                ],
                borderWidth: 1,
                borderRadius: 8
            }]
        };
        
        new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                maintainAspectRatio: false,
                indexAxis: 'y',  // Horizontal bar chart
                scales: {
                    y: {
                        grid: {
                            display: false
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.7)',
                        padding: 10,
                        titleFont: {
                            size: 14
                        },
                        bodyFont: {
                            size: 13
                        },
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw} points`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 1500
                }
            }
        });
    }
}

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Set up chore sharing toggle
    setupChoreSharing();
    
    // Initialize charts if we're on the dashboard
    if (document.getElementById('weeklyChart') || document.getElementById('monthlyChart') || document.getElementById('choreDistributionChart')) {
        initCharts();
    }
}); 