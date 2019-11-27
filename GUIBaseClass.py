import os
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import matplotlib
import multiprocessing as mp
from random import randint
from pymeasure import instruments
from MeasurementClass import Measurement
# has to be called before pyplot, backends are imported
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GUIBase(tk.Tk):  # Base GUI class with all features universal to code environment

    # initialize this class, includes passed arguments
    def __init__(self, _graph, _machines, order_dict, *args):

        # initialize the tk.Tk class portion
        tk.Tk.__init__(self, _graph['gui_title'])
        tk.Tk.wm_title(self, _graph['gui_title'])

        tk.Tk.columnconfigure(self, 0, weight=1)
        tk.Tk.rowconfigure(self, 0, weight=1)

        # dictionaries of measurement settings, graph settings and results
        self.settings = args
        self.graph = _graph
        self.machines = _machines
        self.results = {'x_data': mp.Array('d', 1500),
                        'y_data': mp.Array('d', 1500),
                        # for cases where Gaussmeter data is recorded
                        'x2_data': mp.Array('d', 1500),
                        # counts the number of data points to graph
                        'counter': mp.Value('i', 0),
                        # int value of the percentage done the total measurement loop is
                        'progress': mp.Value('i', 0),
                        'time': mp.Value('i', 0)
                        }
        self.queue = mp.Queue()
        # directions for measure module import (since can't be pickled) and loop direction commands
        self.order = order_dict

        # make sure that there is a Measurements folder that exists
        if os.path.isdir(os.path.expanduser('~\\Documents') + '\\Measurements'):
            pass
        else:
            os.mkdir(os.path.expanduser('~\\Documents') + '\\Measurements')

        # save parameters
        self.directory = os.path.expanduser('~\\Documents\\Measurements')
        # loop and file name initial values, later changed to widgets
        self.file_name = 'test_file'
        self.loop = ['low-high', 'zero-zero', 'high-low', 'standard']

        # multiprocessing.Process controls, for quit and pause functions
        self.measure_process = ''  # initialized when measurement button is pressed
        # flag which will pause process at the top of the measurement loop
        self.pause_flag = mp.Event()
        # flag that kills the measurement process after safely releasing resources
        self.quit_flag = mp.Event()

        # initialize the plot figure and axes necessary for drawing
        self.fig = plt.Figure(figsize=(6, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)

        # Main frame that will hold the frames for each specific group of widgets
        base_frame = ttk.Frame(self)
        base_frame.grid(row=0, column=0, sticky='nsew')
        base_frame.columnconfigure(0, weight=1)
        base_frame.rowconfigure(0, weight=1)

        # The four frames that house each different section of widgets
        plot_frame = ttk.Frame(base_frame, borderwidth=5)
        settings_frame = ttk.Frame(base_frame, borderwidth=5)
        info_frame = ttk.Frame(base_frame, borderwidth=5)
        buttons_frame = ttk.Frame(base_frame, borderwidth=5)
        progress_frame = ttk.Frame(base_frame, borderwidth=5)

        # Use grid to place all frames on the base_frame
        plot_frame.grid(row=0, column=0, sticky='nsew')
        settings_frame.grid(row=0, column=1, sticky='nsew')
        progress_frame.grid(row=1, column=0, sticky='nsew')
        info_frame.grid(row=2, column=0, sticky='nsew')
        buttons_frame.grid(row=1, column=1, rowspan=2, sticky='nsew')

        # creates and grids the listbox and scroll bar
        self.datalog = tk.Listbox(info_frame, height=5)
        self.y_scroll = ttk.Scrollbar(info_frame, command=self.datalog.yview)
        self.datalog['yscrollcommand'] = self.y_scroll.set
        self.datalog.grid(column=0, row=0, sticky='nsew')
        self.y_scroll.grid(column=1, row=0, sticky='ns')

        # test that title is indeed string
        try:
            if type(self.graph['graph_title'] + "\n" + self.graph['fixed_param_1'] + " " + self.graph['fixed_param_2']) is str:
                self.ax.set_title(self.graph['graph_title'] + "\n" +
                                  self.graph['fixed_param_1'] + " " + self.graph['fixed_param_2'])
            else:
                raise Exception(
                    'Graph Title or Fixed Parameters not a string.')
        except Exception as err:
            print('An exception occured for graph titles: ' + str(err))
            self.datalog.insert(
                'end', 'An exception occured for graph titles: ' + str(err))
            self.datalog.see('end')
        # test that x and y axis labels are indeed strings
        try:
            if type(self.graph['x_title'] + self.graph['y_title']) is str:
                self.ax.set_xlabel(self.graph['x_title'])
                self.ax.set_ylabel(self.graph['y_title'])
            else:
                raise Exception('X or Y Axis label not a string.')
        except Exception as err2:
            print('An exception occured for axis labels: ' + str(err2))
            self.datalog.insert(
                'end', 'An exception occured for axis labels: ' + str(err2))
            self.datalog.see('end')

        # Draw the plot on canvas
        plot_canvas = FigureCanvasTkAgg(self.fig, plot_frame)
        plot_canvas.draw()
        plot_canvas.get_tk_widget().grid(row=0, column=0, pady=0, padx=0, sticky='nsew')

        # variable that updates in animation, letting user how long left there is
        self.time_var = tk.StringVar()
        self.time_var.set('Time Remaining')

        # creates and grids a progress bar and estimated time remaining label
        self.progress_bar = ttk.Progressbar(
            progress_frame, orient='horizontal', length=500, mode='determinate', maximum=100, value=0)
        self.progress_bar.grid(column=0, row=0, sticky='nsew')
        self.time_label = ttk.Label(progress_frame, textvar=self.time_var)
        self.time_label.grid(column=1, row=0, sticky='nsew')

        # make test settings
        for dic in self.settings:
            try:
                if type(dic) is dict:
                    # for each dictionary in the list, build items
                    self.make_form(settings_frame, dic)
                else:
                    raise Exception(
                        'List element (' + str(dic) + ') must be a dictionary')
            except Exception as err3:
                print(
                    'An exception occured with the list of measurement parameters: ' + str(err3))
                self.datalog.insert('end',
                                    'An exception occured with the list of measurement parameters: ' + str(err3))
                self.datalog.see('end')

        # make loop parameters buttons/labels/entries (the misc commands)
        misc_lf = ttk.LabelFrame(settings_frame, text='Measurement Options')
        misc_lf.grid(ipadx=2, ipady=5, sticky='nsew')
        file_name_lbl = ttk.Label(
            misc_lf, width=20, text='File Name:', anchor='w')
        file_name_ent = ttk.Entry(misc_lf, width=15)
        file_name_ent.insert(0, self.file_name)
        # update dictionary value to the entry
        self.file_name = file_name_ent
        file_name_lbl.grid(row=0, column=0, sticky='nsew')
        file_name_ent.grid(row=0, column=1, sticky='nsew')
        loop_lbl = ttk.Label(misc_lf, width=20,
                             text='Loop Type:', anchor='w')
        loop_box = ttk.Combobox(misc_lf, width=10,
                                state='readonly', values=self.loop)
        loop_box.set('low-high')
        self.loop = loop_box  # update dictionary value to the box
        loop_lbl.grid(row=1, column=0, sticky='nsew')
        loop_box.grid(row=1, column=1, sticky='nsew')

        # make the buttons
        self.measure_button = ttk.Button(
            buttons_frame, text='Measure', command=lambda: self.measure_method())
        self.output_button = ttk.Button(
            buttons_frame, text='Output', command=lambda: self.output_method())
        self.dir_button = ttk.Button(
            buttons_frame, text='Change Directory', command=lambda: self.change_directory_method())
        self.stop_button = ttk.Button(
            buttons_frame, text='Stop', command=lambda: self.stop_method(), state='disabled')
        self.quit_button = ttk.Button(
            buttons_frame, text='Quit', command=lambda: self.quit_method())

        # grid buttons
        self.measure_button.grid(row=0, column=0, sticky='nsew')
        self.output_button.grid(row=1, column=0, sticky='nsew')
        self.dir_button.grid(row=2, column=0, sticky='nsew')
        self.stop_button.grid(row=3, column=0, sticky='nsew')
        self.quit_button.grid(row=4, column=0, sticky='nsew')

        # weights columns/rows that are of weight 1, frames with specific weights are written explicitly
        self.weight_col(buttons_frame)
        self.weight_col(settings_frame)
        self.weight_col(plot_frame)
        self.weight_row(buttons_frame)
        self.weight_row(plot_frame)
        self.weight_row(info_frame)

        # necessary to keep the scroll bar tiny
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=0)

        # necessary to keep the label tiny
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.columnconfigure(1, weight=0)

        # test that all instruments are on and the gpib addresses are correct
        self.check_resources()

    # takes the input parent and dictionary and creates label and entry widgets for them
    def make_form(self, parent, dictionary):

        lf = ttk.LabelFrame(parent, text=dictionary['title'])
        lf.grid(ipadx=2, ipady=2, sticky='nsew')
        mod = 0  # modifies the counter to account for the title which does not take up a row
        for key, value in dictionary.items():
            if key == 'title':  # ignores the title key in the dictionary
                pass
            elif dictionary['title'] == 'Lockin':
                if key == 'Mode':
                    lab = ttk.Label(lf, width=20, text=key + ':', anchor='w')
                    bx = ttk.Combobox(
                        lf, width=10, state='readonly', values=('1st', '2nd'))
                    if value in bx.cget('values'):
                        bx.set(value)
                    else:
                        self.datalog.insert(
                            'end', value + ' not a recognized mode setting.')
                        self.datalog.see('end')
                    lab.grid(row=mod, column=0, sticky='nsew')
                    bx.grid(row=mod, column=1, sticky='nsew')
                    dictionary[key] = bx
                    mod += 1
                elif key == 'Sensitivity':
                    lab = ttk.Label(lf, width=20, text=key + ':', anchor='w')
                    bx = ttk.Combobox(lf, width=10, state='readonly', values=('2nV', '5nV', '10nV', '20nV', '50nV', '100nV', '200nV', '500nV', '1uV', '2uV',
                                                                              '5uV', '10uV', '20uV', '50uV', '100uV', '200uV', '500uV', '1mV', '2mV', '5mV', '10mV', '20mV', '50mV', '100mV', '200mV', '500mV', '1V'))

                    if value in bx.cget('values'):
                        bx.set(value)
                    else:
                        self.datalog.insert(
                            'end', value + ' is not a recognized sensitivity setting.')
                        self.datalog.see('end')
                    lab.grid(row=mod, column=0, sticky='nsew')
                    bx.grid(row=mod, column=1, sticky='nsew')
                    dictionary[key] = bx
                    mod += 1
                else:
                    lab = ttk.Label(lf, width=20, text=key + ':', anchor='w')
                    ent = ttk.Entry(lf, width=15)
                    ent.insert(0, str(value))
                    lab.grid(row=mod, column=0, sticky='nsew')
                    ent.grid(row=mod, column=1, sticky='nsew')
                    # set dictionary value to entry widget
                    dictionary[key] = ent
                    mod += 1
            else:
                lab = ttk.Label(lf, width=20, text=key + ':', anchor='w')
                ent = ttk.Entry(lf, width=15)
                ent.insert(0, str(value))
                lab.grid(row=mod, column=0, sticky='nsew')
                ent.grid(row=mod, column=1, sticky='nsew')
                dictionary[key] = ent  # set dictionary value to entry widget
                mod += 1

    # takes a given frame and gives all columns a weight of 1
    def weight_col(self, frame):

        for x in range(frame.grid_size()[0]):
            frame.columnconfigure(x, weight=1)

    # takes a given frame and gives all rows a weight of 1
    def weight_row(self, frame):

        for x in range(frame.grid_size()[1]):
            frame.rowconfigure(x, weight=1)

    # take list of resources and checks if there is a device at the address that is on
    def check_resources(self):
        available_resources = instruments.list_resources()
        # note, this fails to identify specific machines, it only identifies addresses
        for key, value in self.machines.items():
            try:
                if value in available_resources:
                    pass
                else:
                    raise Exception(key + ' not found at ' + str(value))
            except Exception as err:
                self.datalog.insert(
                    'end', 'Resource not detected: ' + str(err))
                self.datalog.see('end')

    # =====================Button Controls Here===================== #
    # measure loop, this will acutally just spawn a thread that runs the target function passed to it
    def measure_method(self):
        try:
            # makes sure there are no other measurement processes alive
            if len(mp.active_children()) == 0:
                self.datalog.insert('end', 'Starting Measurement')
                self.datalog.see('end')
                # make sure pause is set to false
                self.pause_flag.set()
                self.quit_flag.clear()  # quits on true
                # enables the stop button
                self.stop_button.state(['!disabled'])
                # initialize process and queue for measurement loop
                # get the loop parameters from the tkinter entryboxes and pass them as a dictionary of kwargs to measure process
                loop_params = {}
                for dic in self.settings:
                    for key, value in dic.items():
                        if key != 'title':
                            loop_params[key] = value.get()
                        else:
                            pass
                m = Measurement(self.order, self.results, self.graph, self.pause_flag,
                                self.quit_flag, self.directory, self.file_name.get(),
                                self.loop.get(), self.queue, self.machines, loop_params)
                self.measure_process = mp.Process(
                    target=m.measure, name='Measurement', daemon=True)
                self.measure_process.start()
                # checks to see if measurement is finished
                self.after(100, self.process_queue)
            else:
                raise Exception(
                    'Multiple Active Measurement Processes Detected!')
        except Exception as err:
            print('An Exception Occured starting measurement: ' + str(err))
            self.datalog.insert('end', 'An Exception Occured starting measurement: ' + str(err))
            self.datalog.see('end')

    # Calls updates after processing the queue, runs every 100 ms
    def process_queue(self):
        try:
            if not self.measure_process.is_alive():
                self.stop_button.state(['disabled'])
                while not self.queue.empty():  # empty out any leftover messages from the queue
                    self.queue.get()
            elif not self.queue.empty():  # prints the message passed from the measurement
                msg = self.queue.get(0)
                # resets the system if job is finished
                if type(msg) is str and msg == 'Job Finished':
                    self.datalog.insert('end', msg)
                    self.datalog.see('end')
                    self.results['progress'].value = 0
                    self.results['time'].value = 0
                    self.time_var.set('Time Remaining')
                    self.stop_button.state(['disabled'])
                    self.measure_process.join()  # safely releases process
                elif type(msg) is dict:
                    # update dictionary values to updated fields
                    self.graph.update(msg)
                    self.after(100, self.process_queue)
                else:
                    self.datalog.insert('end', msg)
                    self.datalog.see('end')
                    self.after(100, self.process_queue)
            else:
                raise Exception('Empty')
        except Exception:
            self.after(100, self.process_queue)

    # output field for given time
    def output_method(self):
        # pop up a window with input of time, direction, strength
        t = tk.Toplevel()
        t.title('Single Output')

        x_dac = -1
        z_dac = -1
        x_con = -1
        z_con = -1
        z_lim = 1
        x_lim = 12

        # find the lockin dictionary
        for dic in self.settings:
            if dic['title'] == 'Lockin':
                d = dic

        # get the conversion factors and channels
        for key, value in d.items():
            if 'Hx Dac' in key:
                x_dac = value.get()
            elif 'Hz Dac' in key:
                z_dac = value.get()
            elif 'Hx Conversion' in key:
                x_con = float(value.get())
            elif 'Hz Conversion' in key:
                z_con = float(value.get())
            elif 'Hz Max' in key:
                z_lim = float(value.get())
            elif 'Hx Max' in key:
                x_lim = float(value.get())
            else:
                pass

        # see what directions are exceptable for the output
        if x_dac != -1 and z_dac != -1:
            v = ['x', 'z']
        elif x_dac != -1 and z_dac == -1:
            v = ['x']
        elif x_dac == -1 and z_dac != -1:
            v = ['z']
        else:
            self.output_button.state(['disabled'])
            self.datalog.insert('end', 'No magnet control settings found!')
            self.datalog.see('end')
            t.destroy()

        # try setting up pymeasure lockin instance
        try:
            lockin = instruments.signalrecovery.DSP7265(
                self.machines['dsp_lockin'])
            # direction label and combobox
            output_lbl = ttk.Label(
                t, width=15, text='Output direction:', anchor='w')
            output_direction = ttk.Combobox(
                t, width=15, state='readonly', values=(v))
            output_direction.set(v[0])
            output_lbl.grid(row=0, column=0, ipadx=2,
                            ipady=2, sticky='nsew')
            output_direction.grid(row=0, column=1, ipadx=2,
                                  ipady=2, sticky='nsew')

            # field strength
            s_lbl = ttk.Label(
                t, width=15, text='Output Strength (Oe)', anchor='w')
            s_ent = ttk.Entry(t, width=15)
            s_ent.insert(0, 100)
            s_lbl.grid(row=1, column=0, ipadx=2, ipady=2, sticky='nsew')
            s_ent.grid(row=1, column=1, ipadx=2, ipady=2, sticky='nsew')

            # output time
            ot_lbl = ttk.Label(t, width=15, text='Output Time (s)', anchor='w')
            ot_ent = ttk.Entry(t, width=15)
            ot_ent.insert(0, 1)
            ot_lbl.grid(row=2, column=0, ipadx=2, ipady=2, sticky='nsew')
            ot_ent.grid(row=2, column=1, ipadx=2, ipady=2, sticky='nsew')

            out = ttk.Button(t, text='Output', command=lambda: out_field())
            out.grid(row=3, columnspan=2, ipadx=5, ipady=5, sticky='nsew')
        except Exception as err:
            self.datalog.insert(
                'end', "Failed to find lockin at " + self.machines['dsp_lockin'] + ':' + str(err))
            self.datalog.see('end')
            t.destroy()

        def out_field():  # outputs a field in a given direction if not above the limit
            self.datalog.insert(
                'end', 'Output %s direction field for %s seconds' % (output_direction.get(), ot_ent.get()))
            if output_direction.get() == 'z':
                if float(s_ent.get()) / z_con <= z_lim:
                    setattr(lockin,
                            z_dac, float(s_ent.get()) / z_con)
                    time.sleep(float(ot_ent.get()))
                    setattr(lockin, z_dac, 0)
                else:
                    self.datalog.insert(
                        'end', 'Output exceeds Hz amp limit of %d V' % z_lim)
                    self.datalog.see('end')
            else:
                if float(s_ent.get()) / float(x_con) <= x_lim:
                    setattr(lockin,
                            x_dac, float(s_ent.get()) / x_con)
                    time.sleep(float(ot_ent.get()))
                    setattr(lockin, x_dac, 0)
                else:
                    self.datalog.insert(
                        'end', 'Output exceeds Hx amp limit of %d V' % x_lim)
                    self.datalog.see('end')
            lockin.shutdown()

    # change directory, sweet and simple
    def change_directory_method(self):
        self.directory = tk.filedialog.askdirectory()
        self.datalog.insert('end', self.directory)

    # stop, first will pause and then can end the measure process and shut down the instruementss
    def stop_method(self):

        self.pause_flag.clear()  # pauses process
        self.datalog.insert('end', 'Pausing Process...')
        self.datalog.see('end')
        q1 = tk.messagebox.askquestion('Loop Paused', 'Do you wish to stop?')

        if q1 == 'yes':
            self.datalog.insert('end', 'Terminating measurement process...')
            self.quit_flag.set()  # kills the process
            # process queue will join thread and is called every 0.1 seconds
            time.sleep(0.2)
            # reset the progress bar, time remaining
            self.results['progress'].value = 0
            self.results['time'].value = 0
            self.time_var.set('Time Remaining')
            self.datalog.insert('end', 'Process Terminated')
            self.datalog.see('end')
            self.stop_button.state(['disabled'])
        else:
            self.datalog.insert('end', 'Resuming measurement...')
            self.datalog.see('end')
            self.pause_flag.set()  # resumes measurement

    # quit, shuts down all instruments, kills process, closes program
    def quit_method(self):
        q = tk.messagebox.askquestion('Quit', 'Are you sure you want to quit?')

        if q == 'yes':
            try:
                if len(mp.active_children()) != 0:
                    self.datalog.insert(
                        'end', 'Terminating measurement process...')
                    self.quit_flag.set()  # kills the process
                    # process queue will join thread and is called every 0.1 seconds
                    time.sleep(0.2)
                    self.datalog.insert('end', 'Process Terminated')
                    self.datalog.see('end')
            finally:
                self.datalog.see('end')
                time.sleep(0.1)
                self.quit()
        else:
            pass


