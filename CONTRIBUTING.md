# Contributing

## Scope

Contributions should improve one of these areas:

- official artifact detection
- safety boundaries
- deterministic plan generation
- verification quality
- test coverage

Please do not submit “delete everything matching a keyword” changes. This repo is intentionally conservative.

## Local checks

```bash
python3 -m unittest discover -s tests -v
```

## Pull requests

- explain which platform or install path you are improving
- include a regression test where practical
- document any newly supported official artifact in `references/artifact-matrix.md`
- document any newly observed ambiguous trace in `references/research-notes.md`
