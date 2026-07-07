import numpy as np
import plotly.graph_objects as go
from scipy.optimize import curve_fit
import plotly.colors as pc
import pandas as pd
import sys

df = pd.read_excel("4D_Datas.xlsx")

selected_gas = sys.argv[1]

def roundf(*args):
    return tuple(round(x, 4) for x in args)

def round2(value):
    return round(value, 2)

def yaxb(valuea, value, valueb):
    return valuea * np.power(value, valueb)

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

def fit_daily_sine(t_sec, temps, period=86400.0):
    w = 2*np.pi/period
    t_sec = np.array(t_sec, dtype=float)
    temps = np.array(temps, dtype=float)
    X = np.column_stack([np.ones_like(t_sec), np.sin(w*t_sec), np.cos(w*t_sec)])
    coeffs, *_ = np.linalg.lstsq(X, temps, rcond=None)
    return coeffs[0], coeffs[1], coeffs[2], w

def predict_temp(t, M, C, D, w):
    return M + C*np.sin(w*t) + D*np.cos(w*t)

def function(constant, mini_slope):
    return constant * mini_slope + constant

def differentiation(valuea, value, valueb):
    slope = valuea * valueb * np.power(value, valueb-1)
    slope = limit(slope, -1, 1)
    mini_slope = slope / 4
    return mini_slope
    # return True if slope >= 0 else False

def create_cube(center, xmin, xmax, ymin, ymax, zmin, zmax):
    x0, y0, z0 = center
    vertices = [[x0 + xmin, y0 + ymin, z0 + zmin], [x0 + xmax, y0 + ymin, z0 + zmin], [x0 + xmax, y0 + ymax, z0 + zmin], [x0 + xmin, y0 + ymax, z0 + zmin], [x0 + xmin, y0 + ymin, z0 + zmax], [x0 + xmax, y0 + ymin, z0 + zmax], [x0 + xmax, y0 + ymax, z0 + zmax], [x0 + xmin, y0 + ymax, z0 + zmax]]
    return np.array(vertices)

def add_cube_edges(fig, vertices, color, trace_name):
    edges = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 5), (7, 4), (4, 5), (3, 7)]
    for start, end in edges: fig.add_trace(go.Scatter3d(x=[vertices[start, 0], vertices[end, 0]], y=[vertices[start, 1], vertices[end, 1]], z=[vertices[start, 2], vertices[end, 2]], mode='lines+text', line=dict(color=color, width=4), text=[trace_name, trace_name], textposition="middle center", name=trace_name, hoverinfo='text+name', textfont=dict(size=15, color=color, weight='bold')))

def add_cube_faces(fig, vertices, color, trace_name):
    faces = [[0, 1, 2], [0, 2, 3], [0, 1, 5], [0, 5, 4], [0, 3, 7], [0, 7, 4]]
    fig.add_trace(go.Mesh3d(x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2], i=[face[0] for face in faces], j=[face[1] for face in faces], k=[face[2] for face in faces], color=color, opacity=0.3, name=trace_name, flatshading=True, hoverinfo='none'))

def add_z_faces(fig, outer_vertices, inner_vertices, color, trace_name):
    z_faces = [(0, 1, 5, 4), (4, 5, 1, 0), (0, 3, 7, 4), (4, 7, 3, 0)]
    for face in z_faces: fig.add_trace(go.Mesh3d(x=[outer_vertices[face[i], 0] for i in range(4)] + [inner_vertices[face[i], 0] for i in range(4)], y=[outer_vertices[face[i], 1] for i in range(4)] + [inner_vertices[face[i], 1] for i in range(4)], z=[outer_vertices[face[i], 2] for i in range(4)] + [inner_vertices[face[i], 2] for i in range(4)], color=color, opacity=0.3, name=trace_name, flatshading=True, hoverinfo='none'))

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
M, C, D, w = fit_daily_sine(time, temperature)
SensorValue = percentile / 100
correction_coefficient = np.array([calculate_correction(t) for t in time])
corrected_time = time if min(time)==1 else (time - min(time)) / 20 + 1
temp_time = np.array([predict_temp(t, M, C, D, w) for t in time])
r2_temp_time = calculate_r2(temperature, temp_time)

