# OpenAPI Compatibility Checker

A Python command-line tool that compares two versions of an API description and flags changes that could break existing clients. It reads OpenAPI 3.0 files directly, so you can check a proposed change before starting the API.

## How it works

In the sample book API, a client can send `POST /books` with just `{"title": "Kindred"}`. What happens if the API adds an ISBN field?

| Proposed change | Can the client still send just a title? | Result |
| --- | --- | --- |
| Add an optional `isbn` | Yes. The request is still valid. | Pass |
| Make `isbn` required | No. The request is missing a required field. | Breaking change |

The checker also compares routes, parameters and response schemas. For example, if a response used to guarantee a field and now makes it optional, an existing client might still expect it.

## Run locally

Requires Python 3.10 or newer. From the repository root, install the tool and compare the original spec with the proposed one:

```bash
python -m pip install ".[test]"
openapi-check examples/catalog.yaml examples/required-isbn.yaml
```

Expected output:

```text
BREAKING  POST /books request application/json.isbn  request property now required
```

Run the same command with `examples/optional-isbn.yaml` as the second file to see the passing case.

## Tests and CI

```bash
python -m pytest -q
```

On pull requests, GitHub Actions also compares [the catalog spec](contracts/catalog.yaml) against the base branch and attaches a JUnit report. See the check in action on the [passing PR](https://github.com/choidanny719/openapi-compatibility-checker/pull/1) and the [intentionally failing PR](https://github.com/choidanny719/openapi-compatibility-checker/pull/2).

<details>
<summary>Supported files, report formats and exit codes</summary>

Use one YAML or JSON file per version. The checker validates both files and follows references within each file. External and recursive references are unsupported. A pass means the implemented rules found no compatibility issues in the specs. Runtime behavior needs separate testing.

Output defaults to plain text. Use `--format json` for scripts or `--format junit` for CI.

| Exit code | Meaning |
| --- | --- |
| 0 | No compatibility findings |
| 1 | At least one breaking change |
| 2 | Invalid input, unsupported document or incorrect command |
| 3 | A change needs human review, such as an altered schema constraint |

</details>
