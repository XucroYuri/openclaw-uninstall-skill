## Summary

- what changed
- why it is needed
- which platform/install path it affects

## Validation

- [ ] `python3 -m unittest discover -s tests -v`
- [ ] updated docs if artifact behavior changed

## Risk review

- [ ] this change does not broaden deletion scope accidentally
- [ ] companion/manual-review artifacts remain non-destructive unless intentionally changed