a_rh_time, b_rh_time, r2_rh_time = fit_time_with_r2(corrected_time, rh)
a_percentile_time, b_percentile_time, r2_percentile_time = fit_time_with_r2(corrected_time, percentile)

a_rh_time, b_rh_time, r2_rh_time, r2_temp_time = roundf(a_rh_time, b_rh_time, r2_rh_time, r2_temp_time)
a_percentile_time, b_percentile_time, r2_percentile_time = roundf(a_percentile_time, b_percentile_time, r2_percentile_time)

time_surface = vals(min(time), max(time)*2 if min(time)==1 else (max(time) - min(time)) * 2 + min(time) + 20, 200)
corrected_time_surface = time_surface if min(time)==1 else (time_surface - min(time)) / 20 + 1
temperature_surface = limit(np.array([predict_temp(t, M, C, D, w) for t in time_surface]), -10, 50)
rh_surface = limit(yaxb(a_rh_time, corrected_time_surface, b_rh_time), 0, 100)
correction_coefficient_surface = np.array([calculate_correction(t) for t in time_surface])
percentile_surface = limit(yaxb(a_percentile_time, corrected_time_surface, b_percentile_time), 0, 100)
SensorValue_surface = percentile_surface / 100

mintime = np.min(time_surface)
maxtime = np.max(time_surface)

fig = go.Figure()

ppm = Sensorppm(temperature, rh, interpolate(SensorValue, 0, 1, emf_max, emf_min), selected_gas, time, True)
false_ppm = Sensorppm(temperature, rh, interpolate(SensorValue, 0, 1, emf_max, emf_min), selected_gas, time, False)
fig.add_trace(go.Scatter(x=time, y=false_ppm, mode='markers', marker=dict(color="#636efa"), name=selected_gas))
ppm_surface = Sensorppm(temperature_surface, rh_surface, interpolate(SensorValue_surface, 0, 1, emf_max, emf_min), selected_gas, time_surface, True)
false_ppm_surface = Sensorppm(temperature_surface, rh_surface, interpolate(SensorValue_surface, 0, 1, emf_max, emf_min), selected_gas, time_surface, False)
fig.add_trace(go.Scatter(x=time_surface, y=false_ppm_surface, mode='lines', marker=dict(color="#636efa"), name=selected_gas))

mintemp = np.min(temperature_surface)
maxtemp = np.max(temperature_surface)
        
minrh = np.min(rh_surface)
maxrh = np.max(rh_surface)
        
mincr = np.min(correction_coefficient_surface)
maxcr = np.max(correction_coefficient_surface)
        
minppm = np.min(ppm_surface)
maxppm = np.max(ppm_surface)
    
xmin, xmax = mintemp, maxtemp
ymin, ymax = minrh, maxrh
zmin, zmax = minppm, maxppm

x_middle_min = (xmax-xmin)/4
x_middle_max = x_middle_min*3
x_middle = (xmax+xmin)/2

y_middle_min = (ymax-ymin)/4
y_middle_max = y_middle_min*3
y_middle = (ymax+ymin)/2

z_middle_min = (zmax-zmin)/4
z_middle_max = z_middle_min*3
z_middle = (zmax+zmin)/2

x_middle_min += xmin
x_middle_max += xmin
y_middle_min += ymin
y_middle_max += ymin
z_middle_min += zmin
z_middle_max += zmin

outer_cube = create_cube(center=(0, 0, 0), xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, zmin=zmin, zmax=zmax)
inner_cube = create_cube(center=(0, 0, 0), xmin=x_middle_min, xmax=x_middle_max, ymin=y_middle_min, ymax=y_middle_max, zmin=z_middle_min, zmax=z_middle_max)

def add_cubes_faces():
    add_cube_faces(fig, outer_cube, 'blue', "x")
    add_cube_faces(fig, inner_cube, 'red', "y")
    add_z_faces(fig, outer_cube, inner_cube, 'green', "z")

