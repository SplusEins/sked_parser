from sked_parser.scraper import (
    create_id,
    extract_semester,
    optimize_label,
    guess_degree,
)


def test_extract_semester_normal():
    """Test normal/default string"""
    sem_str = "Angewandte Informatik - 1. Semester"
    assert extract_semester(sem_str, "") == 1


def test_extract_semester_multiple_numbers():
    """Test string with other numbers"""
    sem_str = "Wasser- und Bodenmanagement - PO 2018 - 3. Semester"
    assert extract_semester(sem_str, "") == 3
    sem_str = "Wasser- und Bodenmanagement - 20. Sem"
    assert extract_semester(sem_str, "") is None


def test_extract_semester_abbrevation():
    """Test string with shortened Sem."""
    sem_str = "1. Sem. EIT"
    assert extract_semester(sem_str, "") == 1


def test_extract_semester_no_delimiter():
    """Test that strings with no delimiter or non-digit after number match as well"""
    sem_str = "IVG_1_1.Sem"
    assert extract_semester(sem_str, "") == 1
    sem_str = "1 Sem Informatik"
    assert extract_semester(sem_str, "") == 1


def test_extract_semester_no_semester():
    """Test string without semester returns a string, not an int"""
    sem_str = "IMES Teilzeit 2018"
    assert extract_semester(sem_str, "") is None


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


def test_extract_semester_url_fallback():
    """Test that URL parsing is used when no desc is provided"""
    url_str = "i/Semester/Semester-Liste/I-B.Sc. WI 1. Sem..html"
    assert extract_semester("Nothing in here", url_str) == 1


def test_extract_semester_url_digit_at_end():
    """Test that URL parsing with digit at end works"""
    url_str = "r/studentenset/23-03-r-b-rfs-2.html"
    assert extract_semester("Nothing in here", url_str) == 2


def test_extract_semester_url_no_digit_in_middle():
    url_str = "r/studentenset/23-2-r-b-rfs.html"
    assert extract_semester("Nothing in here", url_str) is None


def test_extract_semester_fachsemester_string():
    sem_str = "2. Fachsemester Smart Vehicle Systems"
    assert extract_semester(sem_str, "") == 2


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
