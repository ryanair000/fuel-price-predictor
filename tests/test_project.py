import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

import app
from src.calculators import cost_for_litres, litres_for_budget, trip_estimate
from src.data import (
    load_component_history,
    load_official_prices,
    load_prediction_dataset,
    load_sources,
)
from src.modeling import (
    JULY_2026_CYCLE,
    MODEL_FEATURES,
    DataAvailabilityError,
    coefficient_table,
    evaluate_latest_cycle,
    fit_linear_regression,
    predict_for_cycle,
    predict_july_2026,
)
from src.pricing import reconstruct_price, reconstruction_audit, scenario_estimate


class CsvValidationMixin:
    def write_csv(self, frame: pd.DataFrame) -> Path:
        temporary = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        temporary.close()
        path = Path(temporary.name)
        frame.to_csv(path, index=False)
        self.addCleanup(path.unlink, missing_ok=True)
        return path


class RepositoryTests(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            "app.py",
            "data/component_prediction_dataset.csv",
            "data/current_nairobi_price.csv",
            "data/nairobi_component_history.csv",
            "data/nairobi_price_history.csv",
            "data/price_revisions_2026.csv",
            "data/sources.csv",
            "docs/Ryan_Final_Project_Report.docx",
            "notebooks/FuelPriceAnalysis.ipynb",
        ]
        for relative_path in required:
            self.assertTrue(Path(relative_path).is_file(), relative_path)


