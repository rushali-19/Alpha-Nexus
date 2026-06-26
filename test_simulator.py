import unittest
import numpy as np
from simulator import MonteCarloSimulator, PortfolioOptimizer, BlackScholes

class TestAlphaNexusSimulator(unittest.TestCase):
    def test_single_asset_simulation(self):
        print("\nTesting single asset simulation (AAPL)...")
        sim = MonteCarloSimulator(["AAPL"], lookback_period="6mo")
        sim.fetch_data()
        
        results = sim.run_simulation(days=20, num_simulations=100, plot_paths=15)
        
        self.assertEqual(len(results["dates"]), 21) # 20 days + start date
        self.assertIn("AAPL", results["paths"])
        self.assertEqual(len(results["paths"]["AAPL"]), 15) # plot_paths=15
        self.assertEqual(len(results["paths"]["AAPL"][0]), 21)
        
        self.assertIn("AAPL", results["terminal_prices"])
        self.assertEqual(len(results["terminal_prices"]["AAPL"]), 100) # num_simulations=100
        
        metrics = results["risk_metrics"]["AAPL"]
        self.assertTrue(metrics["start_price"] > 0)
        self.assertTrue(0 <= metrics["prob_profit"] <= 100)
        self.assertIsNotNone(metrics["var_95"])
        self.assertIsNotNone(metrics["cvar_95"])
        
        params = results["calculated_parameters"]["AAPL"]
        self.assertTrue(params["volatility"] > 0)
        print("Single asset simulation test passed!")

    def test_portfolio_simulation(self):
        print("\nTesting multi-asset portfolio simulation (AAPL, MSFT)...")
        sim = MonteCarloSimulator(["AAPL", "MSFT"], lookback_period="6mo")
        sim.fetch_data()
        
        results = sim.run_simulation(days=10, num_simulations=50, weights=[0.6, 0.4], plot_paths=10)
        
        self.assertEqual(len(results["dates"]), 11)
        self.assertIn("AAPL", results["paths"])
        self.assertIn("MSFT", results["paths"])
        self.assertEqual(len(results["paths"]["AAPL"]), 10) # plot_paths=10
        self.assertEqual(len(results["portfolio_paths"]), 10) # plot_paths=10
        self.assertEqual(len(results["terminal_prices"]["Portfolio"]), 50) # num_simulations=50
        
        port_metrics = results["risk_metrics"]["Portfolio"]
        self.assertTrue(port_metrics["start_price"] > 0)
        print("Portfolio simulation test passed!")

    def test_portfolio_optimization(self):
        print("\nTesting portfolio optimization (AAPL, MSFT, GOOGL)...")
        opt = PortfolioOptimizer(["AAPL", "MSFT", "GOOGL"], lookback_period="6mo")
        results = opt.optimize(rf_rate=0.04, num_portfolios=200)
        
        self.assertIn("max_sharpe", results)
        self.assertIn("min_vol", results)
        self.assertEqual(len(results["simulations"]["returns"]), 200)
        
        max_sharpe_weights = results["max_sharpe"]["weights"]
        self.assertAlmostEqual(sum(max_sharpe_weights.values()), 1.0, places=4)
        print("Portfolio optimization test passed!")

    def test_black_scholes(self):
        print("\nTesting Black-Scholes pricing...")
        # S=100, K=100, T=1, r=0.05, sigma=0.2
        call_res = BlackScholes.price_and_greeks(100, 100, 1, 0.05, 0.2, "call")
        put_res = BlackScholes.price_and_greeks(100, 100, 1, 0.05, 0.2, "put")
        
        self.assertTrue(call_res["price"] > 0)
        self.assertTrue(put_res["price"] > 0)
        self.assertTrue(0 < call_res["delta"] < 1)
        self.assertTrue(-1 < put_res["delta"] < 0)
        self.assertTrue(call_res["gamma"] > 0)
        self.assertEqual(call_res["gamma"], put_res["gamma"])
        print("Black-Scholes test passed!")

if __name__ == "__main__":
    unittest.main()
