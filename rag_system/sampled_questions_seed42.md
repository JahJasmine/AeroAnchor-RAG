# Pre-Flight Benchmark — Sampled Questions (Seed 42)

This document records the exact set of questions sampled for the **sample-mode**
Pre-Flight experiment. The sampling was performed with `random.seed(42)` using
the stratified sampling configuration defined in `test_preflight_optimized.py`.

## Sampling Configuration

| Category | Sample Size | Notes |
|---|---|---|
| international airport ground operations | 30 | sampled |
| ICAO rules and regulations | 20 | sampled |
| FAA rules and regulations | 15 | sampled |
| aviation trivia | -1 | all questions included |
| complex ground scenarios | -1 | all questions included |

**Total sampled questions: 77**

## Sampled Question IDs

### Ground Operations (30 questions)

```
q64, q32, q146, q187, q35, q66, q13, q59, q108, q94,
q100, q30, q183, q73, q97, q78, q55, q169, q58, q192,
q93, q88, q81, q95, q162, q180, q65, q154, q109, q147
```

### ICAO (20 questions)

```
q320, q329, q339, q306, q311, q420, q426, q344, q301, q307,
q403, q342, q341, q333, q340, q413, q304, q309, q308, q447
```

### FAA (15 questions)

```
q454, q435, q479, q459, q471, q436, q472, q443, q448, q453,
q440, q452, q444, q470, q422
```

### Trivia (8 questions)

```
q481, q483, q501, q500, q503, q482, q502, q484
```

### Complex Scenarios (4 questions)

```
q505, q504, q506, q507
```

## Full List (sorted by question number)

```
q13, q30, q32, q35, q55, q58, q59, q64, q65, q66,
q73, q78, q81, q88, q93, q94, q95, q97, q100, q108,
q109, q146, q147, q154, q162, q169, q180, q183, q187, q192,
q301, q304, q306, q307, q308, q309, q311, q320, q329, q333,
q339, q340, q341, q342, q344, q403, q413, q420, q422, q426,
q435, q436, q440, q443, q444, q447, q448, q452, q453, q454,
q459, q470, q471, q472, q479, q481, q482, q483, q484, q500,
q501, q502, q503, q504, q505, q506, q507
```

## How to Reproduce

The sampling can be reproduced by running the experiment script with the
following settings:

```python
TEST_MODE = "sample"
random.seed(42)

SAMPLE_CONFIG = {
    "international airport ground operations": 30,
    "ICAO rules and regulations": 20,
    "FAA rules and regulations": 15,
    "aviation trivia": -1,
    "complex ground scenarios": -1
}
```

Note: reproduction requires the same dataset file (`pre-flight-06.jsonl`) and a
compatible Python version, since `random.sample` and `random.shuffle` consume
the global random state in a fixed order.
