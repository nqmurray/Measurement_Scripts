import numpy as np
import time
import csv
from scipy import optimize
from pymeasure import instruments
from GaussMeterClass import GaussMeter

SCREAM = {
    'Hx Dac': 'dac3',
    'Hz Dac': 'dac2',
    'Hx Conversion': 393.5,
    'Hz Conversion': 1022,
    'Hx Delay': 0,
    'Hz Delay': 0,
    'Hz Max': 1,  # max voltage allowed through the amp
    'Hx Max': 10
}

SCREAM_RESOURCES = {
    'dsp_lockin': 'GPIB0::10::INSTR',
    'keithley_2000': 'GPIB0::16::INSTR',
    'keithley_2400': 'GPIB0::20::INSTR',
    'gaussmeter': 'GPIB0::7::INSTR',
    'sig_gen_8257': 'GPIB0::18::INSTR'
}

SCREAM02 = {
    'Hx Dac': 'dac1',
    'Hz Dac': 'dac2',
    'Hx Conversion': 3740,
    'Hz Conversion': 1029.5,
    'Hx Delay': 0,
    'Hz Delay': 0,
    'Hz Max': 0.25,  # max voltage allowed through the amp
    'Hx Max': 0.5
}

SCREAM02_RESOURCES = {
    'dsp_lockin': 'GPIB0::10::INSTR',
    'keithley_2000': 'GPIB0::16::INSTR',
    'keithley_2400': 'GPIB0::20::INSTR',
    'gaussmeter': 'GPIB0::7::INSTR',
    'sig_gen_8257': 'GPIB0::18::INSTR'
}


def update_values():  # run update on conversion factor and delay time
    acceptable_error = 0.1  # percentage error for delay calibration
    step = 0.5
    rest = 1
    # choose the computer to use
    computer = input('Choose the computer in use (SCREAM / SCREAM02): ')
    if computer == 'SCREAM':
        controls = SCREAM
    elif computer == 'SCREAM02':
        controls == SCREAM02
    else:
        print('Computer name not recognized. Please try again')
    direction = input('Pick a field direction to calibrate (Hz / Hx): ')
    # set x or z direction
    if direction == 'Hx':
        x_array = np.arange(-1, 1, step)
        field_array = np.array([-10, 10])
        # field_array = np.array([5, 10, 20, 30, 40, 50, 75, 100, 125, 150, 200, 250, 300, 400,
        # 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 1800, 2000])
        channel = controls['Hx Dac']
    elif direction == 'Hz':
        x_array = np.arange(-1, 1, step)
        field_array = np.array([5, 10, 15, 20, 30, 40,
                                50, 75, 100, 150, 200, 250])
        channel = controls['Hz Dac']
    else:
        print('Calibration direction unrecognized')

    q1 = input('Do you wish to run a calibration test? (y/n): ')
    if q1 == 'y' or q1 == 'Y':
        # try calibration
        try:
            x, y = run_conversion_update(x_array, channel, rest)
            np_param, np_covar = optimize.curve_fit(
                test_func, x[:len(x_array)], y[:len(x_array)])
            pn_param, pn_covar = optimize.curve_fit(
                test_func, x[len(x_array):], y[len(x_array):])
            print(
                f'{direction} Direction Calibration gave\n Neg to Pos Slope = {np_param[0]} with Intercept = {np_param[1]}')
            print(
                f'Pos to Neg Slope = {pn_param[0]} with Intercept = {pn_param[1]}')

            header = ['Voltage (V)', 'Field (Oe)', 'Neg Pos Slope',
                      'Neg Pos Intercept', 'Pos Neg Slope', 'Pos Neg Intercept']
            misc = [np_param[0], np_param[1], pn_param[0], pn_param[1]]
            save_data('Conversion_calibration', x, y, header, misc)

        except Exception as err:
            print('Failed to run test with error:' + str(err))
    else:
        pass

    q2 = input('Do you wish to run delay calibration test? (y/n): ')
    if q2 == 'y' or q2 == 'Y':
        try:
            delay_times = run_delay_test(
                field_array, channel, acceptable_error, controls['%s Conversion' % direction], controls['%s Max' % direction])
            print(type(len(delay_times)))
            if len(delay_times) == len(field_array):
                delay_param, delay_covar = optimize.curve_fit(
                    test_func, field_array, delay_times)
            else:
                print('Array lengths not equal, fitting failed')
                delay_param = ['NaN', 'NaN']
            header = ['Field (Oe)', 'Delay (s)', 'Slope', 'Intercept']
            save_data('Delay_calibration', field_array,
                      delay_times, header, delay_param)
        except Exception as err:
            print('Failed to perform delay test with error: ' + str(err))
    else:
        print('Job finished. Shutting down.')


