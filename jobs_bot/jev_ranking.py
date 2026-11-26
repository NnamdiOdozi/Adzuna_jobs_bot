"""Choose suitable vacancies through Jev's fixed-choice classification API.

The daily coordinator uses this adapter when ``ranking.method`` is ``jev``.
Shared preparation removes seen and duplicate adverts, then each bounded batch
is assessed against the candidate profile and editable suitability policy.
Validated class probabilities determine acceptance and ordering. A separate
salary question reads pay wording; Python excludes above-cap ranges and keeps
unknown salaries explicit instead of inventing amounts.

The returned shortlist contains original provider records, preserving the data
used by the email builder. The accompanying assessment record contains decisions,
probabilities and usage metadata for the coordinator to save. Jev neither runs
agent tools nor formats emails or updates delivery history in this path.
"""

import json
import logging
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener
from zoneinfo import ZoneInfo

from jobs_bot.model_ranking import (
    RankingFailure,
    _hash,
    _NoRedirect,
    prepare_candidates,
)
from jobs_bot.screening import salary_details


def _failure_details(error):
    """Recognize documented provider codes without retaining private error text."""
    status = error.code if isinstance(error, HTTPError) else None
    reason = "request_or_response_failed"
    if isinstance(error, HTTPError):
        try:
            body = error.read(16384).decode("utf-8", errors="replace")
            # Emit only a fixed documented code, never arbitrary provider wording.
            if re.search(r"\bmax_tokens_exceeded\b", body):
                reason = "max_tokens_exceeded"
            else:
                reason = {
                    400: "invalid_request",
                    401: "authentication_failed",
                    413: "request_body_too_large",
                    422: "request_validation_failed",
                    429: "rate_limited",
                    529: "provider_overloaded",
                }.get(status, "provider_http_error")
        except Exception:
            reason = "provider_http_error_details_unavailable"
        finally:
            error.close()
    message = (
        "Jev rejected the batch because its context token limit was exceeded. "
        "Reduce the vacancy batch size or description length."
        if reason == "max_tokens_exceeded"
        else "Jev ranking failed; inspect the HTTP status and safe reason code."
    )
    return {"http_status": status, "reason": reason, "message": message}


def _choice(answer, labels):
    """Validate each suitability or salary decision before using it."""
    probabilities = answer["probabilities"]
    if (
        answer["type"] != "choice"
        or answer["choice"] not in labels
        or set(probabilities) != labels
        or any(
            type(p) not in (float, int) or not math.isfinite(p) or not 0 <= p <= 1
            for p in probabilities.values()
        )
        or abs(sum(probabilities.values()) - 1) > 0.001
    ):
        raise ValueError("Invalid classification probabilities")
    return answer["choice"], probabilities


