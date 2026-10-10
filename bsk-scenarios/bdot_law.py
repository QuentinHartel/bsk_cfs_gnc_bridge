"""
bsk-scenarios/bdot_law.py
 
Classic B-dot detumble control law, kept as a pure function with zero
Basilisk (or any framework) dependency. This is deliberate: the same
math gets ported to C for gnc_app later, and keeping it standalone here
means it's unit-testable in isolation and the eventual C port is a
faithful translation, not a reinterpretation.
 
Law: m_cmd = -k * dB/dt
 
Where B is the sensed magnetic field in the body frame (Tesla) and m_cmd
is the commanded magnetic dipole (A*m^2) sent to the torque bars. No
angular rate measurement is used or needed — that's the point of B-dot.
"""
 
from __future__ import annotations
from math import trunc

TRUNCATE_DECIMAL_PLACES = 4
FACTOR = 10 ** TRUNCATE_DECIMAL_PLACES
 
 
def bdot_dipole_cmd(B_body: tuple[float, float, float], B_body_prev: tuple[float, float, float], 
                    dt: float, gain: float, m_max: float) -> tuple[float, float, float]:
    """Compute the commanded magnetic dipole from consecutive B-field samples.
    Args:
        B_body: current sensed magnetic field in body frame, Tesla.
        B_body_prev: previous sample's sensed field, same frame, Tesla.
        dt: time between the two samples, seconds. Must be > 0.
        gain: B-dot gain k (A*m^2*s/T). Tune this — it's the one free
            parameter in the whole law.
        m_max: per-axis saturation limit for the commanded dipole, A*m^2
            (real torque rods have a maximum dipole they can produce).
    Returns:
        Commanded dipole (mx, my, mz), each clamped to +/- m_max.
    """

    #Validates time elapsed is > 0
    if dt <= 0.0:
        raise ValueError("bdot_dipole_cmd: dt must be positive")

    #Creates a zip for x, y ,z fo b and b prev. Then itterates through the pairs and calculates b_dot for x, y, z and gives it to the B_dot tuple
    B_dot = tuple((b - b_prev) / dt for b, b_prev in zip(B_body, B_body_prev))

    #Uses the B_dot tuples values and m = -kB to create the raw m commands for x, y, z and gives it to m_cmd_raw
    m_cmd_raw = tuple(-gain * bd for bd in B_dot)
    
    #Validates that the m's are not outside of the hardware capability and then returns the touple of the m's or max's
    m_cmd = tuple(max(-m_max, min(m_max, m)) for m in m_cmd_raw)
    #The truncate is for removing super small decimals caused by computer math and rounding issues
    return tuple(trunc(m*FACTOR)/FACTOR for m in m_cmd)
 
 
if __name__ == "__main__":
    B_prev = (2.0e-5, 0.0, 0.0)     #Initial field reading
    B_now = (1.8e-5, 0.3e-5, 0.0)   #The field rotated slightly

    #This runs out function to caculate the dipole command and puts the x, y, z commands in cmd
    cmd = bdot_dipole_cmd(B_now, B_prev, dt=0.5, gain=1e5, m_max=5.0)
    print(f"B_prev={B_prev}, B_now={B_now} -> dipole_cmd={cmd}")
    assert all(-5.0 <= c <= 5.0 for c in cmd)
 
    cmd_sat = bdot_dipole_cmd(B_now, B_prev, dt=0.5, gain=1e12, m_max=5.0)
    assert abs(cmd_sat[0]) == 5.0 and abs(cmd_sat[1]) == 5.0 and cmd_sat[2] == 0.0
    print(f"Saturation check OK: {cmd_sat}")