def add_cubes_edges():
    add_cube_edges(fig, outer_cube, 'blue', "x")
    add_cube_edges(fig, inner_cube, 'red', "y")
    
    for i in range(8):
        if i == 6 or i == 2: continue
        
        fig.add_trace(go.Scatter3d(x=[outer_cube[i, 0], inner_cube[i, 0]], y=[outer_cube[i, 1], inner_cube[i, 1]], z=[outer_cube[i, 2], inner_cube[i, 2]], mode='lines+text', line=dict(color='green', width=2), text=["z", "z"], textposition="middle center", name="z", hoverinfo='text+name', textfont=dict(size=15, color='green', weight='bold')))
    xgrid_lines = vals(x_middle_min, x_middle_max, 10)
    ygrid_lines = vals(y_middle_min, y_middle_max, 10)
    zgrid_lines = vals(z_middle_min, z_middle_max, 10)

    for g in xgrid_lines:
        fig.add_trace(go.Scatter3d(x=[g, g], y=[y_middle_min, y_middle_min], z=[z_middle_max, z_middle_min], mode='lines', line=dict(color='red', width=1), name="x", hoverinfo='none'))
        fig.add_trace(go.Scatter3d(x=[g, g], y=[y_middle_max, y_middle_min], z=[z_middle_min, z_middle_min], mode='lines+text', line=dict(color='red', width=1), text=[str(round2(interpolate(g, x_middle_min, x_middle_max, xmin, xmax)))], textposition="middle center", name="x", hoverinfo='text+name', textfont=dict(size=9, color='white')))

    for g in ygrid_lines:
        fig.add_trace(go.Scatter3d(x=[x_middle_min, x_middle_min], y=[g, g], z=[z_middle_max, z_middle_min], mode='lines', line=dict(color='red', width=1), name="y", hoverinfo='none'))
        fig.add_trace(go.Scatter3d(x=[x_middle_max, x_middle_min], y=[g, g], z=[z_middle_min, z_middle_min], mode='lines+text', line=dict(color='red', width=1), text=[str(round2(interpolate(g, y_middle_min, y_middle_max, ymin, ymax)))], textposition="middle center", name="y", hoverinfo='text+name', textfont=dict(size=9, color='white')))

    for g in zgrid_lines:
        fig.add_trace(go.Scatter3d(x=[x_middle_min, x_middle_min], y=[y_middle_max, y_middle_min], z=[g, g], mode='lines', line=dict(color='red', width=1), name="z", hoverinfo='none'))
        fig.add_trace(go.Scatter3d(x=[x_middle_max, x_middle_min], y=[y_middle_min, y_middle_min], z=[g, g], mode='lines+text', line=dict(color='red', width=1), text=[str(round2(interpolate(g, z_middle_min, z_middle_max, mincr, maxcr)))], textposition="middle center", name="z", hoverinfo='text+name', textfont=dict(size=9, color='white')))
        
    xvalues = [xmin, x_middle_min, x_middle_max, xmax]
    yvalues = [ymin, y_middle_min, y_middle_max, ymax]
    zvalues = [zmin, z_middle_min, z_middle_max, zmax]
    colors = ['purple', 'orange', 'purple']

    for i in range(3):
        fig.add_trace(go.Scatter3d(x=[xvalues[i], xvalues[i+1]], y=[y_middle, y_middle], z=[z_middle, z_middle], mode='lines+text', line=dict(color=colors[i], width=4), text=["x", "x"], textposition="middle center", name="x", hoverinfo='text+name', textfont=dict(size=15, color=colors[i], weight='bold')))
        fig.add_trace(go.Scatter3d(x=[x_middle, x_middle], y=[yvalues[i], yvalues[i+1]], z=[z_middle, z_middle], mode='lines+text', line=dict(color=colors[i], width=4), text=["y", "y"], textposition="middle center", name="y", hoverinfo='text+name', textfont=dict(size=15, color=colors[i], weight='bold')))
        fig.add_trace(go.Scatter3d(x=[x_middle, x_middle], y=[y_middle, y_middle], z=[zvalues[i], zvalues[i+1]], mode='lines+text', line=dict(color=colors[i], width=4), text=["z", "z"], textposition="middle center", name="z", hoverinfo='text+name', textfont=dict(size=15, color=colors[i], weight='bold')))

