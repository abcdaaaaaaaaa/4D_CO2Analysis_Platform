import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

x_points = np.array([0, 1, 2, 3, 5, 7, 9, 11, 13, 15, 17, 19])
y_points = np.array([325.79, 325.79, 326.15, 325.05, 288.06, 285.86, 285.86, 285.86, 288.06, 319.93, 324.87, 324.87])

def interpolate(x, x0, x1, y0, y1):
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)

def inverseyaxb(valuea, value, valueb):
    return np.power(value / valuea, 1 / valueb)

def time(x):
    y = np.zeros_like(x, dtype=float)
    for i, xi in enumerate(x):
        if 0 <= xi <= 1:
            y[i] = 325.79
        elif 1 < xi <= 2:
            y[i] = interpolate(xi, 1, 2, 325.79, 326.15)
        elif 2 < xi <= 3:
            y[i] = interpolate(xi, 2, 3, 326.15, 325.05)
        elif 3 < xi <= 5:
            y[i] = interpolate(xi, 3, 5, 325.05, 288.06)
        elif 5 < xi <= 7:
            y[i] = 285.86 + (3.2 * (xi - 4) ** -1.0587 - 1)
        elif 7 < xi <= 11:
            y[i] = 285.86
        elif 11 < xi <= 13:
            y[i] = 285.86 + (3.2 * (14 - xi) ** -1.0587 - 1)
        elif 13 < xi <= 15:
            y[i] = interpolate(xi, 13, 15, 288.06, 319.93)
        elif 15 < xi <= 17:
            y[i] = 324.87 - (5.94 * (xi - 14) ** -1.6218 - 1)
        elif 17 < xi <= 19:
            y[i] = 324.87
        elif 19 < xi <= 20:
            y[i] = interpolate(xi, 19, 20, 324.87, 325.79)
        else:
            y[i] = np.nan
    return y

fig = make_subplots(rows=1, cols=2, subplot_titles=("Response and Resume Curve (3500ppmCO2)", "Change of Correction Coefficient with Time"))

intervals = [(0,1),(1,2),(2,3),(3,5),(5,7),(7,11),(11,13),(13,15),(15,17),(17,19),(19,20)]
for start, end in intervals:
    x_line = np.linspace(start, end, 100)
    y_line = time(x_line)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', line=dict(color='blue', width=2), showlegend=False, hoverinfo='x+y'), row=1, col=1)

fig.add_trace(go.Scatter(x=x_points, y=y_points, mode='markers', marker=dict(color='blue', size=10, symbol='diamond'), showlegend=False, hoverinfo='text', hovertext=[f'x={x:.2f}, y={y:.2f}' for x,y in zip(x_points,y_points)]), row=1, col=1)

t = np.linspace(0, 20, 200)
temp_corr_a = interpolate(28, 20, 30, 523.094, 527.0596)
temp_corr_b = interpolate(28, 20, 30, -0.0863, -0.0879)
a_corr = (temp_corr_a + 538.2376 + 499.0689) / 3
b_corr = (temp_corr_b + -0.0733 + -0.0722) / 3
correction = 3500 / inverseyaxb(a_corr, time(t), b_corr)
fig.add_trace(go.Scatter(x=t, y=correction, mode='lines', line=dict(color='red', width=2), showlegend=False, hoverinfo='x+y'), row=1, col=2)

fig.update_layout(
    xaxis=dict(title='(s)', tickmode='array', tickvals=[0, 5, 10, 15, 20], range=[0, 20]),
    xaxis2=dict(title='(s)', tickmode='array', tickvals=[0, 5, 10, 15, 20], range=[0, 20]),
    yaxis=dict(title='EMF (mV)', tickmode='array', tickvals=[280, 290, 300, 310, 320, 330], range=[280, 330]),
    yaxis2=dict(title='Correction Coefficient'),
    template='plotly_dark'
)

fig.write_html("Response and Resume Curve.html")
