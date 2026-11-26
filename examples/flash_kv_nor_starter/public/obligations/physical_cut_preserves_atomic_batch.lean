import Firmware
import Spec
import Lean

open Aeneas Aeneas.Std Result firmware NorFlashSpec

theorem FirmwareGymProof (first replacement : I32) (rest : List I32)
    (hBound : rest.length ≤ 31) :
    ∃ initial primed staged completed writes,
      boot erased = some initial ∧
      prime initial (first :: rest) = some primed ∧
      stageBatch primed replacement = some staged ∧
      execute staged 2#i32 0#i32 0#i32 =
        some (.replied completed 1 0 writes) ∧ 0 < writes ∧
      let oldKeys := (List.replicate 16 none).set 2 (some ((rest.getLast?).getD first).val)
      let newKeys := (List.replicate 16 none).set 0 (some replacement.val)
      (boot completed.2 >>= fun recovered => observe recovered allKeys) = some newKeys ∧
      ∀ cut, 0 < cut → cut ≤ writes →
        ∃ medium recovered again values,
          execute staged 2#i32 0#i32 0#i32 (some cut) = some (.interrupted medium) ∧
          boot medium = some recovered ∧ observe recovered allKeys = some values ∧
          (values = oldKeys ∨ values = newKeys) ∧
          boot recovered.2 = some again ∧ observe again allKeys = some values := by
  sorry
