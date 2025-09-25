import logging
import re
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

log = logging.getLogger("sked_parser")


# Install request cache with 10 minute expiration time to avoid spamming requests
# import requests_cache
# requests_cache.install_cache(expire_after=600)

# Create a requests session with our own user agent, so it's clear who manages the automated requests.
session = requests.Session()
session.headers.update({"User-Agent": "Sked parser for spluseins.de", "From": "team@spluseins.de"})


def get_links(overview_url: str, auth, faculty=""):
    """Scrape all valid timetable URLS from `overview_url`.

    Args:
        overview_url (str): Faculty timetable overview URL that has all single timetable URLs on it
        auth (dict): Dict containing `user` and `pass` to access the ostfalia timetable module
        faculty (str): Faculty name. Is used for applying special scrapers based on the faculty. Defaults to "".

    Returns:
        Set[Tuple]: List of tuples with (url description, absolute url)
    """
    resp = session.get(overview_url, auth=HTTPBasicAuth(auth["user"], auth["pass"]))
    soup = BeautifulSoup(resp.content, "lxml")
    tables: set[tuple[str, str]] = set()
    if "Informatik" in faculty:
        valid_url_regex = re.compile(r"^https://intranet-i.ostfalia.de/fips/stundenplan/\d+\.html$", re.IGNORECASE)
    else:
        valid_url_regex = re.compile(r"^https://stundenplan.ostfalia.de/\w/.+\.(html|csv)$", re.IGNORECASE)
    for anchor_tag_href in soup.find_all("a", href=True):
        absolute_url: str = urljoin(overview_url, anchor_tag_href["href"])
        if absolute_url.endswith("index.html"):
            continue
        if valid_url_regex.match(absolute_url):
            desc: str = anchor_tag_href.text.strip()
            # Prepend the content of the previous paragraph to the description because it contains the real name of the plan
            if "Wirtschaft" in faculty:
                desc = anchor_tag_href.parent.parent.find("summary").text.strip() + " " + desc
            if "Recht" in faculty:
                if anchor_tag_href.parent.parent.name == "ol":
                    desc = anchor_tag_href.parent.parent.previous + " " + desc
            tables.add((desc, absolute_url))
    return tables


def create_id(sked_path, faculty_short, current_sem_str, extracted_semester, label=""):
    """Create a unique ID from the `sked_path` (timetable URL) and keep it as short as possible while maintaining readability"""
    # Unqoute the URL first
    sked_path = unquote(sked_path)
    # Get a basic id from the url page, which is the last part excluding the .extension
    id_re = re.compile(r"\w/(?:.*/)?(.+?)\.+(html|csv)", re.IGNORECASE)
    m = id_re.search(sked_path)
    if m:
        sked_id = m.group(1).lower().strip()
    else:
        sked_id = label.lower().strip()

    # Replace any non alphanumeric chars with underscore and remove duplicated underscores
    sked_id = re.sub(r"\W+", "_", sked_id, flags=re.ASCII)
    sked_id = sked_id = re.sub(r"_+(?=_|$)", "", sked_id)

    # Remove any strings like SoSe, WS, SS including the year from the id
    sked_id = re.sub(r"((s|w)s|(so|w)se)(_?\d+)(_\d+)?_?", "", sked_id)

    # Remove some faculty specific stuff to shorten the id:
    sked_id = sked_id.replace("semester_", "")
    sked_id = sked_id.replace("_semester", "")
    sked_id = sked_id.replace("_sem", "")
    sked_id = sked_id.replace("soziale_arbeit", "")
    sked_id = sked_id.replace("wirtschaftsingenieur_", "")
    sked_id = sked_id.replace("energie_und_gebaeudetechnik_", "")
    sked_id = sked_id.replace("bio_und_umwelttechnik_", "")
    sked_id = sked_id.replace("bachelor_of_science", "")
    sked_id = sked_id.replace("bachelor", "")
    sked_id = sked_id.replace("b_sc", "")
    sked_id = sked_id.replace("m_sc", "m")
    # sked_id = sked_id.replace("master_of_science", "master")
    sked_id = sked_id.replace("energie_", "")
    sked_id = sked_id.replace("umwelt_", "")
    sked_id = sked_id.replace("stdgrp_", "")  # weird faculty S specific string
    sked_id = sked_id.replace("stjg_", "")  # weird faculty K specific string
    # Remove unneccessary chars at end or beginning of string
    sked_id = sked_id.strip("_ ")

    if isinstance(extracted_semester, int):
        # If semester was successfully extracted, scrape all single digits from ID and add extracted semester back
        sked_id = re.sub(r"(?<!\d)" + f"{extracted_semester}" + r"(?=_|$)", "", sked_id)
        sked_id = f"{sked_id}_{extracted_semester}"

    # Prefix the label with the faculty shortcut
    faculty_prefix = f"{faculty_short}_"
    if not sked_id.startswith(faculty_prefix):
        sked_id = faculty_prefix + sked_id

    # Append the current semester string (sth like ws20) at the end
    sked_id = f"{sked_id}_{current_sem_str}"
    # Again remove duplicated underscores that have been introduced by the removals before
    sked_id = re.sub(r"_+(?=_|$)", "", sked_id)
    return sked_id


