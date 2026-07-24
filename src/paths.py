from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_PRICES_PATH = ROOT / "data" / "current_nairobi_price.csv"
COMPONENT_HISTORY_PATH = ROOT / "data" / "nairobi_component_history.csv"
PREDICTION_DATASET_PATH = ROOT / "data" / "component_prediction_dataset.csv"
SOURCES_PATH = ROOT / "data" / "sources.csv"
