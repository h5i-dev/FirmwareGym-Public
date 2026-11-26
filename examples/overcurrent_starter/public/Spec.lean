import Firmware

-- Specification owned by FirmwareGym. The kernel obligations live in Theorems.lean.

namespace OvercurrentSpec

def thresholdMa : Int := 5000

def nextTripped (tripped currentMa reset : Int) : Int :=
  if currentMa >= thresholdMa then 1
  else if tripped = 0 then 0
  else if reset = 1 then 0
  else 1

def relayClosed (tripped currentMa reset : Int) : Int :=
  if nextTripped tripped currentMa reset = 0 then 1 else 0

theorem overcurrent_always_trips (tripped reset : Int) :
    nextTripped tripped 5000 reset = 1 := by
  unfold nextTripped thresholdMa
  simp

theorem overcurrent_opens_relay (tripped reset : Int) :
    relayClosed tripped 6000 reset = 0 := by
  unfold relayClosed nextTripped thresholdMa
  simp

theorem safe_armed_closes_relay :
    relayClosed 0 1200 0 = 1 := by
  unfold relayClosed nextTripped thresholdMa
  decide

open Aeneas Aeneas.Std Result firmware

abbrev Observation := Int × Int × Int × Int

def stepModel (tripped : Int) (i : Inputs) : Int × Observation :=
  let trip := nextTripped tripped i.a.val i.b.val
  (trip, (if trip = 0 then 1 else 0, trip, 0, 0))
def modelTrace (s : Int) : List Inputs → List Observation
  | [] => []
  | i :: rest =>
    let (next, out) := stepModel s i
    out :: modelTrace next rest

def observedTrace (s : State) : List Inputs → Result (List Observation)
  | [] => ok []
  | i :: rest => do
    let (next, out) ← transition s i
    let after ← observedTrace next rest
    ok ((out.a.val, out.b.val, out.c.val, out.d.val) :: after)

end OvercurrentSpec
