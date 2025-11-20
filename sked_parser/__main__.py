"""Console script for sked_parser."""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from sked_parser import app

log = logging.getLogger("sked_parser")


def load_yaml_conf(yaml_file):
    """Helper function to load the configuration yaml files"""
    with open(yaml_file, "r") as stream:
        return yaml.safe_load(stream)


def main():
    # Add helpful logging handler
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s (%(filename)s:%(lineno)d) %(message)s")
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # Add argparse for help text and future enhancements
    parser = argparse.ArgumentParser(
        description="Convert sked timetables from overview URLs into a readable format for spluseins.de",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--config-file",
        type=str,
        help="Path to the main yaml configuration file. Defaults to the provided `sked_parser/config.yaml`",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--secrets-file",
        type=str,
        default="secrets.yaml",
        help="Path to the yaml secrets file containing ostfalia user and password",
    )
    parser.add_argument(
        "-o",
        "--out-file",
        type=str,
        action="append",
        help="Where to store the resulting json file. Can be specified multiple times.",
    )
    args = parser.parse_args()

    # Config contains the urls and other configuration.
    config = load_yaml_conf(Path(args.config_file).resolve())

    # Load username and password to access ostfalia sked URLs either from yaml if exists or from environment
    secrets = {}
    secrets["user"] = os.environ.get("OSTFALIA_USER")
    secrets["pass"] = os.environ.get("OSTFALIA_PASS")
    secrets_path = Path(args.secrets_file).resolve()
    if secrets_path.exists():
        secrets = load_yaml_conf(secrets_path)
        secrets["user"] = secrets["sked"]["user"]
        secrets["pass"] = secrets["sked"]["pass"]
    if secrets["user"] is None or secrets["pass"] is None:
        raise Exception("Please specify your Ostalia credentials either via a secrets.yaml file or via environment variables.")

    #
    if args.out_file is None:
        out_files = [Path("timetables.json").resolve()]
    else:
        out_files = [Path(x).resolve() for x in args.out_file]
    app.main(config, secrets, out_files)


if __name__ == "__main__":
    sys.exit(main())