def animate_plot(i, ax, _graph, _results, progress_bar, time_var):  # animation function
    ax.clear()
    ax.grid(True)
    ax.set_title(_graph['graph_title'] + "\n" +
                 _graph['fixed_param_1'] + " " + _graph['fixed_param_2'])
    ax.set_xlabel(_graph['x_title'])
    ax.set_ylabel(_graph['y_title'])
    # avoids a situation where len(x_data[:counter]) != len(y_data[:counter])
    tmp_x = _results['x_data'][0:_results['counter'].value]
    ax.plot(tmp_x,
            _results['y_data'][0:len(tmp_x)], 'b-o', ms=10, mew=0.5)
    progress_bar['value'] = _results['progress'].value
    if _results['time'].value != 0 and _results['time'].value / 60 >= 1:
        time_var.set(
            str(round(_results['time'].value / 60)) + ' mins remaining')
    elif _results['time'].value != 0:
        time_var.set('<1 min remaining')


# ======================================= Test Version Below ============================================ #

def testf1(output, delay, resources):
    time.sleep(0.01)
    print(f'testf1 {output} with {delay}')
    print(resources)


def testf2(output, delay, resources):
    time.sleep(0.01)
    print(f'testf2 {output} with {delay}')


def testx(output, delay, resources):
    time.sleep(0.01)
    print(float(output), float(output % 2 + randint(0, 100)), delay, 'testx')
    return float(output), float(output % 2 + randint(0, 100)), delay


