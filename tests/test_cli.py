import json

import pytest

from apicheck.cli import main
from apicheck.document import DocumentError, load


def spec(paths=None):
    return {"openapi": "3.0.3", "info": {"title": "Example", "version": "1"},
            "paths": {} if paths is None else paths}


def test_cli(tmp_path, capsys):
    base = tmp_path / "base.json"
    candidate = tmp_path / "new.yaml"
    base.write_text(json.dumps(spec({"/items": {"get": {"responses": {"200": {"description": "OK"}}}}})))
    candidate.write_text('openapi: 3.0.3\ninfo: {title: Example, version: "1"}\npaths: {}\n')
    assert main([str(candidate), str(base)]) == 0
    capsys.readouterr()
    assert main([str(base), str(candidate), "--format", "json"]) == 1
    assert json.loads(capsys.readouterr().out)[0]["location"] == "GET /items"


@pytest.mark.parametrize("content", ["[invalid", "openapi: 3.1.0", "a: 1\na: 2", "null",
                                    json.dumps(spec({"/a": {"$ref": "https://example.com/schema"}})),
                                    json.dumps(spec({"/a": {"$ref": "#/paths/~1a"}})),
                                    json.dumps(spec({"/a": {"$ref": "#/missing"}})),
                                    json.dumps(spec({"/a": {"get": {}}}))])
def test_invalid_document(tmp_path, content):
    path = tmp_path / "spec.yaml"
    path.write_text(content)
    with pytest.raises(DocumentError):
        load(path)


def test_missing_input_is_error(tmp_path):
    assert main([str(tmp_path / "missing"), "other"]) == 2
