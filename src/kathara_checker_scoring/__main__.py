import argparse
import csv
import logging
from pathlib import Path
import subprocess
import sys
import traceback

from kathara_checker_scoring import parsing, scoring
from kathara_checker_scoring.models import ScoringConfig, ScoringResult

_logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable more logging.")
    parser.add_argument("-c", "--config", required=True, type=Path, help="Path to the JSON scoring configuration file.")
    lab_or_labs_group = parser.add_mutually_exclusive_group(required=True)
    lab_or_labs_group.add_argument("--lab", type=Path, help="Path to the network scenario to score.")
    lab_or_labs_group.add_argument(
        "--labs", type=Path, help="Path to a directory containing multiple network scenarios to score."
    )
    parser.add_argument(
        "--run-kathara",
        type=Path,
        help="Execute kathara-lab-checker with the specified configuration (rather than using the CSVs generated from a prior execution).",
    )
    parser.add_argument(
        "--show-hidden-categories",
        action="store_true",
        help="By default, categories with a multiplier of 0 are hidden by default. This option shows them.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        force=True,
        level="DEBUG" if args.verbose else "INFO",
        format="%(levelname)s [%(name)s] %(message)s" if args.verbose else "%(message)s",
        stream=sys.stdout,
    )

    config = load_config(args.config)
    if args.run_kathara:
        run_kathara(args.run_kathara, args.lab, args.labs)
    if args.lab:
        handle_single_lab(config, args.lab, args.show_hidden_categories)
    else:
        results = handle_multiple_labs(config, args.labs, args.show_hidden_categories)
        save_csv_summary(args.labs / "result-scoring.csv", results)


def load_config(path: Path) -> ScoringConfig:
    try:
        _logger.info("Loading configuration file at '%s'...", path)
        return parsing.load_config(path)
    except Exception as e:
        _logger.debug("Exception caught when loading configuration", exc_info=True)
        _logger.error("Failed to load configuration file: %s", traceback.format_exception_only(e)[0].strip())
        exit(-1)


def run_kathara(kathara_config: Path, lab: Path | None, labs: Path | None) -> None:
    """Runs the kathara-lab-checker application as a subprocess."""
    cmd = [sys.executable, "-m", "kathara_lab_checker", "-c", str(kathara_config), "--no-cache", "--report-type", "csv"]
    if lab:
        cmd.extend(["--lab", str(lab)])
    else:
        cmd.extend(["--labs", str(labs)])
    _logger.info("Executing kathara-lab-checker via the following command:")
    _logger.info("$ %s", " ".join(cmd))

    proc = subprocess.run(cmd)
    if proc.returncode != 0:
        _logger.error("Failed to execute kathara-lab-checker (exit code: %d)", proc.returncode)
        exit(-1)
    else:
        _logger.info("Successfully executed kathara-lab-checker")


def score_lab(config: ScoringConfig, lab_directory: Path) -> ScoringResult:
    """Loads the records of a single lab and computes its scores."""
    csv_path = lab_directory / f"{lab_directory.name}_result_all.csv"
    _logger.info("Processing '%s'...", csv_path)
    try:
        records = parsing.load_result_all_csv(csv_path)
        return scoring.score(config, records)
    except Exception as e:
        _logger.debug("Exception caught when processing lab '%s'", lab_directory.name, exc_info=True)
        _logger.error(
            "Failed to process lab '%s': %s", lab_directory.name, traceback.format_exception_only(e)[0].strip()
        )
        exit(-1)


def handle_single_lab(config: ScoringConfig, lab: Path, show_hidden_categories: bool) -> ScoringResult:
    """Handles when this tool was launched via the --lab argument."""
    result = score_lab(config, lab)
    for line in scoring.format_result(result, show_hidden_categories):
        _logger.info(line)
    return result


def handle_multiple_labs(
    config: ScoringConfig, lab_container: Path, show_hidden_categories: bool
) -> dict[str, ScoringResult]:
    """
    Handles when this tool was launched via the --labs argument.
    Returns the lab names map to their individual results.
    """
    lab_names = [p.parent.name for p in lab_container.glob("*/lab.conf")]
    _logger.info("The following labs were found: %s", ", ".join(lab_names))
    out_name = "result-scoring.txt"
    _logger.info("Individual lab results will be written to '*/%s'.", out_name)

    results = dict()
    for lab in lab_names:
        result = score_lab(config, lab_container / lab)
        results[lab] = result
        with (lab_container / lab / out_name).open("w", encoding="utf-8") as f:
            f.writelines(x + "\n" for x in scoring.format_result(result, show_hidden_categories))
    return results


def save_csv_summary(out_path: Path, results: dict[str, ScoringResult]) -> None:
    """
    Takes the lab names mapped to their results and saves a CSV file containing lab-specified summaries
    in the containing folder of the labs.
    """
    _logger.info("Writing summary to '%s'...", out_path)
    with out_path.open(mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Lab name", "Earned points", "Max points", "Score percentage"])
        for lab, res in results.items():
            writer.writerow([lab, res.earned_points, res.max_points, f"{res.earned_points_percentage:.2f}%"])


if __name__ == "__main__":
    main()
