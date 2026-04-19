/**
 * Claro Simulator — Client-side projection engine
 * 
 * Runs lightweight projections in the browser so the slider
 * feels instantaneous. Uses the same compound growth maths
 * as the Python service.
 */

const GROWTH_RATE = 0.04; // Moderate — matches Python service default
const MONTHLY_RATE = GROWTH_RATE / 12;

/**
 * Projects when a goal will be reached at a given monthly contribution.
 * Returns months to target and month-by-month balances.
 */
function projectGoal(targetAmount, currentAmount, monthlyContribution) {
    if (monthlyContribution <= 0 || targetAmount <= currentAmount) {
        return {
            months: 0,
            balances: [currentAmount],
            dates: [new Date()],
            interestEarned: 0,
            reachable: targetAmount <= currentAmount
        };
    }

    let balance = currentAmount;
    let months = 0;
    const maxMonths = 600;
    const balances = [balance];
    const dates = [new Date()];

    while (balance < targetAmount && months < maxMonths) {
        const interest = balance * MONTHLY_RATE;
        balance += monthlyContribution + interest;
        months++;

        const d = new Date();
        d.setMonth(d.getMonth() + months);
        dates.push(d);
        balances.push(Math.round(balance * 100) / 100);
    }

    return {
        months: months,
        balances: balances,
        dates: dates,
        interestEarned: Math.round((balance - currentAmount - (monthlyContribution * months)) * 100) / 100,
        reachable: balance >= targetAmount,
        finalBalance: Math.round(balance * 100) / 100
    };
}

/**
 * Formats a date as "Mon YYYY" (abbreviated month for chart axis readability)
 */
function formatDate(d) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[d.getMonth()] + ' ' + d.getFullYear();
}

/**
 * Formats months into human-readable duration
 */
function formatDuration(months) {
    if (months === 0) return 'Already reached';
    if (months === 1) return '1 month';
    if (months < 12) return months + ' months';

    const years = Math.floor(months / 12);
    const remaining = months % 12;

    if (remaining === 0) return years + (years === 1 ? ' year' : ' years');
    return years + (years === 1 ? ' year ' : ' years ') + remaining + (remaining === 1 ? ' month' : ' months');
}

/**
 * Initialises the goal projection chart with two-mode contrast.
 * Grey line = current path. Gold line = proposed path.
 */
function initProjectionChart(canvasId, targetAmount, currentAmount, currentContribution) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext('2d');

    // Get CSS variables from the document
    const style = getComputedStyle(document.body);
    const goldColor = style.getPropertyValue('--roman-gold').trim() || '#C5A35D';
    const textSecondary = style.getPropertyValue('--text-secondary').trim() || 'rgba(255,255,255,0.5)';
    const textTertiary = style.getPropertyValue('--text-tertiary').trim() || 'rgba(255,255,255,0.3)';
    const glassBorder = style.getPropertyValue('--glass-border').trim() || 'rgba(197,163,93,0.12)';

    const currentPath = projectGoal(targetAmount, currentAmount, currentContribution);

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: currentPath.dates.map(d => formatDate(d)),
            datasets: [
                {
                    label: 'Current path',
                    data: currentPath.balances,
                    borderColor: textSecondary,
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3
                },
                {
                    label: 'Your potential',
                    data: currentPath.balances.slice(),
                    borderColor: goldColor,
                    backgroundColor: goldColor + '15',
                    borderWidth: 3,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Target',
                    data: currentPath.balances.map(() => targetAmount),
                    borderColor: glassBorder,
                    borderWidth: 1,
                    borderDash: [4, 4],
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1400,
                easing: 'easeInOutQuart'
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: textSecondary,
                        font: { family: 'Inter, sans-serif', size: 11 },
                        usePointStyle: true,
                        pointStyleWidth: 16,
                        padding: 16
                    },
                    afterFit(legend) { legend.height += 24; }
                },
                tooltip: {
                    backgroundColor: 'rgba(2, 4, 8, 0.9)',
                    titleColor: goldColor,
                    bodyColor: '#ffffff',
                    borderColor: glassBorder,
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    titleFont: { family: 'Cormorant Garamond, serif', size: 14 },
                    bodyFont: { family: 'Inter, sans-serif', size: 12 },
                    callbacks: {
                        label: function(ctx) {
                            return ctx.dataset.label + ': £' + ctx.parsed.y.toLocaleString('en-GB', {
                                minimumFractionDigits: 2, maximumFractionDigits: 2
                            });
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    ticks: {
                        color: textTertiary,
                        font: { family: 'Inter, sans-serif', size: 11 },
                        maxTicksLimit: 4,
                        maxRotation: 0,
                        autoSkipPadding: 16
                    },
                    grid: { display: false }
                },
                y: {
                    display: true,
                    ticks: {
                        color: textTertiary,
                        font: { family: 'Inter, sans-serif', size: 11 },
                        callback: function(value) {
                            return '£' + value.toLocaleString('en-GB');
                        }
                    },
                    grid: {
                        color: 'rgba(255,255,255,0.03)'
                    }
                }
            }
        }
    });

    return chart;
}

