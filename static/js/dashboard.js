// Frontend Logic for AlphaNexus Dashboard

document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initMonteCarlo();
    initPortfolioOptimizer();
    initOptionsPricing();
});

// 1. Navigation Tab Controller
function initTabs() {
    const tabButtons = document.querySelectorAll('#main-tabs .tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // Toggle active buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Toggle active panels
            tabPanels.forEach(panel => {
                if (panel.id === targetTab) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
            
            // Trigger Plotly redraw on tab switch to fix container size issues
            setTimeout(() => {
                const mcChart = document.getElementById('mc-chart');
                const mcHist = document.getElementById('mc-histogram');
                const optChart = document.getElementById('opt-chart');
                if (mcChart && mcChart.data) Plotly.Plots.resize(mcChart);
                if (mcHist && mcHist.data) Plotly.Plots.resize(mcHist);
                if (optChart && optChart.data) Plotly.Plots.resize(optChart);
            }, 100);
        });
    });

    // Portfolio allocation sub-tabs
    const subTabButtons = document.querySelectorAll('.tabs-sub-nav .sub-tab-btn');
    const subTabPanels = document.querySelectorAll('.sub-tab-content .sub-tab-panel');

    subTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetSubTab = btn.getAttribute('data-subtab');
            
            subTabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            subTabPanels.forEach(panel => {
                if (panel.id === targetSubTab) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });
}

// Helper to format currency
function formatCurrency(val) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
}

// Helper to format percentage
function formatPercent(val) {
    return (val * 100).toFixed(2) + '%';
}

// 2. Monte Carlo Simulation Handler
function initMonteCarlo() {
    const form = document.getElementById('mc-form');
    const tickersInput = document.getElementById('mc-tickers');
    const weightsGroup = document.getElementById('portfolio-weights-group');
    const loadingOverlay = document.getElementById('mc-loading');
    const histLoadingOverlay = document.getElementById('mc-hist-loading');
    
    // Toggle portfolio weights field if multiple tickers are entered
    tickersInput.addEventListener('input', () => {
        const val = tickersInput.value;
        if (val.includes(',')) {
            weightsGroup.style.display = 'flex';
        } else {
            weightsGroup.style.display = 'none';
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const tickers = tickersInput.value;
        const weights = document.getElementById('mc-weights').value;
        const period = document.getElementById('mc-period').value;
        const days = document.getElementById('mc-days').value;
        const simulations = document.getElementById('mc-paths').value;
        const plot_paths = document.getElementById('mc-plot-paths').value;
        const drift_override = document.getElementById('mc-drift-override').value;
        const volatility_override = document.getElementById('mc-volatility-override').value;
        
        // Show loading overlays
        loadingOverlay.style.display = 'flex';
        histLoadingOverlay.style.display = 'flex';
        loadingOverlay.querySelector('p').innerText = "Running Monte Carlo stock simulations...";
        
        try {
            const response = await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    tickers, 
                    weights, 
                    period, 
                    days, 
                    simulations, 
                    plot_paths,
                    drift_override,
                    volatility_override
                })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                renderMCSimulation(result, tickers.includes(','));
            } else {
                alert("Error running simulation: " + (result.error || "Unknown error"));
            }
        } catch (err) {
            console.error(err);
            alert("Failed to connect to the backend server.");
        } finally {
            loadingOverlay.style.display = 'none';
            histLoadingOverlay.style.display = 'none';
        }
    });
}

