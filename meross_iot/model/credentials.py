class MerossCloudCreds(object):
    def __init__(self, token, key, user_id, user_email, issued_on):
        self.token = token
        self.key = key
        self.user_id = user_id
        self.user_email = user_email
        self.issued_on = issued_on
