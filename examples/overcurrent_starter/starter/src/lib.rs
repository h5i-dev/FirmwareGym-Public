#![no_std]

pub struct State {
    pub a: i32,
    pub b: i32,
    pub c: i32,
    pub d: i32,
}

pub const INITIAL: State = State { a: 0, b: 0, c: 0, d: 0 };

pub struct Inputs {
    pub a: i32,
    pub b: i32,
    pub c: i32,
    pub d: i32,
    pub tick_ms: u32,
    pub len: u8,
    pub bytes: [u8; 64],
}

pub struct Outputs {
    pub a: i32,
    pub b: i32,
    pub c: i32,
    pub d: i32,
}

/// Stub. The evaluator calls `transition` once per simulation step.
pub fn transition(state: &State, input: &Inputs) -> (State, Outputs) {
    let _ = input;
    (
        State { a: state.a, b: state.b, c: state.c, d: state.d },
        Outputs { a: 0, b: 0, c: 0, d: 0 },
    )
}
