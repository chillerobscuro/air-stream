import requests
import time
import yaml


def show_data(params, show_time=True, text=False):
    if show_time:
        print_time()
    rsp = get_realtime_data(params['sensor_number'])
    if not rsp:
        print("Couldn't get data! Cancelling this round")
        return text
    temp_f, aqi, label = rsp['temp_f'], rsp['aqi'], rsp['label']
    # if not len(params['nearby_sensors']):
    nearby_avg = average_sensors(params['nearby_sensors'])
    outdoor_f, outdoor_aqi = nearby_avg['temp_f'], nearby_avg['aqi']
    printer(temp_f, aqi, label, outdoor_f, outdoor_aqi)
    if text and aqi >= params['aqi_texting_threshold']:
        send_text_message(params['dest_phone_num'], params['sender_email'], params['sender_email_pw'],
                          aqi, label, params['aqi_texting_threshold'])
    return text and not aqi >= params['aqi_texting_threshold']  # return 0 if threshold text has been sent, else 1


def printer(temp_f, aqi, label, outdoor_f, outdoor_aqi):
    # format the output data
    box_str = '-'*32
    print(f"\n{box_str}\n"
          f"PurpleAir Data for {label}:\n\n"
          f"   Indoor   |   Outdoor\n"
          f"{box_str}\n"
          f"   AQI: {aqi}{' '*3 if aqi<10 else ' '*2}|  {outdoor_aqi}\n"
          f"  Temp: {temp_f}  |  {outdoor_f}\n"
          f"{box_str}\n")


def print_time():
    print(f'\n{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')


def get_realtime_data(sensor):
    # pull data for one sensor from purpleair.com
    response = requests.get(f'https://www.purpleair.com/json?show={sensor}')
    try:
        rsp = response.json()
    except JSONDecodeError:
        print(f'No values for sensor number {sensor}')
        return None
    rsp1, rsp2 = rsp['results'][0], rsp['results'][1]
    label = rsp1['Label']
    temp_f = int(rsp1['temp_f']) - 8  # purpleair customer support said to subtract 8 from the raw reading
    aqi_raw = (float(rsp1['PM2_5Value']) + float(rsp2['PM2_5Value'])) / 2.  # average the sensors
    aqi = aqi_from_pm(aqi_raw)
    humidity = float(rsp1['humidity'])
    humidity = humidity - humidity * .04  # 4% correction
    ret_dict = {'temp_f': temp_f, 'aqi': aqi, 'humidity': humidity, 'label': label}
    return ret_dict


def average_sensors(sensor_list):
    # Pull data for multiple sensors and return average temp_f and aqi
    vals = get_realtime_data(sensor_list[0])
    for i in range(1, len(sensor_list)):
        new_sensor_data = get_realtime_data(sensor_list[i])
        if not new_sensor_data:
            # run function again without missing sensor
            average_sensors([s for s in sensor_list if s != sensor_list[i]])
        else:
            for v in ['temp_f', 'aqi', 'humidity']:
                vals[v] = (vals[v]*i + new_sensor_data[v]) / float(i+1)  # calculate running average
    return vals


def aqi_from_pm(pm25):
    # Calculations taken from purpleair's javascript example at
    # https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit
    if pm25 < 0 or pm25 > 1000:
        print(f'PM2.5 {pm25} out of range')
        return None
    if pm25 > 350.5:
        return calc_aqi(pm25, 500, 401, 500, 350.5)
    elif pm25 > 250.5:
        return calc_aqi(pm25, 400, 301, 350.4, 250.5)
    elif pm25 > 150.5:
        return calc_aqi(pm25, 300, 201, 250.4, 150.5)
    elif pm25 > 55.5:
        return calc_aqi(pm25, 200, 151, 150.4, 55.5)
    elif pm25 > 35.5:
        return calc_aqi(pm25, 150, 101, 55.4, 35.5)
    elif pm25 > 12.1:
        return calc_aqi(pm25, 100, 51, 35.4, 12.1)
    else:
        return calc_aqi(pm25, 50, 0, 12, 0)


def calc_aqi(cp, ih, il, bph, bpl):
    a = (ih - il)
    b = (bph - bpl)
    c = (cp - bpl)
    return round((a / b) * c + il)


def send_text_message(dest_phone_number, from_email, email_pw, aqi, label, thresh):
    import smtplib
    # Establish a secure session with gmail's outgoing SMTP server using your gmail account
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(from_email, email_pw)
    # Send text message through SMS gateway of destination number
    server.sendmail(from_email, f'{dest_phone_number}@vtext.com', message_to_send(label, aqi))
    server.quit()
    message = f'Text sent at: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} | AQI: {aqi} Threshold: {thresh}\n'
    write_to_log(message)


def message_to_send(x, y):
    return f'PM2.5 AQI at {x} is now {y}'


def write_to_log(msg, file='log.txt'):
    with open(file, 'a') as f:
        f.write(msg)


def load_params(file='params.yaml'):
    with open(file) as f:
        params = yaml.safe_load(f)
    return params
