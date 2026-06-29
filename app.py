import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import traceback

# Import our quantitative simulation functions
from simulator import simulate_gbm, get_historical_parameters

# Page settings
st.set_page_config(
    page_title="Alpha Nexus | Monte Carlo Stock Simulator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
<style>
    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    /* Sidebar styling adjustment */
    .css-1d391kg {
        background-color: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

# Application Header
st.title("📈 Alpha Nexus: Monte Carlo Stock Simulator")
st.markdown(
    "A high-performance stock trajectory projection engine powered by Geometric Brownian Motion (GBM) "
    "and vectorized NumPy operations. Originally built in C++, now modernized in Python."
)
st.markdown("---")

# Sidebar Configuration
st.sidebar.header("⚙️ Simulation Settings")

# 1. Stock Ticker Input
ticker_input = st.sidebar.text_input("Stock Ticker", value="AAPL", help="Enter a valid stock ticker symbol (e.g., AAPL, MSFT, TSLA, GOOG)").upper().strip()

# 2. Parameter Source Toggle
param_source = st.sidebar.radio(
    "Parameter Selection Mode",
    ["Auto-calculate from Historical Data", "Manual Parameter Override"],
    help="Select whether to estimate expected drift and volatility from historical data or define them manually."
)

# Default values
S0 = 100.0
drift = 0.10
volatility = 0.20
historical_data = None
param_error = None

# If auto-calculate, fetch data and estimate parameters
if param_source == "Auto-calculate from Historical Data":
    lookback_period = st.sidebar.selectbox(
        "Historical Lookback Period",
        ["6mo", "1y", "2y", "5y"],
        index=1,
        help="The time window of historical daily closing prices used to calculate drift and volatility."
    )
    
    if ticker_input:
        try:
            with st.spinner(f"Fetching historical data for {ticker_input}..."):
                S0, drift, volatility, historical_data = get_historical_parameters(ticker_input, period=lookback_period)
            
            # Display calculated parameters in sidebar as informational metrics
            st.sidebar.markdown("### 📊 Estimated Parameters")
            st.sidebar.metric("Last Close Price", f"${S0:,.2f}")
            st.sidebar.metric("Annualized Drift (μ)", f"{drift * 100:.2f}%")
            st.sidebar.metric("Annualized Volatility (σ)", f"{volatility * 100:.2f}%")
        except Exception as e:
            param_error = str(e)
            st.sidebar.error(f"Error fetching parameters: {param_error}")
else:
    # Manual Input overrides
    st.sidebar.markdown("### ✏️ Custom Parameters")
    S0 = st.sidebar.number_input("Starting Stock Price ($)", min_value=0.01, value=100.0, step=1.0, format="%.2f")
    drift = st.sidebar.slider("Expected Annualized Drift (μ)", min_value=-100.0, max_value=100.0, value=10.0, step=0.5) / 100.0
    volatility = st.sidebar.slider("Expected Annualized Volatility (σ)", min_value=1.0, max_value=150.0, value=20.0, step=0.5) / 100.0

st.sidebar.markdown("---")
st.sidebar.header("🚀 Run Parameters")

# 3. Path & Horizon Controls
num_paths = st.sidebar.slider(
    "Number of Simulation Paths",
    min_value=100,
    max_value=1000,
    value=500,
    step=50,
    help="The total number of random walks to simulate. Higher numbers yield more accurate risk distributions."
)

horizon_days = st.sidebar.slider(
    "Time Horizon (Trading Days)",
    min_value=30,
    max_value=365,
    value=252,
    step=10,
    help="Number of trading days into the future to project (252 trading days = 1 year)."
)

# Run simulation trigger
run_button = st.sidebar.button("Run Simulation", type="primary", use_container_width=True)

# Display error if yfinance failed and we are in auto mode
if param_error:
    st.error(
        f"⚠️ **Could not fetch parameters for '{ticker_input}':** {param_error}\n\n"
        "Please check the ticker spelling, network connection, or switch to **Manual Parameter Override** mode."
    )
else:
    # Perform simulation (automatically run on load or button click)
    # We cache results or keep them in session state to prevent rerun lag
    if "simulation_results" not in st.session_state or run_button:
        # Run GBM simulation
        # Daily time steps
        dt = 1.0 / 252.0
        simulated_paths = simulate_gbm(S0, drift, volatility, horizon_days, num_paths, dt)
        
        # Save results in session state
        st.session_state.simulation_results = {
            "paths": simulated_paths,
            "S0": S0,
            "drift": drift,
            "volatility": volatility,
            "num_paths": num_paths,
            "horizon_days": horizon_days,
            "ticker": ticker_input if param_source == "Auto-calculate from Historical Data" else "Manual Asset"
        }
        
    # Retrieve cached simulation outputs
    sim_data = st.session_state.simulation_results
    paths = sim_data["paths"]
    
    # Calculate statistics on final ending values
    final_prices = paths[:, -1]
    mean_ending = np.mean(final_prices)
    median_ending = np.median(final_prices)
    worst_case = np.percentile(final_prices, 5) # 5th percentile (representing VaR style downside)
    best_case = np.percentile(final_prices, 95)  # 95th percentile (representing upside)
    
    # Grid layout for summary metrics
    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
    with m_col1:
        st.metric("Starting Price", f"${sim_data['S0']:,.2f}")
    with m_col2:
        st.metric("Mean Ending Price", f"${mean_ending:,.2f}", f"{(mean_ending - sim_data['S0'])/sim_data['S0']*100:+.2f}%")
    with m_col3:
        st.metric("Median Ending Price", f"${median_ending:,.2f}", f"{(median_ending - sim_data['S0'])/sim_data['S0']*100:+.2f}%")
    with m_col4:
        st.metric("Worst-Case (5%)", f"${worst_case:,.2f}", f"{(worst_case - sim_data['S0'])/sim_data['S0']*100:+.2f}%")
    with m_col5:
        st.metric("Best-Case (95%)", f"${best_case:,.2f}", f"{(best_case - sim_data['S0'])/sim_data['S0']*100:+.2f}%")
        
    st.markdown("---")
    
    # Tabs for Visualizations
    tab1, tab2, tab3 = st.tabs(["📈 Simulation Paths", "📊 Distribution & Risk Analytics", "📋 Historical Data"])
    
    with tab1:
        st.subheader("Simulated Price Trajectories")
        st.markdown(
            "Showing the projected price walks over time. The **golden bold line** represents the median path "
            "which represents the 50th percentile outcome."
        )
        
        # Build paths DataFrame for plotting
        days_axis = np.arange(horizon_days + 1)
        
        # Sample up to 100 paths for Plotly plotting performance
        num_plot_paths = min(100, num_paths)
        plot_indices = np.random.choice(num_paths, size=num_plot_paths, replace=False)
        
        # Find the path closest to the median final price to represent the median scenario
        median_idx = np.argmin(np.abs(final_prices - median_ending))
        
        # Setup Plotly line chart
        fig_paths = go.Figure()
        
        # Add background paths
        for idx in plot_indices:
            if idx == median_idx:
                continue # Plot median path separately
            fig_paths.add_trace(go.Scatter(
                x=days_axis,
                y=paths[idx],
                mode='lines',
                line=dict(color='rgba(99, 102, 241, 0.15)', width=1),
                hoverinfo='none',
                showlegend=False
            ))
            
        # Add the Median Path (Bold)
        fig_paths.add_trace(go.Scatter(
            x=days_axis,
            y=paths[median_idx],
            mode='lines',
            line=dict(color='#F59E0B', width=3.5),
            name='Median Path (50th Percentile)',
            hovertemplate='Day %{x}: $%{y:,.2f}<extra></extra>'
        ))
        
        # Add starting price line for reference
        fig_paths.add_trace(go.Scatter(
            x=[0, horizon_days],
            y=[sim_data['S0'], sim_data['S0']],
            mode='lines',
            line=dict(color='rgba(239, 68, 68, 0.5)', width=1.5, dash='dash'),
            name='Starting Price Baseline'
        ))
        
        fig_paths.update_layout(
            xaxis_title="Trading Days",
            yaxis_title="Stock Price ($)",
            hovermode="x unified",
            template="plotly_dark",
            margin=dict(l=20, r=20, t=20, b=20),
            height=500,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(10, 10, 10, 0.6)"
            )
        )
        st.plotly_chart(fig_paths, use_container_width=True)
        
    with tab2:
        st.subheader("Terminal Price Distribution")
        st.markdown(
            "This histogram shows the probability density distribution of the stock price at the end of the "
            f"**{horizon_days}-day** simulation window."
        )
        
        # Create Terminal Price Histogram
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=final_prices,
            nbinsx=40,
            name="Ending Price Density",
            marker_color='#6366F1',
            opacity=0.75,
            hovertemplate='Price Range: %{x}<br>Frequency: %{y}<extra></extra>'
        ))
        
        # Add line indicators for key percentiles
        percentile_lines = [
            (worst_case, 'Worst-case (5th Percentile)', '#EF4444'),
            (median_ending, 'Median Final Price', '#F59E0B'),
            (best_case, 'Best-case (95th Percentile)', '#10B981')
        ]
        
        for val, label, color in percentile_lines:
            fig_dist.add_vline(
                x=val,
                line_width=2,
                line_dash="dash",
                line_color=color,
                annotation_text=f"{label}: ${val:,.2f}",
                annotation_position="top right",
                annotation_font=dict(color=color, size=11)
            )
            
        fig_dist.update_layout(
            xaxis_title="Terminal Stock Price ($)",
            yaxis_title="Path Count",
            template="plotly_dark",
            margin=dict(l=20, r=20, t=50, b=20),
            height=450,
            showlegend=False
        )
        
        # Risk stats section
        r_col1, r_col2 = st.columns([2, 1])
        with r_col1:
            st.plotly_chart(fig_dist, use_container_width=True)
        with r_col2:
            st.markdown("### 🛡️ Risk & Probability Analysis")
            
            # Probability of profit calculation (final price > starting price)
            prob_profit = np.mean(final_prices > sim_data['S0']) * 100.0
            
            # Value at Risk (VaR)
            # Maximum loss at 95% confidence level (relative to start price)
            ending_returns = (final_prices - sim_data['S0']) / sim_data['S0']
            var_95_return = np.percentile(ending_returns, 5) # 5% worse return
            var_95_val = sim_data['S0'] * abs(var_95_return) if var_95_return < 0 else 0.0
            
            st.markdown(f"""
            - **Probability of Profit (Ending Price > Starting Price):** `{prob_profit:.1f}%`
            - **Value at Risk (95% Confidence Level):** 
              - There is a 95% statistical probability that the maximum loss will not exceed **{abs(var_95_return)*100:.1f}%** (or **${var_95_val:,.2f}** per share).
            - **Distribution Skewness:**
              - The distribution is log-normal (skewed to the right), showing that stock prices have a bounded downside ($0) but theoretically unlimited upside.
            """)
            
            # Quick summary stats block
            stats_df = pd.DataFrame({
                "Metric": ["Minimum Final Price", "10th Percentile", "Median (50th)", "Mean (Average)", "90th Percentile", "Maximum Final Price"],
                "Value": [
                    f"${np.min(final_prices):,.2f}",
                    f"${np.percentile(final_prices, 10):,.2f}",
                    f"${median_ending:,.2f}",
                    f"${mean_ending:,.2f}",
                    f"${np.percentile(final_prices, 90):,.2f}",
                    f"${np.max(final_prices):,.2f}"
                ]
            })
            st.table(stats_df)
            
    with tab3:
        st.subheader("Historical Stock Variance")
        if historical_data is not None:
            st.markdown(
                f"Historical daily price charts and performance for **{ticker_input}** over the selected "
                f"lookback window."
            )
            
            # Plot historical stock price
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Scatter(
                x=historical_data.index,
                y=historical_data['Close'],
                mode='lines',
                line=dict(color='#10B981', width=2),
                name='Close Price',
                hovertemplate='Date: %{x}<br>Close: $%{y:,.2f}<extra></extra>'
            ))
            
            fig_hist.update_layout(
                xaxis_title="Date",
                yaxis_title="Historical Stock Price ($)",
                hovermode="x unified",
                template="plotly_dark",
                margin=dict(l=20, r=20, t=20, b=20),
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_hist, use_container_width=True)
            
            # Show standard table statistics
            st.markdown("### 📋 Recent Data Records")
            st.dataframe(
                historical_data[['Open', 'High', 'Low', 'Close', 'Volume']].tail(10).iloc[::-1],
                use_container_width=True
            )
        else:
            st.info("Historical data is not available when manually overriding simulation parameters.")
