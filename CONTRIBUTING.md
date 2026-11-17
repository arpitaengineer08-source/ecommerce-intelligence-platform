# Contributing

Thanks for your interest in improving the E-Commerce Intelligence Platform.

## Getting started
1. Fork the repository and clone your fork.
2. Create and activate a Python virtual environment.
3. Install the dependencies with `pip install -r requirements.txt`.
4. Follow the README to generate the sample data, build the warehouse and launch the dashboard.

## Before submitting a change
- Keep the raw, staging and analytics data grains separate.
- Do not describe synthetic-data outputs as real business findings.
- Add or update tests when changing ETL, SQL or analytics behaviour.
- Run `pytest` before opening a pull request.
- Never commit credentials, local databases or generated private data.

## Pull requests
Explain the problem, the approach, relevant test results and any dashboard/report changes. Keep pull requests focused and include screenshots for visual changes where useful.

For bugs or feature ideas, open an issue with reproducible steps and expected behaviour.
