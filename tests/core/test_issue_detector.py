from src.core.issue_detector import classify_issue


def make_record(**overrides):
    base = {
        "actual_in": "08:00",
        "actual_out": "16:00",
        "late_minutes": 0,
        "early_leave_minutes": 0,
        "day_type": "Hari Kerja",
    }
    base.update(overrides)
    return base


def test_case_a_full_absent():
    rec = make_record(actual_in=None, actual_out=None)
    assert classify_issue(rec) == "A"


def test_case_b_no_masuk():
    rec = make_record(actual_in=None, actual_out="19:00")
    assert classify_issue(rec) == "B"


def test_case_c_no_keluar():
    rec = make_record(actual_in="08:14", actual_out=None)
    assert classify_issue(rec) == "C"


def test_case_d_late_mild():
    rec = make_record(late_minutes=6)
    assert classify_issue(rec, late_threshold=15) == "D"


def test_case_e_late_severe():
    rec = make_record(late_minutes=161)
    assert classify_issue(rec, late_threshold=15) == "E"


def test_case_f_pulang_cepat():
    rec = make_record(early_leave_minutes=30)
    assert classify_issue(rec, pulang_cepat_threshold=0) == "F"


def test_case_g_istirahat():
    rec = make_record(day_type="Istirahat")
    assert classify_issue(rec) == "G"


def test_late_threshold_null_disables_de():
    rec = make_record(late_minutes=20)
    assert classify_issue(rec, late_threshold=None) is None


def test_pulang_cepat_threshold_null_disables_f():
    rec = make_record(early_leave_minutes=30)
    assert classify_issue(rec, pulang_cepat_threshold=None) is None


def test_no_issue_clean_record():
    rec = make_record()
    assert classify_issue(rec) is None
