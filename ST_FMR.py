import os
import sys
import time
import importlib
import matplotlib.animation as animation
from pymeasure import instruments
from GUIBaseClass import GUIBase
from GUIBaseClass import animate_plot

sys.path.append(os.getcwd())  # add path to import dictionary
defaults = importlib.import_module('FieldControls',
                                   os.getcwd())  # import dictionary based on the name of the computer
mag_settings = getattr(defaults, os.environ.get('USERNAME'))
res_settings = getattr(defaults, os.environ.get('USERNAME') + '_RESOURCES')


def fix_param1(index, output, delay, resources, kwargs):
    if index == 0:  # initialize machines first time around
        resources['sig_gen_8257'].enable()
        resources['sig_gen_8257'].enable_modulation()
        resources['sig_gen_8257'].enable_amplitude_modulation()
        resources['sig_gen_8257'].enable_low_freq_out()
        resources['sig_gen_8257'].amplitude_source = 'internal'
        resources['sig_gen_8257'].low_freq_out_source = 'internal'
        resources['sig_gen_8257'].amplitude_depth = 99.0
        resources['dsp_lockin'].reference = 'external front'
        resources['dsp_lockin'].sensitivity = kwargs['Sensitivity']
        resources['sig_gen_8257'].internal_frequency = float(
            kwargs['modulation frequency'])
        resources['sig_gen_8257'].low_freq_out_amplitude = float(
            kwargs['signal voltage'])
    resources['sig_gen_8257'].power = output


def fix_param2(output, delay, resources, kwargs):
    resources['sig_gen_8257'].frequency = output * 10**9


def measure_y(output, delay, resources, fix1_output, fix2_output, kwargs):
    setattr(resources['dsp_lockin'], kwargs['Hx Dac'],
            output / float(kwargs['Hx Conversion']))
    time.sleep(delay)
    y = 0.0
    for i in range(int(kwargs['averages'])):
        y += resources['dsp_lockin'].x
    y = (y / int(kwargs['averages']))

    return output, y, 0


def main():
    resource_dict = {
        'dsp_lockin': res_settings['dsp_lockin'],
        'sig_gen_8257': res_settings['sig_gen_8257'],
    }

    graph_dict = {
        "gui_title": 'ST-FMR',
        "graph_title": "Graph Title",
        "x_title": "Applied Field",
        "y_title": "Lockin Voltage",
        "x2_title": "",
        "fixed_param_1": "Power (dBm)",
        "fixed_param_2": "Frequency (Ghz)"
    }

    loop_commands = {
        'fixed_func_1': 'fix_param1',  # name of fixed parameter one function
        'fixed_func_2': 'fix_param2',
        'measure_y_func': 'measure_y',
        # directory from which the preceeding modules will be imported from
        'module_path': os.getcwd(),
        # name of the file to get the functions from
        'module_name': 'ST_FMR',
        'fix1_start': 'power start',
        'fix1_stop': 'power stop',
        'fix1_step': 'power step',
        'fix2_start': 'frequency start',
        'fix2_stop': 'frequency stop',
        'fix2_step': 'frequency step',
        'x_start': 'hx start',
        'x_stop': 'hx stop',
        'x_step': 'hx step',
        'MOKE': False
    }

    controls_dict1 = {
        "title": "Magnet Controls",
        "hx start": 1000,
        "hx stop": -1000,
        "hx step": -5,
    }

    controls_dict2 = {
        "title": "Signal Generator Controls",
        "power start": 5.0,
        "power stop": 10,
        "power step": 1,
        "frequency start": 4.0,
        "frequency stop": 5.0,
        "frequency step": 0,
        "modulation frequency": 500,
        "signal voltage": 0.7
    }

    lockin_controls = {
        "title": "Lockin",
        "Sensitivity": '10uV',
        "averages": 1,
        'Hx Dac': mag_settings['Hx Dac'],
        'Hx Conversion': mag_settings['Hx Conversion'],
        'Hx Max': mag_settings['Hx Max'],

    }

    measurement_gui = GUIBase(graph_dict, resource_dict, loop_commands,
                              controls_dict1, controls_dict2, lockin_controls)
    ani = animation.FuncAnimation(
        measurement_gui.fig, animate_plot, interval=200, fargs=[measurement_gui.ax, measurement_gui.graph, measurement_gui.results, measurement_gui.progress_bar, measurement_gui.time_var])
    measurement_gui.mainloop()


if __name__ == '__main__':
    main()
