import Firmware
import Spec

open Aeneas Aeneas.Std Result firmware

theorem FirmwareGymProof (i : Inputs) (h : i.a = 999#i32) :
    ∃ next out, transition INITIAL i = ok (next, out) ∧
      out.a = 0#i32 ∧ out.b = (-1)#i32 := by
  sorry
