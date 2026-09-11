import unittest

from rfdi.experiments import _records


class HoldoutTests(unittest.TestCase):
    def test_final_fails_closed(self):
        with self.assertRaises(PermissionError): _records("final")


if __name__ == "__main__": unittest.main()
