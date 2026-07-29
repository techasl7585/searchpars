import unittest

from searchpars.ai import OllamaProvider


class FakeProvider(OllamaProvider):
    def _request(self, payload, timeout=35):
        return {
            "message": {
                "content": (
                    '{"intent":"search","keywords":["fatura","ödeme"],'
                    '"file_type":"pdf","date_filter":"last_week",'
                    '"action":null,"answer_needed":false}'
                )
            }
        }


class FakeGeneralProvider(OllamaProvider):
    def _request(self, payload, timeout=35):
        return {"message": {"content": "Steve Jobs, Apple'ın kurucularındandır."}}


class AITests(unittest.TestCase):
    def test_ai_intent_is_applied(self):
        provider = FakeProvider()
        intent = provider.parse_intent("Geçen haftaki faturayı bul")
        self.assertEqual(intent.file_type, "pdf")
        self.assertEqual(intent.date_filter, "last_week")
        self.assertIn("ödeme", intent.keywords)

    def test_general_knowledge_answer(self):
        provider = FakeGeneralProvider()
        answer = provider.general_answer("Steve Jobs")
        self.assertIn("Apple", answer)


if __name__ == "__main__":
    unittest.main()
