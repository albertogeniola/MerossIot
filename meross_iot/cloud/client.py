from hashlib import md5
import string
from threading import Event, RLock
import json
import uuid as UUID
import ssl
import random
import copy
import time
from meross_iot.cloud.timeouts import SHORT_TIMEOUT
from meross_iot.cloud.exceptions.CommandTimeoutException import CommandTimeoutException
from meross_iot.logger import CONNECTION_MANAGER_LOGGER as l
import paho.mqtt.client as mqtt
from meross_iot.credentials import MerossCloudCreds
from meross_iot.cloud.client_status import ClientStatus
from meross_iot.cloud.connection import ConnectionStatusManager
from meross_iot.utilities.synchronization import AtomicCounter
from meross_iot.logger import NETWORK_DATA as networkl


def build_client_request_topic(client_uuid):
    return "/appliance/%s/subscribe" % client_uuid


class PendingMessageResponse(object):
    """
    This class is used as an Handle for mqtt messages that expect an ACK back.
    When a callback is passed to the constructor, this object is configured as an "async" waiter.
    Instead, passing a None callback, makes this object to act as a synchronously waiter.
    It is meant to be used internally by the library, in order to handle ACK waiting and callback calling.
    Note that this object is not thread safe.
    """
    _message_id = None
    _callback = None
    _event = None
    _response = None
    _error = None

    def __init__(self, message_id, callback=None):
        self._message_id = message_id

        # Only instantiate an event if no callback has been specified
        if callback is None:
            self._event = Event()
        else:
            self._callback = callback

    def wait_for_response(self, timeout=SHORT_TIMEOUT):
        """
        This method blocks until an ACK/RESPONSE message is received for the corresponding message_id that it refers
        to. Note that this method only works when the user is synchronously waiting for the response message.
        This method raises an exception if invoked when a callback was specified in the constructor.
        :param timeout:
        :return:
        """
        if self._event is None:
            raise Exception("Error: you can invoke this method only if you don't use a callback (i.e. sync invocation)")

        # Wait until we receive the message.
        # If timeout occurs, return failure and None as received message.
        success = self._event.wait(timeout=timeout)
        return success, self._response

    def notify_message_received(self, error=None, response=None):
        self._response = copy.deepcopy(response)
        self._error = error

        if self._event is not None:
            self._event.set()
        elif self._callback is not None:
            try:
                self._callback(self._error, self._response)
            except:
                l.exception("Unhandled error occurred while executing the callback")


