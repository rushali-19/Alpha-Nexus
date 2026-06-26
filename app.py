from flask import Flask, request, jsonify, render_template
import numpy as np
import yfinance as yf
import traceback
from simulator import MonteCarloSimulator, PortfolioOptimizer, BlackScholes

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/simulate', methods=['POST'])
def api_simulate():
    try:
        data = request.get_json() or {}
        
        tickers_str = data.get('tickers', 'AAPL').strip()
        if not tickers_str:
            return jsonify({"error": "Stock ticker is required."}), 400
            
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        period = data.get('period', '1y')
        
        try:
            days = int(data.get('days', 126))
            num_simulations = int(data.get('simulations', 100))
        except ValueError:
            return jsonify({"error": "Days and Simulations must be integers."}), 400
            
        if days < 5 or days > 504:
            return jsonify({"error": "Days must be between 5 and 504."}), 400
        if num_simulations < 10 or num_simulations > 10000:
            return jsonify({"error": "Simulations must be between 10 and 10,000."}), 400
            
        # Parse optional overrides
        drift_override = data.get('drift_override')
        volatility_override = data.get('volatility_override')
        
        d_val = None
        v_val = None
        
        if drift_override is not None and str(drift_override).strip() != "":
            try:
                d_val = float(drift_override)
            except ValueError:
                return jsonify({"error": "Drift override must be a number."}), 400
                
        if volatility_override is not None and str(volatility_override).strip() != "":
            try:
                v_val = float(volatility_override)
            except ValueError:
                return jsonify({"error": "Volatility override must be a number."}), 400
                
        weights_str = data.get('weights', '')
        weights = None
        if weights_str and len(tickers) > 1:
            try:
                weights = [float(w.strip()) for w in weights_str.split(',') if w.strip()]
            except ValueError:
                return jsonify({"error": "Weights must be comma-separated numbers."}), 400
                
        try:
            plot_paths = int(data.get('plot_paths', 30))
        except ValueError:
            plot_paths = 30
            
        # Initialize and fetch data
        simulator = MonteCarloSimulator(tickers, lookback_period=period)
        simulator.fetch_data()
        
        # Run simulation
        results = simulator.run_simulation(
            days=days, 
            num_simulations=num_simulations, 
            weights=weights,
            drift_override=d_val,
            volatility_override=v_val,
            plot_paths=plot_paths
        )
        
        # Add basic info to the response
        results["tickers"] = tickers
        results["is_portfolio"] = len(tickers) > 1
        
        return jsonify(results)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/optimize', methods=['POST'])
def api_optimize():
    try:
        data = request.get_json() or {}
        
        tickers_str = data.get('tickers', '')
        if not tickers_str:
            return jsonify({"error": "Tickers are required."}), 400
            
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        if len(tickers) < 2:
            return jsonify({"error": "At least 2 tickers are required for portfolio optimization."}), 400
            
        period = data.get('period', '1y')
        
        try:
            rf_rate = float(data.get('rf_rate', 0.04))
            simulations = int(data.get('simulations', 2000))
        except ValueError:
            return jsonify({"error": "Risk-free rate and Simulations must be numbers."}), 400
            
        optimizer = PortfolioOptimizer(tickers, lookback_period=period)
        results = optimizer.optimize(rf_rate=rf_rate, num_portfolios=simulations)
        return jsonify(results)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/options', methods=['POST'])
def api_options():
    try:
        data = request.get_json() or {}
        
        ticker = data.get('ticker', '').strip().upper()
        if not ticker:
            return jsonify({"error": "Ticker is required."}), 400
            
        try:
            strike = float(data.get('strike', 0))
            expiry = float(data.get('expiry', 0))  # in years
            rf_rate = float(data.get('rf_rate', 0.04))
        except ValueError:
            return jsonify({"error": "Strike, Expiry, and Risk-free rate must be numbers."}), 400
            
        if strike <= 0 or expiry <= 0:
            return jsonify({"error": "Strike and Expiry must be greater than 0."}), 400
            
        # Download stock data to get current price and calculate volatility
        stock = yf.Ticker(ticker)
        history = stock.history(period="1y")
        if history.empty:
            return jsonify({"error": f"No data found for ticker: {ticker}"}), 404
            
        S = float(history['Close'].iloc[-1])
        
        # Calculate historical volatility (annualized)
        log_returns = np.log(history['Close'] / history['Close'].shift(1)).dropna()
        sigma = float(log_returns.std() * np.sqrt(252))  # Annualized volatility
        
        option_type = data.get('option_type', 'call').lower()
        if option_type not in ['call', 'put']:
            option_type = 'call'
            
        bs_results = BlackScholes.price_and_greeks(
            S=S, K=strike, T=expiry, r=rf_rate, sigma=sigma, option_type=option_type
        )
        
        # Add metadata for display
        bs_results['stock_price'] = S
        bs_results['volatility_used'] = sigma
        bs_results['ticker'] = ticker
        
        return jsonify(bs_results)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
