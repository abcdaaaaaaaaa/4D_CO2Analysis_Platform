import numpy as np
from decimal import Decimal, getcontext
import plotly.graph_objects as go
import pandas as pd

getcontext().prec = 200

def interpolate(value, min_value, max_value, target_min, target_max):
    return target_min + (value - min_value) * (target_max - target_min) / (max_value - min_value)

def exponential_interpolate(value, min_value, max_value, target_min, target_max):
    log_min = Decimal(target_min).log10()
    log_max = Decimal(target_max).log10()
    ratio = (value - min_value) / (max_value - min_value)
    log_val = log_min + ratio * (log_max - log_min)
    return (Decimal(10) ** log_val)

def model(x, a, b, c):
    return 1000.0 - 600.0 * np.exp(-(a*x + b*x**2 + c*x**3))

def fit_model(x, y):
    best = (1e9, None, None, None)
    for a in np.linspace(4.0, 7.0, 61):
        for b in np.linspace(2.0, 7.0, 61):
            for c in np.linspace(-5.0, 0.0, 61):
                pred = model(x, a, b, c)
                err = np.sqrt(np.mean((pred - y) ** 2))
                if err < best[0]:
                    best = (err, a, b, c)
    return best

def TheoreticalCO2_func(x: float) -> float:
    t = a*x + b*x*x + c*x**3
    return 1000.0 - 600.0 * np.exp(-t)

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

sensor_values = []
ppm_values = []
func_values = []

for sv in np.linspace(0, 1, 1000):
    sensor_value = Decimal(sv)
    V_out = sensor_value / Decimal(10)
    P_co2 = ((E_c - V_out) / coeff).exp()
    ppm = P_co2 * Decimal(1e6)

    current_ppm = round(exponential_interpolate(interpolate(ppm, min_ppm, max_ppm, max_sensor_value, min_sensor_value), min_sensor_value, max_sensor_value, min_co2_ppm, max_co2_ppm))
    if (current_ppm != min_co2_ppm and current_ppm != max_co2_ppm): 
        current_ppm = exponential_interpolate(interpolate(ppm, min_ppm, max_ppm, max_sensor_value, min_sensor_value), min_sensor_value, max_sensor_value, min_co2_ppm, max_co2_ppm)

    sensor_values.append(float(sensor_value))
    ppm_values.append(float(current_ppm))

    if current_ppm >= 1000:
        break

df = pd.DataFrame({"SensorValue": sensor_values, "TheoreticalCO2": ppm_values})
df = df.iloc[:-1]

df.to_excel("MG811_Theoretical_CO2.xlsx", index=False)

df = pd.read_excel("MG811_Theoretical_CO2.xlsx")
SensorValue, TheoreticalCO2 = np.array(df["SensorValue"], dtype=float), np.array(df["TheoreticalCO2"], dtype=float)

err, a, b, c = fit_model(SensorValue, TheoreticalCO2)

for sv in np.linspace(0, 1, 1000):
    current_func = round(TheoreticalCO2_func(sv))
    
    if (current_func != min_co2_ppm and current_func != max_co2_ppm): 
        current_func = TheoreticalCO2_func(sv)
        
    func_values.append(float(current_func))

    if current_func >= 1000:
        break

fig = go.Figure()
fig.add_trace(go.Scatter(x=sensor_values, y=ppm_values, mode='lines',  line=dict(width=3), name="CO₂ PPM"))
fig.add_trace(go.Scatter(x=sensor_values, y=func_values, mode='lines', line=dict(color='rgba(0, 0, 255, 0.9)', width=1.5), name="Func PPM"))

fig.update_layout(
    title=f"MG811 Theoretical CO₂ Analyses: a={a:.4f}, b={b:.4f}, c={c:.4f}, RMSE={err:.4f}",
    xaxis=dict(title='X: SensorValue'),
    yaxis=dict(title='Y: Theoretical CO₂ ppm'),
    template="plotly_dark"
)

fig.write_html("MG811_Theoretical_CO2.html")
