import Firmware
import Spec
import Lean

open Aeneas Aeneas.Std Result firmware

theorem FirmwareGymProof :
    transition INITIAL {
        a := 6000#i32, b := 0#i32, c := 0#i32, d := 0#i32,
        tick_ms := 10#u32, len := 0#u8, bytes := Array.repeat 64#usize 0#u8
      } = ok (
        { a := 1#i32, b := 0#i32, c := 0#i32, d := 0#i32 },
        { a := 0#i32, b := 1#i32, c := 0#i32, d := 0#i32 }
      ) := by
  sorry
