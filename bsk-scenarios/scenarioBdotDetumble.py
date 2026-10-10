"""
bsk-scenarios/scenarioBdotDetumble.py
 
Week 1-2 baseline: a tumbling spacecraft in LEO, detumbled using a
classic B-dot control law (bdot_law.py) driving three orthogonal
magnetic torque bars, with the Earth's field modeled via WMM and sensed
through a noisy three-axis magnetometer (TAM).
 
This is the pure-Basilisk baseline this project will later compare the
cFS-driven closed loop against — same physics, same control law, just
running natively in Basilisk instead of over the ZeroMQ bridge into
gnc_app.
 
IMPORTANT — verify against your local install before trusting this
blindly: I built this against the Basilisk 2.x documentation for
MagneticFieldWMM / Magnetometer / MtbEffector, but I don't have Basilisk
installed in the environment I wrote this in, so I could not execute it
end-to-end myself. The dynamics/orbit/spacecraft setup follows the
standard pattern (same as scenarioBasicOrbit, which you've already run
successfully). The parts most likely to need small fixes for your exact
v2.10.2 API are marked with `# VERIFY:` comments below — cross-check
those specifically against your local
{basilisk_install}/examples/scenarioTAM.py and
{basilisk_install}/examples/scenarioMtbMomentumManagement.py, which
exercise the same modules. Paste me the traceback if something doesn't
match and we'll fix it together.
 
Run: python3 scenarioBdotDetumble.py
"""
 
from __future__ import annotations
 
import numpy as np
import matplotlib.pyplot as plt
 
from Basilisk.utilities import (
    SimulationBaseClass,
    macros,
    orbitalMotion,
    simIncludeGravBody,
    unitTestSupport,
)
from Basilisk.simulation import spacecraft, magneticFieldWMM, magnetometer, MtbEffector
from Basilisk.architecture import messaging, sysModel
from Basilisk import __path__ as bsk_path
 
from bdot_law import bdot_dipole_cmd
 
bskPath = bsk_path[0]
 
# --- tunables -----------------------------------------------------------
SIM_STEP_S = 0.5          # simulation + control step, seconds
SIM_DURATION_S = 12000.0   # ~1.5 orbits at 500 km, plenty of time to detumble
OMEGA_INIT_RPS = (0.05, -0.03, 0.02)   # initial tumble rate, rad/s (~2-3 deg/s)
BDOT_GAIN = 1.0e7         # A*m^2 * s / T — tune this, it's the one free knob
MTB_MAX_DIPOLE = 5.0      # A*m^2, per-axis saturation
 
 
class BdotController(sysModel.SysModel):
    """Python BSK module implementing the B-dot law from bdot_law.py.
 
    Reads the TAM output message each step, finite-differences it against
    the previous sample, and writes a commanded dipole to the MTB
    effector's input message. See "Making Python Modules" in the
    Basilisk docs for the SysModel contract this follows.
    """
 
    def __init__(self, tam_out_msg, gain: float, m_max: float):
        super().__init__()
        self.tam_out_msg = tam_out_msg
        self.mtbCmdOutMsg = messaging.MTBCmdMsg()
        self.gain = gain
        self.m_max = m_max
        self._B_prev = None
        self._t_prev_ns = None
 
    def Reset(self, CurrentSimNanos):
        self._B_prev = None
        self._t_prev_ns = None
 
    def UpdateState(self, CurrentSimNanos):
        tam_payload = self.tam_out_msg.read()
        B_now = tuple(tam_payload.tam_S)
 
        cmd_payload = messaging.MTBCmdMsgPayload()
        if self._B_prev is None or self._t_prev_ns is None:
            # first call: no derivative available yet, command zero
            dipole_cmd = (0.0, 0.0, 0.0)
        else:
            dt_s = (CurrentSimNanos - self._t_prev_ns) * macros.NANO2SEC
            dipole_cmd = bdot_dipole_cmd(B_now, self._B_prev, dt_s, self.gain, self.m_max)
 
        cmd_payload.mtbDipoleCmds = list(dipole_cmd)
        self.mtbCmdOutMsg.write(cmd_payload, CurrentSimNanos, self.moduleID)
 
        self._B_prev = B_now
        self._t_prev_ns = CurrentSimNanos
 
 
