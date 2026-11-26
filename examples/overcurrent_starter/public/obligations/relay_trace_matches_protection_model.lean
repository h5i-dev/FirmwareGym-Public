import Firmware
import Spec
import Lean

open Aeneas Aeneas.Std Result firmware

theorem FirmwareGymProof (history : List Inputs) :
    OvercurrentSpec.observedTrace INITIAL history = ok (OvercurrentSpec.modelTrace 0 history) := by
  sorry
