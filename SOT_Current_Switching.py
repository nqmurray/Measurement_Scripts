import os
import sys
import time
import importlib
import matplotlib.animation as animation
from GUIBaseClass import GUIBase
from GUIBaseClass import animate_plot

sys.path.append(os.getcwd())  # add path to import dictionary
defaults = importlib.import_module('FieldControls',
                                   os.getcwd())  # import dictionary based on the name of the computer
mag_settings = getattr(defaults, os.environ.get('USERNAME'))
res_settings = getattr(defaults, os.environ.get('USERNAME') + '_RESOURCES')


def fix_param1(index, output, delay, resources, kwargs):
    if index == 0:
        resources['keithley_2000'].auto_range()
        resources['keithley_2000'].mode = 'voltage'
        resources['keithley_2400'].apply_current(
            compliance_voltage=200)
        resources['keithley_2400'].auto_range_source()
    setattr(resources['dsp_lockin'], kwargs['Hx Dac'],
            output / float(kwargs['Hx Conversion']))
    time.sleep(delay)


def fix_param2(output, delay, resources, kwargs):
    pass


def measure_y(output, delay, resources, fix1_output, fix2_output, kwargs):
    x2 = resources['gaussmeter'].measure()
    resources['keithley_2400'].source_current = output * 10e-3  # mA
    time.sleep(fix2_output)  # write pulse time
    resources['keithley_2400'].source_current = 0  # turn off current
    time.sleep(float(kwargs['write-read delay']))
    resources['keithley_2400'].source_current = float(
        kwargs['sensing current']) * 10e-3  # mA
    time.sleep(float(kwargs['read pulse width']))
    y = 0.0
    for i in range(int(kwargs['averages'])):
        y += resources['keithley_2000'].voltage
        y = (y * 1000 / int(kwargs['averages'])) / float(
            kwargs['sensing current'])
    resources['keithley_2400'].source_current = 0  # turn off current
    return output, y, x2


def main():
    resource_dict = {
        'dsp_lockin': res_settings['dsp_lockin'],
        'keithley_2000': res_settings['keithley_2000'],
        'keithley_2400': res_settings['keithley_2400'],
        'gaussmeter': res_settings['gaussmeter'],
    }

    graph_dict = {
        "gui_title": 'SOT_Current_Switching',
        "graph_title": "Resistance (Ohm) vs. Current (mA)",
        "x_title": "Pulse Current (mA)",
        "y_title": "Resistance (Ohm)",
        "x2_title": "Gaussmeter (Oe)",
        "fixed_param_1": "Hx Field (Oe)",
        "fixed_param_2": "Pulse Width (s)"
    }

    loop_commands = {
        'fixed_func_1': 'fix_param1',  # name of fixed parameter one function
        'fixed_func_2': 'fix_param2',
        'measure_y_func': 'measure_y',
        # directory from which the preceeding modules will be imported from
        'module_path': os.getcwd(),
        # name of the file to get the functions from
        'module_name': 'SOT_Current_Switching',
        'fix1_start': 'hx start',
        'fix1_stop': 'hx stop',
        'fix1_step': 'hx step',
        'fix2_start': 'pulse width start',
        'fix2_stop': 'pulse width stop',
        'fix2_step': 'pulse width step',
        'x_start': 'current start',
        'x_stop': 'current stop',
        'x_step': 'current step',
        'MOKE': False
    }

    controls_dict1 = {
        "title": "Magnet Controls",
        "hx start": 0,
        "hx stop": 0,
        "hx step": 0,
    }

    controls_dict2 = {
        "title": "Current Controls",
        "current start": -6.0,
        "current stop": 6.0,
        "current step": 0.5,
        "pulse width start": 0.05,
        "pulse width end": 0.05,
        "pulse width step": 0,
        "sensing current": 0.5,
        "write-read delay": 0.1,  # delay between write and read
        # how long after read current sourced is read voltage measured
        "read pulse width": 0.05,
        "averages": 1
    }

    lockin_controls = {
        "title": "Lockin",
        'Hx Dac': mag_settings['Hx Dac'],
        'Hz Dac': mag_settings['Hz Dac'],
        'Hx Conversion': mag_settings['Hx Conversion'],
        'Hz Conversion': mag_settings['Hz Conversion'],
        'Hx Max': mag_settings['Hx Max'],
        'Hz Max': mag_settings['Hz Max']
    }

    measurement_gui = GUIBase(graph_dict, resource_dict, loop_commands,
                              controls_dict1, controls_dict2, lockin_controls)
    ani = animation.FuncAnimation(
        measurement_gui.fig, animate_plot, interval=200, fargs=[measurement_gui.ax, measurement_gui.graph,
                                                                measurement_gui.results, measurement_gui.progress_bar, measurement_gui.time_var])
    measurement_gui.mainloop()


if __name__ == '__main__':
    main()
