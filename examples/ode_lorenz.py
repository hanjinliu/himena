import scipy.integrate
import numpy as np
from himena import WidgetDataModel, Parametric, new_window
from himena.plugins import register_function, configure_gui
import himena.standards.plotting as hplt

# This example adds a command "ODE" to the "Plugins" menu.
# The output parametric window has a "preview" button, which shows the real time plot
# of the Lorenz attractor.

def lorenz(vec, time, p, r, b):
    x, y, z = vec
    dxdt = -p * x + p * y
    dydt = -x * z + r * x - y
    dzdt = x * y - b * z
    return [dxdt, dydt, dzdt]

@register_function(command_id="simulate-ode", title="ODE")
def f() -> Parametric:
    t = np.linspace(0, 100, 10000)
    @configure_gui(preview=True)
    def run(p=10.0, r=10.0, b=3.0):
        initval= [0.1, 0.1, 0.1]
        result=scipy.integrate.odeint(lorenz, initval, t, args=(p, r, b))
        fig = hplt.figure_3d()
        fig.axes.plot(result[:,0],result[:,1],result[:,2], width=0.6, color="red")
        return WidgetDataModel(value=fig, type="plot")
    return run

if __name__ == "__main__":
    ui = new_window()
    ui.show(run=True)
