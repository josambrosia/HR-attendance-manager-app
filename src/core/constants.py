"""Constants used across the app."""

DEFAULT_SETTINGS = {
    "coaching_threshold_minutes": 75,
    "late_threshold_minutes": 15,        # set to None to disable late cell coloring
    "lupa_absen_penalty_minutes": 16,    # set to None to disable
    "pulang_cepat_threshold_minutes": 0, # set to None to disable Pulang Cepat flagging
    "working_hours_start": "08:00",
    "working_hours_end": "16:00",
    "workdays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "theme": "dark",
    "repeat_offender_weeks": 3,
}

REASON_CODES = {
    "tugas_lapangan": {"label": "Tugas Lapangan", "extra": "location"},
    "tugas_paparan": {"label": "Tugas Paparan", "extra": "location"},
    "sakit": {"label": "Izin Sakit", "extra": None},
    "cuti": {"label": "Cuti", "extra": None},
    "izin_pagi": {"label": "Izin Pagi", "extra": "reason_detail"},
    "pulang_awal": {"label": "Pulang Lebih Awal", "extra": "reason_detail"},
    "telat_kerja": {"label": "Masuk Terlambat dengan Alasan Pekerjaan", "extra": "reason_detail"},
    "telat_personal": {"label": "Terlambat", "extra": None},
    "lupa_absen": {"label": "Lupa Absen (terhitung telat 16 menit)", "extra": None},
    "belum_kabar": {"label": "Belum Ada Kabar", "extra": None},
    "tidak_hadir": {"label": "Tidak Hadir", "extra": None},
}

# Sunset Coral palette
COLORS = {
    "primary": "#7C3AED",
    "accent": "#F472B6",
    "highlight": "#FBBF24",
    "resolved": "#34D399",
    "late_mild": "#FCD34D",
    "late_severe": "#F87171",
    "pulang_cepat": "#C084FC",
    "bg_dark": "#1a0b2e",
    "bg_light": "#faf5ff",
    "surface_dark": "#2d1b4e",
    "surface_light": "#ffffff",
    "text_dark": "#e9d5ff",
    "text_light": "#1e1b4b",
}
