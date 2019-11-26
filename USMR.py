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


# set Hx field, wait for delay
def fix_param1(index, output, delay, resources, kwargs):
    if index == 0:
        resources['keithley_2000'].auto_range()
        resources['keithley_2000'].mode = 'voltage'
        resources['keithley_2400'].apply_current(
            compliance_voltage=200)
        resources['keithley_2400'].auto_range_source()
    setattr(resources['dsp_lockin'], kwargs['Hz Dac'],
            output / float(kwargs['Hz Conversion']))
    time.sleep(delay)


# for USMR keithley2400 set in measure_y
def fix_param2(output, delay, resources, kwargs):
    pass


# set Hz field, wait for delay, measure Hz field, measure voltage, take average return resistance
def measure_y(output, delay, resources, fix2, kwargs):
    setattr(resources['dsp_lockin'], kwargs['Hx Dac'],
            output / float(kwargs['Hx Conversion']))  # obj, name, value
    time.sleep(delay)
    x2 = resources['gaussmeter'].measure()
    resources['keithley_2400'].source_current = -fix2 * 10e-3  # set to mA
    time.sleep(float(kwargs['read delay']))
    y_neg = 0.0
    for i in range(int(kwargs['averages'])):
        y_neg += resources['keithley_2000'].voltage
    resources['keithley_2400'].source_current = fix2 * 10e-3  # set to mA
    time.sleep(float(kwargs['read delay']))
    y_pos = 0.0
    for i in range(int(kwargs['averages'])):
        y_pos += resources['keithley_2000'].voltage
    return float(output), (abs(y_neg) - abs(y_pos)) * 1000 / (fix2 * int(kwargs['averages'])), x2


def main():
    resource_dict = {
        'dsp_lockin': res_settings['dsp_lockin'],
        'keithley_2000': res_settings['keithley_2000'],
        'keithley_2400': res_settings['keithley_2400'],
        'gaussmeter': res_settings['gaussmeter'],
    }

    graph_dict = {
        # i.e. AHE Measurement (should be the measurement type)
        "gui_title": 'USMR Measurement',
        # Resistance vs. Hx
        "graph_title": "Avg Abs Resistance (Ohm) vs Hx (Oe)",
        "x_title": "Applied Field (Oe)",  # i.e. Applied Field (Oe)
        # i.e. Hall Resistance (Ohm)
        "y_title": "Realtime Avg Resistance (Ohm)",
        # for gaussmeter readings, leave blank if no gaussmeter used
        "x2_title": "Gaussmeter (Oe)",
        "fixed_param_1": "Hz (Oe)",  # i.e. Hx 100 (Oe)
        "fixed_param_2": "Current (mA)"  # i.e. Current 1.9 (mA)
    }

    loop_commands = {
        'fixed_func_1': 'fix_param1',  # name of fixed parameter one function
        'fixed_func_2': 'fix_param2',
        'measure_y_func': 'measure_y',
        # directory from which the preceeding modules will be imported from
        'module_path': os.getcwd(),
        # name of the file to get the functions from
        'module_name': 'USMR',
        'fix1_start': 'hz start',
        'fix1_stop': 'hz stop',
        'fix1_step': 'hz step',
        'fix2_start': 'current start',
        'fix2_stop': 'current stop',
        'fix2_step': 'current step',
        'x_start': 'hx start',
        'x_stop': 'hx stop',
        'x_step': 'hx step',
        'MOKE': False
    }

    controls_dict1 = {
        "title": "Magnet Controls",
        "hx start": -100,
        "hx stop": 100,
        "hx step": 5,
        "hz start": 0,
        "hz stop": 0,
        "hz step": 0,
    }

    controls_dict2 = {
        "title": "Keithley 2400",
        "current start": 0,
        "current stop": 0.5,
        "current step": 0,
        "read delay": 0.4,
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
        measurement_gui.fig, animate_plot, interval=200, fargs=[measurement_gui.ax, measurement_gui.graph, measurement_gui.results, measurement_gui.progress_bar, measurement_gui.time_var])
    measurement_gui.mainloop()


if __name__ == '__main__':
    main()