# runs a loop test with given channel
def run_conversion_update(vals, channel, rest):
    y = []
    gm = GaussMeter("GPIB0::7")   # initiate Gaussmeter
    lockin = instruments.signalrecovery.DSP7265(
        "GPIB0::10")  # initiate lockin by pymeasure
    # neg to pos loop
    for x in vals:
        setattr(lockin, channel, x)
        time.sleep(rest)
        y.append(gm.measure())
    # reset after neg to pos look
    setattr(lockin, channel, 0)
    time.sleep(rest)
    # pos to neg loop
    for x in vals[::-1]:
        setattr(lockin, channel, x)
        time.sleep(rest)
        y.append(gm.measure())

    setattr(lockin, channel, 0)
    print('Finished, shutting down instruments')
    lockin.shutdown()
    gm.shutdown()
    print('Instruments shut down.')

    return np.concatenate([vals, vals[::-1]]), y


def run_delay_test(vals, channel, acceptable_error, conversion, max_val):  # calibration delay test

    print(
        f'Running delay test on {channel} using conversion factor {conversion} with a max voltage cap of {max_val}')
    y = []
    gm = GaussMeter("GPIB0::7")   # initiate Gaussmeter
    lockin = instruments.signalrecovery.DSP7265(
        "GPIB0::10")  # initiate lockin by pymeasure
    max_time = 20  # maximum amount of time to test a field at
    for ind, x in enumerate(vals):
        # loop to test delay time or cut off if timeout happens
        if float(x / conversion) > max_val:
            print(
                f'{x/conversion} voltage corresponding to a field strength of {x} exceeds the amp limit {max_val}')
            break
        start_time = time.time()
        f1 = gm.measure()
        setattr(lockin, channel, float(x / conversion))
        while True:
            f2 = gm.measure()
            tot = abs(f1) - abs(f2)
            if time.time() > start_time + max_time:
                y.append(max_time + 1)
                print('Timeout occured')
                break
            elif abs(abs(tot) - abs(x)) <= (x * acceptable_error):
                y.append(time.time() - start_time)
                print(f'{tot} Oe step reached in {time.time() - start_time}')
                break
            else:
                time.sleep(0.1)
        # let amp rest for 15 seconds after each test
        setattr(lockin, channel, 0)
        time.sleep(15)

    setattr(lockin, channel, 0)
    print('Finished, shutting down instruments')
    gm.shutdown()
    lockin.shutdown()
    print('Insturments shutdown')

    return y


def test_func(x, m, b):  # test function for scipy optimization
    return (m * x) + b


def save_data(filename, x_data, y_data, headers, misc_data):
    print('Now saving file ', filename)
    t = time.strftime('%Y-%m-%d-%H-%M-%S')
    with open(filename + t + '.csv', 'w', newline='', encoding='utf-8') as csvfile:
        savewriter = csv.writer(csvfile, dialect='excel')
        savewriter.writerow(headers)
        for i in range(len(x_data)):
            if i == 0:
                savewriter.writerow([x_data[i], y_data[i]] + misc_data)
            elif i > len(y_data):
                savewriter.writerow([x_data[i], 'NaN'])
            else:
                savewriter.writerow([x_data[i], y_data[i]])
        csvfile.close()
    print('File save complete')


def main():
    update_values()
    while True:
        q = input('Do you wish to run the program again? (y/n)')
        if q == 'y' or q == 'Y':
            update_values()
        else:
            print('Program finished')
            time.sleep(1)
            break


if __name__ == '__main__':
    main()
