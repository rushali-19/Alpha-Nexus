# Monte Carlo Stock Simulator (Web based)

A lightweight, high-performance web application built entirely in Python that uses Geometric Brownian Motion (GBM) and vectorized NumPy operations to project future stock trajectories based on historical financial market variance.




---

##  Key Features

* **Real-Time Stock Data Integration:** Fetch historical market data instantly using `yfinance` to automatically configure simulation parameters based on real assets.
* **Vectorized Multi-Path Simulation:** High-performance, vectorized NumPy computations generating hundreds of stock price trajectories using Geometric Brownian Motion (GBM).
* **Manual Parameter Override:** Fine-tune starting stock price, expected annual return (drift), and annual volatility to test custom market conditions or stress tests.
* **Interactive Data Visualization:** Custom-built Streamlit UI featuring interactive Plotly charts:
  * **Simulated Price Trajectories:** Plots paths over time, dynamically highlighting the bold median path.
  * **Terminal Price Distribution:** Histogram of final simulated price states highlighting statistical downside (5th percentile) and upside (95th percentile).
* **Statistical Risk Analytics:** Instantly displays Value at Risk (VaR) estimates and probability of profit (final price > starting price).

---

##  Mathematical Foundations

The future trajectories are generated step-by-step using the discretized solution to the Geometric Brownian Motion (GBM) stochastic differential equation:

$$S_t = S_0 \cdot \exp\left(\left(\mu - \frac{\sigma^2}{2}\right)dt + \sigma \sqrt{dt} Z\right)$$

Where:
* $S_t$: Simulated stock price at day $t$.
* $S_0$: Starting stock price (e.g. the last historical close price).
* $\mu$ (Drift): Annualized expected rate of return.
* $\sigma$ (Volatility): Annualized standard deviation of asset log returns.
* $dt$: Time step size (fixed at $1 / 252$ trading days).
* $Z$: Standard normal random variable, $Z \sim \mathcal{N}(0, 1)$.

---

##  Prerequisites & Installation

To run the simulator locally, you need **Python 3.8+** installed.

### 1. Clone the Repository
```bash
git clone https://github.com/rushali-19/alpha-nexus.git
cd alpha-nexus
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
Install all required libraries pinned in `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 💻 Running the Application

Launch the Streamlit dashboard on your local machine:
```bash
streamlit run app.py
```

Once running, the application will print the local URL:
```text
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.100:8501
```
Open **`http://localhost:8501`** in your web browser to interact with the simulator.

---

##  Project Structure

```text
alpha-nexus/
│
├── app.py              # Streamlit Web UI and dashboard configuration
├── simulator.py        # Quantitative simulation engine (GBM logic, parameter estimation)
├── requirements.txt    # Python package dependencies
├── README.md           # Project documentation and specifications
└── .gitignore          # Git exclusion rules for venv, cache, and logs
```

---

##  Disclaimer
This simulator is created for educational and research purposes. The mathematical models rely on past historical performance, which is not a guarantee of future stock returns. Use at your own risk.
