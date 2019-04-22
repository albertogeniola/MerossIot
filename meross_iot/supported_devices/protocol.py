import random
import ssl
import string
from threading import RLock, Condition
import paho.mqtt.client as mqtt
from paho.mqtt import MQTTException
from meross_iot.supported_devices.exceptions.CommandTimeoutException import CommandTimeoutException
from meross_iot.supported_devices.exceptions.ConnectionDroppedException import ConnectionDroppedException
from meross_iot.utilities.synchronization import AtomicCounter
import json
import time
from hashlib import md5
import logging
import sys
from logging import StreamHandler

from abc import ABC, abstractmethod
from enum import Enum


l = logging.getLogger("meross_protocol")
h = StreamHandler(stream=sys.stdout)
h.setLevel(logging.DEBUG)
l.addHandler(h)
l.setLevel(logging.INFO)
LONG_TIMEOUT = 30.0  # For wifi scan
SHORT_TIMEOUT = 10.0  # For any other command


# Call this module to adjust the verbosity of the stream output. By default, only INFO is written to STDOUT log.
def set_debug_level(level):
    l.setLevel(level)


class ClientStatus(Enum):
    INITIALIZED = 1
    CONNECTING = 2
    CONNECTED = 3
    SUBSCRIBED = 4
    CONNECTION_DROPPED = 5


