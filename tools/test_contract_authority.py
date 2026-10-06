"""Offline S0-06 contract guard tests: python3 -m unittest tools.test_contract_authority"""

import tempfile
import unittest
from pathlib import Path

from tools.check_contract_authority import check_client, check_python, scan


class EphemerisBoundaryTests(unittest.TestCase):
    def test_import_forms_and_dynamic_imports_are_rejected_outside_pcs(self):
        for source in (
            "import swisseph as swe\n",
            "from swisseph import calc_ut\n",
            "import pyswisseph\n",
            "__import__('swisseph')\n",
            "importlib.import_module('swisseph')\n",
        ):
            with self.subTest(source=source):
                self.assertEqual(check_python(source, "services/api/src/api/new.py")[0].rule,
                                 "ephemeris-boundary")
                self.assertEqual(check_python(source, "services/panchang/src/panchang/engine.py"), [])

    def test_text_is_not_an_import(self):
        self.assertEqual(check_python('"""import swisseph"""\n# import swisseph\n',
                                      "services/api/src/api/new.py"), [])

    def test_python_312_generic_syntax_on_older_host_still_checks_imports(self):
        source = "class Result[T]:\n    pass\nimport swisseph as swe\n"
        self.assertTrue(check_python(source, "services/api/src/api/result.py"))
        unrelated_symbol = "class Result[T]:\n    pass\nfrom api import swisseph\n"
        self.assertEqual(check_python(unrelated_symbol, "services/api/src/api/result.py"), [])


class ClientAuthorityTests(unittest.TestCase):
    WEB = "apps/web/src/features/checkout/quote.ts"
    IOS = "apps/ios/ThePandit/Sources/ThePandit/Booking/Quote.swift"
    ANDROID = "apps/android/app/src/main/java/com/pandit/android/Quote.kt"

    def test_violations_across_all_client_languages(self):
        for path, source in (
            (self.WEB, "const totalPrice = basePrice + tax;"),
            (self.IOS, "let commission = price * rate"),
            (self.ANDROID, "val tithi = moonLongitude - sunLongitude"),
            (self.WEB, "function calculateNakshatra(moonLongitude: number) {}"),
            (self.IOS, "func computePanchang() -> String { return \"\" }"),
            (self.ANDROID, "booking.state = confirmed"),
            (self.WEB, 'const canCheckout = tier === "gold";'),
            (self.WEB, 'import { calc } from "swisseph";'),
            (self.WEB, 'import "swisseph";'),
            (self.IOS, "import swisseph"),
            (self.ANDROID, "import swisseph.Engine"),
        ):
            with self.subTest(path=path, source=source):
                self.assertTrue(check_client(source, path))

    def test_rendering_cached_data_and_formatting_are_allowed(self):
        for path, source in (
            (self.WEB, 'const tithi = day.tithi;\nconst time = hours + 24;'),
            (self.WEB, 'const price = quote.price;\nconst status = booking.state;'),
            (self.WEB, 'const isGold = tier === "gold"; // UI badge'),
            (self.IOS, "let cached = try await cache.fetchPanchang(date: date)"),
            (self.ANDROID, "Text(data.tithi.firstOrNull()?.name ?: \"—\")"),
        ):
            with self.subTest(path=path):
                self.assertEqual(check_client(source, path), [])

    def test_comments_strings_and_server_are_excluded(self):
        source = "// const tax = price * rate;\n" \
                 "const message = 'calculateTithi()'; /* booking.state = confirmed */\n"
        self.assertEqual(check_client(source, self.WEB), [])
        self.assertEqual(check_client("const tax = price * rate;", "services/api/src/api/server.ts"), [])

    def test_source_discovery_ignores_docs_tests_and_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path, source in (
                ("services/api/src/api/unsafe.py", "import swisseph\n"),
                ("apps/web/src/features/quote.ts", "const tax = price * rate;"),
                ("apps/web/tests/quote.test.ts", "const tax = price * rate;"),
                ("apps/web/src/generated/quote.ts", "const tax = price * rate;"),
                ("docs/example.py", "import swisseph\n"),
            ):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source)
            self.assertEqual([(v.path, v.rule) for v in scan(root)], [
                ("apps/web/src/features/quote.ts", "client-arithmetic"),
                ("services/api/src/api/unsafe.py", "ephemeris-boundary"),
            ])


if __name__ == "__main__":
    unittest.main()
