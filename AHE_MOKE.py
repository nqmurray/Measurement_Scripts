import os
import sys
import importlib
import time
import matplotlib.animation as animation
import mss
from PIL import Image
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
            output / float(kwargs['Hx Conversion']))  # obj, name, value
    time.sleep(delay)


def fix_param2(output, delay, resources, kwargs):
    resources['keithley_2400'].source_current = output * 10e-3  # set to mA


def measure_y(output, delay, resources, points, fix1_output, fix2_output, kwargs):
    # takes the dictionary passed in and measures the rgb values for each pixel in the given
    def image_rgb(point_dict):

        with mss.mss() as sct:
            sct_img = sct.grab(point_dict)
            img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)

        r, g, b = 0, 0, 0

        # count up the rgb pixels
        for x in range(img.size[0]):  # image width
            for y in range(img.size[1]):  # image height
                r += img.getpixel((x, y))[0]
                g += img.getpixel((x, y))[1]
                b += img.getpixel((x, y))[2]

        return (r + g + b) / (img.size[0] * img.size[1])

    setattr(resources['dsp_lockin'], kwargs['Hz Dac'],
            output / float(kwargs['Hz Conversion']))
    time.sleep(delay)
    x2 = resources['gaussmeter'].measure()
    y = image_rgb(points)
    return float(output), y, x2


def main():  # test version of the GUI_base and animation
    # test dictionary for settings
    resource_dict = {
        'dsp_lockin': res_settings['dsp_lockin'],
        'keithley_2000': res_settings['keithley_2000'],
        'keithley_2400': res_settings['keithley_2400'],
        'gaussmeter': res_settings['gaussmeter'],
    }

    graph_dict = {
        # i.e. AHE Measurement (should be the measurement type)
        "gui_title": 'AHE_MOKE',
        "graph_title": "Realtime MOKE Signal vs. Applied Field",  # Resistance vs. Hx
        "x_title": "Applied Field (Oe)",  # i.e. Applied Field (Oe)
        "y_title": "MOKE Signal (rgb)",  # i.e. Hall Resistance (Ohm)
        "x2_title": "Gaussmeter (Oe)",  # for gaussmeter readings, leave blank if no gaussmeter used
        "fixed_param_1": "Hx Field (Oe)",  # i.e. Hx 100 (Oe)
        "fixed_param_2": "Current (mA)"  # i.e. Current 1.9 (mA)
    }

    loop_commands = {
        'fixed_func_1': 'fix_param1',  # name of fixed parameter one function
        'fixed_func_2': 'fix_param2',
        'measure_y_func': 'measure_y',
        # directory from which the preceeding modules will be imported from
        'module_path': os.getcwd(),
        # name of the file to get the functions from
        'module_name': 'AHE_MOKE',
        'fix1_start': 'hx start',
        'fix1_stop': 'hx stop',
        'fix1_step': 'hx step',
        'fix2_start': 'current start',
        'fix2_stop': 'current stop',
        'fix2_step': 'current step',
        'x_start': 'hz start',
        'x_stop': 'hz stop',
        'x_step': 'hz step',
        'MOKE': True
    }

    controls_dict1 = {
        "title": "Magnet Controls",
        "hx start": 0,
        "hx stop": 0,
        "hx step": 0,
        "hz start": -100,
        "hz stop": 100,
        "hz step": 5,
    }

    controls_dict2 = {
        "title": "Current Controls",
        "current start": 0,
        "current stop": 0,
        "current step": 0.5
    }

    lockin_controls = {
        "title": "Lockin",
        'Hx Dac': mag_settings['Hx DAC'],
        'Hz Dac': mag_settings['Hz DAC'],
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