def extract_semester(desc, url):
    """Extract/guess the current semester from the link description or the link using regex."""
    # Find any timetables that are "Wahlpflichfächer"
    for keyword in ["wahlpflicht", "wpf"]:
        if keyword in desc.lower() or keyword in url.lower():
            return "WPF"
    # should always return none
    for keyword in ["gremien", "termine"]:
        if keyword in desc.lower() or keyword in url.lower():
            return None
    # Try to extract the semester by finding a number followed by non word characters and something starting with Sem
    sem_regex = re.compile(r"(?:^|\D)(\d)\W+(fachsem|sem|html$)", re.IGNORECASE)
    m_desc = sem_regex.search(desc)
    m_url = sem_regex.search(url)
    if m_desc:
        return int(m_desc.group(1))
    elif m_url:
        # Use the semester from URL if description search was unsuccessful
        return int(m_url.group(1))
    else:
        log.warning(f'Kein Semester bestimmbar bei "{desc}" mit sked path "{url}"')
        return None


def get_faculty_shortcode(desc, sked_path):
    """Extract the faculty one letter shortcode from the link description or the provided sked path"""
    shortcode = sked_path.split("/")[0]
    if len(shortcode) == 1 or shortcode.isalpha():
        return shortcode
    if "Informatik" in desc or "Digital Technologies" in desc or "Wirtschaftsinformatik" in desc:
        return "i"
    raise Exception(f"Could not get faculty shorthand from sked path '{sked_path}' or description '{desc}'")


def optimize_label(desc, uses_shorthand_syntax):
    """Optimize the user visible label by removing faculty names and try to use only the shorthand of that course if possible"""
    desc = desc.replace("S-", "")
    desc = desc.replace("I-", "")
    desc = desc.replace("B.Sc.", "")
    desc = desc.replace("I-M.Sc.", "")
    desc = desc.replace("Bachelor of Science", "")
    desc = desc.replace("Bachelor", "")
    desc = desc.replace("Master of Science", "")
    desc = desc.replace("Master", "")
    desc = desc.replace("- WiSe 21/22", "")
    desc = desc.replace(".csv", "")
    desc = re.sub(r"\s+", " ", desc)  # replace all (even duplicated) whitespaces by single space
    if uses_shorthand_syntax:
        # Those faculties writes their modules as "long name (shorthand) additional info"
        # So discard the long name and use only the shorthand but keep the info
        shorthand_re = re.compile(r"^.*?\((\D+?)\)(.*)$")
        m = shorthand_re.search(desc)
        if m:
            shorthand = m.group(1).strip()
            additional_stuff = m.group(2).strip()
            desc = f"{shorthand} {additional_stuff}"
    # Remove any semester related information
    desc = re.sub(r"(\d\. ?-)?-? ?\d\.?\W+(Fachs|S)em(?:ester|\.)?", "", desc)
    desc = desc.replace("Semester", "")
    # Strip any remaining single digits
    desc = re.sub(r"[_-]\d(?=_|$)", "", desc)
    # Remove duplicated spaces
    desc = desc.replace("  ", " ")
    return desc.strip("-_ ")


def guess_degree(desc, link):
    """Return an estimation whether it's a master or bachelor degree"""
    link = link.lower()
    if "master" in desc.lower() or "m.sc" in desc.lower() or "imes" in desc.lower() or "IST" in desc or "IVG" in desc:
        return "Master"
    if "-m-" in link or "_m_" in link or "_ma_" in link or "-ma-" in link:
        if "studienprofil m" in desc.lower():
            return "Bachelor"
        log.info(f"Master vermutet für '{desc}'. Bitte manuell überprüfen, dass es kein Bachelor ist. Link ist {link}.")
        return "Master"
    else:
        return "Bachelor"
