"""User-facing explanations for algorithmic matching and moderation decisions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import PHOTO_REVEAL_THRESHOLD
from app.engine import compute_compatibility


MATCH_POLICY_VERSION = "matching-v1"


def _reason(
    code: str,
    effect: str,
    explanation: str,
    evidence: dict[str, Any] | None = None,
    next_step: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "code": code,
        "effect": effect,
        "explanation": explanation,
    }
    if evidence:
        result["evidence"] = evidence
    if next_step:
        result["next_step"] = next_step
    return result


def explain_match_decision(
    viewer_profile: dict | None,
    target_profile: dict | None,
    *,
    cooling_off: bool = False,
    blocked: bool = False,
    weights: dict | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Explain whether a target would be shown by the matching endpoint.

    The function deliberately reports score dimensions rather than questionnaire
    answers. That makes the explanation useful without disclosing another
    person's private responses.
    """
    viewer_id = viewer_profile.get("id") if viewer_profile else None
    target_id = target_profile.get("id") if target_profile else None
    reasons: list[dict[str, Any]] = []
    timestamp = evaluated_at or datetime.now(timezone.utc).isoformat()
    response: dict[str, Any] = {
        "decision_type": "match",
        "policy": {"name": "Kindred compatibility matching", "version": MATCH_POLICY_VERSION},
        "viewer_profile_id": viewer_id,
        "target_profile_id": target_id,
        "evaluated_at": timestamp,
        "decision": "hidden",
        "algorithmic_outcome": "match_hidden",
        "reasons": reasons,
        "score": None,
    }

    if viewer_profile is None:
        reasons.append(_reason(
            "viewer_profile_missing",
            "hidden",
            "A profile is required before compatibility matching can run.",
            next_step="Complete your profile to receive compatibility matches.",
        ))
        return response

    if target_profile is None:
        reasons.append(_reason(
            "target_profile_unavailable",
            "hidden",
            "The requested profile is not available for matching.",
        ))
        return response

    if viewer_id == target_id:
        reasons.append(_reason(
            "same_profile",
            "hidden",
            "A profile is never recommended to itself.",
        ))
        return response

    if blocked:
        reasons.append(_reason(
            "safety_block",
            "hidden",
            "This profile is hidden because a block is active between the two profiles.",
            next_step="Remove the block if you want this profile to become eligible again.",
        ))

    if cooling_off:
        reasons.append(_reason(
            "report_cooling_off",
            "hidden",
            "This profile is hidden during the safety cooling-off period following a report.",
            next_step="The profile can become eligible again when the cooling-off period ends.",
        ))

    viewer_seeking = viewer_profile.get("seeking")
    target_gender = target_profile.get("gender")
    if viewer_seeking and target_gender != viewer_seeking:
        reasons.append(_reason(
            "viewer_preference_mismatch",
            "hidden",
            "The target profile does not match the viewer's stated gender preference.",
            {"viewer_seeking": viewer_seeking, "target_gender": target_gender},
        ))

    target_seeking = target_profile.get("seeking")
    viewer_gender = viewer_profile.get("gender")
    if target_seeking and viewer_gender != target_seeking:
        reasons.append(_reason(
            "target_preference_mismatch",
            "hidden",
            "The viewer does not match the target profile's stated gender preference.",
            {"viewer_gender": viewer_gender, "target_seeking": target_seeking},
        ))

    if reasons:
        return response

    compatibility = compute_compatibility(viewer_profile, target_profile, weights)
    response["decision"] = "shown"
    response["algorithmic_outcome"] = "match_shown"
    response["score"] = {
        "total": compatibility["total"],
        "raw_total": compatibility.get("raw_total"),
        "dimensions": compatibility["breakdown"],
        "weights": compatibility["weights"],
        "dealbreaker_conflict": compatibility["dealbreaker_conflict"],
        "conflicts": compatibility.get("conflicts", []),
    }
    reasons.append(_reason(
        "eligible_for_matching",
        "shown",
        "The profile passed the matching eligibility filters.",
    ))

    if compatibility["dealbreaker_conflict"]:
        reasons.append(_reason(
            "hard_dealbreaker_conflict",
            "score_zero",
            "A hard dealbreaker conflict reduced this compatibility score to zero; the matching feed still includes the result so the score decision is transparent.",
            {"conflicts": compatibility.get("conflicts", [])},
        ))

    if compatibility["total"] < PHOTO_REVEAL_THRESHOLD:
        reasons.append(_reason(
            "photo_reveal_threshold",
            "photo_hidden",
            "The match remains visible, but its photo is locked until the compatibility score reaches the photo reveal threshold.",
            {
                "score": compatibility["total"],
                "threshold": PHOTO_REVEAL_THRESHOLD,
            },
        ))

    return response


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _appeal_status(record: dict[str, Any]) -> str:
    if not record.get("appealed"):
        return "not_submitted"
    if not record.get("appeal_reviewed"):
        return "pending"
    result = record.get("appeal_result")
    return "overturned" if result == "overturned" else "upheld"


def _suspension_status(record: dict[str, Any], now: datetime) -> str:
    result = record.get("appeal_result")
    if result == "overturned":
        return "overturned"
    if result == "expired":
        return "expired"
    expires_at = _parse_timestamp(record.get("expires_at"))
    if record.get("suspension_type") == "temporary" and expires_at and expires_at <= now:
        return "expired"
    if record.get("appealed") and not record.get("appeal_reviewed"):
        return "appeal_pending"
    return "active"


def explain_suspension(
    user: dict,
    suspension_records: list[dict],
    *,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Return an account owner's suspension state and appeal evidence."""
    timestamp = evaluated_at or datetime.now(timezone.utc).isoformat()
    now = _parse_timestamp(timestamp) or datetime.now(timezone.utc)
    records: list[dict[str, Any]] = []
    for record in suspension_records:
        records.append({
            "id": record.get("id"),
            "reason": record.get("reason"),
            "suspension_type": record.get("suspension_type"),
            "expires_at": record.get("expires_at"),
            "appeal_status": _appeal_status(record),
            "status": _suspension_status(record, now),
            "created_at": record.get("created_at"),
        })

    current_status = "suspended" if bool(user.get("suspended")) else "active"
    active_record = next(
        (record for record in records if record["status"] in {"active", "appeal_pending"}),
        None,
    )
    if current_status == "suspended":
        reason = _reason(
            "active_suspension",
            "account_restricted",
            "Your account is currently suspended by a moderation decision.",
            {
                "suspension_type": active_record.get("suspension_type") if active_record else None,
                "expires_at": active_record.get("expires_at") if active_record else None,
                "appeal_status": active_record.get("appeal_status") if active_record else "not_available",
            },
            "Submit an appeal if you believe this decision was made in error.",
        )
    else:
        reason = _reason(
            "no_active_suspension",
            "account_allowed",
            "No active suspension is currently restricting this account.",
        )

    return {
        "decision_type": "suspension",
        "policy": {"name": "Kindred account moderation", "version": "suspension-v1"},
        "user_id": user.get("id"),
        "evaluated_at": timestamp,
        "decision": current_status,
        "algorithmic_outcome": "suspension_active" if current_status == "suspended" else "suspension_not_active",
        "reasons": [reason],
        "suspensions": records,
    }
