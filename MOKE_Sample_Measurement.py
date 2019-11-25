import os
import sys
import importlib
import time
import matplotlib.animation as animation
import mss
from PIL import Image
from random import randint
from GUIBaseClass import GUIBase
from GUIBaseClass import animate_plot

"""
Function is passed in the iterated value (output) from the array built with fix1 (loop control),
the delay time returned from the charging delay fucntion, and the dictionary of resources that are available.
For the measure_y function, return x, y, x2 values.  If x2 is not used, return won't be saved.

These functions can do any of the following:
    pass - essentially ignoring the call
    take a instrument from the resources dictionary and set it to a value
    i.e. resources['dsp_lockin'].dac1 = 10
    any other instrument related settings, turn on/off/measure/etc

Furthermore these functions need to be defined outside of main(). They names of the functions will be passed into
the MeasurementClass where they will be imported.  This is done because the measurement class is a child process and
functions are not easily pickled in python.
"""

sys.path.append(os.getcwd())  # add path to import dictionary
mag_settings = importlib.import_module(os.environ.get('USERNAME'),
                                       os.getcwd())  # import dictionary based on the name of the computer


def fix_param1(output, delay, resources, kwargs):
    time.sleep(delay)


def fix_param2(output, delay, resources, kwargs):
    time.sleep(0.01)


def measure_y(output, delay, resources, points, fix2, kwargs):
    time.sleep(0.01)
    return float(output), image_rgb(points), delay

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


def main():  # test version of the GUI_base and animation
    # test dictionary for settings
    resource_dict = {
        'dsp_lockin': 'GPIB0::10::INSTR',
        'keithley_2000': 'GPIB0::16::INSTR',
        'keithley_2400': 'GPIB0::20::INSTR',
        'gaussmeter': 'GPIB0::7::INSTR',
        'sig_gen_8257': 'GPIB0::19::INSTR',
    }

    graph_dict = {
        # i.e. AHE Measurement (should be the measurement type)
        "gui_title": 'TEST GUI',
        "graph_title": "Graph Title",  # Resistance vs. Hx
        "x_title": "X Axis",  # i.e. Applied Field (Oe)
        "y_title": "Y Axis",  # i.e. Hall Resistance (Ohm)
        "x2_title": "",  # for gaussmeter readings, leave blank if no gaussmeter used
        "fixed_param_1": "Fixed 1 (Oe)",  # i.e. Hx 100 (Oe)
        "fixed_param_2": "Fixed 2 (mA)"  # i.e. Current 1.9 (mA)
    }

    """
    This dictionary offers the user specific yet flexible control of the measurement loop.  The measurement loop
    is comprised of three nested for loops that each call a unique function defined at the beginning of this file.
    In psuedo code:
    for fix1 loop:
        fixed1func()
        for fix2 loop:
            fixed2func()
            for meas y loop():
                measy()
    The GUIBase and Measurement method automatically manage array creation, save functions, GUI commands, graphing
    and resource control/release.  In the loop command dictionary the user passes the name of three functions that run
    for each section, which should be defined at the top of this file.  They are imported from the path and with the module name.
    Finally the loop arrays will be built using the values associated with the start, stop, step keys for each loop.
    As an example, if 'fix1_stop': 'hx stop' is a key,value pair, the instance of the measurement class will look for the
    value given by kwarg['hx stop'] and set that as the np.array(,stop,) value.
    """
    loop_commands = {
        'fixed_func_1': 'fix_param1',  # name of fixed parameter one function
        'fixed_func_2': 'fix_param2',
        'measure_y_func': 'measure_y',
        # directory from which the preceeding modules will be imported from
        'module_path': os.getcwd(),
        # name of the file to get the functions from
        'module_name': 'Sample_Measurement',
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

    """
    The following dictionaries are passed in as *args, meaning there can be a variable number.  The key,value combos
    for each individual dictionary are autogenerated in the GUIBaseClass and the value becomes a corresponding tkinter widgit.
    These key,value combos are then passed to the measurement class when the measure button is pressed (note that values are passed
    as value.get()).  The arrays generated for the three measurement for loops are set by the loop commands dictionary above.
    """

    controls_dict1 = {
        "title": "Magnet Controls",
        "hx start": 0,
        "hx stop": 2,
        "hx step": 1,
        "hz start": -100,
        "hz stop": 100,
        "hz step": 1,
        "averages": 1
    }

    controls_dict2 = {
        "title": "Current Controls",
        "current start": 1,
        "current stop": 2,
        "current step": 0.5
    }

    lockin_controls = {
        "title": "Lockin",
        "Sensitivity": '10uV',
        "Mode": '1st',
        "Frequency": 100,
        "Signal": 1,
        'Hx Dac': mag_settings['Hx DAC'],
        'Hz Dac': mag_settings['Hz DAC'],
        'Hx Conversion': mag_settings['Hx Conversion'],
        'Hz Conversion': mag_settings['Hz Conversion'],
        'Hx Max': mag_settings['Hx Conversion'],
        'Hz Max': mag_settings['Hz Conversion']
    }

    """
    Below are the three lines of code that create an instance of the GUIBase, animation function
    and then start the GUIBase.
    """

    measurement_gui = GUIBase(graph_dict, resource_dict, loop_commands,
                              controls_dict1, controls_dict2, lockin_controls)
    ani = animation.FuncAnimation(
        measurement_gui.fig, animate_plot, interval=200, fargs=[measurement_gui.ax, measurement_gui.graph, measurement_gui.results, measurement_gui.progress_bar, measurement_gui.time_var])
    measurement_gui.mainloop()


if __name__ == '__main__':
    main()
