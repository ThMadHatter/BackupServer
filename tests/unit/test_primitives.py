import pytest
from backup_server.primitives.network import HttpGet
from backup_server.primitives.utils import JsonQuery, TemplatePrimitive

def test_json_query():
    data = {
        "result": {
            "collections": [
                {"name": "col1"},
                {"name": "col2"}
            ]
        }
    }
    query = "result.collections[].name"
    primitive = JsonQuery("test", {"data": data, "query": query})
    result = primitive.execute({})
    assert result == ["col1", "col2"]

def test_json_query_complex():
    data = {
        "a": {
            "b": [
                {"c": 1},
                {"c": 2},
                {"d": 3}
            ]
        }
    }
    primitive = JsonQuery("test", {"data": data, "query": "a.b[].c"})
    result = primitive.execute({})
    assert result == [1, 2]

def test_template_primitive():
    context = {"user": "jules", "action": "testing"}
    template = "Hello {{ user }}, you are {{ action }}."
    primitive = TemplatePrimitive("test", {"template": template})
    result = primitive.execute(context)
    assert result == "Hello jules, you are testing."
