import numpy as np
from decimal import Decimal, getcontext
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.optimize import curve_fit
import pandas as pd

df = pd.read_excel("4D_Datas.xlsx")

getcontext().prec = 200

def roundf(*args):
    return tuple(round(x, 4) for x in args)

def round4(value):
    return round(value, 4)

def yaxb(a, x, b):
    return a * np.power(x, b)

def interpolate(value, min_value, max_value, target_min, target_max):
    return target_min + (value - min_value) * (target_max - target_min) / (max_value - min_value)

def exponential_interpolate(value, min_value, max_value, target_min, target_max):
    log_min = Decimal(target_min).log10()
    log_max = Decimal(target_max).log10()
    ratio = (value - min_value) / (max_value - min_value)
    log_val = log_min + ratio * (log_max - log_min)
    return (Decimal(10) ** log_val)

def calculate_r2(y, y_pred):
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - (ss_res / ss_tot)
    return r2

def fit_time_with_r2(x, y):
    popt, _ = curve_fit(lambda x, a, b: yaxb(a, x, b), x, y)
    a, b = popt
    y_pred = yaxb(a, x, b)
    r2 = calculate_r2(y, y_pred)
    return a, b, r2

def vals(minval, maxval, count):
    return np.linspace(minval, maxval, count)

def limit(value, minlim, maxlim):
    return np.minimum(np.maximum(value, minlim), maxlim)

time, percentile = np.array(df["Time"], dtype=float), np.array(df["Per"], dtype=float)
percentile = limit(percentile, 0, 100)

E_c = Decimal(6.0)
T = Decimal(298.15)
R = Decimal(8.314)
F = Decimal(96485.0)

coeff = (R * T) / (Decimal(2) * F)

P_co2_min = ((E_c - Decimal(0.1)) / coeff).exp()
P_co2_max = (E_c / coeff).exp()

min_ppm = P_co2_min * Decimal(1e6)
max_ppm = P_co2_max * Decimal(1e6)

min_sensor_value = Decimal(0)
max_sensor_value = Decimal(1)

min_co2_ppm = Decimal(400)
max_co2_ppm = Decimal(1000)

ppm_values = []
ppm_values_surface = []

corrected_time = time if min(time)==1 else (time - min(time)) / 20 + 1

a_percentile_time, b_percentile_time, r2_percentile_time = fit_time_with_r2(corrected_time, percentile)
a_percentile_time, b_percentile_time, r2_percentile_time = roundf(a_percentile_time, b_percentile_time, r2_percentile_time)

SensorValue = percentile / 100

time_surface = vals(min(time), max(time)*2 if min(time)==1 else (max(time) - min(time)) * 2 + min(time) + 20, 200)
corrected_time_surface = time_surface if min(time)==1 else (time_surface - min(time)) / 20 + 1
percentile_surface = limit(yaxb(a_percentile_time, corrected_time_surface, b_percentile_time), 0, 100)
SensorValue_surface = percentile_surface / 100

mintime = np.min(time_surface)
maxtime = np.max(time_surface)

minval = np.min(SensorValue_surface)
maxval = np.max(SensorValue_surface)

fig = go.Figure()

with open("DataReport.txt", "a") as f:
    f.write("\n")
    
with open("EstimationReport.txt", "a") as f:
    f.write("\n")

print(f"Gas: Theoretical CO2 | R²_Per={round4(r2_percentile_time)} |")

with open("DataReport.txt", "a") as f:
    f.write(f"Gas: Theoretical CO2 | R²_Per={round4(r2_percentile_time)} |\n")

with open("EstimationReport.txt", "a") as f:
    f.write(f"Gas: Theoretical CO2 | R²_Per={round4(r2_percentile_time)} |\n")

for i, sv in enumerate(SensorValue):
    sensor_value = Decimal(sv)
    V_out = sensor_value / Decimal(10)
    P_co2 = ((E_c - V_out) / coeff).exp()
    ppm = P_co2 * Decimal(1e6)

    current_ppm = round(exponential_interpolate(interpolate(ppm, min_ppm, max_ppm, max_sensor_value, min_sensor_value), min_sensor_value, max_sensor_value, min_co2_ppm, max_co2_ppm))
    if (current_ppm != min_co2_ppm and current_ppm != max_co2_ppm): 
        current_ppm = round4(exponential_interpolate(interpolate(ppm, min_ppm, max_ppm, max_sensor_value, min_sensor_value), min_sensor_value, max_sensor_value, min_co2_ppm, max_co2_ppm))

    if current_ppm >= 1000:
        current_ppm = 1000

    ppm_values.append(float(current_ppm))

    print(f"t={time[i]:.4f}s Sensor={sensor_value:.4f} ppm={current_ppm:.4f}")
    with open("DataReport.txt", "a") as f:
        f.write(f"t={time[i]:.4f}s Sensor={sensor_value:.4f} ppm={current_ppm:.4f}\n")
print("")

for i, sv in enumerate(SensorValue_surface):
    sensor_value = Decimal(sv)
    V_out = sensor_value / Decimal(10)
    P_co2 = ((E_c - V_out) / coeff).exp()
    ppm = P_co2 * Decimal(1e6)

    current_ppm = round(exponential_interpolate(interpolate(ppm, min_ppm, max_ppm, max_sensor_value, min_sensor_value), min_sensor_value, max_sensor_value, min_co2_ppm, max_co2_ppm))
    if (current_ppm != min_co2_ppm and current_ppm != max_co2_ppm): 
        current_ppm = round4(exponential_interpolate(interpolate(ppm, min_ppm, max_ppm, max_sensor_value, min_sensor_value), min_sensor_value, max_sensor_value, min_co2_ppm, max_co2_ppm))

    if current_ppm >= 1000:
        current_ppm = 1000

    ppm_values_surface.append(float(current_ppm))

    print(f"t={time_surface[i]:.4f}s Sensor={sensor_value:.4f} ppm={current_ppm:.4f}")
    with open("EstimationReport.txt", "a") as f:
        f.write(f"t={time_surface[i]:.4f}s Sensor={sensor_value:.4f} ppm={current_ppm:.4f}\n")
print("")
    
fig = make_subplots(rows=1, cols=2)

fig.add_trace(go.Scatter(x=time, y=SensorValue, mode='markers', name = "Real SensorValues", marker=dict(color="#636EFA")), row=1, col=1)
fig.add_trace(go.Scatter(x=time_surface, y=SensorValue_surface, mode='lines', name = "SensorValue's Curve", line=dict(color="#636EFA")), row=1, col=1)

fig.add_trace(go.Scatter(x=SensorValue, y=ppm_values, mode='markers', name = "Real SensorValues", marker=dict(color="#EF553B")), row=1, col=2)
fig.add_trace(go.Scatter(x=SensorValue_surface, y=ppm_values_surface, mode='lines', name = "SensorValue's Curve", line=dict(color="#EF553B")), row=1, col=2)

fig.update_layout(
    title=f"MG811 Theoretical CO₂ Slope Estimation: R² = {round4(r2_percentile_time)}",
    xaxis=dict(title='X: Time (w)'),
    yaxis=dict(title='Y: SensorValue (z)'),
    xaxis2=dict(title='X: SensorValue'),
    yaxis2=dict(title='Y: Theoretical CO₂ ppm'),
    template='plotly_dark'
)

fig.write_html(f"MG811_Theoretical_CO2_Slope_Estimation.html")
