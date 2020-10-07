from helper import *
import sys


if __name__ == '__main__':
    parameters = load_params()
    if 'repeat' in sys.argv:
        to_text = 'text' in sys.argv
        while True:
            try:
                to_text = show_data(parameters, text=to_text)
            except Exception as e:
                msg = f'\n{time.strftime("%m/%d %H:%M:%S", time.localtime())}: Cannot run this cycle: {e}'
                write_to_log(msg)
                pass
            time.sleep(parameters['wait_between_steps_secs'])
    else:
        show_data(parameters)
