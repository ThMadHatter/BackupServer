import pytest
from unittest.mock import MagicMock, patch
from engine.runner import ExecutionEngine
from engine.loader import ServiceSpec, StepSpec
from src.core.exceptions import PrimitiveError

def test_engine_retry():
    spec = ServiceSpec(
        name="retry_test",
        backup=[
            StepSpec(
                name="fail_step",
                type="http_get",
                options={"url": "http://fail"},
                retry=2
            )
        ]
    )

    engine = ExecutionEngine()

    with patch("primitives.network.HttpGet.execute") as mock_execute:
        mock_execute.side_effect = Exception("Network Error")

        with pytest.raises(PrimitiveError, match="Network Error"):
            engine.run_service(spec)

        assert mock_execute.call_count == 3 # 1 initial + 2 retries
