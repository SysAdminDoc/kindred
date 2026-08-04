import json
import re
import unittest
from pathlib import Path

from app.admin_app import admin_app
from app.config import APP_VERSION
from app.main import app
from app.ws_app import ws_app


class VersionMetadataTests(unittest.TestCase):
    ROOT = Path(__file__).parents[1]

    def test_runtime_and_release_surfaces_share_one_version(self):
        version = APP_VERSION
        manifest = json.loads(
            (self.ROOT / "static" / "manifest.json").read_text(encoding="utf-8")
        )
        readme = (self.ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (self.ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        index = (self.ROOT / "static" / "index.html").read_text(encoding="utf-8")
        admin = (self.ROOT / "static" / "admin.html").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], version)
        self.assertIn(f"version-{version}-", readme)
        self.assertIsNotNone(
            re.search(rf"^## \[v{re.escape(version)}\] - ", changelog, re.MULTILINE)
        )
        self.assertIn(f"Kindred v{version} - Find Your Match", index)
        self.assertIn(f'class="ver">v{version}</span>', index)
        self.assertIn(f'class="ver">v{version}</span>', admin)
        self.assertEqual(app.version, version)
        self.assertEqual(admin_app.version, version)
        self.assertEqual(ws_app.version, version)


if __name__ == "__main__":
    unittest.main()
