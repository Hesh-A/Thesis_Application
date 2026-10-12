from datetime import time

import pandas as pd
import pytest

from database.utils.import_parsing import get_row_data, parse_time_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("01.02.003", 62.003),
        ("62.003", 62.003),
        (time(0, 1, 2, 3000), 1.005),
    ],
)
def test_parse_time_value_converts_supported_formats(value, expected):
    assert parse_time_value(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", ["01.60.000", "not-a-time"])
def test_parse_time_value_rejects_invalid_formats(value):
    with pytest.raises(ValueError, match="invalid time value"):
        parse_time_value(value)


def test_get_row_data_returns_normalized_session_data():
    row = pd.Series({
        "Participant": " P01 (asp) ",
        "Entry Number": 7.0,
        "Total Swallows": 2,
        "Final Audio start": "00.12.500",
        "Method of drinking": "cup",
        "Dx": "anemia",
        "Sex": "F",
        "Age (mths)": 18,
    })
    warnings = []

    assert get_row_data(row, excel_row=4, warnings=warnings) == (
        "P01", "7", 2, True, 12.5, "cup", "anemia", "F", 18
    )
    assert warnings == []


def test_get_row_data_skips_negative_swallow_count():
    row = pd.Series({
        "Participant": "P01",
        "Entry Number": "7",
        "Total Swallows": -1,
        "Final Audio start": 0,
    })
    warnings = []

    assert get_row_data(row, excel_row=4, warnings=warnings) is None
    assert "cannot be negative" in warnings[0]
