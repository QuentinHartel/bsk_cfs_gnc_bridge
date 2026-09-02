# Basilisk Setup

Built from source, not installed via pip (Basilisk requires a compiled
C++/SWIG build, not a standard Python package).

## Version
Tag `v2.10.2` — https://github.com/AVSLab/basilisk/releases/tag/v2.10.2
Requires Python 3.10+. Avoid SWIG 4.4.0 (known compile regressions;
use 4.4.1+ or an earlier 4.x release).

## Location
Cloned and built at `~/dev/basilisk` (kept outside this repo — Basilisk's
build tree is large and not meant to be vendored).

## Build
```bash
git clone https://github.com/AVSLab/basilisk.git ~/dev/basilisk
cd ~/dev/basilisk
git checkout v2.10.2
python3 -m venv .venv
source .venv/bin/activate
pip install wheel conan
python3 conanfile.py   # or current official build entrypoint — see AVSLab docs
```

## Verifying the build
```bash
source ~/dev/basilisk/.venv/bin/activate
python3 -c "import Basilisk; print(Basilisk.__version__)"
python3 bsk-scenarios/scenarioBasicOrbit.py
```
Confirmed working: orbit propagation scenario runs and produces plots.

## Note on numpy version
Basilisk's compiled extensions are built against the numpy version present
at build time. If installing requirements.txt into a *different* venv than
the one used to build Basilisk, verify numpy compatibility rather than
assuming pip's resolved version will work with the existing Basilisk build.
