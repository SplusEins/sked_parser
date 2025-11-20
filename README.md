# Sked Parser

[![Python package](https://github.com/SplusEins/sked_parser/actions/workflows/python-package.yml/badge.svg?event=push)](https://github.com/SplusEins/sked_parser/actions/workflows/python-package.yml)

Parses Ostfalia University [`sked`](https://www.sked.de/) timetables into a JSON format than can be used inside [SplusEins](https://github.com/SplusEins/SplusEins).

# Installation & Usage

1. Install python, git and [uv](https://docs.astral.sh/uv/getting-started/installation/)
2. Clone this repository: `git clone https://github.com/SplusEins/sked_parser.git` and `cd sked_parser`.
3. Install the tool: `uv sync`.
4. Copy `secrets.example.yaml` into `secrets.yaml` and fill it with your Ostfalia credentials.
5. Add `sked_parser/config.yaml` with the current timetable URLs. See below for syntax reference.
6. Run the tool by executing `uv run sked-parser`. It'll then create the desired `timetables.json`.

## `config.yaml` syntax reference

This is how the file looks like:

```yaml
plans:
  - url: https://stundenplan.ostfalia.de/e/ # Required, the "overview" URL which directly lists the single timetables for that faculty
    faculty: Elektrotechnik # Required, faculty name which will be displayed to the user on spluseins.de
  - url: https://stundenplan.ostfalia.de/i/Semester/Semester-Liste/
    faculty: Informatik
    type: "list" # Optional, defaults to 'graphical'. Only needs to be specified as 'list' if the timetables are in list form or as 'csv' if the timetables are stored as CSV.
  - url: https://stundenplan.ostfalia.de/v/stundenplan/bee/
    faculty: Versorgungstechnik
    shorthand_syntax: True # Optional, defaults to false. See section shorthand syntax further below.
current_sem: "ss21" # Current semester string that will be appended to the IDs (to have unique IDs for each semester)
timetable_blacklist:
  - "blacklisted timetable name or URL"
```

Refer to the [SplusEins Documentation](https://spluseins-i.ostfalia.de/docs/semesterbeginn.html#aktualisierung-der-plane) for details on the resulting JSON format.

## Command line options

usage: `sked-parser [-h] [-c CONFIG_FILE] [-s SECRETS_FILE] [-o OUT_FILE]`

- `-c CONFIG_FILE`: Path to the main yaml configuration file. Defaults to the provided `sked_parser/config.yaml`.
- `-s SECRETS_FILe` Path to the YAML secrets file containing Ostfalia user and password (Default: `secrets.yaml` in current directory)
- `-o OUT_FILE` Where to store the resulting json file. Can be specified multiple times (Default: `timetables.json` in current directory)

It's also possible to specify the Ostfalia credentials via `OSTFALIA_USER` and `OSTFALIA_PASS` environment variables.

# How it works

The single timetable are scraped from each specified timetable overview page. The link of that timetable (called `timetablePath` in SplusEins) and its description/label are then stored and further processed:

## Label optimization

The label is optimized by removing any faculty names, duplicated white spaces and any current semester strings (like `4. Semester` or `- 5. Sem.`). Optionally it's possible to only use the abbreviation of the course name:

### Shorthand syntax optimization

If the timetables of the current faculty are listed as `long form of course (Abbreviation) - additional info`, it is possible to set `shorthand_syntax` to true in the `config.yaml`. In that case the tool will remove the `long form of course` and only keep `Abbreviation - additional info` to keep the label as short as possible in the UI. For example the faculty "Versorgungstechnik" uses course names like `Bio- und Umwelttechnik (BEE) - PO18`, which will be simplified to `BEE - PO18` when `shorthand_syntax` is set to true for that faculty / overview page.

## Semester extraction

The semester of that timetable is retrieved by parsing the stored description with a regex searching for a number followed by any non-alphanumeric character and then `Sem`. See [the tests for extract_semester](tests/test_scraper.py) for all allowed/possible variants.

## Credits

This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage)
project template.
