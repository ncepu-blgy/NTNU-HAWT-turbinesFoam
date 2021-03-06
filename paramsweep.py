#!/usr/bin/env python
"""
Run multiple simulations varying a single parameter.
"""

import foampy
from foampy.dictionaries import replace_value
import numpy as np
from subprocess import call
import os
import pandas as pd
import shutil
from pynhtf import processing as pr


def log_perf(param="tsr", append=True):
    """Log performance to file."""
    if not os.path.isdir("processed"):
        os.mkdir("processed")
    fpath = "processed/{}_sweep.csv".format(param)
    if append and os.path.isfile(fpath):
        df = pd.read_csv(fpath)
    else:
        df = pd.DataFrame(columns=["tsr_turbine1", "cp_turbine1",
                                   "cd_turbine1", "tsr_turbine2",
                                   "cp_turbine2", "cd_turbine2"])
    df = df.append(pr.calc_perf(t1=1.0), ignore_index=True)
    df.to_csv(fpath, index=False)


def set_params(args):
    """Set run parameters by calling `scripts/set_turbines.py`"""
    cmd = "python scripts/set_turbines.py"
    for key, val in args.items():
        cmd += " --" + key + "=" + str(val)
    call(cmd, shell=True)


def run_solver(parallel=True):
    """Run `pimpleFoam`."""
    if parallel:
        call("mpirun -np 2 pimpleFoam -parallel > log.pimpleFoam", shell=True)
    else:
        call("pimpleFoam > log.pimpleFoam", shell=True)


def single_turbine_tsr_sweep(start=1, stop=12, step=1, turbine="turbine1",
                             tsr_other_turbine=4, other_turbine_active="on",
                             parallel=True, append=False):
    """Run over multiple TSRs. `stop` will not be included."""
    fpath = "processed/{}_tsr_sweep.csv".format(turbine)
    if not append and os.path.isfile(fpath):
        os.remove(fpath)
    tsrs = np.arange(start, stop, step)
    if turbine == "turbine1":
        other_turbine = "turbine2"
    elif turbine == "turbine2":
        other_turbine = "turbine1"
    for tsr in tsrs:
        params = {turbine + "_tsr": tsr,
                  other_turbine + "_tsr": tsr_other_turbine,
                  other_turbine + "_active": other_turbine_active}
        set_params(params)
        if tsr == tsrs[0]:
            call("./Allclean")
            print("Running blockMesh")
            call("blockMesh > log.blockMesh", shell=True)
            print("Running snappyHexMesh")
            call("snappyHexMesh -overwrite > log.snappyHexMesh",
                 shell=True)
            print("Running topoSet")
            call("topoSet > log.topoSet", shell=True)
            shutil.copytree("0.org", "0")
            if parallel:
                print("Running decomposePar")
                call("decomposePar > log.decomposePar", shell=True)
                call("ls -d processor* | xargs -I {} rm -rf ./{}/0", shell=True)
                call("ls -d processor* | xargs -I {} cp -r 0.org ./{}/0",
                     shell=True)
            print("Running pimpleFoam")
            run_solver(parallel=parallel)
        else:
            print("Running pimpleFoam")
            run_solver(parallel=parallel)
        os.rename("log.pimpleFoam", "log.pimpleFoam." + str(tsr))
        log_perf(param=turbine + "_tsr", append=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run mulitple simulations, "
                                     "varying a single parameter.")
    parser.add_argument("start", default=1, type=float)
    parser.add_argument("stop", default=12, type=float)
    parser.add_argument("step", default=1, type=float)
    parser.add_argument("--turbine", "-t", default="turbine1")
    parser.add_argument("--tsr-other-turbine", default=4, type=float)
    parser.add_argument("--parallel", default=True, type=bool)
    parser.add_argument("--append", "-a", default=False, action="store_true")

    args = parser.parse_args()
    single_turbine_tsr_sweep(args.start, args.stop, args.step,
                             turbine=args.turbine, append=args.append,
                             tsr_other_turbine=args.tsr_other_turbine,
                             parallel=args.parallel)
