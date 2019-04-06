import json
import logging
import random
import ssl
import string
import sys
import time
from enum import Enum
from hashlib import md5
from logging import StreamHandler
from threading import RLock, Condition
import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from meross_iot.supported_devices.abilities import *
from meross_iot.supported_devices.exceptions.CommandTimeoutException import CommandTimeoutException

from meross_iot.utilities.synchronization import AtomicCounter

l = logging.getLogger("meross_powerplug")
h = StreamHandler(stream=sys.stdout)
h.setLevel(logging.DEBUG)
l.addHandler(h)
l.setLevel(logging.INFO)


LONG_TIMEOUT = 30.0  # For wifi scan
SHORT_TIMEOUT = 5.0  # For any other command


# Call this module to adjust the verbosity of the stream output. By default, only INFO is written to STDOUT log.
def set_debug_level(level):
    l.setLevel(level)


class ClientStatus(Enum):
    INITIALIZED = 1
    CONNECTING = 2
    CONNECTED = 3
    SUBSCRIBED = 4
    CONNECTION_DROPPED = 5


class GenericPlug:
    _status_lock = None
    _client_status = None

    _token = None
    _key = None
    _user_id = None
    _domain = None
    _port = 2001
    _channels = []

    _uuid = None
    _client_id = None
    _app_id = None

    # Device info
    _name = None
    _type = None
    _hwversion = None
    _fwversion = None

    # Topic name where the client should publish to its commands. Every client should have a dedicated one.
    _client_request_topic = None

    # Topic name in which the client retrieves its own responses from server.
    _client_response_topic = None

    # Topic where important notifications are pushed (needed if any other client is dealing with the same device)
    _user_topic = None

    # Paho mqtt client object
    _mqtt_client = None

    # Waiting condition used to wait for command ACKs
    _waiting_message_ack_queue = None
    _waiting_subscribers_queue = None
    _waiting_message_id = None

    _ack_response = None

    # Block for at most 10 seconds.
    _command_timeout = 10

    _error = None

    # Cached list of abilities
    _abilities = None

    # Dictionary {channel->status}
    _state = None

    def __init__(self,
                 token,
                 key,
                 user_id,
                 **kwords):

        self._status_lock = RLock()

        self._waiting_message_ack_queue = Condition()
        self._waiting_subscribers_queue = Condition()
        self._subscription_count = AtomicCounter(0)

        self._set_status(ClientStatus.INITIALIZED)

        self._token = token,
        self._key = key
        self._user_id = user_id
        self._uuid = kwords['uuid']
        if "domain" in kwords:
            self._domain = kwords['domain']
        else:
            self._domain = "eu-iot.meross.com"
        if "channels" in kwords:
            self._channels = kwords['channels']

        # Informations about device
        if "devName" in kwords:
            self._name = kwords['devName']
        if "deviceType" in kwords:
            self._type = kwords['deviceType']
        if "fmwareVersion" in kwords:
            self._fwversion = kwords['fmwareVersion']
        if "hdwareVersion" in kwords:
            self._hwversion = kwords['hdwareVersion']

        # Lookup port and certificate for MQTT server
        self._port = kwords.get('port', GenericPlug._port)
        self._ca_cert = kwords.get('ca_cert', None)

        self._generate_client_and_app_id()

        # Password is calculated as the MD5 of USERID concatenated with KEY
        md5_hash = md5()
        clearpwd = "%s%s" % (self._user_id, self._key)
        md5_hash.update(clearpwd.encode("utf8"))
        hashed_password = md5_hash.hexdigest()

        # Start the mqtt client
        self._mqtt_client = mqtt.Client(client_id=self._client_id,
                                        protocol=mqtt.MQTTv311)  # ex. app-id -> app:08d4c9f99da40203ebc798a76512ec14
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_subscribe = self._on_subscribe
        self._mqtt_client.on_log = self._on_log
        # Avoid login if user_id is None
        if self._user_id is not None:
            self._mqtt_client.username_pw_set(username=self._user_id,
                                              password=hashed_password)
        self._mqtt_client.tls_set(ca_certs=self._ca_cert, certfile=None,
                                  keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)

        self._mqtt_client.connect(self._domain, self._port, keepalive=30)
        self._set_status(ClientStatus.CONNECTING)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        self._mqtt_client.loop_start()

        with self._waiting_subscribers_queue:
            self._waiting_subscribers_queue.wait()
            if self._client_status != ClientStatus.SUBSCRIBED:
                # An error has occurred
                raise Exception(self._error)

        self.get_status()

    # Private methods used by the base class in order to handle basic protocol communication
    # --------------------------------------------------------------------------------------
    def _on_disconnect(self, client, userdata, rc):
        l.info("Disconnection detected. Reason: %s" % str(rc))

        # We should clean all the data structures.
        with self._status_lock:
            self._subscription_count = AtomicCounter(0)
            self._error = "Connection dropped by the server"
            self._set_status(ClientStatus.CONNECTION_DROPPED)

        with self._waiting_subscribers_queue:
            self._waiting_subscribers_queue.notify_all()

        with self._waiting_message_ack_queue:
            self._waiting_message_ack_queue.notify_all()

        if rc == mqtt.MQTT_ERR_SUCCESS:
            pass
        else:
            # TODO: Should we reconnect by calling again the client.loop_start() ?
            client.loop_stop()

    def _on_unsubscribe(self):
        l.debug("Unsubscribed from topic")
        self._subscription_count.dec()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        l.debug("Succesfully subscribed!")
        if self._subscription_count.inc() == 2:
            with self._waiting_subscribers_queue:
                self._set_status(ClientStatus.SUBSCRIBED)
                self._waiting_subscribers_queue.notify_all()

    def _on_connect(self, client, userdata, rc, other):
        l.debug("Connected with result code %s" % str(rc))
        self._set_status(ClientStatus.SUBSCRIBED)

        self._set_status(ClientStatus.CONNECTED)

        self._client_request_topic = "/appliance/%s/subscribe" % self._uuid
        self._client_response_topic = "/app/%s-%s/subscribe" % (self._user_id, self._app_id)
        self._user_topic = "/app/%s/subscribe" % self._user_id

        # Subscribe to the relevant topics
        l.debug("Subscribing to topics...")
        client.subscribe(self._user_topic)
        client.subscribe(self._client_response_topic)

    # The callback for when a PUBLISH message is received from the server.
    # --------------------------------------------------------------------
    def _on_message(self, client, userdata, msg):
        l.debug(msg.topic + " --> " + str(msg.payload))

        try:
            message = json.loads(str(msg.payload, "utf8"))
            header = message['header']

            message_hash = md5()
            strtohash = "%s%s%s" % (header['messageId'], self._key, header['timestamp'])
            message_hash.update(strtohash.encode("utf8"))
            expected_signature = message_hash.hexdigest().lower()

            if (header['sign'] != expected_signature):
                raise MQTTException('The signature did not match!')

            # If the message is the RESP for some previous action, process return the control to the "stopped" method.
            if header['messageId'] == self._waiting_message_id:
                with self._waiting_message_ack_queue:
                    self._ack_response = message
                    self._waiting_message_ack_queue.notify()

            # Otherwise process it accordingly
            if self._message_from_self(message):
                if header['method'] == "PUSH" and 'namespace' in header:
                    self._handle_namespace_payload(header['namespace'], message['payload'])
                else:
                    l.debug("UNKNOWN msg received by %s" % self._uuid)
            else:
                # do nothing because the message was from a different device
                pass
        except Exception as e:
            l.error("%s failed to process message because: %s" % (self._uuid, e))

    def _on_log(self, client, userdata, level, buf):
        # print("Data: %s - Buff: %s" % (userdata, buf))
        pass

    def _generate_client_and_app_id(self):
        md5_hash = md5()
        md5_hash.update(("%s%s" % ("API", self._uuid)).encode("utf8"))
        self._app_id = md5_hash.hexdigest()
        self._client_id = 'app:%s' % md5_hash.hexdigest()

    def _mqtt_message(self, method, namespace, payload):
        # Generate a random 16 byte string
        randomstring = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))

        # Hash it as md5
        md5_hash = md5()
        md5_hash.update(randomstring.encode('utf8'))
        messageId = md5_hash.hexdigest().lower()
        timestamp = int(round(time.time()))

        # Hash the messageId, the key and the timestamp
        md5_hash = md5()
        strtohash = "%s%s%s" % (messageId, self._key, timestamp)
        md5_hash.update(strtohash.encode("utf8"))
        signature = md5_hash.hexdigest().lower()

        data = {
            "header":
                {
                    "from": self._client_response_topic,
                    "messageId": messageId,  # Example: "122e3e47835fefcd8aaf22d13ce21859"
                    "method": method,  # Example: "GET",
                    "namespace": namespace,  # Example: "Appliance.System.All",
                    "payloadVersion": 1,
                    "sign": signature,  # Example: "b4236ac6fb399e70c3d61e98fcb68b74",
                    "timestamp": timestamp
                },
            "payload": payload
        }
        strdata = json.dumps(data)
        l.debug("--> %s" % strdata)
        self._mqtt_client.publish(topic=self._client_request_topic, payload=strdata.encode("utf-8"))
        return messageId

    def _wait_for_status(self, status):
        ok = False
        while not ok:
            if not self._status_lock.acquire(True, self._command_timeout):
                raise TimeoutError()
            ok = status == self._client_status
            self._status_lock.release()

    def _set_status(self, status):
        with self._status_lock:
            self._client_status = status

    def _execute_cmd(self, method, namespace, payload, timeout=SHORT_TIMEOUT):
        # Before executing any command, we need to be subscribed to the MQTT topics where to listen for ACKS.
        with self._waiting_subscribers_queue:
            while self._client_status != ClientStatus.SUBSCRIBED:
                self._waiting_subscribers_queue.wait()

            # Execute the command and retrieve the message-id
            self._waiting_message_id = self._mqtt_message(method, namespace, payload)

            # Wait synchronously until we get the ACK.
            with self._waiting_message_ack_queue:
                if not self._waiting_message_ack_queue.wait(timeout=timeout):
                    # Timeout expired.
                    raise CommandTimeoutException()

            return self._ack_response['payload']

    def _message_from_self(self, message):
        try:
            return 'from' in message['header'] and message['header']['from'].split('/')[2] == self._uuid
        except:
            return False

    def _get_consumptionx(self):
        return self._execute_cmd("GET", CONSUMPTIONX, {})

    def _get_electricity(self):
        return self._execute_cmd("GET", ELECTRICITY, {})

    def _toggle(self, status):
        payload = {"channel": 0, "toggle": {"onoff": status}}
        return self._execute_cmd("SET", TOGGLE, payload)

    def _togglex(self, channel, status):
        payload = {'togglex': {"onoff": status, "channel": channel}}
        return self._execute_cmd("SET", TOGGLEX, payload)

    def _channel_control_impl(self, channel, status):
        if TOGGLE in self.get_abilities():
            return self._toggle(status)
        elif TOGGLEX in self.get_abilities():
            return self._togglex(channel, status)
        else:
            raise Exception("The current device does not support neither TOGGLE nor TOGGLEX.")

    def _handle_namespace_payload(self, namespace, payload):
        with self._status_lock:
            if namespace == TOGGLE:
                self._state[0] = payload['toggle']['onoff'] == 1

            elif namespace == TOGGLEX:
                if isinstance(payload['togglex'], list):
                    for c in payload['togglex']:
                        channel_index = c['channel']
                        self._state[channel_index] = c['onoff'] == 1
                elif isinstance(payload['togglex'], dict):
                    channel_index = payload['togglex']['channel']
                    self._state[channel_index] = payload['togglex']['onoff'] == 1
            else:
                raise Exception("Unknown/Unsupported namespace/command: %s" % namespace)

    def _get_status_impl(self):
        res = {}
        data = self.get_sys_data()['all']
        if 'digest' in data:
            for c in data['digest']['togglex']:
                res[c['channel']] = c['onoff'] == 1
        elif 'control' in data:
            res[0] = data['control']['toggle']['onoff'] == 1
        return res

    def _get_channel_id(self, channel):
        # Otherwise, if the passed channel looks like the channel spec, lookup its array indexindex
        if channel in self._channels:
            return self._channels.index(channel)

        # if a channel name is given, lookup the channel id from the name
        if isinstance(channel, str):
            for i, c in enumerate(self.get_channels()):
                if c['devName'] == channel:
                    return c['channel']

        # If an integer is given assume that is the channel ID
        elif isinstance(channel, int):
            return channel

        # In other cases return an error
        raise Exception("Invalid channel specified.")

    def __str__(self):
        basic_info = "%s (%s, %d channels, HW %s, FW %s): " % (
            self._name,
            self._type,
            len(self._channels),
            self._hwversion,
            self._fwversion
        )

        for i, c in enumerate(self._channels):
            channel_type = c['type'] if 'type' in c else "Master" if c == {} else "Unknown"
            channel_state = "On" if self.get_status(i) else "Off"
            channel_desc = "%s=%s" % (channel_type, channel_state)
            basic_info += channel_desc + ", "

        return basic_info

    def supports_consumption_reading(self):
        return CONSUMPTIONX in self.get_abilities()

    def supports_electricity_reading(self):
        return ELECTRICITY in self.get_abilities()

    def get_power_consumption(self):
        if CONSUMPTIONX in self.get_abilities():
            return self._get_consumptionx()
        else:
            # Not supported!
            return None

    def get_electricity(self):
        if ELECTRICITY in self.get_abilities():
            return self._get_electricity()
        else:
            # Not supported!
            return None

    def device_id(self):
        return self._uuid

    def get_sys_data(self):
        return self._execute_cmd("GET", "Appliance.System.All", {})

    def get_channels(self):
        return self._channels

    def get_wifi_list(self):
        return self._execute_cmd("GET", "Appliance.Config.WifiList", {}, timeout=LONG_TIMEOUT)

    def get_trace(self):
        return self._execute_cmd("GET", "Appliance.Config.Trace", {})

    def get_debug(self):
        return self._execute_cmd("GET", "Appliance.System.Debug", {})

    def get_abilities(self):
        # TODO: Make this cached value expire after a bit...
        if self._abilities is None:
            self._abilities = self._execute_cmd("GET", "Appliance.System.Ability", {})['ability']
        return self._abilities

    def get_report(self):
        return self._execute_cmd("GET", "Appliance.System.Report", {})

    def get_channel_status(self, channel):
        c = self._get_channel_id(channel)
        return self.get_status(c)

    def turn_on_channel(self, channel):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 1)

    def turn_off_channel(self, channel):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 0)

    def turn_on(self, channel=0):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 1)

    def turn_off(self, channel=0):
        c = self._get_channel_id(channel)
        return self._channel_control_impl(c, 0)

    def get_status(self, channel=0):
        # In order to optimize the network traffic, we don't call the get_status() api at every request.
        # On the contrary, we only call it the first time. Then, the rest of the API will silently listen
        # for state changes and will automatically update the self._state structure listening for
        # messages of the device.
        # Such approach, however, has a side effect. If we call TOGGLE/TOGGLEX and immediately after we call
        # get_status(), the reported status will be still the old one. This is a race condition because the
        # "status" RESPONSE will be delivered some time after the TOGGLE REQUEST. It's not a big issue for now,
        # and synchronizing the two things would be inefficient and probably not very useful.
        # Just remember to wait some time before testing the status of the item after a toggle.
        with self._status_lock:
            c = self._get_channel_id(channel)
            if self._state is None:
                self._state = self._get_status_impl()
            return self._state[c]

    def get_usb_channel_index(self):
        # Look for the usb channel
        for i, c in enumerate(self.get_channels()):
            if 'type' in c and c['type'] == 'USB':
                return i
        return None

    def enable_usb(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.turn_on_channel(c)

    def disable_usb(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.turn_off_channel(c)

    def get_usb_status(self):
        c = self.get_usb_channel_index()
        if c is None:
            return
        else:
            return self.get_channel_status(c)
