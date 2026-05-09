def classify_issue(
    record: dict,
    late_threshold: int | None = 15,
    pulang_cepat_threshold: int | None = 0,
) -> str | None:
    """
    Classify the attendance record into one of cases A-G or None.
    See spec §6 for the full rule set.

    Priority order matters: data-missing cases (A/B/C) take precedence over
    timing-based cases (D/E/F). Case G (Istirahat) short-circuits.
    """
    # Case G: rest day, skip
    if record.get("day_type") == "Istirahat":
        return "G"

    actual_in = record.get("actual_in")
    actual_out = record.get("actual_out")

    # Case A: both empty
    if not actual_in and not actual_out:
        return "A"
    # Case B: masuk empty, keluar filled
    if not actual_in and actual_out:
        return "B"
    # Case C: masuk filled, keluar empty
    if actual_in and not actual_out:
        return "C"

    # Both timestamps present — check passive issues
    late = record.get("late_minutes", 0) or 0
    early = record.get("early_leave_minutes", 0) or 0

    # Case F: Pulang Cepat (data-complete but unusual — needs follow-up + color)
    if pulang_cepat_threshold is not None and early > pulang_cepat_threshold:
        return "F"

    # Cases D / E: late (color only — never returned if threshold is None)
    if late_threshold is not None and late > 0:
        if late < late_threshold:
            return "D"
        return "E"

    return None


def needs_follow_up(case: str | None) -> bool:
    """Cases that appear in the Issues list."""
    return case in ("A", "B", "C", "F")


def needs_cell_color(case: str | None) -> str | None:
    """Returns CSS-like color name or None for cell display."""
    return {
        "D": "yellow",
        "E": "red",
        "F": "orange",
    }.get(case)


RECOMMENDATIONS = {
    "A": "Tidak Hadir / Cuti / Izin Sakit?",
    "B": "Izin Pagi / Lupa Absen Masuk?",
    "C": "Lupa Absen Pulang / Pulang Lebih Awal?",
    "F": "Pulang Lebih Awal?",
}


def recommend(issue_case: str | None) -> str | None:
    """Suggest plausible resolution categories given an issue_case.
    Used by Issues page UI as an inline hint."""
    if not issue_case:
        return None
    return RECOMMENDATIONS.get(issue_case)
