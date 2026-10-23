from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "messages.csv"


def load_data(path=DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|", dtype=str, keep_default_na=False)
    for col in ["unit", "issue", "time_mentioned"]:
        df[col] = df[col].str.strip()
    return df
