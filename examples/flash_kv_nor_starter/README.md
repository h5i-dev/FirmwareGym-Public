# NOR flash store

FirmwareGym L4 task ID `flash-kv-store-nor`. Implement a 16-key store with staged batches of at most four distinct keys. Reads see committed values. An acknowledged commit survives a reboot. If power fails before a reply, recovery must return the entire old or new map. Rebooting again must recover the same map.

The evaluator retains four 160-byte NOR blocks across a power cut and resets firmware RAM. Each byte program and block erase is atomic. A cut can occur after the operation takes effect and before the firmware receives completion. Programming may only clear bits. The grader checks bounded command I/O and wear distribution under sustained writes.

## Mailbox

| Input `a` | Command | Arguments |
| --- | --- | --- |
| 0 | BOOT | Recover from NOR after reset |
| 1 | STAGE_PUT | `b` key, `c` signed value |
| 2 | COMMIT | None |
| 3 | GET | `b` key |
| 4 | STAGE_DELETE | `b` key |
| 5 | IO_RESPONSE | Evaluator reply after an I/O request. Reads return `len` bytes in `bytes`. |

| Output `a` | Meaning | Arguments |
| --- | --- | --- |
| 0 | Complete the host command | `b` status, `c` value for a found GET |
| 1 | Read | `b` block, `c` offset, `d` byte count from 1 to 64 |
| 2 | Program one byte | `b` block, `c` offset, `d` desired byte |
| 3 | Erase one block | `b` block |

Unused words are zero. BOOT and staging report 0 on success. COMMIT reports 1 on success or 0 for an empty batch. GET reports 1 with a value or 0 for an absent key. Invalid commands and arguments report -1. An invalid stage leaves the batch unchanged. Restaging a key replaces its pending action. Only BOOT and COMMIT may initiate persistent changes.

## Submit a solution

Implement [the Rust starter](starter/src/lib.rs) and fill in [the Lean proof template](proofs/Submission.lean). The grader generates the `Firmware` module from your Rust submission. The [fixed obligations](public/obligations) use the [Lean model](public/Spec.lean) to check command rejection and atomic recovery across physical cuts. The [sample YAML scenario](public/simulation.yaml) checks invalid commands. Hosted evaluation also exercises commit and recovery on evaluator-owned NOR.

The task budgets are 50,000 CPU instructions per step, 32 KiB binary size, 4 KiB RAM, and 4 KiB peak stack.

With a FirmwareGym API key that grants access to this task, submit the starter source as `src/lib.rs` and the completed Lean file as `proof` using the [evaluation API](../../docs/API.md). Fetch the task through the API for the contract used by your hosted grader.
