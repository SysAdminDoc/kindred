import unittest
from pathlib import Path

from fastapi.routing import APIWebSocketRoute

from app.main import app
from app.ws_app import ws_app


class ProcessTopologyTests(unittest.TestCase):
    def test_dedicated_worker_exposes_only_the_websocket_route(self):
        websocket_routes = [
            route.path
            for route in ws_app.routes
            if isinstance(route, APIWebSocketRoute)
        ]
        self.assertEqual(websocket_routes, ["/ws/{profile_id}"])
        self.assertTrue(any(route.path == "/api/health" for route in ws_app.routes))
        self.assertTrue(any(route.path == "/api/health" for route in app.routes))

    def test_production_gateway_routes_websockets_to_dedicated_service(self):
        caddy = Path(__file__).parents[1] / "deploy" / "Caddyfile.docker"
        compose = Path(__file__).parents[1] / "deploy" / "docker-compose.prod.yml"
        caddy_text = caddy.read_text(encoding="utf-8")
        compose_text = compose.read_text(encoding="utf-8")
        self.assertIn("path /ws/*", caddy_text)
        self.assertIn("reverse_proxy kindred-ws:8002", caddy_text)
        self.assertIn("kindred-user:", compose_text)
        self.assertIn("kindred-admin:", compose_text)
        self.assertIn("kindred-ws:", compose_text)
        self.assertIn("kindred-worker:", compose_text)
        self.assertIn("app.ws_app:ws_app", compose_text)
        self.assertIn("app.tasks", compose_text)
        self.assertIn("kindred-redis:", compose_text)


if __name__ == "__main__":
    unittest.main()