def rank_jobs(jobs, seen, config, *, api_key=None):
    """Assess each unseen advert once; return selected jobs and probabilities."""
    settings = config["jev"]
    if settings["base_url"] != "https://api.typesafe.ai/v1/systemone":
        raise ValueError("Jev requires its intended HTTPS endpoint")
    for name in ("batch_size", "timeout_seconds"):
        if type(settings[name]) is not int or settings[name] <= 0:
            raise ValueError("Jev limits must be positive integers")
    policy = json.loads(Path(settings["policy_path"]).read_text())
    labels = set(config["ranking"]["allowed_labels"])
    if set(policy["criteria"]) != labels:
        raise ValueError("Jev policy must define every suitability category")
    salary_policy = None
    cap = config["search"].get("max_salary_gbp")
    if settings.get("salary_policy_path") and cap is not None:
        if type(cap) not in (int, float) or not math.isfinite(cap) or cap <= 0:
            raise ValueError("Salary cap must be positive and finite")
        salary_policy = json.loads(
            Path(settings["salary_policy_path"])
            .read_text()
            .replace("{cap_gbp}", str(cap))
        )
        if not set(salary_policy["excluded_labels"]) <= set(salary_policy["criteria"]):
            raise ValueError("Salary exclusions must be defined categories")
    candidates = prepare_candidates(jobs, seen, config)
    if (
        math.ceil(len(candidates) / settings["batch_size"])
        > config["ranking"]["max_calls"]
    ):
        raise ValueError("Jev request budget exceeded before inference")
    state = {
        "candidate_profile": config["candidate"]["profile"],
        "policy": policy["context"],
        "assessment_date": datetime.now(ZoneInfo(config["email"]["timezone"]))
        .date()
        .isoformat(),
    }
    receipt = {
        "model": settings["model"],
        "calls": 0,
        "attempted_calls": 0,
        "assessments": [],
        "token_usage": {"input_tokens": 0, "output_tokens": 0},
        "input_hash": _hash(
            {
                "candidates": candidates,
                "state": state,
                "policy": policy,
                "salary_policy": salary_policy,
            }
        ),
        "truncation": [job["id"] for job in candidates if job["description_truncated"]],
    }
    started = time.monotonic()
    pending = [
        candidates[start : start + settings["batch_size"]]
        for start in range(0, len(candidates), settings["batch_size"])
    ]
    while pending:
        if receipt["attempted_calls"] >= config["ranking"]["max_calls"]:
            failure = RankingFailure("request_budget_exceeded")
            failure.receipt = receipt
            raise failure
        batch = pending.pop(0)
        questions = {}
        for i, job in enumerate(batch):
            advert = {
                "title": job["title"],
                "employer": job["company"]["display_name"],
                "location": job["location"]["display_name"],
                "description": job["description"],
                "description_truncated": job["description_truncated"],
            }
            questions[f"job_{i}"] = {
                "type": "choice",
                "criteria": policy["criteria"],
                "instructions": {
                    "question": "How does this vacancy fit the candidate?",
                    "advert": advert,
                },
            }
            if salary_policy:
                questions[f"salary_{i}"] = {
                    "type": "choice",
                    "criteria": salary_policy["criteria"],
                    "instructions": {
                        "question": salary_policy["question"],
                        "advert": advert,
                    },
                }
        payload = {"model": settings["model"], "state": state, "questions": questions}
        request_bytes = len(json.dumps(payload).encode())
        description_chars = sum(len(job["description"]) for job in batch)
        receipt.setdefault("batches", []).append(
            {
                "vacancies": len(batch),
                "questions": len(questions),
                "request_bytes": request_bytes,
                "description_characters": description_chars,
            }
        )
        receipt["attempted_calls"] += 1
        batch_number = receipt["attempted_calls"]
        remaining = config["ranking"]["max_elapsed_seconds"] - (
            time.monotonic() - started
        )
        if remaining <= 0:
            failure = RankingFailure("timeout", batch=batch_number)
            failure.receipt = receipt
            raise failure
        logging.info(
            "event=jev_request state=ready->requested batch=%d "
            "questions=%d request_bytes=%d description_characters=%d input_hash=%s",
            batch_number,
            len(questions),
            request_bytes,
            description_chars,
            receipt["input_hash"],
        )
        try:
            request = Request(
                settings["base_url"],
                data=json.dumps(payload).encode(),
                method="POST",
                headers={
                    "Authorization": "Bearer "
                    + (api_key or os.environ["TYPESAFE_API_KEY"]),
                    "Content-Type": "application/json",
                },
            )
            with build_opener(_NoRedirect()).open(
                request, timeout=min(settings["timeout_seconds"], remaining)
            ) as response:
                result = json.load(response)
            if result["model"] != settings["model"] or set(result["answers"]) != set(
                questions
            ):
                raise ValueError("Unexpected model or incomplete assessment coverage")
            assessed = []
            for i, job in enumerate(batch):
                answer = result["answers"][f"job_{i}"]
                category, probabilities = _choice(answer, labels)
                salary = {}
                if salary_policy:
                    salary_category, salary_probabilities = _choice(
                        result["answers"][f"salary_{i}"], set(salary_policy["criteria"])
                    )
                    salary = {
                        "salary_category": salary_category,
                        "salary_probabilities": salary_probabilities,
                    }
                assessed.append(
                    {
                        "id": job["id"],
                        "suitability": category,
                        "probabilities": probabilities,
                        **salary,
                    }
                )
            for name in receipt["token_usage"]:
                value = result["usage"][name]
                if type(value) is not int or value < 0:
                    raise ValueError("Invalid Jev token usage")
            receipt["assessments"].extend(assessed)
            for name in receipt["token_usage"]:
                receipt["token_usage"][name] += result["usage"][name]
            receipt["calls"] += 1
        except Exception as error:
            details = _failure_details(error)
            logging.error(
                "event=jev_request state=requested->failed batch=%d "
                "http_status=%s reason=%s request_bytes=%d message=%s",
                batch_number,
                details["http_status"],
                details["reason"],
                request_bytes,
                details["message"],
            )
            if details["reason"] == "max_tokens_exceeded" and len(batch) > 1:
                # Retry smaller groups, never the identical oversized payload.
                # Attempt and elapsed-time budgets still apply to every call.
                middle = len(batch) // 2
                pending[:0] = [batch[:middle], batch[middle:]]
                logging.warning(
                    "event=jev_request state=rejected->split batch=%d "
                    "vacancies=%d left=%d right=%d",
                    batch_number,
                    len(batch),
                    middle,
                    len(batch) - middle,
                )
                continue
            failure = RankingFailure(
                "jev_request_failed",
                batch=batch_number,
                request_bytes=request_bytes,
                **details,
            )
            failure.receipt = receipt
            raise failure from None
    by_id = {job["id"]: job for job in candidates}
    if salary_policy:
        for row in receipt["assessments"]:
            row["salary_assessment"] = salary_details(by_id[row["id"]], row)
    excluded_salary = set(salary_policy["excluded_labels"]) if salary_policy else set()
    receipt["salary_exclusions"] = [
        row["id"]
        for row in receipt["assessments"]
        if row.get("salary_category") in excluded_salary
    ]
    acceptable = [
        row
        for row in receipt["assessments"]
        if row["suitability"] in config["ranking"]["selected_labels"]
        and row.get("salary_category") not in excluded_salary
    ]
    acceptable.sort(
        key=lambda row: (
            -(
                row["probabilities"]["strong_fit"]
                + row["probabilities"]["possible_fit"]
            ),
            -row["probabilities"]["strong_fit"],
            row["id"],
        )
    )
    receipt["elapsed_seconds"] = time.monotonic() - started
    return [
        {
            **by_id[row["id"]],
            **(
                {"salary_assessment": row["salary_assessment"]} if salary_policy else {}
            ),
        }
        for row in acceptable[: config["search"]["shortlist_size"]]
    ], receipt