def run(show_plots: bool = True):
    scSim = SimulationBaseClass.SimBaseClass()
    dyn_process_name = "dynProcess"
    dyn_task_name = "dynTask"
    step = macros.sec2nano(SIM_STEP_S)
 
    dyn_process = scSim.CreateNewProcess(dyn_process_name)
    dyn_process.addTask(scSim.CreateNewTask(dyn_task_name, step))
 
    # --- spacecraft hub ---------------------------------------------------
    scObject = spacecraft.Spacecraft()
    scObject.ModelTag = "bskSat"
    I = [10.0, 0.0, 0.0,
         0.0, 9.0, 0.0,
         0.0, 0.0, 7.0]  # kg*m^2, small-sat-scale inertia — adjust to taste
    scObject.hub.mHub = 12.0
    scObject.hub.r_BcB_B = [[0.0], [0.0], [0.0]]
    scObject.hub.IHubPntBc_B = unitTestSupport.np2EigenMatrix3d(I)
    scSim.AddModelToTask(dyn_task_name, scObject)
 
    # --- gravity + orbit ---------------------------------------------------
    gravFactory = simIncludeGravBody.gravBodyFactory()
    planet = gravFactory.createEarth()
    planet.isCentralBody = True
    mu = planet.mu
    gravFactory.addBodiesTo(scObject)
 
    oe = orbitalMotion.ClassicElements()
    oe.a = 6378136.6 + 500e3   # 500 km altitude LEO
    oe.e = 0.001
    oe.i = 51.6 * macros.D2R
    oe.Omega = 48.2 * macros.D2R
    oe.omega = 347.8 * macros.D2R
    oe.f = 85.3 * macros.D2R
    rN, vN = orbitalMotion.elem2rv(mu, oe)
    scObject.hub.r_CN_NInit = rN
    scObject.hub.v_CN_NInit = vN
    scObject.hub.sigma_BNInit = [[0.0], [0.0], [0.0]]
    scObject.hub.omega_BN_BInit = [[OMEGA_INIT_RPS[0]], [OMEGA_INIT_RPS[1]], [OMEGA_INIT_RPS[2]]]
 
    # --- magnetic field (centered dipole; no data file needed) ---------------
    from Basilisk.simulation import magneticFieldCenteredDipole
    from Basilisk.utilities import simSetPlanetEnvironment
 
    magModule = magneticFieldCenteredDipole.MagneticFieldCenteredDipole()
    magModule.ModelTag = "CenteredDipole"
    simSetPlanetEnvironment.centeredDipoleMagField(magModule, "earth")
    magModule.addSpacecraftToModel(scObject.scStateOutMsg)
    scSim.AddModelToTask(dyn_task_name, magModule)
 
    # --- TAM (magnetometer) sensor -----------------------------------------
    tamModule = magnetometer.Magnetometer()
    tamModule.ModelTag = "TAM_sensor"
    tamModule.stateInMsg.subscribeTo(scObject.scStateOutMsg)     # VERIFY: exact input msg name
    tamModule.magInMsg.subscribeTo(magModule.envOutMsgs[0])       # VERIFY: exact input msg name
    # Modest noise floor to start — this is realistic-sensor-noise territory
    # from the original plan; tighten/loosen once the clean case detumbles.
    tamModule.senNoiseStd = [1.0e-9, 1.0e-9, 1.0e-9]  # Tesla, per axis
    scSim.AddModelToTask(dyn_task_name, tamModule)
 
    # --- magnetic torque bars (3 orthogonal rods) --------------------------
    mtbConfig = messaging.MTBArrayConfigMsgPayload()
    mtbConfig.numMTB = 3
    mtbConfig.GtMatrix_B = [1.0, 0.0, 0.0,
                            0.0, 1.0, 0.0,
                            0.0, 0.0, 1.0]   # row-major, rods aligned with body axes
    mtbConfig.maxMtbDipoles = [MTB_MAX_DIPOLE] * 3
    mtbParamsMsg = messaging.MTBArrayConfigMsg().write(mtbConfig)
 
    mtbEff = MtbEffector.MtbEffector()
    mtbEff.ModelTag = "MTB"
    mtbEff.mtbParamsInMsg.subscribeTo(mtbParamsMsg)
    mtbEff.magInMsg.subscribeTo(magModule.envOutMsgs[0])
    scObject.addDynamicEffector(mtbEff)
    scSim.AddModelToTask(dyn_task_name, mtbEff)
 
    # --- B-dot controller (Python module) -----------------------------------
    controller = BdotController(
        tam_out_msg=tamModule.tamDataOutMsg,
        gain=BDOT_GAIN,
        m_max=MTB_MAX_DIPOLE,
    )
    controller.ModelTag = "bdotController"
    mtbEff.mtbCmdInMsg.subscribeTo(controller.mtbCmdOutMsg)
    scSim.AddModelToTask(dyn_task_name, controller)
 
    # --- logging -------------------------------------------------------------
    omega_log = scObject.scStateOutMsg.recorder()
    tam_log = tamModule.tamDataOutMsg.recorder()
    scSim.AddModelToTask(dyn_task_name, omega_log)
    scSim.AddModelToTask(dyn_task_name, tam_log)
 
    # --- run ------------------------------------------------------------------
    scSim.InitializeSimulation()
    scSim.ConfigureStopTime(macros.sec2nano(SIM_DURATION_S))
    scSim.ExecuteSimulation()
    print("sim clock [s]:", scSim.TotalSim.CurrentNanos * macros.NANO2SEC)
 
    # --- plot -------------------------------------------------------------------
    time_s = omega_log.times() * macros.NANO2SEC
    omega = omega_log.omega_BN_B  # VERIFY: exact recorded field name
    print(f"|omega| start: {np.linalg.norm(omega[0]):.5f} rad/s, "
          f"end: {np.linalg.norm(omega[-1]):.5f} rad/s")
    
    norm = np.linalg.norm(omega, axis=1)
    below = np.where(norm < 0.017)[0]   # 1 deg/s
    print("time to < 1 deg/s [s]:", time_s[below[0]] if len(below) else "not reached")
    
    print("sim clock [s]:", scSim.TotalSim.CurrentNanos * macros.NANO2SEC)
 
    plt.figure()
    for axis, label in enumerate(["x", "y", "z"]):
        plt.plot(time_s, omega[:, axis] * macros.R2D, label=f"omega_{label}")
    plt.xlabel("Time [s]")
    plt.ylabel("Body rate [deg/s]")
    plt.title("B-dot Detumble — Body Angular Rate")
    plt.legend()
    plt.grid(True)
 
    if show_plots:
        #plt.savefig("bdot_detumble_baseline.png", dpi=150)
        plt.show()
 
    return time_s, omega
 
 
if __name__ == "__main__":
    run(show_plots=True)
