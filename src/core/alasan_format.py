"""Render a (reason_code, location, reason_detail) tuple as the free-form
'Alasan Ijin' text used in the user's Google Sheets monthly recap.

Examples seen in the user's actual sheet:
    "Lapangan ke Klaten"
    "Cuti, kepentingan keluarga"
    "Belum daftar fingerprint"
    "Lupa absen"
"""


def format_alasan(reason_code: str | None,
                  location: str | None,
                  reason_detail: str | None) -> str:
    if not reason_code:
        return ""

    loc = (location or "").strip()
    det = (reason_detail or "").strip()

    if reason_code == "tugas_lapangan":
        return f"Lapangan ke {loc}" if loc else "Lapangan"
    if reason_code == "tugas_paparan":
        return f"Tugas Paparan di {loc}" if loc else "Tugas Paparan"
    if reason_code == "sakit":
        return "Izin Sakit"
    if reason_code == "cuti":
        return f"Cuti, {det}" if det else "Cuti"
    if reason_code == "izin_pagi":
        return f"Izin Pagi - {det}" if det else "Izin Pagi"
    if reason_code == "pulang_awal":
        return f"Pulang Lebih Awal - {det}" if det else "Pulang Lebih Awal"
    if reason_code == "telat_kerja":
        return f"Masuk Terlambat - {det}" if det else "Masuk Terlambat"
    if reason_code == "telat_personal":
        return "Terlambat"
    if reason_code == "lupa_absen":
        return "Lupa absen"
    if reason_code == "belum_kabar":
        # Special case: when a Main DB cell was edited inline as free-form text,
        # it's stored with code='belum_kabar' and the typed text in detail.
        # Round-trip the text exactly.
        return det
    if reason_code == "tidak_hadir":
        return "Tidak Hadir"

    return reason_code  # unknown code — return verbatim as fallback
