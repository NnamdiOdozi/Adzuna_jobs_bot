"""Render vacancy comparisons and their supporting explanations as plain text."""

import html
import re


def _plain_text(value):
    text = " ".join(str(value).split())
    return re.sub(r"([\\`*_{}\[\]()!#|])", r"\\\1", html.escape(text))


def _summary(report):
    lines = [
        "# Ranking comparison",
        "",
        f"Snapshot: {_plain_text(report['snapshot_hash'])}",
        f"Fetched vacancies: {report.get('fetched_count', 'not recorded')}",
        "",
        "Agreement and schema validation do not prove suitability or agent execution.",
        "",
    ]
    for method, result in report["reports"].items():
        lines.extend([f"## {_plain_text(method)}: {_plain_text(result['status'])}", ""])
        status = result["status"]
        if status == "failed":
            lines.extend(["Execution failed. No successful ranking is available.", ""])
        elif status == "not_run":
            lines.extend(["This method was not run.", ""])
        elif status == "validated_output":
            lines.extend(
                [
                    "Output passed assessment checks; "
                    "agent execution is not independently verified.",
                    "",
                ]
            )
        receipt = result.get("receipt", {})
        if receipt.get("model"):
            lines.append(f"Model: {_plain_text(receipt['model'])}")
        if receipt.get("input_hash"):
            lines.append(f"Ranking input: {_plain_text(receipt['input_hash'])}")
        if receipt.get("prompt_hash"):
            lines.append(f"Prompt: {_plain_text(receipt['prompt_hash'])}")
        lines.append("")
        assessments = {str(row["id"]): row for row in receipt.get("assessments", [])}
        if method in report.get("overlap_with_rules", {}):
            lines.extend(
                [
                    f"Selected: {len(result.get('selected', []))}; "
                    f"also selected by rules: {report['overlap_with_rules'][method]}",
                    "",
                ]
            )
        for index, job in enumerate(result.get("selected", []), 1):
            # Render adverts as plain text; never create remote-loading Markdown.
            lines.append(
                f"{index}. {_plain_text(job['title'])} "
                f"(fetched #{report.get('job_index', {}).get(str(job['id']), '?')}; "
                f"ID: {_plain_text(job['id'])})"
            )
            assessment = assessments.get(str(job["id"]))
            if assessment:
                lines.append(
                    f"   Fit: {_plain_text(assessment['suitability'])}. "
                    f"Reason: {_plain_text(assessment['reason'])}"
                )
                if not assessment["evidence"]:
                    lines.append(
                        "   Evidence: not supplied; information is insufficient."
                    )
                for evidence in assessment["evidence"]:
                    lines.append(
                        f"   Evidence from {_plain_text(evidence['field'])}: "
                        f"{_plain_text(evidence['quote'])}"
                    )
        lines.append("")
    return "\n".join(lines) + "\n"
