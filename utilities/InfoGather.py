from meross_iot.api import MerossHttpClient
import csv, io

EMAIL = 'YOUR_EMAIL'
PASSWORD = 'YOUR_PASSWORD'

client = MerossHttpClient(email=EMAIL, password=PASSWORD)
devices = client.list_supported_devices()


def sanitize_personal_info(d):
    if isinstance(d, dict):
        for key, value in d.items():
            k = key.lower()

            if isinstance(value, dict):
                sanitize_personal_info(value)
            elif isinstance(value, str) and (k == 'uuid' or k=='macaddress' or k == 'wifimac' or k == 'userid' or k=='bssid' or k =='ssid'):
                d[key] = 'X'
    elif isinstance(d, list):
        for k in d:
            sanitize_personal_info(k)

    return d


if __name__ == '__main__':
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    for d in devices:
        # TODO: purge mac, user IDS and IPs from responses.
        r = []
        r.append(d._type)
        r.append(d._hwversion)
        r.append(d._fwversion)
        r.append(sanitize_personal_info(d.get_sys_data()))
        r.append(sanitize_personal_info(d.get_channels()))

        abilities = d.get_abilities()
        r.append(sanitize_personal_info(abilities))

        if 'Appliance.Control.Electricity' in abilities['ability'].keys():
            r.append(sanitize_personal_info(d.get_electricity()))
        else:
            r.append(None)

        if 'Appliance.Control.ConsumptionX' in abilities['ability'].keys():
            r.append(sanitize_personal_info(d.get_power_consumptionX()))
        else:
            r.append(None)

        r.append(sanitize_personal_info(d.get_trace()))

        writer.writerow(r)

    print(str(output.getvalue()))