class SourceValidationTests(CsvValidationMixin, unittest.TestCase):
    def test_source_ids_are_unique_and_links_are_https(self):
        sources = load_sources()
        self.assertFalse(sources["Source_ID"].duplicated().any())
        self.assertTrue(sources["URL"].str.startswith("https://").all())

    def test_missing_required_source_value_is_rejected(self):
        sources = pd.read_csv("data/sources.csv")
        sources.loc[0, "Title"] = np.nan
        with self.assertRaisesRegex(ValueError, "blank values"):
            load_sources(self.write_csv(sources))

    def test_duplicate_source_id_is_rejected(self):
        sources = pd.read_csv("data/sources.csv")
        sources.loc[1, "Source_ID"] = sources.loc[0, "Source_ID"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_sources(self.write_csv(sources))

    def test_non_https_source_is_rejected(self):
        sources = pd.read_csv("data/sources.csv")
        sources.loc[0, "URL"] = "http://example.com"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            load_sources(self.write_csv(sources))


class ComponentDataTests(CsvValidationMixin, unittest.TestCase):
    def setUp(self):
        self.components = load_component_history()

    def test_schema_dates_fuels_sources_and_reconstruction(self):
        self.assertEqual(len(self.components), 33)
        self.assertEqual(self.components["Effective_From"].nunique(), 11)
        self.assertEqual(
            set(self.components["Fuel"]),
            {"Super Petrol", "Diesel", "Kerosene"},
        )
        self.assertTrue(
            (self.components["Effective_To"] >= self.components["Effective_From"]).all()
        )
        self.assertTrue(self.components["PDF_URL"].str.startswith("https://").all())
        self.assertLessEqual(
            reconstruction_audit(self.components)["Calculated_Error"].abs().max(),
            0.02,
        )

    def test_component_arithmetic_matches_stored_reconstruction(self):
        calculated = self.components.apply(reconstruct_price, axis=1)
        np.testing.assert_allclose(
            calculated,
            self.components["Reconstructed_Price"],
            atol=0.01,
        )

    def test_missing_component_value_is_rejected(self):
        raw = pd.read_csv("data/nairobi_component_history.csv")
        raw.loc[0, "Landed_Cost"] = np.nan
        with self.assertRaisesRegex(ValueError, "blank values"):
            load_component_history(self.write_csv(raw))

    def test_duplicate_component_record_is_rejected(self):
        raw = pd.read_csv("data/nairobi_component_history.csv")
        raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_component_history(self.write_csv(raw))

    def test_invalid_component_date_is_rejected(self):
        raw = pd.read_csv("data/nairobi_component_history.csv")
        raw.loc[0, "Effective_To"] = "2020-01-01"
        with self.assertRaisesRegex(ValueError, "ends before"):
            load_component_history(self.write_csv(raw))

    def test_unknown_component_source_id_is_rejected(self):
        raw = pd.read_csv("data/nairobi_component_history.csv")
        raw.loc[0, "Source_ID"] = "NOT_REGISTERED"
        with self.assertRaisesRegex(ValueError, "unknown Source_ID"):
            load_component_history(self.write_csv(raw))


class PredictionDatasetTests(CsvValidationMixin, unittest.TestCase):
    def setUp(self):
        self.data = load_prediction_dataset()

    def test_schema_and_cycle_ordering(self):
        self.assertEqual(len(self.data), 33)
        self.assertTrue((self.data["Target_Cycle"] > self.data["Input_Cycle"]).all())
        self.assertEqual(
            self.data.groupby("Target_Cycle")["Fuel"].nunique().unique().tolist(),
            [3],
        )

    def test_invalid_fuel_is_rejected(self):
        raw = pd.read_csv("data/component_prediction_dataset.csv")
        raw.loc[0, "Fuel"] = "Aviation Fuel"
        with self.assertRaisesRegex(ValueError, "unknown fuel"):
            load_prediction_dataset(self.write_csv(raw))

    def test_duplicate_prediction_record_is_rejected(self):
        raw = pd.read_csv("data/component_prediction_dataset.csv")
        raw = pd.concat([raw, raw.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_prediction_dataset(self.write_csv(raw))

    def test_target_before_input_is_rejected(self):
        raw = pd.read_csv("data/component_prediction_dataset.csv")
        raw.loc[0, "Target_Cycle"] = raw.loc[0, "Input_Cycle"]
        with self.assertRaisesRegex(ValueError, "must follow"):
            load_prediction_dataset(self.write_csv(raw))


class LinearRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_prediction_dataset()
        cls.evaluation = evaluate_latest_cycle(cls.data)

    def test_chronological_training_and_july_exclusion(self):
        self.assertEqual(self.evaluation.training_records, 30)
        self.assertEqual(self.evaluation.test_records, 3)
        self.assertEqual(self.evaluation.training_start, pd.Timestamp("2024-09-01"))
        self.assertEqual(self.evaluation.training_end, pd.Timestamp("2026-03-01"))
        self.assertEqual(self.evaluation.test_cycle, pd.Timestamp("2026-04-01"))
        self.assertLess(self.evaluation.training_end, JULY_2026_CYCLE)

    def test_linear_regression_has_finite_coefficients(self):
        model = fit_linear_regression(
            self.data.loc[self.data["Target_Cycle"] < self.evaluation.test_cycle]
        )
        table = coefficient_table(model)
        self.assertEqual(
            table["Term"].tolist(),
            ["Intercept", *MODEL_FEATURES],
        )
        self.assertTrue(np.isfinite(table["Coefficient"]).all())

    def test_predictions_are_finite_for_all_three_test_fuels(self):
        results = self.evaluation.results
        self.assertEqual(set(results["Fuel"]), {"Super Petrol", "Diesel", "Kerosene"})
        self.assertTrue(np.isfinite(results["Predicted_Retail_Price"]).all())
        self.assertTrue(np.isfinite(results["Absolute_Error"]).all())
        self.assertTrue(np.isfinite(results["Percentage_Error"]).all())

    def test_prediction_generation_for_a_complete_cycle(self):
        training = self.data.loc[
            self.data["Target_Cycle"] < self.evaluation.test_cycle
        ]
        model = fit_linear_regression(training)
        predicted = predict_for_cycle(model, self.data, self.evaluation.test_cycle)
        self.assertEqual(len(predicted), 3)
        self.assertTrue(np.isfinite(predicted["Predicted_Retail_Price"]).all())

    def test_mae_and_rmse_match_direct_calculation(self):
        errors = (
            self.evaluation.results["Predicted_Retail_Price"]
            - self.evaluation.results["Target_Retail_Price"]
        )
        self.assertAlmostEqual(self.evaluation.mae, float(errors.abs().mean()))
        self.assertAlmostEqual(
            self.evaluation.rmse,
            float(np.sqrt(np.mean(np.square(errors)))),
        )

    def test_july_prediction_is_blocked_without_june_components(self):
        model = fit_linear_regression(self.data)
        with self.assertRaisesRegex(DataAvailabilityError, "unavailable"):
            predict_july_2026(model, self.data)


class OfficialJulyTests(unittest.TestCase):
    def test_official_july_prices_are_evaluation_values(self):
        official = load_official_prices().iloc[0]
        self.assertEqual(float(official["Super_Petrol"]), 214.03)
        self.assertEqual(float(official["Diesel"]), 222.86)
        self.assertEqual(float(official["Kerosene"]), 191.38)


class PricingAndCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = load_component_history().iloc[0]

    def test_scenario_changes_only_declared_inputs(self):
        result = scenario_estimate(self.row, landed_change_pct=10, tax_change=2)
        expected = round(float(self.row["Landed_Cost"]) * 0.10 + 2, 2)
        self.assertAlmostEqual(result.change, expected)

    def test_purchase_budget_and_journey_formulas(self):
        self.assertAlmostEqual(cost_for_litres(20, 214.03), 4280.60)
        self.assertAlmostEqual(litres_for_budget(4280.60, 214.03), 20.0)
        self.assertEqual(
            trip_estimate(120, 12, 200, 10),
            {"base_litres": 10.0, "litres": 11.0, "cost": 2200.0},
        )

    def test_invalid_calculator_inputs_are_rejected(self):
        invalid_calls = [
            (cost_for_litres, (0, 200)),
            (litres_for_budget, (-1, 200)),
            (trip_estimate, (100, 0, 200)),
            (trip_estimate, (100, 10, 200, 101)),
        ]
        for function, arguments in invalid_calls:
            with self.assertRaises(ValueError):
                function(*arguments)


class StreamlitLoadingTests(unittest.TestCase):
    def test_streamlit_data_loading(self):
        app.load_project_data.clear()
        official, components, prediction_data, sources = app.load_project_data()
        self.assertEqual(len(official), 1)
        self.assertEqual(len(components), 33)
        self.assertEqual(len(prediction_data), 33)
        self.assertGreaterEqual(len(sources), 22)

    def test_every_streamlit_page_runs_without_exception(self):
        pages = [
            "Home",
            "July 2026 Prediction",
            "Factors Affecting Fuel Price",
            "Price Reconstruction",
            "Fuel Calculator",
            "Data and Methodology",
        ]
        application = AppTest.from_file("app.py", default_timeout=30).run()
        for page in pages:
            with self.subTest(page=page):
                application.sidebar.radio[0].set_value(page).run()
                self.assertEqual(list(application.exception), [])


if __name__ == "__main__":
    unittest.main()
