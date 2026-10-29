# Contributing

Changes should keep scene inputs, simulation settings and reported results traceable.

For geometry or solver changes, record the geographic snapshot, dependency versions, transmitter configuration, frequencies, propagation flags, sample count and seeds. Use a distinct result suffix while evaluating a new configuration. Include a comparison against the published baseline and regenerate the analysis and report when updating the baseline.

Documentation changes should use direct technical language, define metrics at first use, and link claims to result files or primary references. Preserve source attribution when adding geographic data or third-party material.

Before submitting a change, run the checks relevant to it:

```bash
python -m compileall -q .
python validate.py
```

The existing validation checks the published mesh and result arrays. Geometry changes may require updating the expected array dimensions and rerunning the study. Include a screenshot for changes to the explorer or report layout.

