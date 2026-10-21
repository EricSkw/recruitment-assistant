"""SAD scoring rubric. Points are recommendations for human review."""

RUBRIC_POINTS: dict[str, int] = {
    "skills_match": 40,
    "seniority_fit": 20,
    "evidence_quality": 25,
    "location_remote_fit": 15,
}

EVIDENCE_CAP_UNVERIFIED = 5


def rubric_total() -> int:
    return sum(RUBRIC_POINTS.values())
