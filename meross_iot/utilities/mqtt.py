import uuid as UUID
from hashlib import md5


def build_device_request_topic(client_uuid: str) -> str:
    """
    Builds the MQTT topic where commands should be send to specific devices
    :param client_uuid:
    :return:
    """
    return f"/appliance/{client_uuid}/subscribe"


def build_client_response_topic(user_id: str, app_id: str) -> str:
    """
    Builds the MQTT topic where the device sends back ACKs to commands
    :param app_id:
    :param user_id:
    :param client_uuid:
    :return:
    """
    return f"/app/{user_id}-{app_id}/subscribe"


def build_client_user_topic(user_id: str):
    """
    Builds the topic name where user push notification are received
    :param user_id:
    :return:
    """
    return f"/app/{user_id}/subscribe"


def device_uuid_from_push_notification(from_topic: str):
    """
    Extracts the device uuid from the "from" header of the received messages.
    :param from_topic:
    :return:
    """
    return from_topic.split('/')[2]


def generate_client_and_app_id():
    """
    Generates a new app-id.
    :return:
    """
    # TODO: Talk to the Meross engineer and check if the APPID should be the same or if we
    #  need to use a convention to discriminate MerossIot python clients.
    md5_hash = md5()
    rnd_uuid = UUID.uuid4()
    md5_hash.update(f"API{rnd_uuid}".encode("utf8"))
    app_id = md5_hash.hexdigest()
    client_id = 'app:%s' % md5_hash.hexdigest()
    return app_id, client_id


def generate_mqtt_password(user_id: str, key: str):
    """
    Generates the MQTT password that the APP uses to connect to the mqtt server.
    :param user_id:
    :param key:
    :return:
    """
    md5_hash = md5()
    clearpwd = f"{user_id}{key}"
    md5_hash.update(clearpwd.encode("utf8"))
    return md5_hash.hexdigest()


def verify_message_signature(header: dict, key: str):
    """
    Verifies if the given message header has a valid signature
    :param header:
    :param key:
    :return:
    """
    message_hash = md5()
    strtohash = "%s%s%s" % (header['messageId'], key, header['timestamp'])
    message_hash.update(strtohash.encode("utf8"))
    expected_signature = message_hash.hexdigest().lower()
    return expected_signature == header['sign']