add_cubes_faces()
add_cubes_edges()

fig.add_trace(go.Scatter3d(
    x=temperature,
    y=rh,
    z=ppm,
    mode='markers',
    marker=dict(size=6, colorscale='Viridis', symbol='circle', color=time, cmin=min(time_surface), cmax=max(time_surface)),
    name='Real Datas',
    hoverinfo='x+y+z',
    hovertemplate=( 
        'SensorPpm (z): %{z}<br>' +
        'Time (w): %{customdata[0]:.4f}<br>' +
        'CorrectionCoefficient: %{customdata[3]:.4f}<br>' +
        'Temperature°C (x): %{customdata[1]:.4f}<br>' +
        'RH (y): %{customdata[2]:.4f}'
    ),
    customdata=np.stack((time, temperature, rh, correction_coefficient), axis=-1)
))

fig.add_trace(go.Scatter3d(
    x=temperature_surface,
    y=rh_surface,
    z=ppm_surface,
    mode='lines',
    line=dict(width=10, colorscale='Viridis', color=time_surface, cmin=min(time_surface), cmax=max(time_surface), colorbar=dict(title='Time(w)')),
    name='Regression Curves',
    hoverinfo='x+y+z',
    hovertemplate=( 
        'SensorPpm (z): %{customdata[4]:.4f}<br>' +
        'Time (w): %{customdata[0]:.4f}<br>' +
        'CorrectionCoefficient: %{customdata[3]:.4f}<br>' +
        'Temperature°C (x): %{customdata[1]:.4f}<br>' +
        'RH (y): %{customdata[2]:.4f}'
    ),
    customdata=np.stack((time_surface, temperature_surface, rh_surface, correction_coefficient_surface, ppm_surface), axis=-1)
))

fig.add_trace(go.Scatter3d(
    x=interpolate(temperature, xmin, xmax, x_middle_min, x_middle_max),
    y=interpolate(rh, ymin, ymax, y_middle_min, y_middle_max),
    z=interpolate(correction_coefficient, mincr, maxcr, z_middle_min, z_middle_max),
    mode='markers',
    marker=dict(size=6, colorscale='Viridis', symbol='circle', color=time, cmin=min(time_surface), cmax=max(time_surface)),
    name='Correction Coefficient Datas',
    hoverinfo='x+y+z',
    hovertemplate=( 
        'CorrectionCoefficient: %{customdata[3]:.4f}<br>' +
        'Time (w): %{customdata[0]:.4f}<br>' +
        'Temperature°C (x): %{customdata[1]:.4f}<br>' +
        'RH (y): %{customdata[2]:.4f}'
    ),
    customdata=np.stack((time, temperature, rh, correction_coefficient), axis=-1)
))

fig.add_trace(go.Scatter3d(
    x=interpolate(temperature_surface, xmin, xmax, x_middle_min, x_middle_max),
    y=interpolate(rh_surface, ymin, ymax, y_middle_min, y_middle_max),
    z=interpolate(correction_coefficient_surface, mincr, maxcr, z_middle_min, z_middle_max),
    mode='lines',
    line=dict(width=10, colorscale='Viridis', color=time_surface, cmin=min(time_surface), cmax=max(time_surface)),
    name='Correction Coefficient Curves',
    hoverinfo='x+y+z',
    hovertemplate=( 
        'CorrectionCoefficient: %{customdata[3]:.4f}<br>' +
        'Time (w): %{customdata[0]:.4f}<br>' +
        'Temperature°C (x): %{customdata[1]:.4f}<br>' +
        'RH (y): %{customdata[2]:.4f}'
    ),
    customdata=np.stack((time_surface, temperature_surface, rh_surface, correction_coefficient_surface), axis=-1)
))

cam1 = 1.75
cam2 = function(1.09375, differentiation(a_rh_time, maxtime, b_rh_time))
cam3 = function(0.088, differentiation(a_percentile_time, maxtime, b_percentile_time))

