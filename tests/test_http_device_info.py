import logging
import unittest
from datetime import datetime
from unittest.mock import patch

from meross_iot.model.http.device import HttpDeviceInfo


class TestHttpDeviceInfoBindTime(unittest.TestCase):
    def make_device(self, **kwargs):
        fields = dict(
            uuid="test-uuid",
            online_status=1,
            dev_name="Test device",
            device_type="mss310",
            channels=[],
            fmware_version="1.0.0",
            hdware_version="1.0.0",
            domain="mqtt.example.com",
            reserved_domain="mqtt.example.com",
        )
        fields.update(kwargs)
        return HttpDeviceInfo(**fields)

    def test_null_or_missing_bind_time_is_silent(self):
        with patch("meross_iot.model.http.device._LOGGER.warning") as warning:
            self.assertIsNone(self.make_device().bind_time)
            self.assertIsNone(self.make_device(bind_time=None).bind_time)
        warning.assert_not_called()

    def test_known_bind_time_formats_remain_supported(self):
        expected = datetime(2023, 1, 1)
        for value in (1672531200, expected, "2023-01-01T00:00:00"):
            with self.subTest(value=value):
                self.assertEqual(self.make_device(bind_time=value).bind_time, expected)

    def test_unexpected_type_still_warns(self):
        with self.assertLogs("meross_iot.model.http.device", level=logging.WARNING) as captured:
            device = self.make_device(bind_time={"unexpected": "value"})
        self.assertIsNone(device.bind_time)
        self.assertIn("unsupported type dict", captured.output[0])


if __name__ == "__main__":
    unittest.main()
