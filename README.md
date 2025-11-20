# Kathara Checker Scoring

A tool designed to simplify the scoring of student submissions by reading the output of
[kathara-lab-checker](https://github.com/KatharaFramework/kathara-lab-checker).
The tests/checks can be assigned various weights and grouped into categories,
providing a highly configurable and easy-to-understand scoring system.

## Example

```bash
# Evaluation of multiple labs (network scenarios) is also supported
$ kathara-lab-checker --config checker.json --report-type csv --lab student_id
...
$ kathara-checker-scoring --config scoring.json --lab student_id
Loading configuration file at 'scoring.json'...
Processing 'student_id/student_id_result_all.csv'...
Summary:
Points: 55
   Max: 70
Result: 78.57%

Task 1: 20 out of 20 (100.00%)
 - Topology: 15 out of 15 (100.00%)
 - IP address: 5 out of 5 (100.00%)

Task 2: 35 out of 50 (70.00%)
 - Reachability: 25 out of 30 (83.33%)
 - HTTP status 200: 10 out of 10 (100.00%)
 - HTTP status 404: 0 out of 10 (0.00%)
```

The `scoring.json` configuration file:

```json
{
  "categories": [
    {
      "name": "Task 1",
      "points_multiplier": 1,
      "groups": [
        {
          "name": "Topology",
          "type": "each",
          "description_regex": "^Checking the collision domain .+$",
          "points": 1
        },
        {
          "name": "IP address",
          "type": "linear_rounded",
          "description_regex": "^Verifying the IP address .+$",
          "points": 5
        }
      ]
    },
    {
      "name": "Task 2",
      "points_multiplier": 2,
      "groups": [
        { ... },
        {
          "name": "HTTP check 404",
          "type": "all",
          "description_regex": "^HTTP check .+ status$",
          "points": 10
        }
      ]
    }
  ]
}
```

## Installation

```bash
python3 -m pip install --upgrade pip
python3 -m pip install "kathara-checker-scoring @ git+https://github.com/Trigary/kathara-checker-scoring.git"
```

For alternative installation methods, please refer to the
[Python documentation](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/#install-packages-using-pip).

## Usage

### Overview

Using *kathara-lab-checker* dozens, or even hundreds of **checks** can be defined (such as connectivity checks, route entry checks).
*This tool* first assigns each individual check to (exactly one) **group**.
There are different **group types**, e.g. X points are awarded for each passed check in the group,
or X points are awarded once and only if all checks within the group pass.
Finally, group types are assigned to **categories**, providing a convenient way assign scoring weights
and add structure to the output.

The use of categories is optional: if only a single category exists,
then the output format will automatically be adjusted to accommodate.
Also note that categories are hidden by default if their assigned weight is zero.

### Commands

After installation, this tool be invoked via `kathara-checker-scoring` or `python3 -m kathara_checker_scoring`.

```txt
usage: kathara-checker-scoring [-h] [-v] -c PATH (--lab PATH | --labs LABS) [--run-kathara PATH] [--show-hidden-categories]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable more logging.
  -c PATH, --config PATH
                        Path to the JSON scoring configuration file.
  --lab PATH             Path to the network scenario to score.
  --labs PATH           Path to a directory containing multiple network scenarios to score.
  --run-kathara CHECKER_CONFIG_PATH
                        Execute kathara-lab-checker with the specified configuration (rather than using the CSVs generated from a prior execution).
  --show-hidden-categories
                        By default, categories with a multiplier of 0 are hidden by default. This option shows them.
```

### Configuration

An example can be found towards the top of this document.
Below a small supplementary documentation can be found:

- Points can be integers or floating-point numbers, both are supported.
- The following group types are supported: *(`X` denotes the value of the `points` field)*
  - `each`: each check in the group are worth `X` points, totalling `X * num_checks`.
  - `linear`: the `X * passed_checks / failed_checks` formula specifies the awarded points.
  - `linear_rounded`: same as `linear`, except the earned points are rounded towards the closest integer.
  - `linear_floored`: same as `linear`, except the earned points are floored.
  - `all`: `X` points are awarded if all checks pass, otherwise `0` points are given.
  - `any`: `X` points are awarded if at least one check passes, otherwise `0` points are given.
- It is recommended to create a category with a `points_multiplier` that can be used to hide the unwanted checks.
- The `points_multiplier` field can also be a floating-point number, making it ideal to configure the weight of sub-tasks.
