# OpenAPI Compatibility Checker

A Python CLI that compares two OpenAPI 3.0.x contracts from the perspective of an existing client. It reads YAML or JSON, validates the documents and follows local references. The service does not need to be running.

## Try it

From the repository root, with Python 3.10 or newer:

```sh
python -m pip install '.[test]'
openapi-check examples/catalog.yaml examples/optional-isbn.yaml
openapi-check examples/catalog.yaml examples/required-isbn.yaml
python -m pytest -q
```

The first comparison passes. The second exits 1 because a client that previously sent only a title must now send an ISBN. Each finding includes the HTTP operation, location and reason. Use `--format json` for structured output or `--format junit` for an XML report.

| Exit | Meaning |
| --- | --- |
| 0 | No findings under the implemented rules |
| 1 | At least one breaking change |
| 2 | Invalid input, unsupported document or usage error |
| 3 | Changes need review; none were classified as breaking |

## Rules and scope

Checks cover removed operations and media types, mandatory request bodies and parameters, property requirements, types, arrays, enum values and nullability. Rules distinguish requests from responses. Accepting another enum value in a request is compatible; returning a new enum value may break an existing client. Changed schema constraints or composition rules outside the implemented set produce review findings. Compatible and breaking cases live in `tests/`.

Use one self-contained document per version. External and recursive references are rejected. Quote response codes and ambiguous YAML strings. The checker describes the documented contract and assumes clients accept extra fields in open response objects. It cannot prove runtime behavior, infer undocumented consumer expectations or assess the effect of every combination of schema constraints.

GitHub Actions runs the tests on pushes and pull requests. For pull requests it also compares `examples/catalog.yaml` against the base revision, fails on findings and attaches the JUnit report. To use the check in another repo, install this tool and point the two arguments at that repo's base and proposed specs.
