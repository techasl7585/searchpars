import unittest
from unittest.mock import patch

from searchpars.app import open_target
from searchpars.models import SearchResult


class ApplicationLaunchTests(unittest.TestCase):
    @patch("searchpars.app.subprocess.Popen")
    @patch("searchpars.app.shutil.which", return_value="/usr/bin/gtk-launch")
    def test_desktop_application_uses_gtk_launcher(self, _which, popen):
        result = SearchResult(
            result_type="application",
            title="Firefox",
            subtitle="Web tarayıcısı",
            target="/usr/share/applications/firefox-esr.desktop",
        )
        open_target(result)
        popen.assert_called_once_with(["gtk-launch", "firefox-esr"])


if __name__ == "__main__":
    unittest.main()
