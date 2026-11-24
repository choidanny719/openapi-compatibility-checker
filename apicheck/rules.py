import json
from dataclasses import dataclass

METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
ANNOTATIONS = {"title", "description", "summary", "example", "examples", "externalDocs", "tags", "deprecated"}


@dataclass(frozen=True, order=True)
class Finding:
    location: str
    severity: str
    message: str


class Comparison:
    def __init__(self):
        self.findings = set()

    def add(self, location, message, severity="breaking"):
        self.findings.add(Finding(location, severity, message))

    def remaining(self, location, old, new, handled):
        for key in sorted((old.keys() | new.keys()) - handled - ANNOTATIONS):
            if old.get(key) != new.get(key):
                self.add(location, f"{key} changed", "review")

    def schema(self, loc, old, new, request):
        if old == new:
            return
        old_type, new_type = old.get("type"), new.get("type")
        if old_type != new_type:
            known = old_type is not None and new_type is not None
            numeric = {old_type, new_type} == {"number", "integer"}
            if numeric:
                if (new_type == "integer") == request:
                    self.add(loc, f"type changed from {old_type} to {new_type}")
            else:
                self.add(loc, f"type changed from {old_type} to {new_type}", "breaking" if known else "review")
        if bool(old.get("nullable")) != bool(new.get("nullable")):
            if bool(new.get("nullable")) != request:
                self.add(loc, "null is no longer accepted" if request else "response may now be null")

        old_enum, new_enum = old.get("enum"), new.get("enum")
        if old_enum != new_enum:
            narrow, wide = (new_enum, old_enum) if request else (old_enum, new_enum)
            if narrow is not None and (wide is None or enum_keys(wide) - enum_keys(narrow)):
                self.add(loc, "accepted enum values narrowed" if request else "possible response enum values expanded")

        hidden = "readOnly" if request else "writeOnly"
        old_props = {k: v for k, v in old.get("properties", {}).items() if not v.get(hidden)}
        new_props = {k: v for k, v in new.get("properties", {}).items() if not v.get(hidden)}
        old_required = set(old.get("required", [])) - (old.get("properties", {}).keys() - old_props.keys())
        new_required = set(new.get("required", [])) - (new.get("properties", {}).keys() - new_props.keys())
        for key in (new_required - old_required if request else old_required - new_required):
            self.add(f"{loc}.{key}", "request property now required" if request else "response property no longer guaranteed")
        for key in old_props.keys() - new_props.keys():
            if not request and key in old_required and key not in new_required:
                continue
            self.add(f"{loc}.{key}", "property removed", "review")
        extra = "additionalProperties"
        if request and old.get(extra) is False and new.get(extra) is False:
            for key in old_props.keys() - new_props.keys():
                self.add(f"{loc}.{key}", "request property now forbidden")
        if not request and old.get(extra) is False:
            for key in new_props.keys() - old_props.keys():
                self.add(f"{loc}.{key}", "new response property outside the former closed schema")
        if old.get(extra, True) != new.get(extra, True):
            if old.get(extra, True) is True and new.get(extra) is False and request:
                self.add(loc, "additional request properties now forbidden")
            else:
                self.add(loc, "additionalProperties policy changed", "review")
        for key in old_props.keys() & new_props.keys():
            self.schema(f"{loc}.{key}", old_props[key], new_props[key], request)
        self.schema(f"{loc}[]", old.get("items", {}), new.get("items", {}), request)
        self.remaining(loc, old, new, {"type", "nullable", "enum", "properties", "required", "items", extra})

    def content(self, loc, old, new, request):
        for mime in old.keys() - new.keys():
            self.add(loc, f"media type {mime} removed")
        if not request:
            for mime in new.keys() - old.keys():
                self.add(loc, f"possible response media type {mime} added", "review")
        for mime in old.keys() & new.keys():
            a, b = old[mime], new[mime]
            self.schema(f"{loc} {mime}", a.get("schema", {}), b.get("schema", {}), request)
            self.remaining(loc, a, b, {"schema"})

    def parameters(self, loc, old, new):
        for key in old.keys() - new.keys():
            self.add(loc, f"{key[0]} parameter {key[1]} removed", "review")
        for key, b in new.items():
            here = f"{loc} {key[0]} parameter {key[1]}"
            a = old.get(key, {})
            if b.get("required") and not a.get("required"):
                self.add(here, "parameter now required")
            if key in old:
                self.schema(here, a.get("schema", {}), b.get("schema", {}), True)
                self.content(here, a.get("content", {}), b.get("content", {}), True)
                self.remaining(here, a, b, {"schema", "name", "in", "required", "content"})

    def operation(self, loc, old, new):
        a, b = old.get("requestBody", {}), new.get("requestBody", {})
        if b.get("required") and not a.get("required"):
            self.add(loc, "request body now required")
        if a:
            self.content(f"{loc} request", a.get("content", {}), b.get("content", {}), True)
            self.remaining(loc, a, b, {"required", "content"})
        old_res, new_res = old["responses"], new["responses"]
        for status in old_res.keys() ^ new_res.keys():
            self.add(f"{loc} {status}", "documented response status changed", "review")
        for status in old_res.keys() & new_res.keys():
            if status.startswith("x-"):
                continue
            a, b = old_res[status], new_res[status]
            self.content(f"{loc} response {status}", a.get("content", {}), b.get("content", {}), False)
            self.remaining(f"{loc} response {status}", a, b, {"content"})
        self.remaining(loc, old, new, {"parameters", "requestBody", "responses"})


def enum_keys(values):
    return {json.dumps(item, sort_keys=True, allow_nan=False) for item in values}


def parameters(path_item, operation):
    result = {}
    for p in [*path_item.get("parameters", []), *operation.get("parameters", [])]:
        name = p["name"].lower() if p["in"] == "header" else p["name"]
        result[p["in"], name] = p
    return result


def compare(base, candidate):
    report = Comparison()
    report.remaining("document", base, candidate, {"openapi", "info", "paths", "components"})
    report.remaining("security schemes", base.get("components", {}).get("securitySchemes", {}),
                     candidate.get("components", {}).get("securitySchemes", {}), set())
    for path, a in base["paths"].items():
        if path.startswith("x-"):
            continue
        b = candidate["paths"].get(path, {})
        report.remaining(path, a, b, METHODS | {"parameters"})
        for method in METHODS.intersection(a):
            loc = f"{method.upper()} {path}"
            if method not in b:
                report.add(loc, "operation removed")
                continue
            report.parameters(loc, parameters(a, a[method]), parameters(b, b[method]))
            report.operation(loc, a[method], b[method])
    return sorted(report.findings)
