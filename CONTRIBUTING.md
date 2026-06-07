# Contributing

Thank you for improving `prompt-asset-inventory`.

## Development Setup

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Guidelines

- Keep runtime dependencies at zero unless there is a strong reason to add one.
- Prefer Python standard library APIs.
- Keep detection heuristics explainable and easy to test.
- Add or update unit tests for scanner behavior, rules parsing, CLI exits, and report formats.
- Do not include real secrets, tokens, or private prompt content in tests or examples.

## Pull Request Checklist

- Tests pass with `python -m unittest discover -s tests -v`.
- README or examples are updated when behavior changes.
- New findings use stable codes.
- New report fields are represented in JSON and CSV when appropriate.
