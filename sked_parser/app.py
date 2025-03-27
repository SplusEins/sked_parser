import json
import logging
from time import sleep

from sked_parser import scraper

log = logging.getLogger("sked_parser")


def write_timetable_json(tables, file_path):
    with open(file_path, "w") as f:
        json.dump(tables, f, indent=2, ensure_ascii=False)
        f.write("\n")


def raise_for_duplicated_ids(dict_to_check):
    """Helper function that prints an error if key `id` of that dict list has duplicated values.
    Also raises if dict key 'id' does not exist."""
    ids = [item["id"] for item in dict_to_check]
    duplicated_ids = set([x for x in ids if ids.count(x) > 1])
    if len(duplicated_ids) > 0:
        log.critical(f"Zwei oder mehr Pläne haben die gleiche ID bekommen: {duplicated_ids}")


def remove_duplicated_urls(dict_to_check):
    """Remove all timetables entries that have a duplicated URL/timetablePath. We always just use the first one."""
    unique_urls = []
    for item in dict_to_check:
        if item["timetablePath"] in unique_urls:
            dict_to_check.remove(item)
        else:
            unique_urls.append(item["timetablePath"])


def is_valid_item(table, blacklist):
    """Returns whether a table is allowed in spluseins. Used for filtering some unwanted items (Klausurenpläne)"""
    if table["faculty"] == "Elektrotechnik" and "block" in table["timetablePath"].lower():
        # Blockveranstaltungen (Fakultät E) erstmal raus
        return False
    if table["faculty"] == "Soziale Arbeit" and "fernstudiengang" in table["label"].lower():
        # schlechte formatierung, wird ignoriert
        return False
    for forbidden in blacklist:
        if forbidden.lower() in table["timetablePath"].lower():
            log.info("Skipping timetable with forbidden path: " + table["timetablePath"])
            return False
        if forbidden.lower() in table["label"].lower():
            log.info("Skipping timetable with forbidden label: " + table["label"])
            return False
    return True


def main(config, secrets, out_files):
    tables = []
    for plan in config["plans"]:
        tuples = scraper.get_links(plan["url"], secrets, plan["faculty"])
        if len(tuples) == 0:
            log.warning(f"URL {plan['url']} hat keine Pläne.")
        for label, absolute_path in tuples:
            label = label.replace("\n", " ").replace("\r", " ")  # for logging purposes
            if "Informatik" in plan["faculty"]:
                sked_path = ""
                faculty_short = "i"
            else:
                sked_path = absolute_path.removeprefix("https://stundenplan.ostfalia.de/")
                faculty_short = scraper.get_faculty_shortcode(label, sked_path)
            degree = scraper.guess_degree(label, sked_path)
            semester = scraper.extract_semester(label, sked_path) or "Sonstige"
            sked_id = scraper.create_id(sked_path, faculty_short, config["current_sem"], semester, label)
            label = scraper.optimize_label(label, plan.get("shorthand_syntax", False))
            plan_type = plan.get("type", "graphical")
            if "alt" in sked_path:
                label += " alt"
            tables.append(
                dict(
                    timetablePath=absolute_path,
                    label=label,
                    faculty=plan["faculty"],
                    type=plan_type,
                    id=sked_id,
                    semester=semester,
                    degree=degree,
                )
            )
        sleep(1)
    tables = [table for table in tables if is_valid_item(table, set(config["timetable_blacklist"]))]
    # Sort first by faculty, then by master/bachelor, then by semester and last by alphabetical label
    tables = sorted(
        tables,
        key=lambda x: (
            x["faculty"],
            x["degree"],
            str(x["semester"]),
            x["label"],
            x["id"],
        ),
    )
    remove_duplicated_urls(tables)
    raise_for_duplicated_ids(tables)
    for out_file in out_files:
        write_timetable_json(tables, out_file)

    log.info(f"Parsed {len(tables)} timetables sucessfully into JSON.")
    return 0