class MerossCloudClient(object):
    # Meross Cloud credentials, which are provided by the HTTP Api.
    _cloud_creds = None

    # Connection info
    connection_status = None
    _domain = None
    _port = 2001
    _ca_cert = None

    # App and client ID
    _app_id = None
    _client_id = None

    # Paho mqtt client object
    _mqtt_client = None

    # Callback to be invoked every time a push notification is received from the MQTT broker
    _push_message_callback = None

    # This dictionary is used to keep track of messages issued to the broker that are waiting for an ACK
    # The key is the message_id, the value is the PendingMessageResponse object.
    # Access to this resource is protected with exclusive locking
    _pending_response_messages = None
    _pending_responses_lock = None

    def __init__(self,
                 cloud_credentials,             # type: MerossCloudCreds
                 push_message_callback=None,    # type: callable
                 **kwords):

        self.connection_status = ConnectionStatusManager()
        self._cloud_creds = cloud_credentials
        self._pending_response_messages = dict()
        self._pending_responses_lock = RLock()
        self._push_message_callback = push_message_callback
        self._subscription_count = AtomicCounter(0)

        if "domain" in kwords:
            self._domain = kwords['domain']
        else:
            self._domain = "iot.meross.com"

        # Lookup port and certificate for MQTT server
        self._port = kwords.get('port', MerossCloudClient._port)
        self._ca_cert = kwords.get('ca_cert', None)

        self._generate_client_and_app_id()

        # Password is calculated as the MD5 of USERID concatenated with KEY
        md5_hash = md5()
        clearpwd = "%s%s" % (self._cloud_creds.user_id, self._cloud_creds.key)
        md5_hash.update(clearpwd.encode("utf8"))
        hashed_password = md5_hash.hexdigest()

        # Start the mqtt client
        self._mqtt_client = mqtt.Client(client_id=self._client_id,
                                        protocol=mqtt.MQTTv311)  # ex. app-id -> app:08d4c9f99da40203ebc798a76512ec14
        self._mqtt_client.on_connect = self._on_connect
        self._mqtt_client.on_message = self._on_message
        self._mqtt_client.on_disconnect = self._on_disconnect
        self._mqtt_client.on_subscribe = self._on_subscribe

        # Avoid login if user_id is None
        if self._cloud_creds.user_id is not None:
            self._mqtt_client.username_pw_set(username=self._cloud_creds.user_id,
                                              password=hashed_password)
        self._mqtt_client.tls_set(ca_certs=self._ca_cert, certfile=None,
                                  keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                  tls_version=ssl.PROTOCOL_TLS,
                                  ciphers=None)

    def close(self):
        l.info("Closing the MQTT connection...")
        self._mqtt_client.disconnect()
        l.debug("Waiting for the client to disconnect...")
        self.connection_status.wait_for_status(ClientStatus.CONNECTION_DROPPED)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        l.debug("Stopping the MQTT looper.")
        self._mqtt_client.loop_stop(True)

        l.info("Client has been fully disconnected.")

    def connect(self):
        """
        Starts the connection to the MQTT broker
        :return:
        """
        l.info("Initializing the MQTT connection...")
        self._mqtt_client.connect(self._domain, self._port, keepalive=30)
        self.connection_status.update_status(ClientStatus.CONNECTING)

        # Starts a new thread that handles mqtt protocol and calls us back via callbacks
        l.debug("(Re)Starting the MQTT looper.")
        self._mqtt_client.loop_stop(True)
        self._mqtt_client.loop_start()

        l.debug("Waiting for the client to connect...")
        self.connection_status.wait_for_status(ClientStatus.SUBSCRIBED)
        l.info("Client connected to MQTT broker and subscribed to relevant topics.")

    # ------------------------------------------------------------------------------------------------
    # MQTT Handlers
    # ------------------------------------------------------------------------------------------------
    def _on_disconnect(self, client, userdata, rc):
        l.info("Disconnection detected. Reason: %s" % str(rc))

        # When the mqtt connection is dropped, we need to reset the subscription counter.
        self._subscription_count = AtomicCounter(0)
        self.connection_status.update_status(ClientStatus.CONNECTION_DROPPED)

        # TODO: should we handle disconnection in some way at this level?

        if rc == mqtt.MQTT_ERR_SUCCESS:
            pass
        else:
            client.loop_stop(True)

    def _on_unsubscribe(self):
        l.debug("Unsubscribed from topic")
        self._subscription_count.dec()

    def _on_subscribe(self, client, userdata, mid, granted_qos):
        l.debug("Succesfully subscribed to topic. Subscription count: %d" % self._subscription_count.get())
        if self._subscription_count.inc() == 2:
            self.connection_status.update_status(ClientStatus.SUBSCRIBED)

    def _on_connect(self, client, userdata, rc, other):
        l.debug("Connected with result code %s" % str(rc))
        self.connection_status.update_status(ClientStatus.CONNECTED)

        self._client_response_topic = "/app/%s-%s/subscribe" % (self._cloud_creds.user_id, self._app_id)
        self._user_topic = "/app/%s/subscribe" % self._cloud_creds.user_id

        # Subscribe to the relevant topics
        l.debug("Subscribing to topics...")
        client.subscribe(self._user_topic)
        client.subscribe(self._client_response_topic)

    def _on_message(self, client, userdata, msg):
        """
        This handler is called when a message is received from the MQTT broker, on the subscribed topics.
        The current implementation checks the validity of the message itself, by verifying its signature.

        :param client: is the MQTT client reference, useful to respond back
        :param userdata: metadata about the received data
        :param msg: message that was received
        :return: nothing, it simply handles the message accordingly.
        """
        networkl.debug(msg.topic + " --> " + str(msg.payload))

        try:
            message = json.loads(str(msg.payload, "utf8"))
            header = message['header']

            message_hash = md5()
            strtohash = "%s%s%s" % (header['messageId'], self._cloud_creds.key, header['timestamp'])
            message_hash.update(strtohash.encode("utf8"))
            expected_signature = message_hash.hexdigest().lower()

            if header['sign'] != expected_signature:
                # TODO: custom exception for invalid signature
                raise Exception('The signature did not match!')

            # Check if there is any thread waiting for this message or if there is a callback that we need to invoke.
            # If so, do it here.
            handle = None
            with self._pending_responses_lock:
                msg_id = header['messageId']
                handle = self._pending_response_messages.get(msg_id)

            from_myself = False
            if handle is not None:
                # There was a handle for this message-id. It means it is a response message to some
                # request performed by the library itself.
                from_myself = True
                try:
                    l.debug("Calling handle event handler for message %s" % msg_id)
                    # Call the handler
                    handle.notify_message_received(error=None, response=message)
                    l.debug("Done handler for message %s" % msg_id)

                    # Remove the message from the pending queue
                    with self._pending_responses_lock:
                        del self._pending_response_messages[msg_id]
                except:
                    l.exception("Error occurred while invoking message handler")

            # Let's also catch all the "PUSH" notifications and dispatch them to the push_notification_callback.
            if self._push_message_callback is not None and header['method'] == "PUSH" and 'namespace' in header:
                self._push_message_callback(message, from_myself=from_myself)

        except Exception:
            l.exception("Failed to process message.")

    # ------------------------------------------------------------------------------------------------
    # Protocol Handlers
    # ------------------------------------------------------------------------------------------------
    def execute_cmd(self, dst_dev_uuid, method, namespace, payload, callback=None, timeout=SHORT_TIMEOUT):
        start = time.time()
        # Build the mqtt message we will send to the broker
        message, message_id = self._build_mqtt_message(method, namespace, payload)

        # Register the waiting handler for that message
        handle = PendingMessageResponse(message_id=message_id, callback=callback)
        with self._pending_responses_lock:
            self._pending_response_messages[message_id] = handle

        # Send the message to the broker
        l.debug("Executing message-id %s, %s on %s command for device %s" % (message_id, method,
                                                                             namespace, dst_dev_uuid))
        self._mqtt_client.publish(topic=build_client_request_topic(dst_dev_uuid), payload=message)

        # If the caller has specified a callback, we don't need to actrively wait for the message ACK. So we can
        # immediately return.
        if callback is not None:
            return None

        # Otherwise, we need to wait until the message is received.
        l.debug("Waiting for response to message-id %s" % message_id)
        success, resp = handle.wait_for_response(timeout=timeout)
        if not success:
            raise CommandTimeoutException("A timeout occurred while waiting fot the ACK: %d" % timeout)

        elapsed = time.time() - start

        l.debug("Message-id: %s, command %s-%s command for device %s took %s" % (message_id, method,
                                                                                 namespace, dst_dev_uuid, str(elapsed)))
        return resp['payload']

    # ------------------------------------------------------------------------------------------------
    # Protocol utilities
    # ------------------------------------------------------------------------------------------------
    def _build_mqtt_message(self, method, namespace, payload):
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
        strtohash = "%s%s%s" % (messageId, self._cloud_creds.key, timestamp)
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
        return strdata.encode("utf-8"), messageId

    def _generate_client_and_app_id(self):
        md5_hash = md5()
        rnd_uuid = UUID.uuid4()
        md5_hash.update(("%s%s" % ("API", rnd_uuid)).encode("utf8"))
        self._app_id = md5_hash.hexdigest()
        self._client_id = 'app:%s' % md5_hash.hexdigest()
