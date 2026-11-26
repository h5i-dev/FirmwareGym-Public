import Firmware
import Spec
import Lean

namespace FirmwareGymSubmission

section

open Aeneas Aeneas.Std Result firmware

theorem overcurrent_overrides_reset (s : State) :
    transition s {
        a := 5000#i32, b := 1#i32, c := 0#i32, d := 0#i32,
        tick_ms := 10#u32, len := 0#u8, bytes := Array.repeat 64#usize 0#u8
      } = ok (
        { a := 1#i32, b := s.b, c := s.c, d := s.d },
        { a := 0#i32, b := 1#i32, c := 0#i32, d := 0#i32 }
      ) := by
  sorry
end

section

open Aeneas Aeneas.Std Result firmware

theorem relay_matches_protection_model (s : State) (i : Inputs) :
    ∃ r, transition s i = ok r ∧
      (r.1.a.val = OvercurrentSpec.nextTripped s.a.val i.a.val i.b.val ∧
        r.2.a.val = OvercurrentSpec.relayClosed s.a.val i.a.val i.b.val) := by
  sorry
end

section

open Aeneas Aeneas.Std Result firmware

theorem relay_trace_matches_protection_model (history : List Inputs) :
    OvercurrentSpec.observedTrace INITIAL history = ok (OvercurrentSpec.modelTrace 0 history) := by
  sorry
end

section

open Aeneas Aeneas.Std Result firmware

theorem stays_closed_when_safe :
    transition INITIAL {
        a := 1200#i32, b := 0#i32, c := 0#i32, d := 0#i32,
        tick_ms := 10#u32, len := 0#u8, bytes := Array.repeat 64#usize 0#u8
      } = ok (
        { a := 0#i32, b := 0#i32, c := 0#i32, d := 0#i32 },
        { a := 1#i32, b := 0#i32, c := 0#i32, d := 0#i32 }
      ) := by
  sorry
end

section

open Aeneas Aeneas.Std Result firmware

theorem trips_on_overcurrent :
    transition INITIAL {
        a := 6000#i32, b := 0#i32, c := 0#i32, d := 0#i32,
        tick_ms := 10#u32, len := 0#u8, bytes := Array.repeat 64#usize 0#u8
      } = ok (
        { a := 1#i32, b := 0#i32, c := 0#i32, d := 0#i32 },
        { a := 0#i32, b := 1#i32, c := 0#i32, d := 0#i32 }
      ) := by
  sorry
end

end FirmwareGymSubmission
