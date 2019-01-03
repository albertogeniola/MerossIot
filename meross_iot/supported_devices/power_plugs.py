import paho.mqtt.client as mqtt
import ssl
import random
import string
import time
import json
import sys
import logging

from paho.mqtt import MQTTException
from threading import RLock, Condition, Event
from hashlib import md5
from enum import Enum
from logging import StreamHandler

l = logging.getLogger("meross_powerplug")
l.addHandler(StreamHandler(stream=sys.stdout))
l.setLevel(logging.DEBUG)

class ClientStatus(Enum):
    INITIALIZED = 1
    CONNECTING = 2
    CONNECTED = 3
    SUBSCRIBED = 4
    CONNECTION_DROPPED = 5

class Device:
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

    _status = None

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

        self._generate_client_and_app_id()

        # Password is calculated as the MD5 of USERID concatenated with KEY
        md5_hash = md5()
        clearpwd = "%s%s" % (self._user_id, self._key)
        md5_hash.update(clearpwd.encode("utf8"))
        hashed_password = md5_hash.hexdigest()

        # Start the mqtt client
        self._mqtt_client = mqtt.Client(client_id=self._client_id, protocol=mqtt.MQTTv311)  # ex. app-id -> app:08d4c9f99da40203ebc798a76512ec14
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_subscribe = self._on_subscribe
        self._mqtt_client.on_log = self._on_log
        self._mqtt_client.username_pw_set(username=self._user_id, password=hashed_password)
        self._mqtt_client.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
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
        l.info("Unsubscribed from topic")
        self._subscription_count.dec()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        l.info("Succesfully subscribed!")
        if self._subscription_count.inc() == 2:
            with self._waiting_subscribers_queue:
                self._set_status(ClientStatus.SUBSCRIBED)
                self._waiting_subscribers_queue.notify_all()

    def _on_connect(self, client, userdata, rc, other):
        l.info("Connected with result code %s" % str(rc))
        self._set_status(ClientStatus.SUBSCRIBED)

        self._set_status(ClientStatus.CONNECTED)

        self._client_request_topic = "/appliance/%s/subscribe" % self._uuid
        self._client_response_topic = "/app/%s-%s/subscribe" % (self._user_id, self._app_id)
        self._user_topic = "/app/%s/subscribe" % self._user_id

        # Subscribe to the relevant topics
        l.info("Subscribing to topics..." )
        client.subscribe(self._user_topic)
        client.subscribe(self._client_response_topic)

    # The callback for when a PUBLISH message is received from the server.
    def _on_message(self, client, userdata, msg):
        l.debug(msg.topic + " --> " + str(msg.payload))

        try:
            message = json.loads(str(msg.payload, "utf8"))
            header = message['header']

            message_hash = md5()
            strtohash = "%s%s%s" % (header['messageId'], self._key, header['timestamp'])
            message_hash.update(strtohash.encode("utf8"))
            expected_signature = message_hash.hexdigest().lower()

            if(header['sign'] != expected_signature):
                raise MQTTException('The signature did not match!')

            # If the message is the RESP for some previous action, process return the control to the "stopped" method.
            if header['messageId'] == self._waiting_message_id:
                with self._waiting_message_ack_queue:
                    self._ack_response = message
                    self._waiting_message_ack_queue.notify()

            # Otherwise process it accordingly
            elif self._message_from_self(message):
                if header['method'] == "PUSH" and 'payload' in message and 'toggle' in message['payload']:
                    self._handle_toggle(message)
                else:
                    l.debug("UNKNOWN msg received by %s" % self._uuid)
                    # if header['method'] == "PUSH":
                    # TODO
            else:
                # do nothing because the message was from a different device
                pass
        except Exception as e:
            l.debug("%s failed to process message because: %s" % (self._uuid, e))

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
                    "messageId": messageId, # Example: "122e3e47835fefcd8aaf22d13ce21859"
                    "method": method, # Example: "GET",
                    "namespace": namespace, # Example: "Appliance.System.All",
                    "payloadVersion": 1,
                    "sign": signature, # Example: "b4236ac6fb399e70c3d61e98fcb68b74",
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

    def _execute_cmd(self, method, namespace, payload):
        with self._waiting_subscribers_queue:
            while self._client_status != ClientStatus.SUBSCRIBED:
                self._waiting_subscribers_queue.wait()

            # Execute the command and retrieve the message-id
            self._waiting_message_id = self._mqtt_message(method, namespace, payload)

            # Wait synchronously until we get the ACK.
            with self._waiting_message_ack_queue:
                self._waiting_message_ack_queue.wait()

            return self._ack_response['payload']

    def _message_from_self(self, message):
        try:
            return 'from' in message['header'] and message['header']['from'].split('/')[2] == self._uuid
        except:
            return false

    def _handle_toggle(self, message):
        if 'onoff' in message['payload']['toggle']:
            self._status = (message['payload']['toggle']['onoff'] == 1)

    def get_sys_data(self):
        return self._execute_cmd("GET", "Appliance.System.All", {})

    def get_wifi_list(self):
        return self._execute_cmd("GET", "Appliance.Config.WifiList", {})

    def get_trace(self):
        return self._execute_cmd("GET", "Appliance.Config.Trace", {})

    def get_debug(self):
        return self._execute_cmd("GET", "Appliance.System.Debug", {})

    def get_abilities(self):
        return self._execute_cmd("GET", "Appliance.System.Ability", {})

    def get_report(self):
        return self._execute_cmd("GET", "Appliance.System.Report", {})

    def get_status(self):
        if self._status is None:
            self._status = self.get_sys_data()['all']['control']['toggle']['onoff'] == 1
        return self._status

    def device_id(self):
        return self._uuid

    def get_channels(self):
        return self._channels

    def turn_on(self):
        self._status = True
        payload = {"channel":0,"toggle":{"onoff":1}}
        return self._execute_cmd("SET", "Appliance.Control.Toggle", payload)

    def turn_off(self):
        self._status = False
        payload = {"channel":0,"toggle":{"onoff":0}}
        return self._execute_cmd("SET", "Appliance.Control.Toggle", payload)
      
class Mss310(Device):
    def get_power_consumptionX(self):
        return self._execute_cmd("GET", "Appliance.Control.ConsumptionX", {})

    def get_electricity(self):
        return self._execute_cmd("GET", "Appliance.Control.Electricity", {})

class Mss425e(Device):
    # TODO Implement for all channels
    def _handle_toggle(self, message):
        return None

    # TODO Implement for all channels
    def get_status(self):
        return None

    def turn_on(self):
        payload = {'togglex':{"onoff":1}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_off(self):
        payload = {'togglex':{"onoff":0}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_on_channel(self, channel):
        payload = {'togglex':{'channel':channel, 'onoff':1}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def turn_off_channel(self, channel):
        payload = {'togglex':{'channel':channel,'onoff': 0}}
        return self._execute_cmd("SET", "Appliance.Control.ToggleX", payload)

    def enable_usb(self):
        return self.turn_on_channel(4)

    def disable_usb(self):
        return self.turn_off_channel(4)

class Mss110(Device):
    pass

class AtomicCounter(object):
    _lock = None

    def __init__(self, initialValue):
        self._lock = RLock()
        self._val = initialValue

    def dec(self):
        with self._lock:
            self._val -= 1
            return self._val

    def inc(self):
        with self._lock:
            self._val += 1
            return self._val
