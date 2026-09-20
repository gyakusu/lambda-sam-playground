from __future__ import annotations

import base64
import json
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd


def http_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def csv_body(event: dict[str, Any]) -> str:
    raw_body = event.get("body")
    if not isinstance(raw_body, str) or not raw_body.strip():
        raise ValueError("CSV request body is empty.")

    return (
        base64.b64decode(raw_body).decode("utf-8")
        if event.get("isBase64Encoded", False)
        else raw_body
    )


def summarize(series: pd.Series) -> dict[str, float | int]:
    values = series.dropna().to_numpy(dtype=float)

    if values.size == 0:
        raise ValueError(f"Column '{series.name}' contains no numeric values.")

    return {
        "count": int(values.size),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values, ddof=0)),
        "max": float(np.max(values)),
        "min": float(np.min(values)),
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    del context

    try:
        csv_text = csv_body(event)
        dataframe = pd.read_csv(StringIO(csv_text))
        numeric_dataframe = dataframe.select_dtypes(include="number")

        if numeric_dataframe.empty:
            raise ValueError("No numeric columns were found in the CSV.")

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
    except (ValueError, UnicodeDecodeError, base64.binascii.Error) as error:
        return http_response(400, {"error": str(error)})
    except Exception:
        return http_response(500, {"error": "Internal server error."})