function renderMCSimulation(data, isPortfolio) {
    const dates = data.dates;
    const paths = data.paths;
    const isMultiAsset = Object.keys(paths).length > 1 || isPortfolio;
    
    // Show Hero Stats Bar
    const heroStatsBar = document.getElementById('hero-stats-bar');
    heroStatsBar.style.display = 'flex';
    
    // Clear metrics container
    const metricsContainer = document.getElementById('mc-metrics-container');
    metricsContainer.innerHTML = '';
    
    // Trace arrays
    const lineTraces = [];
    const histTraces = [];
    let titleLine = "Stock Price Simulations";
    let titleHist = "Terminal Price Distribution";
    
    if (!isMultiAsset) {
        // Single asset simulation
        const ticker = Object.keys(paths)[0];
        const tickerPaths = paths[ticker];
        const mostLikelyPath = data.most_likely_path[ticker];
        const terminalPrices = data.terminal_prices[ticker];
        const metrics = data.risk_metrics[ticker];
        const calculatedParams = data.calculated_parameters[ticker];
        
        titleLine = `${ticker} Monte Carlo Paths`;
        titleHist = `${ticker} Terminal Price Distribution`;
        
        // Update Hero Stats Bar
        document.getElementById('hero-current-price').innerText = formatCurrency(metrics.last_close);
        document.getElementById('hero-projected-price').innerText = formatCurrency(mostLikelyPath[mostLikelyPath.length - 1]);
        document.getElementById('hero-var').innerText = formatPercent(metrics.var_95);
        document.getElementById('hero-prob-profit').innerText = metrics.prob_profit.toFixed(1) + '%';
        
        // Plot representative paths in thin semi-transparent lines
        tickerPaths.forEach((path, idx) => {
            lineTraces.push({
                x: dates,
                y: path,
                mode: 'lines',
                line: { color: 'rgba(99, 102, 241, 0.08)', width: 1.5 },
                name: `Path ${idx + 1}`,
                showlegend: false
            });
        });
        
        // Plot most likely path in bold accent color
        lineTraces.push({
            x: dates,
            y: mostLikelyPath,
            mode: 'lines',
            line: { color: '#00f5ff', width: 3 },
            name: 'Median Path (Most Likely)',
            showlegend: true
        });
        
        // Setup Terminal Price Distribution Histogram
        histTraces.push({
            x: terminalPrices,
            type: 'histogram',
            name: 'Ending Prices',
            marker: {
                color: 'rgba(0, 245, 255, 0.4)',
                line: {
                    color: 'rgba(0, 245, 255, 1)',
                    width: 1
                }
            },
            xbins: {
                size: (Math.max(...terminalPrices) - Math.min(...terminalPrices)) / 30
            }
        });
        
        // Add vertical line at median price
        const medianVal = metrics.median_final;
        histTraces.push({
            x: [medianVal, medianVal],
            y: [0, data.terminal_prices[ticker].length / 6],  // arbitrary height for plotting
            mode: 'lines',
            line: {
                color: '#ffc107',
                width: 2,
                dash: 'dash'
            },
            name: 'Median Ending Price',
            hoverinfo: 'x'
        });
        
        // Update Risk metrics UI
        metricsContainer.innerHTML = `
            <div class="metric-row">
                <span class="metric-label">Start Price</span>
                <span class="metric-value">${formatCurrency(metrics.start_price)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Projected Median Price</span>
                <span class="metric-value" style="color: var(--accent);">${formatCurrency(metrics.median_final)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Projected Mean Price</span>
                <span class="metric-value" style="color: var(--accent);">${formatCurrency(metrics.mean_final)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">95% Value at Risk (VaR)</span>
                <span class="metric-value danger">${formatPercent(metrics.var_95)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">95% Conditional VaR (CVaR)</span>
                <span class="metric-value danger">${formatPercent(metrics.cvar_95)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">99% Value at Risk (VaR)</span>
                <span class="metric-value danger" style="font-weight:800;">${formatPercent(metrics.var_99)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">99% Conditional VaR (CVaR)</span>
                <span class="metric-value danger" style="font-weight:800;">${formatPercent(metrics.cvar_99)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Probability of Profit</span>
                <span class="metric-value success" style="font-weight:700;">${metrics.prob_profit.toFixed(2)}%</span>
            </div>
            <div class="metric-row" style="margin-top: 1rem; border-top: 1px solid var(--border-glass); padding-top: 1rem;">
                <span class="metric-label">Daily Drift (Calculated)</span>
                <span class="metric-value" style="font-size: 0.95rem;">${formatPercent(calculatedParams.drift)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Daily Volatility (Calculated)</span>
                <span class="metric-value" style="font-size: 0.95rem;">${formatPercent(calculatedParams.volatility)}</span>
            </div>
        `;
    } else {
        // Portfolio simulation
        const portPaths = data.portfolio_paths;
        const mostLikelyPortPath = data.most_likely_portfolio_path;
        const terminalPrices = data.terminal_prices.Portfolio;
        const metrics = data.risk_metrics.Portfolio;
        
        titleLine = "Portfolio Value Simulation Paths";
        titleHist = "Portfolio Terminal Value Distribution";
        
        // Update Hero Stats Bar
        document.getElementById('hero-current-price').innerText = formatCurrency(metrics.last_close);
        document.getElementById('hero-projected-price').innerText = formatCurrency(mostLikelyPortPath[mostLikelyPortPath.length - 1]);
        document.getElementById('hero-var').innerText = formatPercent(metrics.var_95);
        document.getElementById('hero-prob-profit').innerText = metrics.prob_profit.toFixed(1) + '%';
        
        // Plot portfolio value paths in thin semi-transparent lines
        portPaths.forEach((path, idx) => {
            lineTraces.push({
                x: dates,
                y: path,
                mode: 'lines',
                line: { color: 'rgba(139, 92, 246, 0.08)', width: 1.5 },
                name: `Path ${idx + 1}`,
                showlegend: false
            });
        });
        
        // Plot most likely portfolio path
        lineTraces.push({
            x: dates,
            y: mostLikelyPortPath,
            mode: 'lines',
            line: { color: '#00f5ff', width: 3 },
            name: 'Median Portfolio Path',
            showlegend: true
        });
        
        // Histogram trace
        histTraces.push({
            x: terminalPrices,
            type: 'histogram',
            name: 'Portfolio Ending Values',
            marker: {
                color: 'rgba(139, 92, 246, 0.4)',
                line: {
                    color: 'rgba(139, 92, 246, 1)',
                    width: 1
                }
            },
            xbins: {
                size: (Math.max(...terminalPrices) - Math.min(...terminalPrices)) / 30
            }
        });
        
        // Update Risk metrics UI
        metricsContainer.innerHTML = `
            <div class="metric-row">
                <span class="metric-label">Starting Portfolio Value</span>
                <span class="metric-value">${formatCurrency(metrics.start_price)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Projected Median Value</span>
                <span class="metric-value" style="color: var(--accent);">${formatCurrency(metrics.median_final)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Projected Mean Value</span>
                <span class="metric-value" style="color: var(--accent);">${formatCurrency(metrics.mean_final)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">95% Portfolio VaR</span>
                <span class="metric-value danger">${formatPercent(metrics.var_95)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">95% Portfolio CVaR</span>
                <span class="metric-value danger">${formatPercent(metrics.cvar_95)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">99% Portfolio VaR</span>
                <span class="metric-value danger" style="font-weight:800;">${formatPercent(metrics.var_99)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">99% Portfolio CVaR</span>
                <span class="metric-value danger" style="font-weight:800;">${formatPercent(metrics.cvar_99)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Probability of Profit</span>
                <span class="metric-value success" style="font-weight:700;">${metrics.prob_profit.toFixed(2)}%</span>
            </div>
        `;
    }
    
    // Plot Line Chart
    const lineLayout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        title: {
            text: titleLine,
            font: { color: '#f8fafc', family: 'Outfit', size: 16 }
        },
        xaxis: {
            gridcolor: 'rgba(255,255,255,0.05)',
            tickcolor: 'rgba(255,255,255,0.1)',
            tickfont: { color: '#94a3b8' }
        },
        yaxis: {
            gridcolor: 'rgba(255,255,255,0.05)',
            tickcolor: 'rgba(255,255,255,0.1)',
            tickfont: { color: '#94a3b8' },
            title: { text: isPortfolio ? 'Portfolio Value ($)' : 'Stock Price ($)', font: { color: '#94a3b8' } }
        },
        margin: { l: 60, r: 20, t: 40, b: 40 },
        legend: {
            font: { color: '#94a3b8' },
            x: 0,
            y: 1
        }
    };
    
    Plotly.newPlot('mc-chart', lineTraces, lineLayout, { responsive: true, displayModeBar: false });
    
    // Plot Histogram Chart (Terminal Distribution)
    const histLayout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        title: {
            text: titleHist,
            font: { color: '#f8fafc', family: 'Outfit', size: 16 }
        },
        xaxis: {
            gridcolor: 'rgba(255,255,255,0.05)',
            tickcolor: 'rgba(255,255,255,0.1)',
            tickfont: { color: '#94a3b8' },
            title: { text: isPortfolio ? 'Ending Portfolio Value ($)' : 'Ending Stock Price ($)', font: { color: '#94a3b8' } }
        },
        yaxis: {
            gridcolor: 'rgba(255,255,255,0.05)',
            tickcolor: 'rgba(255,255,255,0.1)',
            tickfont: { color: '#94a3b8' },
            title: { text: 'Count (Frequency)', font: { color: '#94a3b8' } }
        },
        margin: { l: 60, r: 20, t: 40, b: 40 },
        showlegend: false
    };
    
    Plotly.newPlot('mc-histogram', histTraces, histLayout, { responsive: true, displayModeBar: false });
}