/**
 * Updates the gold line (proposed path) when the slider moves.
 * The grey line (current path) stays fixed for contrast.
 */
function updateProjection(chart, targetAmount, currentAmount, newContribution, elements) {
    const proposed = projectGoal(targetAmount, currentAmount, newContribution);

    // Update labels and gold dataset
    chart.data.labels = proposed.dates.map(d => formatDate(d));
    chart.data.datasets[1].data = proposed.balances;

    // Extend target line to match new length
    chart.data.datasets[2].data = proposed.balances.map(() => targetAmount);

    // Extend grey line if needed (pad with last value)
    const currentData = chart.data.datasets[0].data;
    while (currentData.length < proposed.balances.length) {
        currentData.push(currentData[currentData.length - 1]);
    }
    // Trim if proposed is shorter
    chart.data.datasets[0].data = currentData.slice(0, proposed.balances.length);

    chart.update('active');

    // Update text elements
    if (elements.arrivalDate) {
        elements.arrivalDate.textContent = proposed.reachable ? formatDate(proposed.dates[proposed.dates.length - 1]) : 'Not reachable';
    }
    if (elements.monthsDisplay) {
        elements.monthsDisplay.textContent = formatDuration(proposed.months);
    }
    if (elements.interestDisplay) {
        elements.interestDisplay.textContent = '£' + proposed.interestEarned.toLocaleString('en-GB', {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        });
    }
    if (elements.contributionDisplay) {
        elements.contributionDisplay.textContent = '£' + (newContribution * proposed.months).toLocaleString('en-GB', {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        });
    }
    if (elements.sliderValue) {
        elements.sliderValue.textContent = '£' + newContribution.toFixed(2);
    }

    return proposed;
}

/**
 * Initialises the habit cost bar chart.
 */
function initHabitChart(canvasId, horizons) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const ctx = canvas.getContext('2d');

    const style = getComputedStyle(document.body);
    const goldColor = style.getPropertyValue('--roman-gold').trim() || '#C5A35D';
    const textSecondary = style.getPropertyValue('--text-secondary').trim() || 'rgba(255,255,255,0.5)';
    const textTertiary = style.getPropertyValue('--text-tertiary').trim() || 'rgba(255,255,255,0.3)';
    const successColor = style.getPropertyValue('--success').trim() || '#2D6A4F';

    const labels = ['5 years', '10 years', '20 years'];
    const simpleCosts = [
        horizons['5_year'].simple_cost,
        horizons['10_year'].simple_cost,
        horizons['20_year'].simple_cost
    ];
    const opportunityCosts = [
        horizons['5_year'].opportunity_cost,
        horizons['10_year'].opportunity_cost,
        horizons['20_year'].opportunity_cost
    ];

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Amount spent',
                    data: simpleCosts,
                    backgroundColor: textSecondary,
                    borderRadius: 6
                },
                {
                    label: 'What it could have grown to',
                    data: opportunityCosts,
                    backgroundColor: goldColor,
                    borderRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1200,
                easing: 'easeInOutQuart'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: textSecondary,
                        font: { family: 'Inter, sans-serif', size: 11 },
                        usePointStyle: true,
                        pointStyleWidth: 16,
                        padding: 16
                    },
                    afterFit(legend) { legend.height += 24; }
                },
                tooltip: {
                    backgroundColor: 'rgba(2, 4, 8, 0.9)',
                    titleColor: goldColor,
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(197,163,93,0.12)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    padding: 12,
                    callbacks: {
                        label: function(ctx) {
                            return ctx.dataset.label + ': £' + ctx.parsed.y.toLocaleString('en-GB', {
                                minimumFractionDigits: 2, maximumFractionDigits: 2
                            });
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: textTertiary,
                        font: { family: 'Inter, sans-serif', size: 11 }
                    },
                    grid: { display: false }
                },
                y: {
                    ticks: {
                        color: textTertiary,
                        font: { family: 'Inter, sans-serif', size: 11 },
                        callback: function(v) { return '£' + v.toLocaleString('en-GB'); }
                    },
                    grid: { color: 'rgba(255,255,255,0.03)' }
                }
            }
        }
    });
}