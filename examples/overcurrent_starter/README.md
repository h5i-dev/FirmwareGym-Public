# Overcurrent Trip Latch

Electronic circuit breaker / overcurrent protection latch. Input and output words are the fields `a`, `b`, `c`, and `d` on `Inputs` and `Outputs`. `tick_ms` is the `advance_ms` of this step. `len` and `bytes` are unused.

State word `a` is the trip latch (`0` = armed/closed, `1` = tripped/latched open) and starts at `0`. State words `b`, `c`, and `d` stay unchanged.

Input word `a` is the measured load current in milliamps (`current_ma`). Input word `b` is the operator reset button (`reset`: `1` = reset requested, any other value = no reset).

- **Overcurrent trip (safety override)**: Whenever `current_ma >= 5000` (5.0 A or higher), set the latch to `1`, open the relay (`relay_closed = 0`), and assert `fault = 1` — even if `reset == 1` is asserted at the same time.
- **Latched fault**: If the latch is already `1` and `current_ma < 5000`:
  - If `reset == 1`, clear the latch to `0`, close the relay (`relay_closed = 1`), and clear `fault = 0`.
  - Otherwise, keep the latch at `1`, keep the relay open (`relay_closed = 0`), and keep `fault = 1`.
- **Safe operation**: If the latch is `0` and `current_ma < 5000`, keep the latch at `0`, close the relay (`relay_closed = 1`), and clear `fault = 0`.

Output word `a` is `relay_closed` (`1` closed, `0` open). Output word `b` is `fault` (`1` tripped, `0` clear). Output words `c` and `d` stay `0`.

The simulation names the inputs `current_ma` and `reset`, and the outputs `relay_closed` and `fault`.

## Lean submission

The theorem declarations in [public/obligations](public/obligations) are the grading contracts.
Use [proofs/Submission.lean](proofs/Submission.lean) as the starting point. Fill in the proofs for
your Rust implementation and submit the file contents as `proof` alongside `src/lib.rs`. The
grader generates the `Firmware` module from your Rust submission and reports each theorem
separately.