// 3. Portfolio Optimizer Handler
let maxSharpeChartInstance = null;
let minVolChartInstance = null;

function initPortfolioOptimizer() {
    const form = document.getElementById('opt-form');
    const loadingOverlay = document.getElementById('opt-loading');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const tickers = document.getElementById('opt-tickers').value;
        const period = document.getElementById('opt-period').value;
        const rf_rate = document.getElementById('opt-rf').value;
        const simulations = document.getElementById('opt-simulations').value;
        
        loadingOverlay.style.display = 'flex';
        loadingOverlay.querySelector('p').innerText = "Generating efficient frontier...";
        
        try {
            const response = await fetch('/api/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tickers, period, rf_rate, simulations })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                renderOptimization(result);
            } else {
                alert("Error running optimizer: " + (result.error || "Unknown error"));
            }
        } catch (err) {
            console.error(err);
            alert("Failed to connect to the backend server.");
        } finally {
            loadingOverlay.style.display = 'none';
        }
    });
}

function renderOptimization(data) {
    const sims = data.simulations;
    const maxS = data.max_sharpe;
    const minV = data.min_vol;
    
    const traceAll = {
        x: sims.volatilities,
        y: sims.returns,
        mode: 'markers',
        marker: {
            size: 5,
            color: sims.sharpe_ratios,
            colorscale: 'Viridis',
            colorbar: {
                title: { text: 'Sharpe Ratio', font: { color: '#94a3b8' } },
                tickfont: { color: '#94a3b8' }
            },
            showscale: true
        },
        name: 'Random Portfolios',
        text: sims.sharpe_ratios.map(s => `Sharpe: ${s.toFixed(2)}`),
        hoverinfo: 'x+y+text'
    };
    
    const traceMaxSharpe = {
        x: [maxS.volatility],
        y: [maxS.return],
        mode: 'markers',
        marker: {
            color: '#ff3366',
            size: 14,
            symbol: 'star',
            line: { color: '#ffffff', width: 1 }
        },
        name: 'Max Sharpe Ratio',
        hoverinfo: 'name'
    };
    
    const traceMinVol = {
        x: [minV.volatility],
        y: [minV.return],
        mode: 'markers',
        marker: {
            color: '#00f5ff',
            size: 14,
            symbol: 'diamond',
            line: { color: '#ffffff', width: 1 }
        },
        name: 'Min Volatility',
        hoverinfo: 'name'
    };
    
    const layout = {
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        xaxis: {
            gridcolor: 'rgba(255,255,255,0.05)',
            tickcolor: 'rgba(255,255,255,0.1)',
            tickfont: { color: '#94a3b8' },
            title: { text: 'Expected Volatility (Standard Deviation)', font: { color: '#94a3b8' } }
        },
        yaxis: {
            gridcolor: 'rgba(255,255,255,0.05)',
            tickcolor: 'rgba(255,255,255,0.1)',
            tickfont: { color: '#94a3b8' },
            title: { text: 'Expected Annualized Return', font: { color: '#94a3b8' } }
        },
        margin: { l: 60, r: 20, t: 20, b: 40 },
        legend: {
            font: { color: '#94a3b8' },
            x: 0,
            y: 1
        }
    };
    
    Plotly.newPlot('opt-chart', [traceAll, traceMaxSharpe, traceMinVol], layout, { responsive: true, displayModeBar: false });
    
    renderAllocationTab('max-sharpe', maxS, 'max-sharpe-chart', 'max-sharpe-details');
    renderAllocationTab('min-vol', minV, 'min-vol-chart', 'min-vol-details');
}

