import math
import unittest
from pathlib import Path

import app


class FuelPriceProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = app.load_data()

    def test_dataset_file_exists(self):
        self.assertTrue(Path("fuel_prices.csv").exists())

    def test_required_columns_match_project_schema(self):
        self.assertEqual(list(self.data.columns[:6]), app.REQUIRED_COLUMNS)

    def test_date_column_is_datetime(self):
        self.assertTrue(str(self.data["Date"].dtype).startswith("datetime64"))

    def test_data_is_sorted_chronologically(self):
        self.assertTrue(self.data["Date"].is_monotonic_increasing)

    def test_month_num_is_created_sequentially(self):
        self.assertEqual(self.data["Month_num"].iloc[0], 1)
        self.assertEqual(self.data["Month_num"].iloc[-1], len(self.data))

    def test_super_petrol_lagged_data_has_expected_columns(self):
        lagged = app.create_lagged_data(self.data, "Super_Petrol")
        self.assertIn("Lag_1", lagged.columns)
        self.assertIn("Lag_2", lagged.columns)

    def test_super_petrol_lagged_data_drops_first_two_rows(self):
        lagged = app.create_lagged_data(self.data, "Super_Petrol")
        self.assertEqual(len(lagged), len(self.data) - 2)
        self.assertEqual(lagged.iloc[0]["Date"].strftime("%b-%Y"), "Mar-2022")

    def test_future_input_uses_expected_feature_columns(self):
        future_input = app.build_future_input(
            self.data,
            "Super_Petrol",
            float(self.data["USD_KES"].iloc[-1]),
            float(self.data["Crude_Oil"].iloc[-1]),
        )
        self.assertEqual(list(future_input.columns), app.FEATURE_COLUMNS)

    def test_models_return_numeric_metrics_for_each_fuel(self):
        for fuel_column in app.FUEL_OPTIONS.values():
            lagged = app.create_lagged_data(self.data, fuel_column)
            _, metrics = app.train_model(lagged, fuel_column)
            self.assertTrue(math.isfinite(metrics["MAE"]))
            self.assertTrue(math.isfinite(metrics["MSE"]))
            self.assertTrue(math.isfinite(metrics["R2"]))

    def test_prediction_output_is_numeric(self):
        lagged = app.create_lagged_data(self.data, "Super_Petrol")
        model, _ = app.train_model(lagged, "Super_Petrol")
        future_input = app.build_future_input(
            self.data,
            "Super_Petrol",
            float(self.data["USD_KES"].iloc[-1]),
            float(self.data["Crude_Oil"].iloc[-1]),
        )
        prediction = float(model.predict(future_input)[0])
        self.assertTrue(math.isfinite(prediction))


if __name__ == "__main__":
    unittest.main()
