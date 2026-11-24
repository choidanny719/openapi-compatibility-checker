from dataclasses import dataclass

METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


@dataclass(frozen=True, order=True)
class Finding:
    location: str
    severity: str
    message: str


def compare(base, candidate):
    findings = []
    for path, old_item in base["paths"].items():
        if path.startswith("x-"):
            continue
        new_item = candidate["paths"].get(path, {})
        for method in METHODS.intersection(old_item):
            if method not in new_item:
                findings.append(Finding(f"{method.upper()} {path}", "breaking", "operation removed"))
    return sorted(findings)
