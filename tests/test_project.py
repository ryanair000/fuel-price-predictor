import math
import unittest
from pathlib import Path

import pandas as pd

from src.calculators import cost_for_litres, litres_for_budget, trip_estimate
from src.data import (
    FUEL_COLUMNS,
    get_price,
    load_component_history,
    load_components,
    load_history,
    load_official_prices,
    load_sources,
)
from src.hybrid import reconstruct_price, reconstruction_audit, scenario_estimate
from src.modeling import (
    FEATURE_COLUMNS,
    build_trend_chart,
    create_lagged_data,
    forecast_fuel,
)


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = load_history()
        cls.official = load_official_prices()
        cls.sources = load_sources()

    def test_required_project_files_exist(self):
        required_files = [
            "data/nairobi_price_history.csv",
            "data/current_nairobi_price.csv",
            "data/price_components.csv",
            "data/nairobi_component_history.csv",
            "data/sources.csv",
            "data/price_revisions_2026.csv",
        ]
        for name in required_files:
            self.assertTrue(Path(name).exists(), name)

    def test_scope_is_nairobi_only(self):
        self.assertEqual(self.official["Town"].unique().tolist(), ["Nairobi"])
        self.assertNotIn("Town", self.history.columns)

    def test_history_is_continuous_unique_and_time_ordered(self):
        expected = pd.date_range("2022-01-01", "2026-07-01", freq="MS")
        self.assertEqual(self.history["Cycle"].tolist(), list(expected))
        self.assertFalse(self.history["Cycle"].duplicated().any())
        self.assertTrue(self.history["Cycle"].is_monotonic_increasing)
        self.assertEqual(self.history["Month_num"].tolist(), list(range(1, 56)))

    def test_effective_periods_are_valid(self):
        self.assertTrue(
            (self.history["Effective_To"] >= self.history["Effective_From"]).all()
        )

    def test_every_history_row_has_registered_source(self):
        self.assertTrue(
            set(self.history["Source_ID"]).issubset(set(self.sources["Source_ID"]))
        )
        self.assertTrue(self.sources["URL"].str.startswith("https://").all())

    def test_official_spot_checks(self):
        jul_2022 = self.history.loc[
            self.history["Cycle"].eq(pd.Timestamp("2022-07-01"))
        ].iloc[0]
        apr_2026 = self.history.loc[
            self.history["Cycle"].eq(pd.Timestamp("2026-04-01"))
        ].iloc[0]
        may_2026 = self.history.loc[
            self.history["Cycle"].eq(pd.Timestamp("2026-05-01"))
        ].iloc[0]
        self.assertEqual(
            (jul_2022.Super_Petrol, jul_2022.Diesel, jul_2022.Kerosene),
            (159.12, 140.0, 127.94),
        )
        self.assertEqual(
            (apr_2026.Super_Petrol, apr_2026.Diesel, apr_2026.Kerosene),
            (197.60, 196.63, 152.78),
        )
        self.assertEqual(
            (may_2026.Super_Petrol, may_2026.Diesel, may_2026.Kerosene),
            (214.25, 232.86, 191.38),
        )

    def test_current_cycle_and_prices_are_exact(self):
        row = self.official.iloc[0]
        self.assertEqual(row["Effective_From"], pd.Timestamp("2026-07-15"))
        self.assertEqual(row["Effective_To"], pd.Timestamp("2026-08-14"))
        self.assertEqual(get_price(self.official, "Super Petrol"), 214.03)
        self.assertEqual(get_price(self.official, "Diesel"), 222.86)
        self.assertEqual(get_price(self.official, "Kerosene"), 191.38)

    def test_component_detail_reconciles_to_epra_totals(self):
        totals = (
            load_components()
            .groupby("Fuel")["KES_Per_Litre"]
            .sum()
            .round(2)
            .to_dict()
        )
        self.assertEqual(
            totals,
            {"Diesel": 162.91, "Kerosene": 146.93, "Super Petrol": 177.32},
        )

    def test_component_history_is_real_linked_and_reconciled(self):
        frame = load_component_history()
        self.assertEqual(len(frame), 33)
        self.assertEqual(frame["Effective_From"].nunique(), 11)
        self.assertEqual(
            frame.groupby("Fuel").size().to_dict(),
            {"Diesel": 11, "Kerosene": 11, "Super Petrol": 11},
        )
        self.assertTrue(frame["PDF_URL"].str.startswith("https://www.epra.go.ke/").all())
        self.assertLessEqual(
            reconstruction_audit(frame)["Calculated_Error"].abs().max(),
            0.02,
        )

    def test_known_annex_row_reconstructs_exact_price(self):
        frame = load_component_history()
        row = frame.loc[
            frame["Effective_From"].eq(pd.Timestamp("2025-06-15"))
            & frame["Fuel"].eq("Diesel")
        ].iloc[0]
        self.assertEqual(reconstruct_price(row), 162.91)

    def test_cost_scenario_changes_only_declared_inputs(self):
        frame = load_component_history()
        row = frame.loc[
            frame["Effective_From"].eq(pd.Timestamp("2025-06-15"))
            & frame["Fuel"].eq("Super Petrol")
        ].iloc[0]
        scenario = scenario_estimate(row, landed_change_pct=10, tax_change=2)
        self.assertAlmostEqual(scenario.change, round(row.Landed_Cost * 0.10 + 2, 2))

    def test_lags_use_only_past_values(self):
        lagged = create_lagged_data(self.history, "Super_Petrol")
        first = lagged.iloc[0]
        self.assertEqual(first["Cycle"], pd.Timestamp("2022-04-01"))
        self.assertEqual(first["Lag_1"], self.history.iloc[2]["Super_Petrol"])
        self.assertEqual(first["Lag_2"], self.history.iloc[1]["Super_Petrol"])
        self.assertAlmostEqual(
            first["Rolling_3"],
            self.history.iloc[:3]["Super_Petrol"].mean(),
        )


