from dataclasses import dataclass
import logging
from kathara_checker_scoring.models import (
    CategoryResult,
    CheckGroup,
    GroupCategory,
    GroupResult,
    LabResultRecord,
    ScoringConfig,
    ScoringResult,
)

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecordGroupMatching:
    """Calculates/holds the association between checks (records) and groups."""

    record_to_groups: dict[LabResultRecord, list[CheckGroup]]
    group_to_records: dict[CheckGroup, list[LabResultRecord]]

    def records_matching_multiple_groups(self) -> list[LabResultRecord]:
        return [record for record, groups in self.record_to_groups.items() if len(groups) > 1]

    def records_without_group(self) -> list[LabResultRecord]:
        return [record for record, groups in self.record_to_groups.items() if len(groups) == 0]

    def groups_without_records(self) -> list[CheckGroup]:
        return [group for group, records in self.group_to_records.items() if len(records) == 0]

    @staticmethod
    def create(config: ScoringConfig, records: list[LabResultRecord]) -> "RecordGroupMatching":
        result = RecordGroupMatching(
            record_to_groups={record: [] for record in records}, group_to_records={group: [] for group in config.groups}
        )
        for group in config.groups:
            for record in records:
                if group.matches(record):
                    result.record_to_groups[record].append(group)
                    result.group_to_records[group].append(record)
        return result


def score(config: ScoringConfig, records: list[LabResultRecord]) -> ScoringResult:
    """
    Calculates the score of the specified records (read from a kathara-lab-checker CSV)
    and the specified scoring configuration.
    Throws ValueError if these two are not in sync, e.g. some records are not matched by any groups.
    """
    matching = RecordGroupMatching.create(config, records)

    multiple_groups = matching.records_matching_multiple_groups()
    if len(multiple_groups) > 0:
        _logger.error("The following CSV records match multiple checks groups:")
        _logger.error(", ".join(f"[{record} -> {matching.record_to_groups[record]}]" for record in multiple_groups))
        record = multiple_groups[0]
        groups = matching.record_to_groups[record]
        raise ValueError(f"Some CSV records match multiple check groups, for example: {record} -> {groups}")

    without_group = matching.records_without_group()
    if len(without_group) > 0:
        _logger.error("The following CSV records don't match any check groups:")
        _logger.error(", ".join(str(record) for record in without_group))
        record = without_group[0]
        raise ValueError(f"Some CSV records didn't match any check groups, for example: {record}")

    without_records = matching.groups_without_records()
    if len(without_records) > 0:
        _logger.error("The following check groups don't match any CSV records:")
        _logger.error(", ".join(str(group) for group in without_records))
        group = without_records[0]
        raise ValueError(f"Some check groups didn't match any CSV records, for example: {group}")

    def create_group_result(group: CheckGroup) -> GroupResult:
        return GroupResult(group=group, records=matching.group_to_records[group])

    def create_category_result(category: GroupCategory) -> CategoryResult:
        return CategoryResult(category=category, groups=[create_group_result(group) for group in category.groups])

    return ScoringResult(categories=[create_category_result(cat) for cat in config.categories])


def format_result(result: ScoringResult, show_all: bool) -> list[str]:
    """
    Produces a human-friendly textual output containing the scoring results.
    The automatic hiding of some categories/information can be disabled via the show_all parameter.
    The result is provided is a list, where each element is a distinct line, without trailing newlines.
    """

    # Use the same formatting everywhere: don't wary from group-to-group
    use_float = any(isinstance(group.earned_points, float) for cat in result.categories for group in cat.groups)

    def fmt(number: int | float) -> str:
        return format(number, ".2f") if use_float else str(number)

    lines = [
        "Summary:",
        f"Points: {fmt(result.earned_points)}",
        f"   Max: {fmt(result.max_points)}",
        f"Result: {result.earned_points_percentage:.2f}%",
    ]

    # Hide categories that have a multiplier of 0.
    # If there is only one non-hidden category, then don't summarize its statistics:
    #   there is already a summary at top of the output.
    shown_categories = (
        result.categories if show_all else [cat for cat in result.categories if cat.category.points_multiplier != 0]
    )
    display_category_summary = len(shown_categories) > 1

    def append_group(group: GroupResult) -> None:
        earned_p, max_p = fmt(group.earned_points), fmt(group.max_points)
        lines.append(f" - {group.group.name}: {earned_p} out of {max_p} ({group.earned_points_percentage:.2f}%)")

    def append_category(cat: CategoryResult) -> None:
        header = f"{cat.category.name}:"
        if display_category_summary:
            earned_p, max_p = fmt(cat.earned_points), fmt(cat.max_points)
            header += f" {earned_p} out of {max_p} ({cat.earned_points_percentage:.2f}%)"
        lines.append(header)
        for group in cat.groups:
            append_group(group)

    for category in shown_categories:
        lines.append("")
        append_category(category)

    return lines
