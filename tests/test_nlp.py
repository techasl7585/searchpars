import unittest

from searchpars.nlp import parse_local


class NLPTests(unittest.TestCase):
    def test_natural_file_query(self):
        intent = parse_local("Dün indirdiğim Pardus kurulum PDF'sini bul")
        self.assertEqual(intent.intent, "search")
        self.assertEqual(intent.file_type, "pdf")
        self.assertEqual(intent.date_filter, "yesterday")
        self.assertIn("pardus", intent.keywords)
        self.assertIn("kurulum", intent.keywords)

    def test_bluetooth_action(self):
        intent = parse_local("Bluetooth'u aç")
        self.assertEqual(intent.intent, "action")
        self.assertEqual(intent.action, "bluetooth_on")

    def test_summary_needs_answer(self):
        intent = parse_local("CommunicatePars belgesi ne anlatıyor, özetle")
        self.assertTrue(intent.answer_needed)
        self.assertIn("communicatepars", intent.keywords)

    def test_exact_date_deb_package(self):
        intent = parse_local("27 temmuz indirdiğim deb kurulum paketini bul")
        self.assertEqual(intent.file_type, "package")
        self.assertEqual(intent.date_from, "2026-07-27")
        self.assertEqual(intent.date_to, "2026-07-28")
        self.assertEqual(intent.keywords, [])

    def test_installation_file_means_real_package(self):
        intent = parse_local("kurulum dosyası")
        self.assertEqual(intent.file_type, "package")

    def test_application_possessive_suffix_is_removed(self):
        intent = parse_local("Firefox'u aç")
        self.assertEqual(intent.keywords, ["firefox"])

    def test_local_scope_is_not_searched_as_filename(self):
        intent = parse_local("bilgisayarımdaki deb kurulum paketini bul")
        self.assertEqual(intent.file_type, "package")
        self.assertEqual(intent.keywords, [])


if __name__ == "__main__":
    unittest.main()
