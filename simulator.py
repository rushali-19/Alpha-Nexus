import numpy as np
import pandas as pd
import yfinance as yf

def simulate_gbm(S0: float, drift: float, volatility: float, horizon: int, num_paths: int, dt: float = 1.0 / 252.0) -> np.ndarray:
    """
    Simulates stock price paths using Geometric Brownian Motion (GBM).
    
    Formula implemented:
        St = S0 * exp(cumsum((drift - 0.5 * volatility^2) * dt + volatility * sqrt(dt) * Z))
        where Z is a standard normal distribution random variable.
        
    Vectorized using NumPy arrays for maximum performance.
    
    Parameters:
    -----------
    S0 : float
        The initial stock price (starting price).
    drift : float
        Annualized expected rate of return (drift).
    volatility : float
        Annualized volatility (standard deviation of log returns).
    horizon : int
        Number of steps (days) to simulate.
    num_paths : int
        Number of simulated paths (trajectories).
    dt : float, optional
        Time step size in years. Default is 1.0 / 252.0 (trading days).
        
    Returns:
    --------
    np.ndarray
        A 2D array of shape (num_paths, horizon + 1) representing simulated price paths.
    """
    # Generate independent standard normal random variables
    # Shape: (num_paths, horizon)
    Z = np.random.normal(0.0, 1.0, size=(num_paths, horizon))
    
    # Calculate daily log returns for each path
    # drift_term = (drift - 0.5 * volatility^2) * dt
    # shock_term = volatility * sqrt(dt) * Z
    log_returns = (drift - 0.5 * (volatility ** 2)) * dt + volatility * np.sqrt(dt) * Z
    
    # Cumulative sum across the time axis (axis=1) to compute cumulative log returns
    cumulative_log_returns = np.cumsum(log_returns, axis=1)
    
    # Compute the price paths: S_t = S_0 * exp(cumulative_log_returns)
    paths = np.empty((num_paths, horizon + 1))
    paths[:, 0] = S0
    paths[:, 1:] = S0 * np.exp(cumulative_log_returns)
    
    return paths

def get_historical_parameters(ticker: str, period: str = "1y") -> tuple[float, float, float, pd.DataFrame]:
    """
    Downloads historical data for a ticker from Yahoo Finance and calculates
    the initial stock price (last close), annualized drift, and annualized volatility.
    
    Parameters:
    -----------
    ticker : str
        The stock symbol (e.g., 'AAPL').
    period : str, optional
        The historical data lookback period (e.g., '6mo', '1y', '2y'). Default is '1y'.
        
    Returns:
    --------
    S0 : float
        The most recent close price.
    drift : float
        Estimated annualized drift (expected log return * 252).
    volatility : float
        Estimated annualized volatility (std of log returns * sqrt(252)).
    history : pd.DataFrame
        The fetched pandas DataFrame with historical stock data.
    """
    cleaned_ticker = ticker.strip().upper()
    if not cleaned_ticker:
        raise ValueError("Ticker symbol cannot be empty.")
        
    stock = yf.Ticker(cleaned_ticker)
    
    # Download daily history (auto-adjusted for splits/dividends)
    history = stock.history(period=period)
    
    if history.empty:
        raise ValueError(f"No historical market data found for ticker: '{cleaned_ticker}'. Please verify the symbol.")
        
    # Extract closing price
    close_prices = history['Close']
    S0 = float(close_prices.iloc[-1])
    
    # Calculate daily log returns: ln(S_t / S_{t-1})
    log_returns = np.log(close_prices / close_prices.shift(1)).dropna()
    
    if len(log_returns) < 5:
        raise ValueError(f"Insufficient data points for ticker '{cleaned_ticker}' to estimate parameters.")
        
    # Annualize the mean and standard deviation of daily log returns (assuming 252 trading days)
    daily_mean = log_returns.mean()
    daily_std = log_returns.std()
    
    drift = float(daily_mean * 252.0)
    volatility = float(daily_std * np.sqrt(252.0))
    
    return S0, drift, volatility, history
