from helper import *
import sys


def show_data(params, text=False):
    rsp = get_data(params['sensor_number'])
    temp_f, aqi, label = rsp['temp_f'], rsp['aqi'], rsp['label']
    nearby_avg = average_sensors(params['nearby_sensors'])
    outdoor_f, outdoor_aqi = nearby_avg['temp_f'], nearby_avg['aqi']
    printer(temp_f, aqi, label, outdoor_f, outdoor_aqi)
    if text and aqi >= params['aqi_texting_threshold']:
        send_text_message(params['dest_phone_num'], params['sender_email'], params['sender_email_pw'],
                          aqi, label, params['aqi_texting_threshold'])
    return text and not aqi >= params['aqi_texting_threshold']  # return 0 unless it's the first time passing threshold


if __name__ == '__main__':
    parameters = load_params()
    if 'repeat' in sys.argv:
        to_text = 'text' in sys.argv
        while True:
            show_time()
            to_text = show_data(parameters, text=to_text)
            time.sleep(parameters['wait_between_steps_secs'])
    else:
        show_data(parameters)


