import base64
import json
from io import BytesIO
from unittest.mock import Mock

import pandas as pd
import pytest
from src.statistics import app


def test_summarize_calculates_population_statistics() -> None:
    series = pd.Series([1, 2, 3, None], name="value")

    result = app.summarize(series)

    assert result == {
        "count": 3,
        "mean": 2.0,
        "median": 2.0,
        "std": pytest.approx(0.816496580927726),
        "max": 3.0,
        "min": 1.0,
    }


def test_summarize_rejects_column_without_numeric_values() -> None:
    with pytest.raises(ValueError, match="Column 'value' contains no numeric values"):
        app.summarize(pd.Series([float("nan")], name="value"))


def test_summarize_csv_includes_numeric_columns_only() -> None:
    result = app.summarize_csv("value,label\n10,a\n20,b\n")

    assert result == {
        "value": {
            "count": 2,
            "mean": 15.0,
            "median": 15.0,
            "std": 5.0,
            "max": 20.0,
            "min": 10.0,
        }
    }


def test_summarize_csv_rejects_csv_without_numeric_columns() -> None:
    with pytest.raises(ValueError, match="No numeric columns were found"):
        app.summarize_csv("label\na\nb\n")


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ({"body": "value\n1\n"}, "value\n1\n"),
        (
            {
                "body": base64.b64encode(b"value\n1\n").decode("ascii"),
                "isBase64Encoded": True,
            },
            "value\n1\n",
        ),
    ],
)
def test_csv_body_decodes_payload(event: dict[str, object], expected: str) -> None:
    assert app.csv_body(event) == expected


@pytest.mark.parametrize("body", [None, "", "  "])
def test_csv_body_rejects_empty_payload(body: object) -> None:
    with pytest.raises(ValueError, match="CSV request body is empty"):
        app.csv_body({"body": body})


def test_lambda_handler_returns_csv_statistics() -> None:
    response = app.lambda_handler(
        {"body": "value\n10\n20\n30\n"},
        None,
    )

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json; charset=utf-8"
    assert json.loads(response["body"]) == {
        "columns": {
            "value": {
                "count": 3,
                "mean": 20.0,
                "median": 20.0,
                "std": pytest.approx(8.16496580927726),
                "max": 30.0,
                "min": 10.0,
            }
        }
    }


@pytest.mark.parametrize(
    ("event", "expected_error"),
    [
        ({"body": "  "}, "CSV request body is empty."),
        ({"body": "label\na\nb\n"}, "No numeric columns were found in the CSV."),
    ],
)
def test_lambda_handler_returns_bad_request_for_invalid_csv(
    event: dict[str, object], expected_error: str
) -> None:
    response = app.lambda_handler(event, None)

    assert response["statusCode"] == 400
    assert json.loads(response["body"]) == {"error": expected_error}


def test_lambda_handler_returns_internal_error_for_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_to_summarize(csv_text: str) -> dict[str, dict[str, float | int]]:
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(app, "summarize_csv", fail_to_summarize)

    response = app.lambda_handler({"body": "value\n1\n"}, None)

    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {"error": "Internal server error."}


def test_s3_lambda_handler_skips_non_csv_object() -> None:
    response = app.s3_lambda_handler(
        {"detail": {"bucket": {"name": "data"}, "object": {"key": "readme.txt"}}},
        None,
    )

    assert response == {"status": "skipped",
                        "bucket": "data", "key": "readme.txt"}


def test_s3_lambda_handler_summarizes_csv_object(monkeypatch: pytest.MonkeyPatch) -> None:
    s3_client = Mock()
    s3_client.get_object.return_value = {"Body": BytesIO(b"value\n4\n8\n")}
    monkeypatch.setattr(app.boto3, "client", Mock(return_value=s3_client))
    event = {
        "detail": {
            "bucket": {"name": "data"},
            "object": {"key": "uploads/values.csv"},
        }
    }

    result = app.s3_lambda_handler(event, None)

    s3_client.get_object.assert_called_once_with(
        Bucket="data", Key="uploads/values.csv")
    assert result == {
        "bucket": "data",
        "key": "uploads/values.csv",
        "columns": {
            "value": {
                "count": 2,
                "mean": 6.0,
                "median": 6.0,
                "std": 2.0,
                "max": 8.0,
                "min": 4.0,
            }
        },
    }
