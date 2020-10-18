Meross Protocol Inspection
==========================

This section reports the outcomes of many hours of network sniffing, inspection and reverse engineering, in an
attempt to provide other developers enough information to build their client API/Libraries.

.. warning::
   It is explicitly forbidden to copy, republish this information without explicit consent from the Author.

.. note::
   There is no guarantee about the accuracy of the following information. Meross may update their
   firmware/protocol at any time, possibly making all the following information no more valid.

Client device pairing
---------------------

The pairing protocol of a new Meross device can be resumed as follows:

#. The user puts the device into pairing mode (basically pressing and holding the hardware button on the device)
#. The user uses the APP to configure the device and to use a specific WIFI and to bind it to a Meross account
#. The plug connects to the Wifi, and then connects to the Meross MQTT broker

Once the user puts the device into "pairing mode", the device will put itself into Access Point mode, setting up an
open Wifi network. The name of this network starts as "Meross_<STR1>_<STR2>". This allows the the App to recognize all
the Meross device that are available to be paired by simply scanning all the wifi networks and filtering via the
SSID prefix.

Now it starts the second phase of the pairing protocol. The app connects to the Wifi access point of the
device to pair, and obtain an IP address via a DHCP. The DHCP also pushes the default gateway route, that is
the IP address of the meross plug itself. At this point, the APP performs two separate HTTP posts against to the
plug, in sequence.

.. code-block::

    method: POST
    host: <PLUG_IP_ADDRESS>
    path: /config
    headers: "Content-Type: application/json"
    body:
        {
            "header": {
                "messageId": "{{MESSAGE_ID}}",
                "timestamp": {{TIMESTAMP}},
                "sign": "{{SIGNATURE}}",
                "method": "SET",
                "namespace": "Appliance.Config.Key"
            },
            "payload": {
                "key": {
                    "gateway": {
                        "host":"{{MQTT_HOST}}",
                        "port":"{{MQTT_PORT}}"
                    },
                    "key": "{{KEY}}",
                    "userId": "{{USER_ID}}"
                }
            }
        }

This POST message instructs the plug to use a specific gateway host/port as MQTT broker. It carries the userId
(which is numerical, but treated as string) and a secret key. The userId and the key parameters
are retrieved by the app itself by logging into the Meross account, via HTTP api. The aim of this request is to
tell the plug to which MQTT broker to connect and which are the credentials that should be used to do so.
Once sent, the PLUG won't try to connect to the MQTT broker, as it is still into "pairing mode". There is still another
step to perform in order to make it connect to the MQTT broker: setting the local Wifi connection parameters.

To do so, the APP sends another message to the plug device.

.. code-block::

    method: POST
    host: <PLUG_IP_ADDRESS>
    path: /config
    headers: "Content-Type: application/json"
    body:
        {
        "header": {
            "messageId": "{{MESSAGE_ID}}",
            "timestamp": {{TIMESTAMP}},
            "sign": "{{SIGNATURE}}",
            "method": "SET",
            "namespace": "Appliance.Config.Wifi"
        },
        "payload": {
            "wifi": {
                "ssid": "{{BASE64_ENCODED_SSID}}",
                "password": "{{BASE64_ENCODED_PASSWORD}}"
            }
        }
    }

.. warning::
   Since the plug configures an open WIFI and sends the base64 SSID-password to the plug, it is literally
   broadcasting the Wifi credentials to the neighborhood. This is a serious flaw in security.

Before sending this message, the APP asks the user to input the SSID and the password of the domestic WIFI connection
where the plug should connect to. Once obtained, the app builds up the message above and sends it to the plug.
At this point, the plug reboots itself and attempts to connect to the Wifi network. If successful, it tries to connect
to the MQTT broker (the one that has been configured in the first POST message), using the following credentials.

    username: <mac-address>

    password: <userId>_md5(<mac-address><key>)

.. note::
   The mac address should be in lower case, following the form XX:XX:XX:XX:XX:XX. The password is calculated as the
   numerical userId, followed by the underscore digit, followed by the md5 hex digest (in lower case) of the
   concatenated string <mac-address> + <key>, where the key and the userId have been retrieved by the APP at login
   time via HTTP API.

The plug assumes that the broker uses TLS secured connection, so it expects the broker to use SSL. However it seems
that the plug does not perform any kind of validation of the server certificate. The author was able to make a MSS210
plug to connect to its MQTT broker, which was serving a server certificate signed by an untrusted CA certificate.
The only check that is performed by the Meross client device is about the IP address/hostname of the server
certificate. In other words, the Common Name (CN) of the server certificate must match the IP address/hostname of the
MQTT broker where the device is connecting to.

.. warning::
   This is another important flaw. A simple DNS spoofing attack may de-route the device client to connect against
   a malicious mqtt server.


Meross MQTT architecture
---------------------

Most of the communication between the Meross App and the devices happens via a MQTT broker that Meross hosts (at the time of writing) on AWS cloud.
By inspecting the network traffic among the Meross App, the MQTT broker and the Meross devices, we identify the following **topics**.

.. image:: static/img/mqtt-subscriptions.png
   :width: 800
   :alt: Meross MQTT topics

From the image above, we can discriminate 4 different topics:

- */appliance/<device_uuid>/subscribe*
    Specific to every Meross appliance (as the *device_uuid* portion of the tropic is unique for every hardware device).
    It represents the topic from where the appliance pulls commands to be executed.

- */appliance/<device_uuid>/publish*
    Specific to every Meross appliance (as the *device_uuid* portion of the tropic is unique for every hardware device).
    It is the topic where the appliance publishes events (push notifications).

- */appliance/<user_id>/subscribe*
    Specific for user_id, it is the topic where push notifications are published.
    In general, the Meross App subscribes to this topic in order to update its state as events happen on the physical device.

- */appliance/<user_id>-<app_id>/publish*
    It is the topic to which the Meross App subscribes. It is used by the app to receive the response to commands sent to the appliance.

Flow: App commands
------------------

.. image:: static/img/mqtt-app-command-flow.png
   :width: 800
   :alt: App command flow

Flow: Push notifications
------------------------

.. image:: static/img/mqtt-device-event-flow.png
   :width: 800
   :alt: Device event flow
