"""Statistics Lambda handler for CSV summary generation."""

# Copyright (c) 2026
from __future__ import annotations

import base64
import binascii
import json
from io import StringIO
from typing import Any, NoReturn

import numpy as np
import pandas as pd


def _raise_empty_csv_body_error() -> NoReturn:
    """Raise a consistent error when the CSV payload is empty."""
    message = "CSV request body is empty."
    raise ValueError(message)


def _raise_no_numeric_columns_error() -> NoReturn:
    """Raise a consistent error when the CSV lacks numeric data."""
    message = "No numeric columns were found in the CSV."
    raise ValueError(message)


def _raise_empty_numeric_column_error(series_name: object | None) -> NoReturn:
    """Raise a consistent error when a numeric series contains no valid values."""
    column = str(series_name) if series_name is not None else "unknown"
    message = f"Column '{column}' contains no numeric values."
    raise ValueError(message)


def http_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build a Lambda API Gateway response payload."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def csv_body(event: dict[str, Any]) -> str:
    """Extract and decode the CSV payload from the event body."""
    raw_body = event.get("body")
    if not isinstance(raw_body, str) or not raw_body.strip():
        _raise_empty_csv_body_error()

    return (
        base64.b64decode(raw_body).decode("utf-8")
        if event.get("isBase64Encoded", False)
        else raw_body
    )


def summarize(series: pd.Series) -> dict[str, float | int]:
    """Compute summary statistics for a numeric pandas series."""
    values = series.dropna().to_numpy(dtype=float)

    if values.size == 0:
        _raise_empty_numeric_column_error(series.name)

    return {
        "count": int(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values, ddof=0)),
        "max": float(np.max(values)),
        "min": float(np.min(values)),
    }


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Handle the Lambda request and return a JSON summary response."""
    del context

    try:
        csv_text = csv_body(event)
        dataframe = pd.read_csv(StringIO(csv_text))
        numeric_dataframe = dataframe.select_dtypes(include="number")

        if numeric_dataframe.empty:
            _raise_no_numeric_columns_error()

        statistics = {
            str(column): summarize(numeric_dataframe[column])
            for column in numeric_dataframe.columns
        }

        return http_response(
            200,
            {
                "columns": statistics,
            },
        )
    except (ValueError, UnicodeDecodeError, binascii.Error) as error:
        return http_response(400, {"error": str(error)})
    except Exception:  # noqa: BLE001
        return http_response(500, {"error": "Internal server error."})
