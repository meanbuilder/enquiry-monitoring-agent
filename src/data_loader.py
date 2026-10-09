from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def load_sample_data():
    enquiries = pd.read_csv(ROOT / "sample_data" / "enquiries.csv", keep_default_na=False)
    quotations = pd.read_csv(ROOT / "sample_data" / "quotations.csv", keep_default_na=False)
    return enquiries, quotations
