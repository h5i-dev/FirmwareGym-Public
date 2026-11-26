import Firmware
import Spec
import Lean

open Aeneas Aeneas.Std Result firmware

theorem FirmwareGymProof (s : State) (i : Inputs) :
    ∃ r, transition s i = ok r ∧
      (r.1.a.val = OvercurrentSpec.nextTripped s.a.val i.a.val i.b.val ∧
        r.2.a.val = OvercurrentSpec.relayClosed s.a.val i.a.val i.b.val) := by
  sorry
