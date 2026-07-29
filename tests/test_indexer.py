import tempfile
import unittest
import os
from datetime import datetime
from pathlib import Path

from searchpars.indexer import SearchIndex
from searchpars.nlp import parse_local


class IndexerTests(unittest.TestCase):
    def test_content_search(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "kurulum-notu.txt").write_text(
                "Pardus kurulumu ve CommunicatePars paketleri", encoding="utf-8"
            )
            index = SearchIndex(root / "test.db")
            stats = index.rebuild([root])
            self.assertEqual(stats.files, 1)
            results = index.search(parse_local("CommunicatePars kurulum belgesini bul"))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "kurulum-notu.txt")
            index.close()

    def test_exact_date_package_search(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "uygulama_1.0.0_amd64.deb"
            package.write_bytes(b"test package")
            timestamp = datetime(2026, 7, 27, 14, 30).timestamp()
            os.utime(package, (timestamp, timestamp))
            index = SearchIndex(root / "test.db")
            index.rebuild([root])
            intent = parse_local("27 temmuz indirdiğim deb kurulum paketini bul")
            results = index.search(intent)
            self.assertEqual([result.title for result in results], [package.name])
            index.close()

    def test_installation_file_prefers_real_installers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text(
                "Kurulum dosyası Releases bölümündedir.", encoding="utf-8"
            )
            (root / "install-pardus.sh").write_text("#!/bin/bash\n", encoding="utf-8")
            (root / "uygulama_1.0.0_amd64.deb").write_bytes(b"package")
            index = SearchIndex(root / "test.db")
            index.rebuild([root])
            results = index.search(parse_local("kurulum dosyası"))
            titles = {result.title for result in results}
            self.assertEqual(
                titles,
                {"install-pardus.sh", "uygulama_1.0.0_amd64.deb"},
            )
            index.close()

    def test_computer_scope_finds_deb_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "performancepars_1.0.0_amd64.deb"
            package.write_bytes(b"package")
            index = SearchIndex(root / "test.db")
            index.rebuild([root])
            intent = parse_local("bilgisayarımdaki deb kurulum paketini bul")
            results = index.search(intent)
            self.assertEqual([result.title for result in results], [package.name])
            index.close()


if __name__ == "__main__":
    unittest.main()
