import pytest
from backup_server.dag import ExecutionDAG, DAGError
from backup_server.loader import StepSpec

def test_dag_ordering():
    steps = [
        StepSpec(name="step1", type="test", depends_on=[]),
        StepSpec(name="step2", type="test", depends_on=["step1"]),
        StepSpec(name="step3", type="test", depends_on=["step1"]),
        StepSpec(name="step4", type="test", depends_on=["step2", "step3"]),
    ]
    dag = ExecutionDAG(steps)
    order = [s.name for s in dag.get_execution_order()]

    assert order[0] == "step1"
    assert "step2" in order[1:3]
    assert "step3" in order[1:3]
    assert order[3] == "step4"

def test_dag_cycle_detection():
    steps = [
        StepSpec(name="step1", type="test", depends_on=["step2"]),
        StepSpec(name="step2", type="test", depends_on=["step1"]),
    ]
    with pytest.raises(DAGError, match="Cycle detected"):
        ExecutionDAG(steps)

def test_dag_missing_dependency():
    steps = [
        StepSpec(name="step1", type="test", depends_on=["nonexistent"]),
    ]
    with pytest.raises(DAGError, match="depends on non-existent step"):
        ExecutionDAG(steps)
