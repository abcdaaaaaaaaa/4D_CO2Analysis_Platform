import numpy as np
import plotly.graph_objects as go
from scipy.optimize import curve_fit
import plotly.colors as pc
import pandas as pd
import sys
import EstimateData

df = pd.read_excel("4D_Datas.xlsx")

selected_gas = input("MG811 gas name (CO2 / C2H5OH / CO / CH4): ")

def roundf(*args):
    return tuple(round(x, 4) for x in args)

def round2(value):
    return round(value, 2)

def inverseyaxb(valuea, value, valueb):
    return np.power(value / valuea, 1 / valueb)

def interpolate(x, x0, x1, y0, y1):
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)

def interpolate_from_table(x, table):
    keys = sorted(table.keys())
    if x <= keys[0]:
        return table[keys[0]]
    elif x >= keys[-1]:
        return table[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= x <= keys[i + 1]:
            a0, b0 = table[keys[i]]
            a1, b1 = table[keys[i + 1]]
            a = interpolate(x, keys[i], keys[i + 1], a0, a1)
            b = interpolate(x, keys[i], keys[i + 1], b0, b1)
            return (a, b)

def vals(minval, maxval, count):
    return np.linspace(minval, maxval, count)

def limit(value, minlim, maxlim):
    return np.clip(value, minlim, maxlim)

def time_curve(x):
    if 0 <= x <= 1:
        return 325.79
    elif 1 < x <= 2:
        return interpolate(x, 1, 2, 325.79, 326.15)
    elif 2 < x <= 3:
        return interpolate(x, 2, 3, 326.15, 325.05)
    elif 3 < x <= 5:
        return interpolate(x, 3, 5, 325.05, 288.06)
    elif 5 < x <= 7:
        return 285.86 + (3.2 * (x - 4) ** -1.0587 - 1)
    elif 7 < x <= 11:
        return 285.86
    elif 11 < x <= 13:
        return 285.86 + (3.2 * (14 - x) ** -1.0587 - 1)
    elif 13 < x <= 15:
        return interpolate(x, 13, 15, 288.06, 319.93)
    elif 15 < x <= 17:
        return 324.87 - (5.94 * (x - 14) ** -1.6218 - 1)
    elif 17 < x <= 19:
        return 324.87
    elif 19 < x <= 20:
        return interpolate(x, 19, 20, 324.87, 325.79)
    else:
        return np.nan

def get_constants(name, emf):
    a = np.full_like(emf, None, dtype=float)
    b = np.full_like(emf, None, dtype=float)

    match name:
        case 'CH4':
            a = 326.7924
            b = -0.0017

        case 'C2H5OH':
            cond1 = (emf > 322.2195)
            cond2 = (emf <= 322.2195) & (emf > 321.0224)
            cond3 = (emf <= 321.0224)

            a[cond1], b[cond1] = 327.3446, -0.0024
            a[cond2], b[cond2] = 350.0226, -0.0129
            a[cond3], b[cond3] = 333.2081, -0.0056

        case 'CO':
            cond1 = (emf > 320.0249)
            cond2 = (emf <= 320.0249) & (emf > 315.4364)
            cond3 = (emf <= 315.4364) & (emf > 298.0798)
            cond4 = (emf <= 298.0798) & (emf > 280.5237)
            cond5 = (emf <= 280.5237)

            a[cond1], b[cond1] = 332.606, -0.0061
            a[cond2], b[cond2] = 383.6791, -0.0284
            a[cond3], b[cond3] = 827.293, -0.1396
            a[cond4], b[cond4] = 468.501, -0.0618
            a[cond5], b[cond5] = 483.2887, -0.0654

        case 'CO2':
            a = 499.0689
            b = -0.0722

    return a, b

def correction_time(t):
    return t if t < 20 else t % 20.0

def calculate_correction(t):
    temp_corr_a, temp_corr_b = interpolate_from_table(28, temp_data)
    a_corr = (temp_corr_a + 538.2376 + 499.0689) / 3 # 499.0689: CO2_a
    b_corr = (temp_corr_b + -0.0733 + -0.0722) / 3 # -0.0722: CO2_b
    return 3500 / inverseyaxb(a_corr, time_curve(correction_time(t)), b_corr)

def Sensorppm(temp, rh, EMF, gas_name, t_corr, cr_mode):
    if np.isscalar(temp):
        a_temp, b_temp = interpolate_from_table(temp, temp_data)
    else:
        temp_interp = np.array([interpolate_from_table(t, temp_data) for t in temp])
        a_temp, b_temp = temp_interp[:, 0], temp_interp[:, 1]

    if np.isscalar(rh):
        a_rh, b_rh = interpolate_from_table(rh, rh_data)
    else:
        rh_interp = np.array([interpolate_from_table(r, rh_data) for r in rh])
        a_rh, b_rh = rh_interp[:, 0], rh_interp[:, 1]

    gas_a, gas_b = get_constants(gas_name, EMF)

    a_avg = (a_temp + a_rh + gas_a) / 3
    b_avg = (b_temp + b_rh + gas_b) / 3

    if (cr_mode):
        if np.isscalar(t_corr):
            correction = calculate_correction(t_corr)
        else:
            correction = np.array([calculate_correction(t) for t in t_corr])
    else:
        correction = 1.5371654620976198
    
    ppm = inverseyaxb(a_avg, EMF, b_avg) * correction
    return ppm

temp_data = {
    -10: (522.7202, -0.0843),
    0: (517.0238, -0.0833),
    10: (520.9298, -0.0849),
    20: (523.094, -0.0863),
    30: (527.0596, -0.0879),
    50: (527.0802, -0.0891)
}

rh_data = {
    20: (540, -0.07),
    40: (536.8846, -0.0726),
    65: (538.2376, -0.0733),
    85: (529.1227, -0.0717)
}

gases = {
    'CH4':     (100, 600, 323.217, 324.2145),
    'C2H5OH':  (100, 1000, 320.6234, 323.616),
    'CO':      (100, 10000, 264.1646, 323.616),
    'CO2':     (400, 1000, 303.6658, 324.2145)
}

emf_min = gases[selected_gas][2]
emf_max = gases[selected_gas][3]

time, percentile, temperature, rh = np.array(df["Time"], dtype=float), np.array(df["Per"], dtype=float), np.array(df["Temp"], dtype=float), np.array(df["Rh"], dtype=float)
percentile, temperature, rh = limit(percentile, 0, 100), limit(temperature, -10, 50), limit(rh, 0, 100)

SensorValue = percentile / 100
correction_coefficient = np.array([calculate_correction(t) for t in time])
corrected_time = time if min(time)==1 else (time - min(time)) / 20 + 1

time_surface = vals(min(time), max(time)*2 if min(time)==1 else (max(time) - min(time)) * 2 + min(time) + 20, 200)
corrected_time_surface = time_surface if min(time)==1 else (time_surface - min(time)) / 20 + 1

r2_temp_time, temperature_surface_raw, model_temp = EstimateData.get_best_fit(corrected_time, temperature, corrected_time_surface)
temperature_surface = limit(temperature_surface_raw, -10, 50)

r2_rh_time, rh_surface_raw, model_rh = EstimateData.get_best_fit(corrected_time, rh, corrected_time_surface, temp=temperature, temp_surface=temperature_surface)
rh_surface = limit(rh_surface_raw, 0, 100)

r2_percentile_time, percentile_surface_raw, model_per = EstimateData.get_best_fit(corrected_time, percentile, corrected_time_surface, temp=temperature, temp_surface=temperature_surface)
percentile_surface = limit(percentile_surface_raw, 0, 100)

correction_coefficient_surface = np.array([calculate_correction(t) for t in time_surface])
SensorValue_surface = percentile_surface / 100

ppm = Sensorppm(temperature, rh, interpolate(SensorValue, 0, 1, emf_max, emf_min), selected_gas, time, True)
# false_ppm = Sensorppm(temperature, rh, interpolate(SensorValue, 0, 1, emf_max, emf_min), selected_gas, time, False)
ppm_surface = Sensorppm(temperature_surface, rh_surface, interpolate(SensorValue_surface, 0, 1, emf_max, emf_min), selected_gas, time_surface, True)
# false_ppm_surface = Sensorppm(temperature_surface, rh_surface, interpolate(SensorValue_surface, 0, 1, emf_max, emf_min), selected_gas, time_surface, False)

print(f"Percentile Model: {model_per}")
print(f"Temperature Model: {model_temp}")
print(f"RH Model: {model_rh}")
print()

print(f"Gas: {selected_gas} | R²_Per={r2_percentile_time} | R²_Temp={r2_temp_time} | R²_Rh={r2_rh_time}")

for t_val, temp_val, rh_val, sv_val, corr_val in zip(time_surface, temperature_surface, rh_surface, SensorValue_surface, correction_coefficient_surface):
    EMF_val = interpolate(sv_val, 0, 1, emf_max, emf_min)
    ppm_val = Sensorppm(temp_val, rh_val, EMF_val, selected_gas, t_val, True)
    print(f"t={t_val:.4f}s Sensor={sv_val:.4f} temp={temp_val:.4f} rh={rh_val:.4f} corr={corr_val:.4f} EMF={EMF_val:.4f} ppm={ppm_val:.4f}")
print("")
