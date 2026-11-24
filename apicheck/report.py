from xml.etree import ElementTree as ET


def junit(findings):
    suite = ET.Element("testsuite", name="OpenAPI compatibility", tests=str(max(1, len(findings))),
                       failures=str(len(findings)))
    if not findings:
        ET.SubElement(suite, "testcase", name="contract comparison")
    for finding in findings:
        case = ET.SubElement(suite, "testcase", name=finding.location, classname="compatibility")
        ET.SubElement(case, "failure", type=finding.severity, message=finding.message)
    return ET.tostring(suite, encoding="unicode")
