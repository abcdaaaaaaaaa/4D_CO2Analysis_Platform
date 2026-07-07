import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from scipy.optimize import curve_fit

def print_gas_table(gas_data, typ):
    if typ == 1:
        print()
        print("for ppm = a*EMF^b:")
        print()
        print("Gas    | a       | b")
        for gas, (a, b) in gas_data1.items():
            print(f"{gas.ljust(7)}| {str(a).ljust(8)}| {str(b).ljust(7)}")
        print()
    if typ == 2:
        print("for ppm = 10^[(log10(EMF)-b)/m]:")
        print()
        print("Gas    | m       | b")
        for gas, (m, b) in gas_data2.items():
            print(f"{gas.ljust(7)}| {str(m).ljust(8)}| {str(b).ljust(7)}")
        print()
            
sensor_name = 'MG811'

gases = {}

gas_data1 = {}
gas_data2 = {}

colornum = ListNumber = 0

fig = make_subplots(subplot_titles=["New Curve"])


while True:
    gas_name = input("Enter the gas name (or press 'Enter' to finish): ")
    if gas_name == '':
        break
    else:
        ListNumber += 1

    values = []
    values_input = input(f"Enter (x, y) values for {gas_name} as [(x1, y1), (x2, y2), ...]: ")
    try:
        values = eval(values_input)
        x_values = [value[0] for value in values]
        y_values = [value[1] for value in values]

        x = np.array(x_values)
        y = np.array(y_values)

        def func(x, a, b):
            return a * np.power(x, b)

        popt, pcov = curve_fit(func, x, y)

        residuals = y - func(x, *popt)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1 - (ss_res / ss_tot)

        gases[gas_name] = {'a': popt[0], 'b': popt[1], 'R_squared': r_squared}
        a_rounded = round(popt[0], 4)
        b_rounded = round(popt[1], 4)
        b2 = np.log10(popt[0])
        b2_rounded = round(b2, 4)

        gas_data1[gas_name] = (a_rounded, b_rounded)
        gas_data2[gas_name] = (b_rounded, b2_rounded)

        print(f"logm for {gas_name}: {b_rounded} logb for {gas_name}: {b2_rounded}")
        print(f"valuea for {gas_name}: {a_rounded}, valueb for {gas_name}: {b_rounded}")
        print(f"R-squared for {gas_name}: {r_squared:.4f}")

        new_x = np.linspace(min(x_values), max(x_values), 100)
        new_y = a_rounded * np.power(new_x, b_rounded)

        colornum += 1

        match colornum:
            case 1: hexcolor = "#40E0D0"  # Turquoise
            case 2: hexcolor = "#87CEFA"  # Light Sky Blue
            case 3: hexcolor = "#007FFF"  # Vivid Sky Blue
            case 4: hexcolor = "#CCCCFF"  # Periwinkle
            case 5: hexcolor = "#87CEEB"  # Sky Blue
            case 6: hexcolor = "#6A5ACD"  # Slate Blue
            case 7: hexcolor = "#4B0082"  # Indigo
            case 8: hexcolor = "#FFA500"  # Orange
            case 9: hexcolor = "#4169E1"  # Royal Blue
            case 10: hexcolor = "#0F52BA" # Sapphire
            case _: hexcolor = "Unknown"
    
        fig.add_trace(go.Scatter(x=x, y=y, mode='markers', name=f'New Datas for {gas_name} (R²={r_squared:.4f})', marker=dict(color=hexcolor)))
        fig.add_trace(go.Scatter(x=new_x, y=new_y, mode='lines', name=f'New Curve: y = {a_rounded} * x^{b_rounded}', marker=dict(color=hexcolor)))

    except Exception as e:
        print("An error occurred:", e)
        print("Invalid input format. Please enter the values as [(x1, y1), (x2, y2), ...]")

print_gas_table(gas_data1, 1)
print_gas_table(gas_data2, 2)

fig.update_layout(
    title=f'Regression Curves for {sensor_name}',
    autosize=True,  
    template='plotly_white',
    showlegend=True
)

fig.update_xaxes(title_text="Ppm (y)")
fig.update_yaxes(title_text="EMF (x)")

fig.show()
fig.write_html(f"{sensor_name}_gas_curves.html")

