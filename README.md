# Recovery Readiness Auditor
[![Python tests](https://github.com/joshprandall/recovery-readiness-auditor/actions/workflows/test.yml/badge.svg)](https://github.com/joshprandall/recovery-readiness-auditor/actions/workflows/test.yml)

An offline Python command-line tool that checks a service inventory for recorded recovery gaps. This infrastructure-engineering project demonstrates practical disaster recovery concepts through explicit assumptions, deterministic examples, machine-readable output, and automated boundary testing.

## Quick start

Python 3.10 or newer. No third-party dependencies, accounts, credentials, or network access are required.

```sh
python audit.py examples/services.csv --as-of 2026-09-06T12:00:00Z
python audit.py examples/services.csv --as-of 2026-09-06T12:00:00Z --format json
python -m unittest discover -s tests -v
```

On Windows, use `py` instead of `python` if needed. Run the commands from the project folder.

The sample audit intentionally exits with code **1** because two fictional services contain recovery-readiness gaps. This is expected behavior.

## What it checks

The auditor evaluates recorded recovery-readiness information including:

- Backup age compared with the declared recovery point objective (RPO).
- Restore-test age compared with a configurable policy threshold of 90 days by default.
- Missing service names, owners, runbook references, backup timestamps, and restore-test timestamps.
- Positive, finite recovery point objective (RPO) and recovery time objective (RTO) values.
- Invalid or future timestamps.
- Malformed CSV rows.
- Duplicate service names or duplicate columns.

The CSV is a user-provided inventory rather than a direct connection to a backup platform.

All included examples are fictional. The `runbook_url` field may contain either a path or URL; the tool does not retrieve or verify the referenced resource.

## Results and exit codes

The command-line interface uses deterministic exit codes that make the tool suitable for scripting and CI/CD workflows:

- **Exit 0** — No recorded recovery-readiness gaps were found.
- **Exit 1** — One or more findings were identified.
- **Exit 2** — An input or configuration error occurred.

A finding does not prove that an outage will occur, and a clean result does not prove that a service is recoverable.

The auditor does not independently verify:

- Backup integrity.
- Successful backup completion.
- Replication consistency.
- Application dependencies.
- Restore duration.
- Actual achievement of the declared RTO.

A real restore exercise remains necessary to validate recoverability.

## Time handling

The backup timestamp should represent the latest successful backup according to the source system.

Backups exactly at the RPO boundary pass. Backups older than the declared RPO fail.

Timezone-aware ISO 8601 timestamps are required, and all comparisons are performed in UTC.

The `--as-of` option allows audits to be evaluated against a fixed point in time, making examples and automated tests deterministic and reproducible.

## Design decisions

Several design choices were made to keep the project portable, reviewable, and useful for automation:

- Python standard library only.
- No external dependencies.
- Evaluation logic separated from file input/output.
- Deterministic execution through `--as-of`.
- JSON output for automation and CI/CD integration.
- Explicit findings instead of a synthetic readiness score.
- Defensive input validation.
- Boundary-focused automated testing.

## Example findings

At the sample audit time:

- **Inventory API** has no recorded recovery-readiness gaps.
- **Reporting Database** exceeds its 4-hour RPO and has an overdue restore test.
- **File Services** is missing an owner and runbook reference.

See `examples/sample-report.json` for the corresponding machine-readable output.

## Automated testing

The project includes automated tests covering validation rules, boundary conditions, and expected behavior.

GitHub Actions executes the test suite against Python 3.10, 3.11, 3.12, and 3.13 to verify compatibility and prevent regressions.

Local test execution:

```sh
python -m unittest discover -s tests -v
```

## Project structure

```text
recovery-readiness-auditor/
├── .github/
│   └── workflows/
│       └── test.yml
├── examples/
│   ├── services.csv
│   └── sample-report.json
├── tests/
├── audit.py
└── README.md
```

## Future development

Potential future enhancements include:

- Backup-platform export adapters.
- Per-service restore-test policies.
- Measured restore-duration validation.
- Markdown and HTML reporting.
- Additional machine-readable output formats.
- Dependency-aware recovery analysis.
- Integration with infrastructure monitoring or configuration-management systems.

## Project context

This project demonstrates practical infrastructure engineering concepts related to disaster recovery, backup validation, recovery objectives, automation, defensive input handling, testing, and CI/CD.

All included service inventories and examples are fictional. The project is designed for technical demonstration and evaluation and does not contain proprietary, customer, or employer data.
