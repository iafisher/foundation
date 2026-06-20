import decimal
import unittest
from io import StringIO
from textwrap import dedent

from . import Table


class Test(unittest.TestCase):
    def test_tabular(self):
        table = Table()
        table.row(["country", "capital", "population"])
        table.row(["France", "Paris", "70 million"])
        table.row(["United States", "Washington DC", "300 million"])
        table.row(["Malaysia", "Kuala Lumpur", "35 million"])

        buffer = StringIO()
        table.flush(file=buffer)
        self.assertEqual(
            dedent(
                """\
                country        capital        population
                France         Paris          70 million
                United States  Washington DC  300 million
                Malaysia       Kuala Lumpur   35 million
                """
            ),
            buffer.getvalue(),
        )

        table.sort("country")
        buffer = StringIO()
        table.flush(file=buffer)
        self.assertEqual(
            dedent(
                """\
                country        capital        population
                France         Paris          70 million
                Malaysia       Kuala Lumpur   35 million
                United States  Washington DC  300 million
                """
            ),
            buffer.getvalue(),
        )

    def test_jagged_rows(self):
        table = Table(allow_jagged_rows=True)
        table.row(["Nevada"])
        table.row(["North", "Carolina"])
        table.row(["North", "Dakota"])
        table.row(["Oklahoma"])

        buffer = StringIO()
        table.flush(file=buffer)
        self.assertEqual(
            dedent(
                """\
                Nevada
                North     Carolina
                North     Dakota
                Oklahoma
                """
            ),
            buffer.getvalue(),
        )

    def test_numformat(self):
        table = Table(numformat="{:,.1f}")
        table.row([1000, 1000.0, decimal.Decimal("1000")])
        buffer = StringIO()
        table.flush(file=buffer)
        self.assertEqual(
            dedent(
                """\
                1,000.0  1,000.0  1,000.0
                """
            ),
            buffer.getvalue(),
        )
