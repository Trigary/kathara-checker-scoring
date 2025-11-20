from dataclasses import dataclass
from enum import StrEnum
import math
import re


def _calc_percentage(part: int | float, whole: int | float) -> float:
    return math.nan if whole == 0 else (part / whole) * 100.0


@dataclass(frozen=True)
class LabResultRecord:
    """A parsed line from the <lab>_result_all.csv file, containing the result of a specific check."""

    description: str
    passed: bool
    reason: str


class GroupType(StrEnum):
    """The different types of groups. Each define a unique way regarding how to calculate the score of a group."""

    EACH = "each"
    LINEAR = "linear"
    LINEAR_ROUNDED = "linear_rounded"
    LINEAR_FLOORED = "linear_floored"
    ALL = "all"
    ANY = "any"

    def calculate_earned_points(self, group_points: int | float, records: list[LabResultRecord]) -> int | float:
        count_passed = sum(1 for rec in records if rec.passed)
        if self is GroupType.EACH:
            return group_points * count_passed
        elif self in [GroupType.LINEAR, GroupType.LINEAR_ROUNDED, GroupType.LINEAR_FLOORED]:
            earned = (count_passed / len(records)) * group_points
            if self is GroupType.LINEAR_ROUNDED:
                return round(earned)
            elif self is GroupType.LINEAR_FLOORED:
                return math.floor(earned)
            else:
                return earned
        elif self is GroupType.ALL:
            return group_points if count_passed == len(records) else 0
        elif self is GroupType.ANY:
            return group_points if count_passed >= 1 else 0
        raise NotImplementedError(f"Unhandled group type: {self}")

    def calculate_max_points(self, group_points: int | float, records: list[LabResultRecord]) -> int | float:
        if self is GroupType.EACH:
            return group_points * len(records)
        elif self in [GroupType.LINEAR, GroupType.LINEAR_ROUNDED, GroupType.LINEAR_FLOORED]:
            return group_points
        elif self is GroupType.ALL or self is GroupType.ANY:
            return group_points
        raise NotImplementedError(f"Unhandled group type: {self}")


@dataclass(frozen=True)
class CheckGroup:
    """A group of checks which have a common name, their points are calculated together, etc."""

    name: str
    type: GroupType
    description_regex: re.Pattern
    points: int | float
    category: "GroupCategory"

    def matches(self, record: LabResultRecord) -> bool:
        return self.description_regex.match(record.description) is not None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"

    def __hash__(self):
        return hash((self.name, self.category.name))


@dataclass(frozen=True)
class GroupCategory:
    """A collection of check groups which are displayed and weighted together."""

    name: str
    points_multiplier: int | float
    groups: list[CheckGroup]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.name}')"

    def __hash__(self):
        return hash(self.name)


@dataclass(frozen=True)
class ScoringConfig:
    """Collection of configuration entries defining how scoring should be done."""

    categories: list[GroupCategory]

    @property
    def groups(self) -> list[CheckGroup]:
        return [group for category in self.categories for group in category.groups]

    def category_of(self, group: CheckGroup) -> GroupCategory:
        for cat in self.categories:
            if group in cat.groups:
                return cat
        raise ValueError("The provided group must among this config's groups.")

    def __post_init__(self):
        if len({category.name for category in self.categories}) != len(self.categories):
            raise ValueError("Group category names must be unique")
        for category in self.categories:
            if len({check.name for check in category.groups}) != len(category.groups):
                raise ValueError("Check group names within categories must be unique")
        if any(len(category.groups) == 0 for category in self.categories):
            raise ValueError("Each category must contain at least one check group")


@dataclass(frozen=True)
class GroupResult:
    """Contains the result of the scoring of a group."""

    group: CheckGroup
    records: list[LabResultRecord]

    @property
    def total_checks_count(self) -> int:
        return len(self.records)

    @property
    def passed_checks_count(self) -> int:
        return sum(1 for record in self.records if record.passed)

    @property
    def failed_check_count(self) -> int:
        return self.total_checks_count - self.passed_checks_count

    @property
    def max_points(self) -> int | float:
        return self.group.type.calculate_max_points(
            self.group.points * self.group.category.points_multiplier, self.records
        )

    @property
    def earned_points(self) -> int | float:
        return self.group.type.calculate_earned_points(
            self.group.points * self.group.category.points_multiplier, self.records
        )

    @property
    def earned_points_percentage(self) -> float:
        return _calc_percentage(self.earned_points, self.max_points)


@dataclass(frozen=True)
class CategoryResult:
    """Contains the result of the scoring of a category."""

    category: GroupCategory
    groups: list[GroupResult]

    @property
    def total_checks_count(self) -> int:
        return sum(group.total_checks_count for group in self.groups)

    @property
    def passed_checks_count(self) -> int:
        return sum(group.passed_checks_count for group in self.groups)

    @property
    def failed_check_count(self) -> int:
        return sum(group.failed_check_count for group in self.groups)

    @property
    def max_points(self) -> int | float:
        return sum(group.max_points for group in self.groups)

    @property
    def earned_points(self) -> int | float:
        return sum(group.earned_points for group in self.groups)

    @property
    def earned_points_percentage(self) -> float:
        return _calc_percentage(self.earned_points, self.max_points)


@dataclass(frozen=True)
class ScoringResult:
    """The result of scoring an entire lab."""

    categories: list[CategoryResult]

    @property
    def total_checks_count(self) -> int:
        return sum(category.total_checks_count for category in self.categories)

    @property
    def passed_checks_count(self) -> int:
        return sum(category.passed_checks_count for category in self.categories)

    @property
    def failed_check_count(self) -> int:
        return sum(category.failed_check_count for category in self.categories)

    @property
    def max_points(self) -> int | float:
        return sum(category.max_points for category in self.categories)

    @property
    def earned_points(self) -> int | float:
        return sum(category.earned_points for category in self.categories)

    @property
    def earned_points_percentage(self) -> float:
        return _calc_percentage(self.earned_points, self.max_points)
