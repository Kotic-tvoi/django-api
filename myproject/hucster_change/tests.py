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
        request = self.make_request(
            {"mp": "ym", "key": "ColdBTX150"},
            self.api_key,
        )

        with patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}):
            response = await send_to_hucster(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("mp", response.json()["error"])

    async def test_sends_internal_article_name_to_runner(self):
        request = self.make_request(
            {"mp": "wb", "key": "ColdBTX150"},
            self.api_key,
        )
        expected_key = next(
            key for key, article in product_keys.items()
            if article == "ColdBTX150"
        )

        with (
            patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}),
            patch(
                "hucster_change.views._run_many_keys",
                new_callable=AsyncMock,
            ) as runner,
        ):
            runner.return_value = [{"key": expected_key, "article": "ColdBTX150"}]
            response = await send_to_hucster(request)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["mp"], "wb")
        self.assertEqual(response.json()["requested"], 1)
        runner.assert_awaited_once_with(
            [expected_key],
            mp_key="wb",
            concurrency=CONCURRENCY,
            max_retries=MAX_RETRIES,
        )

    async def test_rejects_unknown_article_without_running_huckster(self):
        request = self.make_request(
            {"mp": "ozon", "key": "unknown-article"},
            self.api_key,
        )

        with (
            patch("hucster_change.auth.ALLOWED_KEYS", {self.api_key}),
            patch(
                "hucster_change.views._run_many_keys",
                new_callable=AsyncMock,
            ) as runner,
        ):
            response = await send_to_hucster(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["unknown"], ["unknown-article"])
        runner.assert_not_awaited()
