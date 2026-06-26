import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import norm
import datetime

class MonteCarloSimulator:
    def __init__(self, tickers, lookback_period="1y"):
        """
        tickers: list of stock symbols (e.g. ['AAPL']) or multiple (['AAPL', 'MSFT'])
        lookback_period: yfinance period string ('6mo', '1y', '2y')
        """
        if isinstance(tickers, str):
            self.tickers = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        else:
            self.tickers = [t.strip().upper() for t in tickers]
        self.lookback_period = lookback_period
        self.historical_data = None
        self.returns = None
        self.mean_returns = None
        self.cov_matrix = None
        self.last_prices = None

    def fetch_data(self):
        """Fetch stock closing prices from yfinance."""
        if not self.tickers:
            raise ValueError("No tickers provided.")
        
        # Download historical closing prices
        data = yf.download(self.tickers, period=self.lookback_period, interval='1d')
        
        if data.empty:
            raise ValueError(f"No historical data found for tickers: {self.tickers}")
        
        # Handle single ticker vs multi-ticker data format
        if len(self.tickers) == 1:
            ticker = self.tickers[0]
            if isinstance(data.columns, pd.MultiIndex):
                # If yfinance returns multi-index, flatten it
                data.columns = data.columns.get_level_values(0)
            
            if 'Adj Close' in data.columns:
                df = data['Adj Close'].to_frame(name=ticker)
            elif 'Close' in data.columns:
                df = data['Close'].to_frame(name=ticker)
            else:
                df = data.iloc[:, [0]].rename(columns={data.columns[0]: ticker})
        else:
            if 'Adj Close' in data.columns:
                df = data['Adj Close']
            elif 'Close' in data.columns:
                df = data['Close']
            else:
                df = data.iloc[:, 0:len(self.tickers)]
            
            # Ensure column order matches self.tickers
            df = df[self.tickers]
        
        # Forward fill and drop any initial NaNs
        df = df.ffill().dropna()
        if df.empty:
            raise ValueError("Data contains too many missing values.")
            
        self.historical_data = df
        self.last_prices = df.iloc[-1].to_dict()
        
        # Calculate daily log returns: ln(S_t / S_{t-1})
        self.returns = np.log(df / df.shift(1)).dropna()
        self.mean_returns = self.returns.mean()
        self.cov_matrix = self.returns.cov()
        
        return self.historical_data

    def run_simulation(self, days=126, num_simulations=100, weights=None, drift_override=None, volatility_override=None, plot_paths=30):
        """
        Runs Monte Carlo simulations using Geometric Brownian Motion.
        If weights are provided and there are multiple tickers, simulates the portfolio.
        
        Parameters:
        - days: Number of days to simulate into the future
        - num_simulations: Number of paths to run
        - weights: List of portfolio weights
        - drift_override: Optional daily drift percentage override (e.g. 0.05 for 5%)
        - volatility_override: Optional daily volatility percentage override
        - plot_paths: Number of representative paths to return in the response
        """
        if self.historical_data is None:
            self.fetch_data()
            
        num_assets = len(self.tickers)
        last_date = self.historical_data.index[-1]
        
        # Generate future dates (calendar days or trading days, let's use trading days: Mon-Fri)
        future_dates = []
        curr_date = last_date
        while len(future_dates) < days:
            curr_date += datetime.timedelta(days=1)
            if curr_date.weekday() < 5:  # Mon-Fri
                future_dates.append(curr_date.strftime('%Y-%m-%d'))
                
        sim_dates = [last_date.strftime('%Y-%m-%d')] + future_dates
        
        # Output structure
        results = {
            "dates": sim_dates,
            "paths": {},
            "most_likely_path": {},
            "risk_metrics": {},
            "calculated_parameters": {},
            "terminal_prices": {}
        }
        
        if num_assets == 1:
            ticker = self.tickers[0]
            S0 = self.last_prices[ticker]
            
            # Compute parameters from historical daily returns
            mu = float(self.mean_returns[ticker])
            var = float(self.returns[ticker].var())
            sigma = float(self.returns[ticker].std())
            
            # C++ formula: drift = mean - variance/2
            drift = mu - 0.5 * var
            volatility = sigma
            
            # Apply overrides if provided (convert from percent to decimal)
            if drift_override is not None:
                drift = drift_override / 100.0
            if volatility_override is not None:
                volatility = volatility_override / 100.0
            
            # Generate random shocks
            # Shape: (num_simulations, days)
            Z = np.random.normal(0, 1, size=(num_simulations, days))
            
            # Calculate paths: S_t = S_0 * exp(cumsum(drift + volatility * Z_t))
            paths = np.ones((num_simulations, days + 1))
            paths[:, 0] = S0
            paths[:, 1:] = S0 * np.exp(np.cumsum(drift + volatility * Z, axis=1))
            
            # Log likelihood: -0.5 * sum(Z_t^2)
            log_likelihoods = -0.5 * np.sum(Z ** 2, axis=1)
            most_likely_idx = int(np.argmax(log_likelihoods))
            
            # Calculate risk metrics based on terminal values
            final_prices = paths[:, -1]
            losses_pct = (S0 - final_prices) / S0  # relative loss
            
            var_95 = float(np.percentile(losses_pct, 95))
            var_99 = float(np.percentile(losses_pct, 99))
            cvar_95 = float(losses_pct[losses_pct >= var_95].mean() if np.any(losses_pct >= var_95) else var_95)
            cvar_99 = float(losses_pct[losses_pct >= var_99].mean() if np.any(losses_pct >= var_99) else var_99)
            
            prob_profit = float(np.mean(final_prices > S0) * 100.0)
            
            # Only send first plot_paths to prevent rendering lag
            results["paths"][ticker] = paths[:plot_paths].tolist()
            results["terminal_prices"][ticker] = final_prices.tolist()
            results["most_likely_path"][ticker] = paths[most_likely_idx].tolist()
            results["risk_metrics"][ticker] = {
                "var_95": var_95,
                "var_99": var_99,
                "cvar_95": cvar_95,
                "cvar_99": cvar_99,
                "start_price": S0,
                "last_close": S0,
                "prob_profit": prob_profit,
                "mean_final": float(np.mean(final_prices)),
                "median_final": float(np.median(final_prices))
            }
            
            # Calculated daily parameters
            results["calculated_parameters"][ticker] = {
                "drift": drift,
                "volatility": volatility,
                "mean_return": mu,
                "variance": var
            }
            
        else:
            # Correlated Multi-Asset Simulation
            if weights is None:
                weights = np.ones(num_assets) / num_assets
            else:
                weights = np.array([float(w) for w in weights])
                weights = weights / np.sum(weights)  # Normalize
                
            # Drift for each asset: mean - var/2
            variances = self.returns.var()
            drifts = self.mean_returns - 0.5 * variances
            
            # Convert to numpy arrays
            mean_vec = drifts.values
            cov_mat = self.cov_matrix.values
            
            asset_paths = {}
            for t in self.tickers:
                asset_paths[t] = np.zeros((num_simulations, days + 1))
                asset_paths[t][:, 0] = self.last_prices[t]
                
            # Simulate correlated joint returns day by day
            for d in range(1, days + 1):
                sim_log_ret = np.random.multivariate_normal(mean_vec, cov_mat, size=num_simulations)
                for i, t in enumerate(self.tickers):
                    asset_paths[t][:, d] = asset_paths[t][:, d - 1] * np.exp(sim_log_ret[:, i])
            
            # Calculate portfolio value paths: sum(weight_i * asset_path_i)
            S0_port = sum(weights[i] * self.last_prices[t] for i, t in enumerate(self.tickers))
            port_paths = np.zeros((num_simulations, days + 1))
            for i, t in enumerate(self.tickers):
                port_paths += weights[i] * asset_paths[t]
                
            # Metrics for portfolio
            final_vals = port_paths[:, -1]
            losses_pct = (S0_port - final_vals) / S0_port
            
            var_95 = float(np.percentile(losses_pct, 95))
            var_99 = float(np.percentile(losses_pct, 99))
            cvar_95 = float(losses_pct[losses_pct >= var_95].mean() if np.any(losses_pct >= var_95) else var_95)
            cvar_99 = float(losses_pct[losses_pct >= var_99].mean() if np.any(losses_pct >= var_99) else var_99)
            
            prob_profit = float(np.mean(final_vals > S0_port) * 100.0)
            
            median_final_val = np.median(final_vals)
            most_likely_idx = int(np.argmin(np.abs(final_vals - median_final_val)))
            
            # Package asset paths (limit to plot_paths to avoid huge payloads)
            for t in self.tickers:
                results["paths"][t] = asset_paths[t][:plot_paths].tolist()
                results["most_likely_path"][t] = asset_paths[t][most_likely_idx].tolist()
                results["calculated_parameters"][t] = {
                    "drift": float(drifts[t]),
                    "volatility": float(self.returns[t].std()),
                    "mean_return": float(self.mean_returns[t]),
                    "variance": float(variances[t])
                }
                
            results["portfolio_paths"] = port_paths[:plot_paths].tolist()
            results["terminal_prices"]["Portfolio"] = final_vals.tolist()
            results["most_likely_portfolio_path"] = port_paths[most_likely_idx].tolist()
            results["risk_metrics"]["Portfolio"] = {
                "var_95": var_95,
                "var_99": var_99,
                "cvar_95": cvar_95,
                "cvar_99": cvar_99,
                "start_price": S0_port,
                "last_close": S0_port,
                "prob_profit": prob_profit,
                "mean_final": float(np.mean(final_vals)),
                "median_final": float(np.median(final_vals))
            }
            
        return results


