import pytest
from pathlib import Path
from engine.loader import load_spec

def test_load_spec(tmp_path):
    spec_content = """
name: test_service
backup:
  - name: step1
    type: http_get
    options:
      url: "http://{{ host }}/api"
"""
    spec_file = tmp_path / "test.yaml"
    spec_file.write_text(spec_content)

    spec = load_spec(spec_file, {"host": "localhost"})
    assert spec.name == "test_service"
    assert spec.backup[0].options["url"] == "http://localhost/api"
