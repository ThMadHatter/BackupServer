import pytest
from unittest.mock import patch
from engine.runner import ExecutionEngine
from engine.loader import ServiceSpec, StepSpec

def test_engine_with_mocks():
    spec = ServiceSpec(
        name="integration_test",
        backup=[
            StepSpec(
                name="get_data",
                type="http_get",
                options={"url": "http://api/data"},
                register="api_data"
            ),
            StepSpec(
                name="process_data",
                type="template",
                options={"template": "Data: {{ api_data.key }}"},
                register="processed"
            )
        ]
    )

    engine = ExecutionEngine()

    with patch("primitives.network.HttpGet.execute") as mock_get:
        mock_get.return_value = {"key": "value"}

        context = engine.run_service(spec)

        assert context["api_data"] == {"key": "value"}
        assert context["processed"] == "Data: value"
