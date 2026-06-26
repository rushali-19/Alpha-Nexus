# AlphaNexus - Institutional Portfolio Risk & Monte Carlo Analytics

AlphaNexus is a web-based financial analytics dashboard designed for simulating asset price trajectories, analyzing portfolio risk, and pricing options. 

This project ports the core logic of a C++ Monte Carlo simulator to pure Python, presenting it through a modern, responsive, and glassmorphic dark-theme web dashboard.

## Features

- **Monte Carlo Stock Price Simulator**:
  - Simulates future stock price paths using Geometric Brownian Motion (GBM).
  - Matches the drift, volatility, and random shock algorithms of the original C++ engine.
  - **Dynamic Double Charts**: Displays both **Monte Carlo Paths** (line chart of simulated trajectories) and **Terminal Price Distribution** (histogram of final values) for a selected stock (e.g. AAPL, MSFT) or index.
  - Supports **custom overrides** for drift and volatility.
  - Computes institutional-grade risk metrics including **95% and 99% Value at Risk (VaR)**, **Conditional Value at Risk (CVaR)**, and **Probability of Profit**.
- **Portfolio Optimizer**:
  - Implements Markowitz Mean-Variance Optimization.
  - Simulates thousands of portfolios to draw the **Efficient Frontier**.
  - Pinpoints and displays optimal allocations for the **Max Sharpe Ratio** and **Minimum Volatility** portfolios with interactive doughnut charts.
- **Option Pricing (Black-Scholes Model)**:
  - Valuation of European Call/Put options.
  - Calculates theoretical option prices and provides real-time Greeks (**Delta, Gamma, Theta, Vega, Rho**).

## Tech Stack

- **Backend**: Python 3.x, Flask (Web server), yfinance (Market data feed), NumPy, Pandas, SciPy (Math/Statistics)
- **Frontend**: Vanilla HTML5, CSS3 (Custom Glassmorphism layout), Vanilla ES6 JavaScript
- **Visualizations**: Plotly.js (Paths, Histograms, Frontier), Chart.js (Doughnut charts)

## Setup & Installation

1. Navigate to the project directory:
   ```bash
   cd alpha_nexus
   ```

2. Create a virtual environment and install dependencies (already completed in this sandbox):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Run the unit tests to verify the engine:
   ```bash
   python test_simulator.py
   ```

4. Start the dashboard:
   ```bash
   ./start.sh
   ```

5. Open your browser and navigate to:
   ```text
   http://localhost:5001
   ```

## Disclaimer

This dashboard is for educational and research purposes only. It should not be used as financial advice or as a guide for live trading.
