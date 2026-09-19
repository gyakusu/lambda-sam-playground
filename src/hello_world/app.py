from typing import Any


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"message":"Hello from local Lambda!"}',
    }
