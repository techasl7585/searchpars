import unittest

from searchpars.nlp import parse_local
from searchpars.router import route_query


class RouterTests(unittest.TestCase):
    def test_file_request_stays_local(self):
        query = "27 Temmuz indirdiğim kurulum dosyasını bul"
        decision = route_query(query, parse_local(query))
        self.assertEqual(decision.route, "local")
        self.assertTrue(decision.use_local)
        self.assertFalse(decision.use_web)

    def test_person_name_is_hybrid(self):
        query = "Steve Jobs"
        decision = route_query(query, parse_local(query))
        self.assertEqual(decision.route, "hybrid")
        self.assertTrue(decision.use_web)
        self.assertTrue(decision.use_ai)

    def test_current_information_uses_web(self):
        query = "bugünkü dolar kuru"
        decision = route_query(query, parse_local(query))
        self.assertEqual(decision.route, "web")
        self.assertFalse(decision.use_local)
        self.assertTrue(decision.use_web)

    def test_document_summary_does_not_leak_to_web(self):
        query = "CommunicatePars belgesini özetle"
        decision = route_query(query, parse_local(query))
        self.assertEqual(decision.route, "local")
        self.assertFalse(decision.use_web)

    def test_system_action_does_not_use_web(self):
        query = "Bluetooth'u aç"
        decision = route_query(query, parse_local(query))
        self.assertEqual(decision.route, "action")
        self.assertFalse(decision.use_web)


if __name__ == "__main__":
    unittest.main()
