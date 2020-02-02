class InvalidSignatureException(Exception):
    def __init__(self, message, expected_signature, provided_signature, data):
        super(InvalidSignatureException, self).__init__(message)
        self.expected_signature = expected_signature
        self.provided_signature = provided_signature
        self.data = data
