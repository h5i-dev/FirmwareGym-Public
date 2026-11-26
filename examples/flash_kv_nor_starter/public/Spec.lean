import Firmware

namespace NorFlashSpec

open Aeneas Aeneas.Std Result firmware

abbrev Medium := List (List U8)
abbrev Keys := List (Option Int)
abbrev World := State × Medium

def erased : Medium := List.replicate 4 (List.replicate 160 255#u8)

def hostInput (op key value : I32) : Inputs := {
  a := op, b := key, c := value, d := 0#i32, tick_ms := 0#u32,
  len := 0#u8, bytes := Aeneas.Std.Array.repeat 64#usize 0#u8
}

def replaceAt {α : Type} (xs : List α) (index : Nat) (value : α) : List α :=
  xs.set index value

def response (payload : List U8) : Inputs :=
  { hostInput 5#i32 0#i32 0#i32 with
    len := UScalar.ofNatCore (min payload.length 64) (by change min payload.length 64 < 256; omega)
    bytes := Aeneas.Std.Array.from
      (List.ofFn (fun i : Fin 64 => payload[i.val]?.getD 0#u8)) (by simp) }

def mediaStep (m : Medium) (out : Outputs) : Option (Medium × Inputs × Bool) := do
  if out.b.val < 0 then none else
  let blockId := out.b.val.toNat
  let block ← m[blockId]?
  if out.a = 3#i32 then
    some (replaceAt m blockId (List.replicate 160 255#u8), response [], true)
  else if out.c.val < 0 then none else
    let offset := out.c.val.toNat
    let old ← block[offset]?
    if out.a = 1#i32 then
      if out.d.val < 1 ∨ 64 < out.d.val ∨ block.length < offset + out.d.val.toNat then none else
        some (m, response ((block.drop offset).take out.d.val.toNat), false)
    else if out.a = 2#i32 then
      if out.d.val < 0 ∨ 255 < out.d.val then none else
        let value := IScalar.hcast .U8 out.d
        if old.val &&& value.val != value.val then none else
          some (replaceAt m blockId (replaceAt block offset value), response [], true)
    else none

inductive End where
  | replied (world : World) (status value : Int) (writes : Nat)
  | interrupted (medium : Medium)

-- The fuel bounds firmware callbacks per command. A cut occurs after a
-- physical mutation, before the device receives the completion event.
def drive (mayWrite : Bool) (cut : Option Nat) :
    Nat → Nat → World → Inputs → Option End
  | 0, _, _, _ => none
  | fuel + 1, writes, (s, m), input => do
    match (transition s input).match with
    | .ok (next, out) =>
      if out.a = 0#i32 then some (.replied (next, m) out.b.val out.c.val writes)
      else
        let (medium, reply, changed) ← mediaStep m out
        if changed && !mayWrite then none else
        let writes := writes + if changed then 1 else 0
        if changed && cut == some writes then some (.interrupted medium)
        else drive mayWrite cut fuel writes (next, medium) reply
    | _ => none

def execute (world : World) (op key value : I32) (cut : Option Nat := none) : Option End :=
  drive (op == 0#i32 || op == 2#i32) cut 2048 0 world (hostInput op key value)

def expectReply (world : World) (op key value : I32) (expected : Int) : Option World := do
  match ← execute world op key value with
  | .replied after status _ _ => if status = expected then some after else none
  | .interrupted _ => none

def boot (m : Medium) : Option World :=
  expectReply (INITIAL, m) 0#i32 0#i32 0#i32 0

def stageBatch (world : World) (value : I32) : Option World := do
  let first ← expectReply world 1#i32 0#i32 value 0
  expectReply first 4#i32 2#i32 0#i32 0

def prime (world : World) : List I32 → Option World
  | [] => some world
  | value :: rest => do
    let staged ← expectReply world 1#i32 2#i32 value 0
    let committed ← expectReply staged 2#i32 0#i32 0#i32 1
    prime committed rest

def observe (world : World) : List I32 → Option Keys
  | [] => some []
  | key :: rest => do
    match ← execute world 3#i32 key 0#i32 with
    | .replied next status value _ =>
      if status = 0 then (none :: ·) <$> observe next rest
      else if status = 1 then (some value :: ·) <$> observe next rest
      else none
    | .interrupted _ => none

def allKeys : List I32 :=
  [0#i32, 1#i32, 2#i32, 3#i32, 4#i32, 5#i32, 6#i32, 7#i32,
    8#i32, 9#i32, 10#i32, 11#i32, 12#i32, 13#i32, 14#i32, 15#i32]

end NorFlashSpec
