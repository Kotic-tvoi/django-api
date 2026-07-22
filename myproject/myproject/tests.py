from importlib import import_module

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve


class DisabledFeatureRoutingTests(SimpleTestCase):
    """Проверяет, что отключённые приложения не затрагивают основные маршруты."""

    def test_features_are_disabled_by_default(self):
        self.assertFalse(settings.PRICE_HISTORY_VIEW_ENABLED)
        self.assertFalse(settings.HUCSTER_CHANGE_ENABLED)

    def test_core_routes_remain_available(self):
        self.assertEqual(resolve("/").url_name, "home")
        self.assertEqual(resolve("/parser/get_price/").namespace, "get_price")
        self.assertEqual(resolve("/ozon_parser/get_price/").namespace, "ozon_price")
        self.assertEqual(resolve("/admin/").namespace, "admin")

    def test_disabled_routes_are_not_registered(self):
        with self.assertRaises(Resolver404):
            resolve("/reports/price-history/")

        with self.assertRaises(Resolver404):
            resolve("/hucster/")

    def test_disabled_application_code_is_still_available(self):
        self.assertIsNotNone(import_module("price_history_view.apps"))
        self.assertIsNotNone(import_module("hucster_change.apps"))
