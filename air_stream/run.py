import sys
import time

from main import load_params, pull_and_show, write_to_log


def run() -> None:
    """
    Parse input from command line and run script
    """
    parameters = load_params()
    pi = "pi" in sys.argv
    if "repeat" in sys.argv:
        to_text = "text" in sys.argv
        while True:
            try:
                to_text = pull_and_show(parameters, text=to_text, pi=pi)
            except Exception as e:
                msg = f'\n{time.strftime("%m/%d %H:%M:%S", time.localtime())}: Cannot run this cycle: {e}'
                write_to_log(msg)
                import traceback
                print(traceback.format_exc())
                pass
            time.sleep(parameters["wait_between_steps_secs"])
    else:
        pull_and_show(parameters, pi=pi)


if __name__ == "__main__":
    run()
