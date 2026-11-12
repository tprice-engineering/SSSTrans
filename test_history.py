import tempfile
import unittest
from pathlib import Path

from history import read_history, summarize


class HistoryTests(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.csv"
            path.write_text(data, encoding="utf-8")
            return read_history(path)

    def test_units_and_nonuniform_sampling(self):
        rows = self.load("temperature_C,time_ms\n0,0\n20,1000\n0,4000\n0,5000\n")
        result = summarize(rows)
        self.assertAlmostEqual(result["duration_s"], 5)
        self.assertAlmostEqual(result["peak"]["time_s"], 1)
        self.assertAlmostEqual(result["peak"]["temperature_K"], 293.15)
        self.assertAlmostEqual(result["time_weighted_mean_temperature_K"], 281.15)

    def test_rejects_ambiguous_units_bad_times_and_nonfinite_values(self):
        for data in (
            "time,temperature_K\n0,290\n1,300\n",
            "time_s,temperature_K\n0,290\n0,300\n",
            "time_s,temperature_K\n1,290\n0,300\n",
            "time_s,temperature_K\n0,290\n1,nan\n",
            "time_s,temperature_K\n0,290\n1,-1\n",
            "time_s,temperature_K\n0,290\n",
        ):
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)


if __name__ == "__main__":
    unittest.main()
