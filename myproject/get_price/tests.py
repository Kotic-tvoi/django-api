from django.test import SimpleTestCase

from .parser import ParseWB


class ParseWBParamsTests(SimpleTestCase):
    def test_catalog_request_is_filtered_by_jkeratin_brand(self):
        parser = ParseWB("https://www.wildberries.ru/seller/215484")

        params = parser._params(page=1)

        self.assertEqual(params["fbrand"], "279103")
