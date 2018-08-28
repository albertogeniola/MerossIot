import paho.mqtt.client as mqtt
import ssl
import random
import string
import time
import json
from threading import RLock, Condition
from hashlib import md5
from enum import Enum, auto


class ClientStatus(Enum):
    INITIALIZED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    SUBSCRIBED = auto()
    CONNECTION_DROPPED = auto()


class  Mss310:
    _status_lock = None
    _client_status = None

    _token = None
    _key = None
    _user_id = None

    _uuid = None
    _client_id = None
    _app_id = None

    _client_request_topic = None # Seems to the the topic dedicated where the client should publish to. Every client should have one.
    _client_response_topic = None  # Seems to be the topic in which the client retrieves his own responses from server
    _user_topic = None # Seems to be the topic where important notifications are pushed (needed if any other client is dealing with the same device)

    _channel = None

    _ack_received = None
    _waiting_message_id = None
    _ack_response = None

    # Block for at most 10 seconds.
    _command_timeout = 10

    def __init__(self,
                 token,
                 key,
                 user_id,
                 **kwords):

        self._status_lock = RLock()

        self._ack_received = Condition()
        self._waiting_subscribers = Condition()

        self._set_status(ClientStatus.INITIALIZED)

        self._token = token,
        self._key = key
        self._user_id = user_id
        self._uuid = kwords['uuid']

        self._generate_client_and_app_id()

        # Password is calculated as the MD5 of USERID concatenated with KEY
        md5_hash = md5()
        clearpwd = "%s%s" % (self._user_id, self._key)
        md5_hash.update(clearpwd.encode("utf8"))
        hashed_password = md5_hash.hexdigest()

        # Start the mqtt client
        self._channel = mqtt.Client(client_id=self._client_id, protocol=mqtt.MQTTv311)  # ex. app-id -> app:08d4c9f99da40203ebc798a76512ec14
        self._channel.on_connect = self._on_connect
        self._channel.on_message = self._on_message
        self._channel.on_disconnect = self._on_disconnect
        self._channel.on_log = self._on_log
        self._channel.username_pw_set(username=self._user_id, password=hashed_password)
        self._channel.tls_set(ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                       tls_version=ssl.PROTOCOL_TLS,
                       ciphers=None)


        self._channel.connect("eu-iot.meross.com", 2001, keepalive=30)
        self._set_status(ClientStatus.CONNECTING)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        self._channel.loop_start()

    def _on_disconnect(self, client, userdata, rc):
        if rc == mqtt.MQTT_ERR_SUCCESS:
            self._set_status(ClientStatus.DISCONNECTED)
        else:
            self._set_status(ClientStatus.CONNECTION_DROPPED)
            # TODO: Should we reconnect by calling again the client.loop_start() ?
            client.loop_stop()

    # The callback for when the client receives a CONNACK response from the server.
    def _on_connect(self, client, userdata, rc, other):
        print("Connected with result code " + str(rc))
        self._set_status(ClientStatus.SUBSCRIBED)

        self._set_status(ClientStatus.CONNECTED)

        self._client_request_topic = "/appliance/%s/subscribe" % self._uuid
        self._client_response_topic = "/app/%s-%s/subscribe" % (self._user_id, self._app_id)
        self._user_topic = "/app/%s/subscribe" % self._user_id

        # Subscribe to the relevant topics
        client.subscribe(self._user_topic)
        client.subscribe(self._client_response_topic)

        self._set_status(ClientStatus.SUBSCRIBED)
        with self._waiting_subscribers:
            self._waiting_subscribers.notify_all()

    # The callback for when a PUBLISH message is received from the server.
    def _on_message(self, client, userdata, msg):
        print(msg.topic + " --> " + str(msg.payload))

        try :
            message = json.loads(str(msg.payload, "utf8"))

            # If the message is the RESP for some previous action, process return the control to the "stopped" method.
            if message['header']['messageId'] == self._waiting_message_id:
                with self._ack_received:
                    self._msg_response = message
                    self._ack_received.notify()

            # Otherwise process it accordingly
            else:
                print("UNKNOWN msg = %s" % message)
                # if message['header']['method'] == "PUSH":
                # TODO
        except:
            # TODO
            print("UNKNOWN2")


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
        print("--> %s" % strdata)
        self._channel.publish(topic=self._client_request_topic, payload=strdata.encode("utf-8"))
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
        with self._waiting_subscribers:
            while self._client_status != ClientStatus.SUBSCRIBED:
                self._waiting_subscribers.wait()

            # Execute the command and retrieve the message-id
            self._waiting_message_id = self._mqtt_message(method, namespace, payload)

            # Wait synchronously until we get the ACK.
            with self._ack_received:
                self._ack_received.wait()

            return self._ack_response

    def poll_sys_data(self):
        return self._execute_cmd("GET", "Appliance.System.All", {})

    def turn_on(self):
        payload = {"channel":0,"toggle":{"onoff":1}}
        return self._execute_cmd("SET", "Appliance.Control.Toggle", payload)

    def turn_off(self):
        payload = {"channel":0,"toggle":{"onoff":0}}
        return self._execute_cmd("SET", "Appliance.Control.Toggle", payload)