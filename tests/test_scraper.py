import csv
from pathlib import Path

from sked_parser.scraper import (
    create_id,
    extract_semester,
    optimize_label,
    guess_degree,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_semester_digit_before_sem():
    """Faculties F, S, V, W write the digit in front of "Sem" (the most common convention)"""
    assert extract_semester("Angewandte Informatik - 1. Semester", "") == 1
    assert extract_semester("1. Sem. EIT", "") == 1
    assert extract_semester("1 Sem Informatik", "") == 1
    assert extract_semester("IVG_1_1.Sem", "") == 1
    assert extract_semester("2. Fachsemester Smart Vehicle Systems", "") == 2
    assert extract_semester("Nothing in here", "i/Semester/Semester-Liste/I-B.Sc. WI 1. Sem..html") == 1
    # URL escaped spaces must not hide the semester
    assert extract_semester("", "s/wp/WS202627/Bachelor%20Soziale%20Arbeit_3_3.%20Sem.html") == 3


def test_extract_semester_digit_glued_to_shorthand():
    """Faculties E, G and M glue the semester digit directly onto the course shorthand"""
    assert extract_semester("", "e/semester/E-EIT-GS-Sem1.html") == 1
    assert extract_semester("", "g/wp/BMRD1_WS2627.html") == 1
    assert extract_semester("BM-WiSe2026 (PO2018) - BM4a", "m/sem/BM4a%20(PO2018).html") == 4
    assert extract_semester("BDE-WiSe2026 (PO2025) - BDE6_SP", "m/sem/BDE6_SP%20(PO2025).html") == 6
    assert extract_semester("BWi-WiSe2026 (PO2025) - BWi1b", "m/sem/BWi1b%20(PO2025).html") == 1
    assert extract_semester("BM-WiSe2026 (PO2018) - BM3", "m/sem/BM3%20(PO2018).html") == 3
    assert extract_semester("BM-WiSe2026 (PO2018) - BM7_P&L", "m/sem/BM7_P&L%20(PO2018).html") == 7


def test_extract_semester_digit_at_end_of_url():
    """Faculties B, H, K and R only put the digit at the very end of the file name"""
    assert extract_semester("Nothing in here", "r/studentenset/23-03-r-b-rfs-2.html") == 2
    assert extract_semester("", "b/wp/ws26_b_stgrp_ai_1.html") == 1
    assert extract_semester("", "h/lvp/wp/h_stdgrp_soa_2.html") == 2
    assert extract_semester("", "k/prod/vorlesungsplaene/wp/ws/stjg_ap_5.html") == 5
    # A digit in the middle is not a semester, it's part of the date prefix
    assert extract_semester("Nothing in here", "r/studentenset/23-2-r-b-rfs.html") is None


def test_extract_semester_ignores_year_numbers():
    """Years must never be mistaken for a semester, no matter how they are written"""
    assert extract_semester("IMES Teilzeit 2018", "") is None
    assert extract_semester("MSE-WiSe2026 - MSE", "m/sem/MSE.html") is None
    assert extract_semester("BM-WiSe2026 (PO2018) - BM4a", "") == 4
    assert extract_semester("Wasser- und Bodenmanagement - PO 2018 - 3. Semester", "") == 3
    # Two digit "semesters" don't exist, so this is some other number
    assert extract_semester("Wasser- und Bodenmanagement - 20. Sem", "") is None


def test_extract_semester_duplicated_sem():
    """Test string with duplicated semesters"""
    sem_str = "Soziale Arbeit - 5. Semester - PO 2018 - 5. Semester - Soziale Arbeit"
    assert extract_semester(sem_str, "") == 5


def test_extract_semester_multiple_semesters():
    """Test that in case of multiple semesters, only the last one is returned (for now)"""
    sem_str = "Bio- und Umwelttechnik (BEE ) - 3. - 4.  Semester"
    assert extract_semester(sem_str, "") == 4


def test_extract_semester_wahlpflicht():
    """Test that "Wahlpflichtfächer" are correctly identified"""
    sem_str = "Management im Gesundheitswesen Wahlpflichtangebot"
    assert extract_semester(sem_str, "") == "WPF"
    # Also make sure to return WPF even if a semester is given
    sem_str = "Wahlpflichtangebot (WPF MIG) 5. und höhere Sem."
    assert extract_semester(sem_str, "") == "WPF"


def test_extract_semester_corpus():
    """Golden test over every timetable URL spluseins published since 2020, from its timetables.json git history.

    `extracted` is what extract_semester(desc="", sked_path) returned when the fixture was written, so a diff
    there is the full blast radius of a pattern change. Prüfungen never enter the corpus because the blacklist
    keeps them out of timetables.json, room plans and URLs Ostfalia recycled across terms are dropped by hand.
    """
    # regenerate: take (timetablePath, semester) from every revision of spluseins' server/assets/timetables.json,
    # dedupe by path, fill `extracted` via extract_semester, then drop Raumbelegung plans (their number is a room,
    # not a semester, and they are no longer scraped) and rows where both columns are numbers but disagree
    with open(FIXTURES / "url_semesters.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    changed, contradictions = [], []
    for row in rows:
        got = extract_semester("", row["sked_path"])
        got_str = "" if got is None else str(got)
        if got_str != row["extracted"]:
            changed.append(f"{row['sked_path']}: fixture says {row['extracted']!r}, got {got_str!r} (spluseins: {row['published']!r})")
        if got_str.isdigit() and row["published"].isdigit() and got_str != row["published"]:
            contradictions.append(f"{row['sked_path']}: spluseins published {row['published']!r}, got {got_str!r}")
    assert not contradictions, "Semester extracted from the URL contradicts what spluseins published for {} URLs:\n{}".format(
        len(contradictions), "\n".join(contradictions[:40])
    )
    assert not changed, "Semester extraction changed for {} of {} URLs, review and regenerate the fixture:\n{}".format(
        len(changed), len(rows), "\n".join(changed[:40])
    )


def test_optimize_label_strip_semester():
    """Verify the semester is correctly stripped from the label"""
    # Semester at end
    in_str = "Bauingenieurwesen - 1. Semester"
    assert optimize_label(in_str, False) == "Bauingenieurwesen"
    # Semester at start
    in_str = "4. Semester Servicetechnik und Prozesse"
    assert optimize_label(in_str, False) == "Servicetechnik und Prozesse"
    # Duplicated / multiple semester strings
    in_str = "5. Semester - PO 2018 - 5. Semester - Handel"
    assert optimize_label(in_str, False) == "PO 2018 - Handel"
    # Multiple semesters in one substring
    in_str = "Umwelttechnik - 3. - 4.  Semester"
    assert optimize_label(in_str, False) == "Umwelttechnik"
    # Fachsemester statt Semester
    in_str = "1. Fachsemester Smart Vehicle Systems"
    assert optimize_label(in_str, False) == "Smart Vehicle Systems"
    # Semester shorthand used
    in_str = "Wirtschaftsinformatik 5. Sem."
    assert optimize_label(in_str, False) == "Wirtschaftsinformatik"
    # Even shorter semester shorthand used
    in_str = "Wirtschaftsinformatik 5 Sem"
    assert optimize_label(in_str, False) == "Wirtschaftsinformatik"
    # Weird duplicated semester string with CSV at end
    in_str = "WI_4_4. Sem..csv"
    assert optimize_label(in_str, False) == "WI"


def test_optimize_label():
    """Verify the semester is correctly stripped from the label"""
    # mit of Science
    in_str = "Bachelor of Science Informatik"
    assert optimize_label(in_str, False) == "Informatik"
    # ohne of Science
    in_str = "Master Informatik"
    assert optimize_label(in_str, False) == "Informatik"
    # WiSe/SoSe year token is stripped (faculty M)
    assert optimize_label("BM-WiSe2026 (PO2018) - BM4a", False) == "BM (PO2018) - BM4a"
    assert optimize_label("Handel - WiSe 21/22", False) == "Handel"


def test_optimize_label_shorthand_strip():
    """Verify that the shorthand is correctly used instead of the longform if requested"""
    # Simple shorthand and text after it
    in_str = "Energie- und Gebäudetechnik (EGT) - TGA"
    assert optimize_label(in_str, True) == "EGT - TGA"
    # Shorthand with special chars and extra whitespace
    in_str = "Energie- und Gebäudetechnik ( EGT / EGTiP ) - TGA"
    assert optimize_label(in_str, True) == "EGT / EGTiP - TGA"
    # Shorthand string with numbers in it should not be replaced/used
    in_str = "Vertiefung CE (PO18)"
    assert optimize_label(in_str, True) == "Vertiefung CE (PO18)"


def test_extract_id():
    """Verify that the ID extraction works correctly"""
    faculty_short = "e"
    current_sem_str = "ws"
    extracted_semester = 1

    def sked_path(part_str):
        return f"e/semester/{part_str}.html"

    # Simple string
    in_str = "eit"
    assert create_id(sked_path(in_str), faculty_short, current_sem_str, extracted_semester) == "e_eit_1_ws"
    # Dot at end
    in_str = "eit."
    assert create_id(sked_path(in_str), faculty_short, current_sem_str, extracted_semester) == "e_eit_1_ws"
    # Duplicated semester
    in_str = "RPP_1_1. Sem"
    assert create_id(sked_path(in_str), faculty_short, current_sem_str, extracted_semester) == "e_rpp_1_ws"
    # Faculty shortname already present
    in_str = "E-eit"
    assert create_id(sked_path(in_str), faculty_short, current_sem_str, extracted_semester) == "e_eit_1_ws"
    # Mutliple special chars
    in_str = "b-.-eit"
    assert create_id(sked_path(in_str), faculty_short, current_sem_str, extracted_semester) == "e_b_eit_1_ws"
    # Special URL for faculty E
    assert create_id("e/E-IST.html", faculty_short, current_sem_str, extracted_semester) == "e_ist_1_ws"
    # Complicated semester specification
    in_str = "PSA_M_1. Semester_Schwerpunkt"
    assert create_id(sked_path(in_str), faculty_short, current_sem_str, extracted_semester) == "e_psa_m_schwerpunkt_1_ws"


def test_is_master():
    def sked_path(part_str):
        return f"e/semester/{part_str}.html"

    assert guess_degree("", sked_path("b_stgrp_ma_glob_1")) == "Master"
    # Faculty M master programme "MSE" has no master/_m_ token in path or label
    assert guess_degree("MSE-WiSe2026 - MSE", "m/sem/MSE.html") == "Master"
