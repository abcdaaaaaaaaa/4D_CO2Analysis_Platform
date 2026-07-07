from datetime import datetime
import subprocess

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

for gas in gases:
    process = subprocess.Popen(["python", "4DSlope.py", gas], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    for line in process.stdout:
        print(line, end='')

    process.wait()

process = subprocess.Popen(["python", "TheoreticalCO2.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

for line in process.stdout:
    print(line, end='')

process.wait()
