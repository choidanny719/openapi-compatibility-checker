import pytest

from apicheck.rules import Comparison, compare


def obj(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required)}


string = {"type": "string"}
number = {"type": "number"}
integer = {"type": "integer"}


@pytest.mark.parametrize("old,new,request_side,severity", [
    (obj({}), obj({"note": string}), True, None),
    (obj({}), obj({"note": string}, ["note"]), True, "breaking"),
    (obj({"name": string}, ["name"]), obj({}), False, "breaking"),
    (obj({"name": string}), obj({}), False, "review"),
    (string, integer, True, "breaking"),
    (integer, number, True, None), (number, integer, True, "breaking"),
    (integer, number, False, "breaking"), (number, integer, False, None),
    ({"enum": ["a"]}, {"enum": ["a", "b"]}, True, None),
    ({"enum": ["a"]}, {"enum": ["a", "b"]}, False, "breaking"),
    ({}, {"enum": ["a"]}, True, "breaking"),
    ({"enum": ["a"]}, {}, False, "breaking"),
    ({"nullable": True}, {}, True, "breaking"), ({}, {"nullable": True}, False, "breaking"),
    ({"minimum": 0}, {"minimum": 1}, True, "review"),
    ({"description": "x"}, {"description": "y"}, True, None),
    (obj({}), obj({"id": {"readOnly": True}}, ["id"]), True, None),
    ({"type": "array", "items": integer}, {"type": "array", "items": string}, True, "breaking"),
])
def test_schema(old, new, request_side, severity):
    report = Comparison()
    report.schema("body", old, new, request_side)
    assert {f.severity for f in report.findings} == ({severity} if severity else set())


def test_operation_parameter_overrides_path_parameter():
    path_param = {"name": "q", "in": "query", "schema": string}
    inherited = {"paths": {"/items": {"parameters": [path_param], "get": {"responses": {}}}}}
    override = {"paths": {"/items": {"get": {"parameters": [dict(path_param, required=True)], "responses": {}}}}}
    finding, = compare(inherited, override)
    assert finding.location == "GET /items query parameter q"
    assert finding.severity == "breaking"


def test_response_type_change_and_removed_request_media():
    def doc(mime, schema):
        body = {"content": {mime: {"schema": schema}}}
        return {"paths": {"/books": {"post": {"requestBody": body, "responses": {"200": {
            "description": "OK", "content": {"application/json": {"schema": schema}}
        }}}}}}
    findings = compare(doc("application/json", string), doc("text/plain", integer))
    assert len(findings) == 2
    assert all(f.severity == "breaking" for f in findings)