class PortfolioOptimizer:
    def __init__(self, tickers, lookback_period="1y"):
        if isinstance(tickers, str):
            self.tickers = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        else:
            self.tickers = [t.strip().upper() for t in tickers]
        self.lookback_period = lookback_period
        
    def optimize(self, rf_rate=0.04, num_portfolios=2000):
        """
        Performs Monte Carlo portfolio optimization (Markowitz Efficient Frontier).
        Returns results containing Max Sharpe and Min Volatility portfolios.
        """
        data = yf.download(self.tickers, period=self.lookback_period, interval='1d')
        if data.empty:
            raise ValueError(f"No historical data found for {self.tickers}")
            
        if len(self.tickers) == 1:
            raise ValueError("Need at least 2 tickers for portfolio optimization.")
            
        df = data['Adj Close'] if 'Adj Close' in data.columns else data['Close']
        df = df.ffill().dropna()
        
        # Daily returns
        returns = np.log(df / df.shift(1)).dropna()
        
        # Annualized mean returns and covariance (252 trading days)
        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252
        
        num_assets = len(self.tickers)
        
        port_returns = []
        port_vols = []
        port_weights = []
        sharpe_ratios = []
        
        np.random.seed(42) # Reproducible
        for _ in range(num_portfolios):
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)
            port_weights.append(weights)
            
            p_ret = np.dot(weights, mean_returns)
            port_returns.append(p_ret)
            
            p_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            port_vols.append(p_vol)
            
            sharpe = (p_ret - rf_rate) / p_vol
            sharpe_ratios.append(sharpe)
            
        port_returns = np.array(port_returns)
        port_vols = np.array(port_vols)
        sharpe_ratios = np.array(sharpe_ratios)
        port_weights = np.array(port_weights)
        
        max_sharpe_idx = np.argmax(sharpe_ratios)
        min_vol_idx = np.argmin(port_vols)
        
        max_sharpe_allocation = {self.tickers[i]: float(port_weights[max_sharpe_idx, i]) for i in range(num_assets)}
        min_vol_allocation = {self.tickers[i]: float(port_weights[min_vol_idx, i]) for i in range(num_assets)}
        
        single_stocks = []
        for i, t in enumerate(self.tickers):
            single_stocks.append({
                "ticker": t,
                "return": float(mean_returns[t]),
                "volatility": float(np.sqrt(cov_matrix.loc[t, t])),
                "sharpe": float((mean_returns[t] - rf_rate) / np.sqrt(cov_matrix.loc[t, t]))
            })
            
        return {
            "max_sharpe": {
                "return": float(port_returns[max_sharpe_idx]),
                "volatility": float(port_vols[max_sharpe_idx]),
                "sharpe": float(sharpe_ratios[max_sharpe_idx]),
                "weights": max_sharpe_allocation
            },
            "min_vol": {
                "return": float(port_returns[min_vol_idx]),
                "volatility": float(port_vols[min_vol_idx]),
                "sharpe": float(sharpe_ratios[min_vol_idx]),
                "weights": min_vol_allocation
            },
            "simulations": {
                "returns": port_returns.tolist(),
                "volatilities": port_vols.tolist(),
                "sharpe_ratios": sharpe_ratios.tolist()
            },
            "single_stocks": single_stocks
        }


class BlackScholes:
    @staticmethod
    def price_and_greeks(S, K, T, r, sigma, option_type="call"):
        """
        S: Current stock price
        K: Option strike price
        T: Time to expiration in years (e.g. 0.5 for 6 months)
        r: Risk-free interest rate (annualized)
        sigma: Volatility (annualized)
        option_type: "call" or "put"
        """
        if T <= 0:
            T = 1e-5
            
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type.lower() == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            delta = norm.cdf(d1)
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                     - r * K * np.exp(-r * T) * norm.cdf(d2))
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = norm.cdf(d1) - 1
            theta = (- (S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) 
                     + r * K * np.exp(-r * T) * norm.cdf(-d2))
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
            
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * np.sqrt(T) * norm.pdf(d1)
        
        theta_daily = theta / 365.0
        vega_1pct = vega / 100.0
        
        return {
            "price": float(price),
            "delta": float(delta),
            "gamma": float(gamma),
            "theta_annual": float(theta),
            "theta_daily": float(theta_daily),
            "vega": float(vega),
            "vega_1pct": float(vega_1pct),
            "rho": float(rho),
            "d1": float(d1),
            "d2": float(d2)
        }
