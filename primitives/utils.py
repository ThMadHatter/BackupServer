import json
from jinja2 import Template
from typing import Any, Dict
from primitives.base import Primitive

class JsonQuery(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        data = self.options.get("data")
        query = self.options.get("query")

        self.logger.info("Executing Json Query", query=query)

        if isinstance(data, str):
            data = json.loads(data)

        # Improved but still simple JMESPath-like implementation
        # Supports: field, field.subfield, list[].field
        parts = query.split('.')
        current = data

        for part in parts:
            if part.endswith('[]'):
                key = part[:-2]
                if key:
                    current = current.get(key, [])
                if not isinstance(current, list):
                    current = []
            else:
                if isinstance(current, list):
                    current = [item.get(part) for item in current if isinstance(item, dict) and part in item]
                elif isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
        return current

class TemplatePrimitive(Primitive):
    def execute(self, context: Dict[str, Any]) -> Any:
        template_str = self.options.get("template")
        variables = self.options.get("variables", {})

        # Merge context into variables
        merged_vars = {**context, **variables}

        self.logger.info("Executing Template rendering")
        template = Template(template_str)
        return template.render(**merged_vars)
