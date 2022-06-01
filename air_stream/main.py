import time
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
import yaml
from tabulate import tabulate


def pull_and_show(
    params: Dict[str, Any], show_time: bool = True, text: bool = False, pi: bool = False
) -> bool:
    """
    Pull the data from purpleair, print to either terminal or Pi's LCD screen
    params: params from load_params()
    show_time: Print the time before each output
    text: Send a text if the air quality threshold is surpassed
    pi: Print to Pi LCD screen instead of terminal
    """
    if show_time:
        print_time()
    rsp = get_realtime_data(params["sensor_number"])
    if not rsp:
        print("Couldn't get data! Cancelling this round")
        return text
    temp_f, aqi, label, hum = rsp["temp_f"], rsp["aqi"], rsp["label"], rsp["humidity"]
    nearby_avg = average_sensors(params["nearby_sensors"])
    outdoor_f, outdoor_aqi, outdoor_hum = (
        nearby_avg["temp_f"],
        nearby_avg["aqi"],
        nearby_avg["humidity"],
    )
    if pi:
        print_lcd(temp_f, aqi, outdoor_f, outdoor_aqi)
    print_terminal(temp_f, aqi, label, outdoor_f, outdoor_aqi)
    bad_air = aqi >= params["aqi_texting_threshold"]
    if text and bad_air:
        send_text_message(
            params["dest_phone_num"],
            params["sender_email"],
            params["sender_email_pw"],
            aqi,
            label,
            params["aqi_texting_threshold"],
        )
    return text and not bad_air  # return False if threshold text has been sent, else True


def print_terminal(
    temp_f: float, aqi: float, label: str, outdoor_f: float, outdoor_aqi: float
) -> None:
    """
    Print to terminal
    """
    print(f"PurpleAir Data for {label}:\n")
    print(
        tabulate(
            [["AQI", aqi, outdoor_aqi], ["Temp", temp_f, outdoor_f]],
            headers=["", "Indoor", "Outdoor"],
            tablefmt="grid",
            numalign="center",
        )
    )


def print_lcd(temp_f: float, aqi: float, outdoor_f: float, outdoor_aqi: float) -> None:
    """
    Print to Rasperry Pi's LCD screen
    """
    from RPLCD.gpio import CharLCD
    from RPi import GPIO
    GPIO.setwarnings(False)
    lcd = CharLCD(
        cols=16,
        rows=2,
        pin_rs=37,
        pin_e=35,
        pins_data=[33, 31, 29, 23],
        numbering_mode=GPIO.BOARD,
        compat_mode=True,
    )
    aqi_str = f" AQI: {aqi} / {round(outdoor_aqi, 1)}"
    temp_str = f"\r\nTemp: {temp_f} / {round(outdoor_f, 1)}"
    lcd.write_string(aqi_str)
    lcd.write_string(temp_str)


def print_time() -> None:
    print(f'\n{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}')


def get_realtime_data(sensor: int) -> Optional[Dict[str, Union[float, str]]]:
    """
    pull data for one sensor from purpleair.com
    """
    # response = requests.get(f"https://www.purpleair.com/json?show={sensor}")
    response = requests.get(f"https://api.purpleair.com/v1/sensors/{sensor}", headers={"X-API-Key": "3FE5554C-E1DF-11EC-8561-42010A800005"})
    try:
        rsp = response.json()
    except (ConnectionError) as ee:
        print(f"No values for sensor number {sensor}: {ee}")
        return None
    # print('rrr', results)
    # rsp1, rsp2 = rsp["results"][0], rsp["results"][1]
    # label = rsp1["Label"]
    # temp_f = (
    #     int(rsp1["temp_f"]) - 8
    # )  # purpleair subtracts 8 from the raw reading due to sensor heating
    # aqi_raw = (
    #     float(rsp1["PM2_5Value"]) + float(rsp2["PM2_5Value"])
    # ) / 2.0  # average the sensors
    # aqi = aqi_from_pm(aqi_raw)
    # humidity = float(rsp1["humidity"])
    # humidity = int(humidity + humidity * 0.1)  # 10% correction
    results = rsp['sensor']
    temp_f = results['temperature'] - 8
    aqi = aqi_from_pm(results['pm2.5'])
    label = results['name']
    humidity = results['humidity']
    humidity = int(humidity + humidity * 0.1)  # 10% correction
    
    ret_dict = {"temp_f": temp_f, "aqi": aqi, "humidity": humidity, "label": label}
    return ret_dict


def average_sensors(sensor_list: List[int]) -> Dict[str, float]:
    """
    Pull data for multiple sensors and return average temp_f and aqi
    """
    vals = get_realtime_data(sensor_list[0])
    for i in range(1, len(sensor_list)):
        new_sensor_data = get_realtime_data(sensor_list[i])
        if not new_sensor_data:
            # run function again without missing sensor
            average_sensors([s for s in sensor_list if s != sensor_list[i]])
        else:
            for v in ["temp_f", "aqi", "humidity"]:
                vals[v] = (vals[v] * i + new_sensor_data[v]) / float(
                    i + 1
                )  # calculate running average
    return vals


def aqi_from_pm(pm25: float) -> Optional[float]:
    """
    Turn raw sensor reading into AQI.
    Calculations converted from purpleair's javascript example at
    https://docs.google.com/document/d/15ijz94dXJ-YAZLi9iZ_RaBwrZ4KtYeCy08goGBwnbCU/edit
    """
    if pm25 < 0 or pm25 > 1000:
        print(f"PM2.5 {pm25} out of range")
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


def calc_aqi(cp: float, ih: float, il: float, bph: float, bpl: float) -> float:
    a = ih - il
    b = bph - bpl
    c = cp - bpl
    return round((a / b) * c + il)


def send_text_message(
    dest_phone_number: str,
    from_email: str,
    email_pw: str,
    aqi: float,
    label: str,
    thresh: int,
) -> None:
    import smtplib

    # Establish a secure session with gmail's outgoing SMTP server using your gmail account
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(from_email, email_pw)
    # Send text message through SMS gateway of destination number
    server.sendmail(
        from_email, f"{dest_phone_number}@vtext.com", message_to_send(label, aqi)
    )
    server.quit()
    message = f'Text sent at: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())} | AQI: {aqi} Threshold: {thresh}\n'
    write_to_log(message)


def message_to_send(x: str, y: float) -> str:
    return f"PM2.5 AQI at {x} is now {y}"


def write_to_log(msg: str, file: str = "log.txt") -> None:
    with open(file, "a") as f:
        f.write(msg)


def load_params(file: str = "params.yaml") -> Dict[str, Any]:
    with open(file) as f:
        params = yaml.safe_load(f)
    return params
