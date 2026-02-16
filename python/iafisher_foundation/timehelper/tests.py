import unittest

from ..prelude import *

from .timehelper import from_epoch_secs, month_to_quarter, to_month_str


class Test(unittest.TestCase):
    def test_to_month_str(self):
        self.assertEqual("2025-02", to_month_str(datetime.date(2025, 2, 12)))
        self.assertEqual("2025-11", to_month_str(datetime.date(2025, 11, 1)))

    def test_from_epoch_secs(self):
        self.assertEqual(
            "2025-04-06T10:15:28.447466-04:00",
            from_epoch_secs(1743948928.447466).isoformat(),
        )

    def test_month_to_quarter(self):
        self.assertEqual(
            [month_to_quarter(m) for m in range(1, 13)],
            [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4],
        )
