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
