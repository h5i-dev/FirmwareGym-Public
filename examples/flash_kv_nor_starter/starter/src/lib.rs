#![no_std]

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

pub struct State {
    pub a: i32,
}

pub const INITIAL: State = State { a: 0 };

pub fn transition(_state: &State, _input: &Inputs) -> (State, Outputs) {
    (
        INITIAL,
        Outputs {
            a: 0,
            b: -1,
            c: 0,
            d: 0,
        },
    )
}
