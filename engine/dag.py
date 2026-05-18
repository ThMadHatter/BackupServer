from typing import List, Dict, Set
from engine.loader import StepSpec

class DAGError(Exception):
    pass

class ExecutionDAG:
    def __init__(self, steps: List[StepSpec]):
        self.steps = {step.name: step for step in steps}
        self.adj: Dict[str, Set[str]] = {step.name: set() for step in steps}

        for step in steps:
            for dep in step.depends_on:
                if dep not in self.steps:
                    raise DAGError(f"Step '{step.name}' depends on non-existent step '{dep}'")
                self.adj[dep].add(step.name)

        self._validate_no_cycles()

    def _validate_no_cycles(self):
        visited = set()
        path = set()

        def visit(node):
            if node in path:
                raise DAGError(f"Cycle detected in execution DAG involving step '{node}'")
            if node in visited:
                return

            path.add(node)
            for neighbor in self.adj[node]:
                visit(neighbor)
            path.remove(node)
            visited.add(node)

        for step_name in self.steps:
            visit(step_name)

    def get_execution_order(self) -> List[StepSpec]:
        # Standard Kahn's algorithm for topological sort
        in_degree = {step_name: 0 for step_name in self.steps}
        for u in self.adj:
            for v in self.adj[u]:
                in_degree[v] += 1

        queue = [step_name for step_name in self.steps if in_degree[step_name] == 0]

        sorted_steps = []
        original_names = [s.name for s in self.steps.values()]

        while queue:
            # Sort queue to be deterministic based on original spec order
            queue.sort(key=lambda name: original_names.index(name))
            u = queue.pop(0)
            sorted_steps.append(self.steps[u])

            for v in self.adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)

        return sorted_steps
