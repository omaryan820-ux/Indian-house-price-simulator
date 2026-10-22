import csv
from datetime import datetime
from pathlib import Path

import streamlit as st

LOCAL_FILE = Path(__file__).resolve().parent.parent / "local_submissions.csv"


def _open_sheet():
    import gspread
    credentials = dict(st.secrets["gcp_service_account"])
    client = gspread.service_account_from_dict(credentials)
    return client.open_by_key(st.secrets["sheets"]["sheet_id"])


def save_row(tab_name, values):
    """Save one row to the Google Sheet tab, or to a local CSV if the Sheet is not set up.
    Returns 'sheet' or 'local'."""
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + list(values)
    try:
        _open_sheet().worksheet(tab_name).append_row(row)
        return "sheet"
    except Exception:
        with open(LOCAL_FILE, "a", newline="", encoding="utf-8") as file:
            csv.writer(file).writerow([tab_name] + row)
        return "local"