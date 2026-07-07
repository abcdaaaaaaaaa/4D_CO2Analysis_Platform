from datetime import datetime
import subprocess
import pandas as pd
import numpy as np
import EstimateData

gases = ['CH4', 'C2H5OH', 'CO', 'CO2']

now = datetime.now()
formatted = now.strftime("%Y-%m-%d %H:%M:%S")

print("")
print("")
print(formatted)
print("")
print("")

with open("DataReport.txt", "a") as f:
    f.write("\n")
    f.write("\n")
    f.write(formatted)
    f.write("\n")
    f.write("\n")

with open("EstimationReport.txt", "a") as f:
    f.write("\n")
    f.write("\n")
    f.write(formatted)
    f.write("\n")
    f.write("\n")

df = pd.read_excel("4D_Datas.xlsx")
time, percentile, temperature, rh = np.array(df["Time"], dtype=float), np.array(df["Per"], dtype=float), np.array(df["Temp"], dtype=float), np.array(df["Rh"], dtype=float)
percentile, temperature, rh = np.clip(percentile, 0, 100), np.clip(temperature, -10, 50), np.clip(rh, 0, 100)

corrected_time = time if min(time)==1 else (time - min(time)) / 20 + 1
time_surface = np.linspace(min(time), max(time)*2 if min(time)==1 else (max(time) - min(time)) * 2 + min(time) + 20, 200)
corrected_time_surface = time_surface if min(time)==1 else (time_surface - min(time)) / 20 + 1

_, temperature_surface_raw, model_temp = EstimateData.get_best_fit(corrected_time, temperature, corrected_time_surface)
temperature_surface = np.clip(temperature_surface_raw, -10, 50)

_, _, model_rh = EstimateData.get_best_fit(corrected_time, rh, corrected_time_surface, temp=temperature, temp_surface=temperature_surface)
_, _, model_per = EstimateData.get_best_fit(corrected_time, percentile, corrected_time_surface, temp=temperature, temp_surface=temperature_surface)

print(f"Percentile Model: {model_per}")
print(f"Temperature Model: {model_temp}")
print(f"RH Model: {model_rh}")
print()

with open("EstimationReport.txt", "a") as f:
    f.write("\n")
    f.write(f"Percentile Model: {model_per}")
    f.write("\n")
    f.write(f"Temperature Model: {model_temp}")
    f.write("\n")
    f.write(f"RH Model: {model_rh}")
    f.write("\n")

for gas in gases:
    process = subprocess.Popen(["python", "4DSlope.py", gas], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in process.stdout:
        print(line, end='')

    process.wait()

process = subprocess.Popen(["python", "TheoreticalCO2.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

for line in process.stdout:
    print(line, end='')

process.wait()
