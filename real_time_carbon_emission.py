import pickle
import argparse
import psutil
import pandas as pd
import numpy as np
import os, time, datetime
import GPUtil as gutil
from sklearn.preprocessing import PolynomialFeatures

PUE_used = 1
PSF = 1

df_enc = pd.read_csv("Encoded Dataset v3.csv")
CI_df =  pd.read_csv("../green-algorithms-tool/data/CI_aggregated.csv",
                     sep=',', skiprows=0)
cpu_df = pd.read_csv("..\green-algorithms-tool\data\TDP_cpu.csv")
gpu_df = pd.read_csv("..\green-algorithms-tool\data\TDP_gpu.csv")

args = argparse.ArgumentParser()
args.add_argument("-ct", required=True, dest="ct", help="Type of core you have i.e. CPU or GPU", default="CPU", choices=["CPU", "GPU"])
args.add_argument("-p", required=True, dest="p", help="processor you possess")
args.add_argument("-lc", required=True, dest="lc", help="Location of the system")
args = args.parse_args()

if args.ct=="CPU":
    # Count the number of cores the CPU has.
    cores = os.cpu_count()

    # Calculate the TDP of the system. Min value in case of no finding of the system.
    if args.p in list(cpu_df["model"].values):
        tdp = cpu_df.loc[cpu_df["model"]==args.p, "TDP_per_core"].values[0]
    else:
        tdp = cpu_df["TDP_per_core"].min()

elif args.ct=="GPU":
    tm = datetime.datetime.now()
    runTime = 0.0
    gpus = gutil.getGPUs()
    cores = len(gpus)
    if args.p in gpu_df["model"]:
        tdp = gpu_df.loc[gpu_df["model"]==args.p, "TDP_per_core"]
    else:
        tdp = gpu_df["TDP_per_core"].min()

ptr = 0
while ptr<10:
    ptr+=1
    if args.ct=="CPU":
        op = psutil.cpu_times()
        runTime = sum(op)/(60*60*6)
        memory = psutil.virtual_memory()[1]/1000000000

    ## TODO
    elif args.ct=="GPU":
        if gutil.getGPUs()[0].memoryUtil < 0.1:
            runTime = 0
        else:
            runTime += (datetime.datetime.now() - tm).total_seconds()/3600
            tm = datetime.datetime.now()

        # Calculate the total memory available by subtracting the total memory with memory currently in use.
        memory = (gutil.getGPUs()[0].memoryTotal - gutil.getGPUs()[0].memoryUsed)/1024  # In GB

    enc = {
        "CPU": 0,
        "GPU": 1
    }
    rec = {}
    rec["tdp"] = tdp
    rec["runTime"] = runTime
    rec["cores"] = cores
    rec["memory"] = memory
    rec["coreType_GPU"] = enc[args.ct]
    row = np.array(list(rec.values()))
    coreType = args.ct

    powerNeeded_core = PUE_used*cores*tdp*1

    # SERVER/LOCATION Taking US by default.
    if args.lc in CI_df.location.values:
        carbonIntensity = CI_df.loc[CI_df.location == args.lc, "carbonIntensity"].values[0]
    else:
        carbonIntensity = 475 # Given in dataset

    #powerNeeded_core = powerNeeded_CPU + powerNeeded_GPU
    powerNeeded_memory = PUE_used * (memory * 0.3725)        #Memory Power
    powerNeeded = powerNeeded_core + powerNeeded_memory
    energyNeeded = runTime * powerNeeded * PSF / 1000

    carbonEmissions = energyNeeded * carbonIntensity

    carbonEmissions_value = carbonEmissions
    carbonEmissions_unit = "g"
    if carbonEmissions_value >= 1e6:
        carbonEmissions_value /= 1e6
        carbonEmissions_unit = "T"
    elif carbonEmissions_value >= 1e3:
        carbonEmissions_value /= 1e3
        carbonEmissions_unit = "kg"

    print(f"{round(carbonEmissions_value, 4)}{carbonEmissions_unit}CO2e") if carbonEmissions>0 else print(0)
    time.sleep(1)