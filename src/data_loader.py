from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "sample_data"

ENQUIRY_FILE = DATA_DIR / "enquiries.csv"
QUOTATION_FILE = DATA_DIR / "quotations.csv"

REQUIRED_ENQUIRY_COLUMNS = [
    "Client Name",
    "Enq. No. & Date",
    "Item",
]

REQUIRED_QUOTATION_COLUMNS = [
    "Quotation No.",
    "Client Name",
    "Items",
    "Remark",
    "WO No.",
    "Total Value",
]


def _read_csv(path: Path) -> pd.DataFrame:
    """Load a CSV as strings, preserving identifiers and blank cells."""
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path.name}")

    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = df.columns.str.strip()

    if df.empty:
        raise ValueError(f"{path.name} contains no records.")

    return df


def _validate_columns(
    df: pd.DataFrame,
    required: list[str],
    filename: str,
) -> None:
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            f"{filename} is missing required columns: " + ", ".join(missing)
        )


def load_sample_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and validate the enquiry and quotation registers."""
    enquiries = _read_csv(ENQUIRY_FILE)
    quotations = _read_csv(QUOTATION_FILE)

    _validate_columns(
        enquiries,
        REQUIRED_ENQUIRY_COLUMNS,
        ENQUIRY_FILE.name,
    )
    _validate_columns(
        quotations,
        REQUIRED_QUOTATION_COLUMNS,
        QUOTATION_FILE.name,
    )

    return enquiries, quotations