class AbstractMerossDevice(ABC):
    # The connection status of the device is represented by the following variable.
    # It is protected by the following variable, called _client_connection_status_lock.
    # The child classes should never change/access these variables directly, though.
    _client_connection_status = None
    _client_connection_status_lock = None

    # Device info and connection parameters
    _token = None
    _key = None
    _user_id = None
    _uuid = None
    _client_id = None
    _app_id = None
    _name = None
    _type = None
    _hwversion = None
    _fwversion = None

    # Connection info
    _domain = None
    _port = 2001

    # Topic name where the client should publish to its commands. Every client should have a dedicated one.
    _client_request_topic = None

    # Topic name in which the client retrieves its own responses from server.
    _client_response_topic = None

    # Topic where important notifications are pushed (needed if any other client is dealing with the same device)
    _user_topic = None

    # Paho mqtt client object
    _mqtt_client = None

    # Waiting condition used to wait for command ACKs
    _waiting_message_ack_condition = None
    _connection_status_condition = None
    _waiting_message_id = None

    _ack_response = None
    _error = None

    # Cached list of abilities
    _abilities = None

    def __init__(self,
                 token,
                 key,
                 user_id,
                 **kwords):

        self._client_connection_status_lock = RLock()
        self._connection_status_condition = Condition(self._client_connection_status_lock)

        self._waiting_message_ack_condition = Condition()
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
        self._port = kwords.get('port', AbstractMerossDevice._port)
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

        with self._connection_status_condition:
            self._connection_status_condition.wait()
            if self._client_connection_status != ClientStatus.SUBSCRIBED:
                # An error has occurred
                raise Exception(self._error)

        self.get_status()

    # ------------------------------------------------------------------------------------------------
    # MQTT Handlers
    # ------------------------------------------------------------------------------------------------
    def _on_disconnect(self, client, userdata, rc):
        l.info("Disconnection detected. Reason: %s" % str(rc))

        # We should clean all the data structures.
        with self._client_connection_status_lock:
            self._subscription_count = AtomicCounter(0)
            self._error = "Connection dropped by the server"
            self._set_status(ClientStatus.CONNECTION_DROPPED)

        with self._connection_status_condition:
            self._connection_status_condition.notify_all()

        with self._waiting_message_ack_condition:
            self._waiting_message_ack_condition.notify_all()

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
            with self._connection_status_condition:
                self._set_status(ClientStatus.SUBSCRIBED)
                self._connection_status_condition.notify_all()

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

    def _on_message(self, client, userdata, msg):
        """
        This handler is called when a message is received from the MQTT broker, on the subscribed topics.
        The current implementation checks the validity of the message itself, byu verifying its signature.
        If the message is an ACK to some precious REQUEST, this method will simply notify the waiting thread.
        Otherwise, if the message is directed to the same device, but issued from another client, the
        _handle_namespace_payload() implementation is called on the base class.

        :param client: is the MQTT client reference, useful to respond back
        :param userdata: metadata about the received data
        :param msg: message that was received
        :return: nothing, it simply handles the message accordingly.
        """
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
            processed = False
            with self._waiting_message_ack_condition:
                if header['messageId'] == self._waiting_message_id:
                    self._ack_response = message
                    self._waiting_message_ack_condition.notify()

            # If the current client was not waiting for the received message, check if it's still something
            # we should process (i.e. an update from another client). If so, process it accordingly.
            if not processed and self._message_from_self(message):
                if header['method'] == "PUSH" and 'namespace' in header:
                    self._handle_namespace_payload(header['namespace'], message['payload'])
                else:
                    l.debug("The following message was unhandled: %s" % message)
            else:
                # do nothing because the message was from a different device
                pass

        except Exception as e:
            l.exception("%s failed to process message." % self._uuid)

    def _on_log(self, client, userdata, level, buf):
        # print("Data: %s - Buff: %s" % (userdata, buf))
        pass

    # ------------------------------------------------------------------------------------------------
    # State Helpers
    # ------------------------------------------------------------------------------------------------
    def _set_status(self, status):
        with self._client_connection_status_lock:
            self._client_connection_status = status

    # ------------------------------------------------------------------------------------------------
    # Protocol Handlers
    # ------------------------------------------------------------------------------------------------
    def _execute_cmd(self, method, namespace, payload, timeout=SHORT_TIMEOUT):
        # Before executing any command, we need to be subscribed to the MQTT topics where to listen to ACKS.
        with self._connection_status_condition:
            while self._client_connection_status in (ClientStatus.CONNECTED, ClientStatus.CONNECTING):
                l.warning("The device is still connecting. Waiting until it connects...")
                self._connection_status_condition.wait()

            # If the connection was previously dropped, we need to take counter-measures here.
            if self._client_connection_status != ClientStatus.SUBSCRIBED:
                #TODO: connection retry?
                raise ConnectionDroppedException("The MQTT connection was dropped at some point.")

            # Execute the command and retrieve the message-id
            self._waiting_message_id = self._mqtt_message(method, namespace, payload)

        # Wait synchronously until we get the ACK.
        with self._waiting_message_ack_condition:
            if not self._waiting_message_ack_condition.wait(timeout=timeout):
                # Timeout expired. Give up waiting for that message_id.
                self._waiting_message_id = None
                raise CommandTimeoutException("A timeout occurred while waiting fot the ACK.")

        with self._connection_status_condition:
            # Check for disconnections. In case the connection was dropped before the ack is received,
            # we should ignore that.
            if self._client_connection_status != ClientStatus.SUBSCRIBED:
                #TODO: connection retry?
                raise ConnectionDroppedException("The MQTT connection was dropped at some point.")

        return self._ack_response['payload']

    def _message_from_self(self, message):
        try:
            return 'from' in message['header'] and message['header']['from'].split('/')[2] == self._uuid
        except:
            return False

    # ------------------------------------------------------------------------------------------------
    # Protocol utilities
    # ------------------------------------------------------------------------------------------------
    def _mqtt_message(self, method, namespace, payload):
        """
        Sends a message to the Meross MQTT broker, respecting the protocol payload.
        :param method:
        :param namespace:
        :param payload:
        :return:
        """

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

    def _generate_client_and_app_id(self):
        md5_hash = md5()
        md5_hash.update(("%s%s" % ("API", self._uuid)).encode("utf8"))
        self._app_id = md5_hash.hexdigest()
        self._client_id = 'app:%s' % md5_hash.hexdigest()

    def device_id(self):
        return self._uuid

    @abstractmethod
    def _handle_namespace_payload(self, namespace, message):
        """
        Handles messages coming from the device. This method should be implemented by the base class in order
        to catch status changes issued by other clients (i.e. the Meross app on the user's device).
        :param namespace:
        :param message:
        :return:
        """
        pass

    @abstractmethod
    def get_status(self):
        pass

    def get_sys_data(self):
        return self._execute_cmd("GET", "Appliance.System.All", {})

    def get_abilities(self):
        # TODO: Make this cached value expire after a bit...
        if self._abilities is None:
            self._abilities = self._execute_cmd("GET", "Appliance.System.Ability", {})['ability']
        return self._abilities

    def get_report(self):
        return self._execute_cmd("GET", "Appliance.System.Report", {})

