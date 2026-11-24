import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from apicheck.cli import main
from apicheck.document import DocumentError, load


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
BASE = str(EXAMPLES / "catalog.yaml")


@pytest.mark.parametrize("filename,code", [("optional-isbn.yaml", 0), ("required-isbn.yaml", 1)])
def test_example_junit(capsys, filename, code):
    assert main([BASE, str(EXAMPLES / filename), "--format", "junit"]) == code
    suite = ET.fromstring(capsys.readouterr().out)
    assert suite.get("failures") == str(code)
    assert len(suite.findall("testcase")) == 1
    if code:
        assert "isbn" in suite.find("testcase").get("name")


def test_unhandled_constraint_reports_review(tmp_path, capsys):
    candidate = tmp_path / "new.yaml"
    candidate.write_text(Path(BASE).read_text().replace("{type: string}", "{type: string, minLength: 4}"))
    assert main([BASE, str(candidate), "--format", "json"]) == 3
    findings = json.loads(capsys.readouterr().out)
    assert [f["severity"] for f in findings] == ["review"]


def test_missing_component_reference(tmp_path):
    p = tmp_path / "ref.yaml"
    p.write_text(Path(BASE).read_text().replace("#/components/schemas/Book", "#/components/schemas/BookCopy"))
    with pytest.raises(DocumentError, match="unresolved"):
        load(p)


@pytest.mark.parametrize("value", [".nan", "2026-01-01", "!!binary ZGF0YQ=="])
def test_non_json_yaml_scalars_are_input_errors(tmp_path, value):
    p = tmp_path / "bad.yaml"
    p.write_text(Path(BASE).read_text().replace("title: Catalog", f"title: {value}"))
    with pytest.raises(DocumentError, match="JSON-compatible"):
        load(p)