fig.update_layout(
    scene=dict(
        camera=dict(eye=dict(x=cam1, y=cam2, z=cam3)),
        xaxis_title=f"X: Temp (°C) R² = {r2_temp_time}",
        yaxis_title=f"Y: RH (%) R² = {r2_rh_time}",
        zaxis_title=f"Z: {selected_gas} (ppm) R² = {r2_percentile_time}",
        xaxis=dict(range=[xmin, xmax], nticks=10, showbackground=False),
        yaxis=dict(range=[ymin, ymax], nticks=10, showbackground=False),
        zaxis=dict(range=[zmin, zmax], nticks=10, showbackground=False),
        aspectmode='cube',
        domain=dict(x=[0.01, 0.51])
    ),
    showlegend=False,
    coloraxis=dict(colorscale='Viridis'),
    template='plotly_dark',
    margin=dict(t=20, b=20, l=20, r=20),
    xaxis=dict(title='X: Time (w)', domain=[0.52, 1]),
    yaxis=dict(title='Y: SensorPpm (z)', domain=[0.07, 0.82])
)

fig.add_annotation(text="4D Slope Estimation", x=0.18, y=0.98, showarrow=False, font=dict(size=19), xref="paper", yref="paper")
fig.add_annotation(text=f"MG811 {selected_gas} Time-based PPM Calculation", x=0.89, y=0.98, showarrow=False, font=dict(size=19), xref="paper", yref="paper")

fig.write_html(f"MG811_{selected_gas}_4D_Slope_Estimation.html")

print(f"Gas: {selected_gas} | R²_Per={r2_percentile_time} | R²_Temp={r2_temp_time} | R²_Rh={r2_rh_time}")
with open("DataReport.txt", "a") as f:
    f.write("\n")
    f.write(f"Gas: {selected_gas} | R²_Per={r2_percentile_time} | R²_Temp={r2_temp_time} | R²_Rh={r2_rh_time}\n")

for t_val, temp_val, rh_val, sv_val, corr_val in zip(time, temperature, rh, SensorValue, correction_coefficient):
    EMF_val = interpolate(sv_val, 0, 1, emf_max, emf_min)
    ppm_val = Sensorppm(temp_val, rh_val, EMF_val, selected_gas, t_val, True)
    print(f"t={t_val:.4f}s Sensor={sv_val:.4f} temp={temp_val:.4f} rh={rh_val:.4f} corr={corr_val:.4f} EMF={EMF_val:.4f} ppm={ppm_val:.4f}")
    with open("DataReport.txt", "a") as f:
        f.write(f"t={t_val:.4f}s Sensor={sv_val:.4f} temp={temp_val:.4f} rh={rh_val:.4f} corr={corr_val:.4f} EMF={EMF_val:.4f} ppm={ppm_val:.4f}\n")
print("")

with open("EstimationReport.txt", "a") as f:
    f.write("\n")
    f.write(f"Gas: {selected_gas} | R²_Per={r2_percentile_time} | R²_Temp={r2_temp_time} | R²_Rh={r2_rh_time}\n")

for t_val, temp_val, rh_val, sv_val, corr_val in zip(time_surface, temperature_surface, rh_surface, SensorValue_surface, correction_coefficient_surface):
    EMF_val = interpolate(sv_val, 0, 1, emf_max, emf_min)
    ppm_val = Sensorppm(temp_val, rh_val, EMF_val, selected_gas, t_val, True)
    print(f"t={t_val:.4f}s Sensor={sv_val:.4f} temp={temp_val:.4f} rh={rh_val:.4f} corr={corr_val:.4f} EMF={EMF_val:.4f} ppm={ppm_val:.4f}")
    with open("EstimationReport.txt", "a") as f:
        f.write(f"t={t_val:.4f}s Sensor={sv_val:.4f} temp={temp_val:.4f} rh={rh_val:.4f} corr={corr_val:.4f} EMF={EMF_val:.4f} ppm={ppm_val:.4f}\n")
print("")
