from helper import *
import sys


if __name__ == '__main__':
    parameters = load_params()
    if 'repeat' in sys.argv:
        to_text = 'text' in sys.argv
        while True:
            to_text = show_data(parameters, text=to_text)
            time.sleep(parameters['wait_between_steps_secs'])
    else:
        show_data(parameters)
