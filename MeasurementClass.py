import csv
import importlib
import sys
import time
import numpy as np
import tkinter as tk
from pymeasure import instruments
from GaussMeterClass import GaussMeter


class Measurement():

        # initialize this class, includes passed arguments
    def __init__(self, order_dict, gui_results,
                 gui_graph, pause_flag, quit_flag, save_dir, save_name,
                 loop, prog_queue, resources, kwargs):

        self.kwargs = kwargs
        sys.path.append(order_dict['module_path'])  # add path to import module
        # import specified module

        m_func = importlib.import_module(order_dict['module_name'],
                                         order_dict['module_path'])

        # results data, all shared between processes
        self.x = gui_results['x_data']  # a shared array of floats
        self.y = gui_results['y_data']  # a shared array of floats
        # a shared array of floats, for guassmeter readings
        self.x2 = gui_results['x2_data']
        # a shared value (int), tells how many data points have been stored
        self.counter = gui_results['counter']
        # a shared value (int) -- percent of the task completed (shown in progress bar)
        self.p = gui_results['progress']
        # a shared value (int) -- tells time remaining
        self.t = gui_results['time']
        self.queue = prog_queue  # queue to GUI process
        self.pause = pause_flag  # flag for if stop is pressed
        self.quit = quit_flag  # flag for if quit is pressed
        # resource command functions
        # get the specific function from module
        try:
            self.fix1func = getattr(m_func, order_dict['fixed_func_1'])
            self.fix2func = getattr(m_func, order_dict['fixed_func_2'])
            self.yfunc = getattr(m_func, order_dict['measure_y_func'])
        except Exception as err:
            self.queue.put('Resource functions not found: ', err)
            self.quit.set()
        # Save function info
        self.graph = gui_graph  # dictionary of graph titles, also used for saving
        self.f1_header = self.graph['fixed_param_1']
        self.f2_header = self.graph['fixed_param_2']
        print(self.f1_header, self.f2_header)
        self.directory = save_dir  # directory where files are saved
        self.name = save_name  # name of file
        self.loop = loop  # loop type for save file
        # int with list of num of measurements, updates every time build_array is called
        self.tot_measurement_len = 1
        self.progress_counter = 0  # increments and updates progress as time goes on
        self.time_counter = 0  # increments and lets user know estimated time remaining
        # dictionary with keys that tell which key to use from kwargs for min, max, step, loop direction
        self.order = order_dict
        # dictionary of resources with names and address, when initialized address becomes instance
        self.measurement_resources = resources
        self.map_sensitivity()

    # map sensitivity to a numerical value
    def map_sensitivity(self):
        sensitivity_dict = {
            '10uV': 10.0e-6,
            '20uV': 20.0e-6,
            '50uV': 50.0e-6,
            '100uV': 100.0e-6,
            '1mV': 1.0e-3,
            '2mV': 2.0e-3,
            '5mV': 5.0e-3,
            '10mV': 10.0e-3,
            '20mV': 20.0e-3,
            '50mV': 50.0e-3,
            '100mV': 100.0e-3,
            '200mV': 200.0e-3,
        }
        if "Sensitivity" in self.kwargs:
            self.kwargs['Sensitivity'] = sensitivity_dict[self.kwargs['Sensitivity']]
            print('sensitivity set to: ', self.kwargs['Sensitivity'])
        else:
            pass

     # save data, including arbitrary data user wants saved
    def save_function(self, f1, f2):

        # save function proper
        t = time.strftime('%Y-%m-%d-%H-%M-%S',)
        string = self.name + '_' + self.graph['gui_title'] + '_' + self.f1_header + '_' + \
            self.f2_header + '_' + self.loop + '_' + \
            t + '.csv'
        # replace all spaces
        str1 = ''.join(['_' if i == ' ' else i for i in string])
        # replace all semicolons
        f = ''.join(['' if i == ':' else i for i in str1])

        try:
            with open(self.directory + '\\' + f, 'w', newline='', encoding='utf-8') as csvfile:
                savewriter = csv.writer(csvfile, dialect='excel')
                # accounts measurements without gaussmeter measurements
                if self.graph['x2_title'] != '':
                    savewriter.writerow([self.graph['x_title'], self.graph['y_title'],
                                         self.graph['x2_title'], self.f1_header, self.f2_header,
                                         'Sample', 'Measurement Type', 'Loop Type', 'Time'])
                    for num in range(self.counter.value):
                        savewriter.writerow(
                            [self.x[num], self.y[num], self.x2[num], f1, f2,
                             self.name, self.graph['gui_title'], self.loop, t])
                    csvfile.close()
                else:  # save files for data with gaussmeter measurements
                    savewriter.writerow([self.graph['x_title'], self.graph['y_title'],
                                         self.f1_header, self.f2_header, 'Sample',
                                         'Measurement Type', 'Time', 'Loop Type'])
                    for num in range(self.counter.value):
                        savewriter.writerow([self.x[num], self.y[num], f1, f2,
                                             self.name, self.graph['gui_title'], self.loop, t, ])
                    csvfile.close()
                return 'File Saved as ' + self.directory + '\\' + f
        except Exception as err:
            return 'Error, could not save file! ' + str(err)

    # import charging delay from file, otherwise use standard
    def charging_delay(self, val):
        if val >= 2500:
            return 7.0
        elif 1500 <= val < 2500:
            return 5.0
        elif 1000 <= val < 1500:
            return 3.0
        elif 500 <= val < 1000:
            return 1.0
        elif 100 <= val < 500:
            return 0.5
        elif 50 <= val < 100:
            return 0.1
        else:
            return 0.02

    def activate_resources(self):
        # check resource and attempt to create instance, throw error if can't do that or find matching name/address
        for name, address in self.measurement_resources.items():
            if name == 'dsp_lockin':
                try:
                    self.measurement_resources[name] = instruments.signalrecovery.DSP7265(
                        address)
                except Exception as err:
                    self.queue.put('Error in initializing ' + str(name) +
                                   ' at ' + str(address) + ':' + str(err))
                    self.quit.set()
            elif name == 'keithley_2000':
                try:
                    self.measurement_resources[name] = instruments.keithley.Keithley2000(
                        address)
                except Exception as err:
                    self.queue.put('Error in initializing ' + str(name) +
                                   ' at ' + str(address) + ':' + str(err))
                    self.quit.set()
            elif name == 'keithley_2400':
                try:
                    self.measurement_resources[name] = instruments.keithley.Keithley2400(
                        address)
                except Exception as err:
                    self.queue.put('Error in initializing ' + str(name) +
                                   ' at ' + str(address) + ':' + str(err))
                    self.quit.set()
            elif name == 'gaussmeter':
                try:
                    self.measurement_resources[name] = GaussMeter(address)
                except Exception as err:
                    self.queue.put('Error in initializing ' + str(name) +
                                   ' at ' + str(address) + ':' + str(err))
                    self.quit.set()
            elif name == 'sig_gen_8257':
                try:
                    self.measurement_resources[name] = instruments.agilent.Agilent8257D(
                        address)
                except Exception as err:
                    self.queue.put('Error in initializing ' + str(name) +
                                   ' at ' + str(address) + ':' + str(err))
                    self.quit.set()
            else:
                self.queue.put(
                    'Instrument ' + str(name) + ' at ' + str(address) + ' not found!')

    # run through instruments list and shut them down
    def shutdown_resources(self):
        # can add exceptions in to alert user if shutdown fails for any instrument
        for name, inst in self.measurement_resources.items():
            try:
                if name == 'keithley_2400':
                    inst.ramp_to_current(10e-6)  # set current to 10 microAmps
                    inst.compliance_voltage = 2.1  # set compliance to 2.1 V
                    resources['keithley_2400'].auto_range_source()
                    inst.shutdown()
                elif name == 'dsp_lockin':
                    inst.dac1, inst.dac2, inst.dac3, inst.dac4 = 0, 0, 0, 0  # turn off all dac outputs
                    inst.shutdown()
                else:
                    inst.shutdown()
            except Exception as err:
                self.queue.put('Failed to shut down ' +
                               str(name) + ':' + str(err))
                print(f'Failed to shut down {inst} with error: {err}')

    # builds numpy arrays determined by the loop direction, updates the total measurement length
    def build_array(self, start, end, step, direction):
        if step == 0:
            return [end]
        elif direction == 'low-high':
            arr = np.arange(start, end + step, step)
            return np.hstack((arr, np.flipud(arr[:-1:])))
        elif direction == 'zero-zero':
            arr = np.arange(0, end + step, step)
            pos_arr = np.hstack((arr, np.flipud(arr[:-1:])))
            return np.hstack((pos_arr, (pos_arr[1::1] * -1)))
        elif direction == 'high-low':
            arr = np.arange(end, start - step, -step)
            return np.hstack((arr, np.flipud(arr[:-1:])))
        else:
            # case for normal numpy arrays
            return np.arange(start, end + step, step)

    # checks if output exceeds limit
    def check_amp_limits(self, direction, array):
        if direction == 'none':  # accounts for loops that don't have hx or hz
            pass
        else:
            try:
                amp_max = float(self.kwargs['%s Max' % direction])
                conversion = float(self.kwargs['%s Conversion' % direction])
            except Exception as err:
                self.queue.put(str(direction) +
                               ' maximum not found! ' + str(err))
                self.quit.set()

            if np.max(array) / conversion > amp_max:
                self.queue.put(str(np.max(array)) + ' exceeds ' +
                               str(direction) + ' amp output limit!')
                self.quit.set()
            else:
                pass

    # check the loop direction and return it
    def check_direction(self, key):
        if 'hx' in self.order[key].lower():
            return 'Hx'
        elif 'hz' in self.order[key].lower():
            return 'Hz'
        else:
            return 'none'

    # user passed function, runs the measurement
    def measure(self):

        if self.order['MOKE']:
            self.points = {'left': 0,
                           'top': 0,
                           'width': 0,
                           'height': 0
                           }
            self.pause.clear()  # sets flag to pause
            # will run the tkinter window that selects the measurement points
            meas_region(self.points, self.pause)
            self.pause.wait()  # pause until measure region is selected
        else:
            pass

        # check that there are commands to build this loop, otherwise just run 1 time
        if all(elem in self.order for elem in ['fix1_start', 'fix1_stop', 'fix1_step']):
            # build the arrays of floats to sweep over
            fix1_values = self.build_array(
                float(self.kwargs[self.order['fix1_start']
                                  ]), float(self.kwargs[self.order['fix1_stop']]),
                float(self.kwargs[self.order['fix1_step']
                                  ]), 'none'
            )
            # check if amp limits are protected
            self.check_amp_limits(
                self.check_direction('fix1_start'), fix1_values)
        else:
            self.queue.put(
                'No fixed loop one values detected, setting loop to 1')
            fix1_values = [1]

        # check that there are commands to build this loop, otherwise just run 1 time
        if all(elem in self.order for elem in ['fix2_start', 'fix2_stop', 'fix2_step']):
            fix2_values = self.build_array(
                float(self.kwargs[self.order['fix2_start']
                                  ]), float(self.kwargs[self.order['fix2_stop']]),
                float(self.kwargs[self.order['fix2_step']
                                  ]), 'none'
            )
            # check if amp limits are protected
            self.check_amp_limits(
                self.check_direction('fix2_start'), fix2_values)
        else:
            self.queue.put(
                'No fixed loop two values detected, setting loop to 1')
            fix2_values = [1]

        # only x_values are loop dependent, the other two are just ordinary arrays from start to stop by step
        x_values = self.build_array(
            float(self.kwargs[self.order['x_start']
                              ]), float(self.kwargs[self.order['x_stop']]),
            float(self.kwargs[self.order['x_step']
                              ]), self.loop
        )
        self.check_amp_limits(self.check_direction('x_start'), x_values)

        # update the total measurement length to the proper value
        self.tot_measurement_len = len(
            fix1_values) * len(fix2_values) * len(x_values)

        # check if measurement exceeds array length
        if len(x_values) >= len(self.x):
            self.queue.put(
                'Measurement exceeds array memory length! Please change in GUIBaseClass')
            self.quit.set()

        # iteratre through dictionary of machines, turn address time into instance of resource
        self.activate_resources()  # sets quit flag if fails

        # set first fixed values
        for f1_count, fix_1 in enumerate(fix1_values):
            if self.quit.is_set():  # quits if quit flag is set
                break
            # delay time for charging/ramping to value if necessary
            if f1_count == 0:
                f1_delay = fix_1
            else:
                f1_delay = abs(fix_1) + abs(fix1_values[f1_count - 1])
            # run user function
            self.fix1func(f1_count, fix_1, self.charging_delay(
                f1_delay), self.measurement_resources, self.kwargs)

            # set fixed values, update graph
            for f2_count, fix_2 in enumerate(fix2_values):

                self.pause.wait()  # waits for pause flag
                if self.quit.is_set():  # check if quit flag is set
                    break
                if self.progress_counter == 0:  # time one loop
                    t_start = time.time()
                # update graph titles
                self.graph['fixed_param_1'] = self.f1_header + ': %.2f' % fix_1
                self.graph['fixed_param_2'] = self.f2_header + ': %.2f' % fix_2
                self.queue.put(self.graph)
                # calculate delay time
                if f2_count == 0:
                    f2_delay = fix_2
                else:
                    f2_delay = abs(fix_2) + abs(fix2_values[f2_count - 1])
                # run user function
                self.fix2func(fix_2, self.charging_delay(
                    f2_delay), self.measurement_resources, self.kwargs)

                # scan x values
                for x_count, x_val in enumerate(x_values):
                    if self.quit.is_set():
                        break
                    # delay time for charging/ramping to value if necessary
                    if x_count == 0:
                        x_delay = x_val
                    else:
                        x_delay = abs(x_val) + abs(x_values[x_count - 1])
                    # run user function depending on if MOKE measurement or not
                    if self.order['MOKE']:
                        self.x[x_count], self.y[x_count], self.x2[x_count] = self.yfunc(
                            x_val, self.charging_delay(
                                x_delay),
                            self.measurement_resources, self.points, fix_1,
                            fix_2, self.kwargs)
                    else:
                        self.x[x_count], self.y[x_count], self.x2[x_count] = self.yfunc(
                            x_val, self.charging_delay(
                                x_delay),
                            self.measurement_resources, fix_1, fix_2, self.kwargs)
                    with self.counter.get_lock():
                        self.counter.value = x_count + 1  # where data is stored to in the shared array
                    self.progress_counter += 1
                    # percent progress completed
                    self.p.value = round(
                        self.progress_counter / self.tot_measurement_len * 100)
                if self.progress_counter == len(x_values + 1):
                    t_finish = time.time()
                    time_approximation = t_finish - t_start
                else:
                    time_approximation = 0
                # estimated time remaing (est. tot time - est. time taken)
                self.t.value = round((time_approximation * (len(fix1_values) * len(fix2_values))) -
                                     (time_approximation * (f2_count + len(fix2_values) * f1_count)))

                try:  # accounts for errors with fix_1, fix_2
                    b = str(round(fix_1, 2))
                    s = str(round(fix_2, 2))
                except Exception:
                    b = ''
                    s = ''
                # only save if quit flag has not been set
                if not self.quit.is_set():
                    # saves data, returns string
                    self.queue.put(self.save_function(b, s))

        if self.quit.is_set():
            self.queue.put('Measurement terminated')
        else:
            self.queue.put('Measurement finished')
        self.queue.put('Shutting down instruments...')
        self.shutdown_resources()
        self.queue.put('Job Finished')  # end measurement

# ============================= MOKE FUNCTIONS ====================================== #


# runs a GUI that has a button which selects the measurement region of the screen
def meas_region(p_dict, flag):
    reg = tk.Tk()
    reg.title("Determine Capture Area Coordinates")
    reg.configure(bg='#F2F2F2')
    reg.geometry("450x200")
    reg.attributes('-alpha', 0.8)

    det_btn = tk.Button(master=reg, text='Select Region',
                        command=lambda: select_coords(reg, p_dict), width=15)
    det_btn.pack()

    reg.protocol('WM_DELETE_WINDOW', quit)
    reg.mainloop()


# button command updates the list to include the coordinates
def select_coords(master, p_dict, flag):
    p_dict['left'] = master.winfo_x()
    p_dict['top'] = master.winfo_y()
    p_dict['width'] = master.winfo_width()
    p_dict['height'] = master.winfo_height()
    flag.clear()  # set the flag to let the measurement continue
    master.quit()  # destroys the GUI window