def main():  # test version of the GUI_base and animation
    # test dictionary for settings
    machine_dict = {
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

    loop_commands = {
        'fixed_func_1': 'testf1',  # name of fixed parameter one function
        'fixed_func_2': 'testf2',
        'measure_y_func': 'testx',
        # directory from which the preceeding modules will be imported from
        'module_path': os.getcwd(),
        'module_name': 'GUIBaseClass_V2',  # name of the file to get the functions from
        'fix1_start': 'hx start',
        'fix1_stop': 'hx stop',
        'fix1_step': 'hx step',
        'fix2_start': 'current start',
        'fix2_stop': 'current stop',
        'fix2_step': 'current step',
        'x_start': 'hz start',
        'x_stop': 'hz stop',
        'x_step': 'hz step',
    }

    test_dict = {
        "title": "Test Field Dict",
        "hx start": 0,
        "hx stop": 5,
        "hx step": 1,
        "hz start": 0,
        "hz stop": 500,
        "hz step": 1
    }

    test_dict_2 = {
        "title": "Test Current Dict",
        "current start": 1,
        "current stop": 2,
        "current step": 0.5
    }

    lockin_test = {
        "title": "Lockin",
        "Sensitivity": '10uV',
        "Mode": '1st',
        "Frequency": 100,
        "Signal": 1,
        'Hx Dac': 1,
        'Hz Dac': 2,
        'Hx Conversion': 1234,
        'Hz Conversion': 2345
    }

    test_gui = GUIBase(graph_dict, machine_dict, loop_commands,
                       test_dict, test_dict_2, lockin_test)
    ani = animation.FuncAnimation(
        test_gui.fig, animate_plot, interval=200, fargs=[test_gui.ax, test_gui.graph, test_gui.results, test_gui.progress_bar, test_gui.time_var])
    test_gui.mainloop()


if __name__ == '__main__':
    main()
