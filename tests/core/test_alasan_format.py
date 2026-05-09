import pytest
from src.core.alasan_format import format_alasan

@pytest.mark.parametrize("code,location,detail,expected", [
    (None, None, None, ""),
    ("tugas_lapangan", "Klaten", None, "Lapangan ke Klaten"),
    ("tugas_lapangan", None, None, "Lapangan"),
    ("tugas_lapangan", "", None, "Lapangan"),
    ("tugas_paparan", "PT FAFIFU", None, "Tugas Paparan di PT FAFIFU"),
    ("tugas_paparan", None, None, "Tugas Paparan"),
    ("sakit", None, None, "Izin Sakit"),
    ("cuti", None, None, "Cuti"),
    ("cuti", None, "kepentingan keluarga", "Cuti, kepentingan keluarga"),
    ("izin_pagi", None, "urus dokumen", "Izin Pagi - urus dokumen"),
    ("izin_pagi", None, None, "Izin Pagi"),
    ("pulang_awal", None, "anak sakit", "Pulang Lebih Awal - anak sakit"),
    ("pulang_awal", None, None, "Pulang Lebih Awal"),
    ("telat_kerja", None, "meeting client", "Masuk Terlambat - meeting client"),
    ("telat_kerja", None, None, "Masuk Terlambat"),
    ("telat_personal", None, None, "Terlambat"),
    ("lupa_absen", None, None, "Lupa absen"),
    ("belum_kabar", None, None, ""),
    ("belum_kabar", None, "Belum daftar fingerprint", "Belum daftar fingerprint"),
    ("tidak_hadir", None, None, "Tidak Hadir"),
])
def test_format_alasan_cases(code, location, detail, expected):
    assert format_alasan(code, location, detail) == expected