function renderAllocationTab(type, portfolio, canvasId, detailsId) {
    const labels = Object.keys(portfolio.weights);
    const weights = Object.values(portfolio.weights);
    
    if (type === 'max-sharpe' && maxSharpeChartInstance) {
        maxSharpeChartInstance.destroy();
    } else if (type === 'min-vol' && minVolChartInstance) {
        minVolChartInstance.destroy();
    }
    
    const ctx = document.getElementById(canvasId).getContext('2d');
    const colors = [
        '#6366f1', '#8b5cf6', '#00f5ff', '#10b981', '#f59e0b', '#ec4899', '#3b82f6', '#14b8a6'
    ];
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: weights,
                backgroundColor: colors.slice(0, labels.length),
                borderColor: 'rgba(15, 22, 42, 0.8)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 10 } }
                }
            }
        }
    });
    
    if (type === 'max-sharpe') maxSharpeChartInstance = chart;
    else minVolChartInstance = chart;
    
    const detailsContainer = document.getElementById(detailsId);
    let tableHtml = `
        <div class="metric-row margin-top">
            <span class="metric-label">Expected Annual Return</span>
            <span class="metric-value success">${formatPercent(portfolio.return)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Annualized Volatility</span>
            <span class="metric-value warning">${formatPercent(portfolio.volatility)}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Sharpe Ratio</span>
            <span class="metric-value" style="color:var(--accent); font-weight:800;">${portfolio.sharpe.toFixed(2)}</span>
        </div>
        <table class="allocation-table">
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Allocation</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    labels.forEach((ticker, idx) => {
        tableHtml += `
            <tr>
                <td><i class="fa-solid fa-circle" style="color: ${colors[idx % colors.length]}; font-size: 8px; margin-right: 6px;"></i>${ticker}</td>
                <td style="font-weight: 600;">${formatPercent(weights[idx])}</td>
            </tr>
        `;
    });
    
    tableHtml += `
            </tbody>
        </table>
    `;
    detailsContainer.innerHTML = tableHtml;
}

// 4. Options Pricing Handler (Black-Scholes)
function initOptionsPricing() {
    const form = document.getElementById('options-form');
    const metricsContainer = document.getElementById('options-metrics-container');
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const ticker = document.getElementById('opt-ticker').value;
        const strike = document.getElementById('opt-strike').value;
        const expiry = document.getElementById('opt-expiry').value;
        const rf_rate = document.getElementById('opt-rf-rate').value;
        const option_type = document.getElementById('opt-type').value;
        
        metricsContainer.innerHTML = `
            <div class="placeholder-text text-center">
                <div class="spinner" style="margin: 0 auto 1rem auto;"></div>
                Calculating Black-Scholes pricing & Greeks...
            </div>
        `;
        
        try {
            const response = await fetch('/api/options', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticker, strike, expiry, rf_rate, option_type })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                renderOptionResults(result, option_type);
            } else {
                alert("Error pricing option: " + (result.error || "Unknown error"));
                metricsContainer.innerHTML = `
                    <p class="placeholder-text" style="color: var(--danger);">
                        Failed to calculate option details. Check ticker symbol or inputs.
                    </p>
                `;
            }
        } catch (err) {
            console.error(err);
            alert("Failed to connect to the server.");
        }
    });
}

function renderOptionResults(data, optionType) {
    const metricsContainer = document.getElementById('options-metrics-container');
    
    metricsContainer.innerHTML = `
        <div class="option-results-grid">
            <div class="option-result-box price-box">
                <span class="option-label">Theoretical ${optionType.toUpperCase()} Price</span>
                <span class="option-value">${formatCurrency(data.price)}</span>
                <span class="option-desc">Underlying Close: ${formatCurrency(data.stock_price)} | Volatility: ${formatPercent(data.volatility_used)}</span>
            </div>
            
            <div class="option-result-box">
                <span class="option-label">Delta (Δ)</span>
                <span class="option-value" style="color: ${data.delta >= 0 ? 'var(--success)' : 'var(--danger)'};">${data.delta.toFixed(4)}</span>
                <span class="option-desc">Per $1 change in stock.</span>
            </div>
            
            <div class="option-result-box">
                <span class="option-label">Gamma (Γ)</span>
                <span class="option-value">${data.gamma.toFixed(4)}</span>
                <span class="option-desc">Delta change per $1 change.</span>
            </div>
            
            <div class="option-result-box">
                <span class="option-label">Theta (Θ - Daily)</span>
                <span class="option-value danger">${formatCurrency(data.theta_daily)}</span>
                <span class="option-desc">Time decay loss per day.</span>
            </div>
            
            <div class="option-result-box">
                <span class="option-label">Vega (ν - 1%)</span>
                <span class="option-value warning">${formatCurrency(data.vega_1pct)}</span>
                <span class="option-desc">Change per 1% vol increase.</span>
            </div>
            
            <div class="option-result-box" style="grid-column: span 2;">
                <span class="option-label">Rho (ρ)</span>
                <span class="option-value">${data.rho.toFixed(4)}</span>
                <span class="option-desc">Interest rate sensitivity (1% change).</span>
            </div>
        </div>
    `;
}
