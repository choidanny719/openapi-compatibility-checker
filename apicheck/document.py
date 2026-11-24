import math
from pathlib import Path
from urllib.parse import unquote

import yaml
from openapi_spec_validator import OpenAPIV30SpecValidator


class DocumentError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise DocumentError(f"expected a string key on line {key_node.start_mark.line + 1}")
            if key in result:
                raise DocumentError(f"duplicate key {key!r} on line {key_node.start_mark.line + 1}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def expand(value, root, trail=(), budget=None):
    if budget is None:
        budget = [250_000]
    budget[0] -= 1
    if budget[0] < 0:
        raise DocumentError("expanded document exceeds 250,000 nodes")
    if isinstance(value, list):
        return [expand(item, root, trail, budget) for item in value]
    if not isinstance(value, dict):
        if value is None or isinstance(value, (bool, int, str)):
            return value
        if isinstance(value, float) and math.isfinite(value):
            return value
        raise DocumentError(f"expected a JSON-compatible value, got {value!r}")
    if "$ref" in value:
        ref = value["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise DocumentError(f"only local JSON pointers are supported: {ref!r}")
        if len(value) != 1:
            raise DocumentError(f"sibling fields on a reference are unsupported: {ref}")
        if ref in trail:
            raise DocumentError(f"recursive reference is unsupported: {ref}")
        target = root
        try:
            for part in unquote(ref[2:]).split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
        except (KeyError, TypeError, IndexError) as exc:
            raise DocumentError(f"unresolved reference: {ref}") from exc
        return expand(target, root, (*trail, ref), budget)
    return {k: expand(v, root, trail, budget) for k, v in value.items()}


def load(path: Path):
    try:
        doc = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
        if not isinstance(doc, dict) or not str(doc.get("openapi", "")).startswith("3.0."):
            raise DocumentError("expected an OpenAPI 3.0.x document")
        resolved = expand(doc, doc)
        error = next(OpenAPIV30SpecValidator(resolved).iter_errors(), None)
        if error is not None:
            raise DocumentError(error.message)
        return resolved
    except (ValueError, OSError, yaml.YAMLError, RecursionError) as exc:
        raise DocumentError(f"{path}: {exc}") from exc
