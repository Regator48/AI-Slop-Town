import tempfile, unittest
from pathlib import Path
from townsim.model import Config, Simulation

class SimulationTests(unittest.TestCase):
    def test_deterministic(self):
        a = Simulation(Config(seed=4)).run(90)
        b = Simulation(Config(seed=4)).run(90)
        self.assertEqual(a.metrics, b.metrics)
        self.assertEqual(a.stocks, b.stocks)

    def test_policy_transmission(self):
        sim = Simulation(Config(policy_rate=.20, seed=1)); sim.run(30)
        self.assertGreater(sim.state.policy_rate, .05)

    def test_checkpoint(self):
        sim = Simulation(Config(seed=8)); sim.run(61)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "state.json"; sim.save(path)
            loaded = Simulation.load(path)
            self.assertEqual(loaded.state.day, sim.state.day)
            self.assertEqual(loaded.state.metrics, sim.state.metrics)

    def test_bank_run_is_stressed(self):
        sim = Simulation(Config(seed=2, scenario="bank_run")); sim.run(90)
        self.assertLess(sim.state.deposits, 100_000_000)

if __name__ == "__main__": unittest.main()
