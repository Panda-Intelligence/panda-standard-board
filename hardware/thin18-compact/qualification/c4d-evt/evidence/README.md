# Raw physical evidence

Place immutable raw evidence here using subdirectories by test and sample, for example:

```text
evidence/Q06/EVT-001/warm-max-current.csv
evidence/Q06/EVT-001/oscilloscope-startup.wfm
evidence/Q11/EVT-001/fpc-pin1-photo.jpg
```

Every file used by a qualification row must have its repository-relative path and SHA-256 recorded in `measurements.csv`. Do not overwrite a cited file; create a new revision and preserve the previous evidence.

Prose, screenshots without scale, CAD reports and datasheet excerpts do not replace raw measurements.