class CalculatorTests(unittest.TestCase):
    def test_litre_cost(self):
        self.assertAlmostEqual(cost_for_litres(20, 214.03), 4280.60)

    def test_budget_litres(self):
        self.assertAlmostEqual(litres_for_budget(4280.60, 214.03), 20.0)

    def test_trip_calculation_includes_traffic_allowance(self):
        result = trip_estimate(120, 12, 200, 10)
        self.assertEqual(
            result,
            {"base_litres": 10.0, "litres": 11.0, "cost": 2200.0},
        )

    def test_invalid_values_are_rejected(self):
        invalid_calls = [
            (cost_for_litres, (0, 200)),
            (litres_for_budget, (-1, 200)),
            (trip_estimate, (100, 0, 200)),
        ]
        for function, args in invalid_calls:
            with self.assertRaises(ValueError):
                function(*args)


class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = load_history()
        cls.results = {
            column: forecast_fuel(cls.history, column)
            for column in FUEL_COLUMNS.values()
        }

    def test_all_fuels_return_finite_deterministic_forecasts(self):
        for column, result in self.results.items():
            values = [
                result.prediction,
                result.lower,
                result.upper,
                result.mae,
                result.rmse,
                result.baseline_mae,
            ]
            for value in values:
                self.assertTrue(math.isfinite(value), (column, value))
            self.assertLessEqual(result.lower, result.prediction)
            self.assertGreaterEqual(result.upper, result.prediction)
            self.assertEqual(result.validation_points, 10)
            self.assertGreaterEqual(result.selection_points, 6)

    def test_forecast_targets_next_monthly_cycle(self):
        for result in self.results.values():
            self.assertEqual(result.next_date, pd.Timestamp("2026-08-01"))

    def test_holdout_is_separate_from_selection(self):
        result = self.results["Super_Petrol"]
        lagged_rows = len(create_lagged_data(self.history, "Super_Petrol"))
        self.assertEqual(
            result.selection_points + result.validation_points + 24,
            lagged_rows,
        )

    def test_chart_connects_last_observation_to_forecast(self):
        result = self.results["Diesel"]
        chart = build_trend_chart(self.history, "Diesel", result)
        self.assertEqual(chart.loc[pd.Timestamp("2026-07-01"), "Forecast"], 222.86)
        self.assertEqual(
            chart.loc[pd.Timestamp("2026-08-01"), "Forecast"],
            result.prediction,
        )

    def test_model_features_exclude_same_cycle_external_values(self):
        self.assertNotIn("USD_KES", FEATURE_COLUMNS)
        self.assertNotIn("Crude_Oil", FEATURE_COLUMNS)
        self.assertEqual(
            set(FEATURE_COLUMNS),
            {"Month_num", "Month_sin", "Month_cos", "Lag_1", "Lag_2", "Rolling_3"},
        )


if __name__ == "__main__":
    unittest.main()
