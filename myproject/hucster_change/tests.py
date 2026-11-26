import json
from unittest.mock import AsyncMock, patch

from django.test import AsyncRequestFactory, SimpleTestCase

from .constants import CONCURRENCY, MAX_RETRIES, product_keys
from .views import send_to_hucster


class HucsterSendApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = AsyncRequestFactory()
        self.api_key = "test-hucster-api-key"

    def make_request(self, payload, api_key=None):
        headers = {}
        if api_key:
            headers["HTTP_X_API_KEY"] = api_key
        return self.factory.post(
            "/hucster/send/",
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    async def test_rejects_request_without_api_key(self):
        request = self.make_request({"mp": "wb", "key": "ColdBTX150"})
        with patch("hucster_change.auth.ALLOWED_KEYS", set()):
            response = await send_to_hucster(request)
        self.assertEqual(response.status_code, 401)

    async def test_rejects_invalid_marketplace(self):
        request = self.make_request({"mp": "ym", "key": "ColdBTX150"}, self.api_key)
        with patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}):
            response = await send_to_hucster(request)
        self.assertEqual(response.status_code, 400)
        self.assertIn("mp", response.json()["error"])

    async def test_sends_existing_internal_article(self):
        request = self.make_request({"mp": "wb", "key": "ColdBTX150"}, self.api_key)
        expected_key = next(
            key for key, article in product_keys.items() if article == "ColdBTX150"
        )

        with (
            patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}),
            patch("hucster_change.views._run_many_keys", new_callable=AsyncMock) as runner,
        ):
            runner.return_value = [{"key": expected_key, "article": "ColdBTX150"}]
            response = await send_to_hucster(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["mp"], "wb")
        self.assertEqual(response.json()["requested"], 1)
        runner.assert_awaited_once_with(
            [expected_key], mp_key="wb",
            concurrency=CONCURRENCY, max_retries=MAX_RETRIES,
        )

    async def test_accepts_dynamic_catalog_id_and_uid(self):
        catalog_id = "4d3eea38f587af3c631c2f96c8ce1f6a"
        request = self.make_request({
            "mp": "ozon",
            "items": [{"uid": "маска_7Seconds", "id": catalog_id}],
        }, self.api_key)

        with (
            patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}),
            patch("hucster_change.views._run_many_keys", new_callable=AsyncMock) as runner,
        ):
            runner.return_value = [{"key": catalog_id, "article": catalog_id}]
            response = await send_to_hucster(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["articles"], ["маска_7Seconds"])
        self.assertEqual(response.json()["results"][0]["article"], "маска_7Seconds")
        runner.assert_awaited_once_with(
            [catalog_id], mp_key="ozon",
            concurrency=CONCURRENCY, max_retries=MAX_RETRIES,
        )

    async def test_rejects_unknown_non_id_value(self):
        request = self.make_request({"mp": "ozon", "key": "unknown-article"}, self.api_key)

        with (
            patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}),
            patch("hucster_change.views._run_many_keys", new_callable=AsyncMock) as runner,
        ):
            response = await send_to_hucster(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["unknown"], ["unknown-article"])
        runner.assert_not_awaited()
