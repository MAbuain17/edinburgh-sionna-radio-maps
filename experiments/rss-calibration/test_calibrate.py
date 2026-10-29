import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import savemat

from calibrate import evaluate, fit_models, metrics, read_csv, split_masks
from import_dryad import convert


class CalibrationTests(unittest.TestCase):
    def test_known_offset_and_affine(self):
        x = np.linspace(-95, -50, 30)
        models, _ = fit_models(x, 1.2 * x + 4)
        np.testing.assert_allclose(models["affine"], (1.2, 4), atol=1e-10)
        models, _ = fit_models(x, x + 7)
        self.assertAlmostEqual(models["offset"][1], 7)

    def test_held_out_labels_do_not_change_fit(self):
        time = np.arange(100.0)
        rows = np.column_stack([time, -80 + time / 10, -75 + time / 10])
        before, _ = evaluate({"link": rows}, 0.5, 10)
        rows[time > 60, 2] += 200
        after, _ = evaluate({"link": rows}, 0.5, 10)
        for name in before["link"]["models"]:
            for key in ["slope", "intercept_db", "train"]:
                self.assertEqual(before["link"]["models"][name][key],
                                 after["link"]["models"][name][key])
        self.assertGreater(after["link"]["models"]["offset"]["test"]["rmse_db"], 190)

    def test_shift_can_make_correction_worse(self):
        time = np.arange(101.0)
        predicted = -80 + np.sin(time)
        measured = predicted + np.where(time <= 50, 6, -6)
        report, _ = evaluate({"link": np.column_stack([time, predicted, measured])}, 0.5, 5)
        result = report["link"]["models"]
        self.assertGreater(result["offset"]["test"]["rmse_db"],
                           result["uncorrected"]["test"]["rmse_db"])

    def test_gap_uses_seconds_on_irregular_samples(self):
        time = np.array([0, 1, 2, 40, 50, 51, 59, 60, 61, 80, 100.])
        train, test, cutoff = split_masks(time, 0.5, 10)
        self.assertEqual(cutoff, 50)
        np.testing.assert_array_equal(time[test], [61, 80, 100])
        self.assertFalse(np.any(train & test))

    def test_degenerate_affine_keeps_offset(self):
        models, warning = fit_models(np.ones(10), np.arange(10.))
        self.assertNotIn("affine", models)
        self.assertIn("offset", models)
        self.assertIsNotNone(warning)

    def test_metrics_sign_and_scale(self):
        result = metrics(np.array([2., 4.]), np.array([1., 1.]))
        self.assertEqual(result["bias_db"], 2)
        self.assertEqual(result["mae_db"], 2)
        self.assertAlmostEqual(result["rmse_db"], np.sqrt(5))

    def test_bad_splits(self):
        for fraction, gap in [(0, 1), (1, 1), (0.5, -1), (0.5, 100), (float("nan"), 1)]:
            with self.subTest(fraction=fraction, gap=gap), self.assertRaises(ValueError):
                split_masks(np.arange(10.), fraction, gap)

    def test_csv_rejects_duplicate_time_and_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            for body in ["a,0,-80,-70\na,0,-81,-71\n", "a,0,nan,-70\n"]:
                path.write_text("link,time_s,predicted_dbm,measured_dbm\n" + body)
                with self.assertRaises(ValueError):
                    read_csv(path)

    def test_mat_import_schema_and_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, output = Path(tmp) / "fixture.mat", Path(tmp) / "out.csv"
            tower = {"time_reference": np.arange(6.), "RSS_arr_plot": np.arange(6.) - 80,
                     "RSS1_offset": np.arange(6.) - 75, "RSS2_offset": np.arange(6.) - 73}
            cells = np.empty((2, 1), dtype=object)
            cells[0, 0] = tower
            cells[1, 0] = tower
            savemat(path, {"LWs": cells})
            convert(path, output, 2)
            groups = read_csv(output)
            self.assertEqual(set(groups), {"LW1_ch2", "LW2_ch2"})
            np.testing.assert_array_equal(groups["LW1_ch2"][:, 2], np.arange(6.) - 73)


if __name__ == "__main__":
    unittest.main()
