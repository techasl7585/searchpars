import unittest

from searchpars.websearch import DuckDuckGoParser, WebSearchProvider, _real_url


class FakeWebProvider(WebSearchProvider):
    def _get(self, url):
        if "wikipedia.org" in url:
            return b'{"query":{"pages":[]}}'
        return b"""
        <div class="result">
          <a class="result__a" href="https://example.com/steve-jobs">Steve Jobs</a>
          <a class="result__snippet">Apple kurucularindan biri.</a>
        </div>
        """


class FakeCurrencyProvider(WebSearchProvider):
    def _get(self, url):
        if "today.xml" in url:
            return b"""<?xml version="1.0" encoding="UTF-8"?>
            <Tarih_Date Tarih="29.07.2026">
              <Currency CurrencyCode="USD">
                <Unit>1</Unit><Isim>ABD DOLARI</Isim>
                <ForexBuying>47.2899</ForexBuying>
                <ForexSelling>47.3751</ForexSelling>
              </Currency>
            </Tarih_Date>"""
        if "wikipedia.org" in url:
            return b'{"query":{"pages":[]}}'
        return b""


class WebSearchTests(unittest.TestCase):
    def test_duckduckgo_html_results_are_parsed(self):
        parser = DuckDuckGoParser()
        parser.feed(
            """
            <div class="result">
              <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fjobs">
                Steve Jobs
              </a>
              <a class="result__snippet">Apple kurucularından biri.</a>
            </div>
            """
        )
        self.assertEqual(parser.links[0][0], "Steve Jobs")
        self.assertEqual(parser.snippets[0], "Apple kurucularından biri.")
        self.assertEqual(_real_url(parser.links[0][1]), "https://example.com/jobs")

    def test_provider_returns_clickable_web_result(self):
        results = FakeWebProvider().search("Steve Jobs")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].result_type, "web")
        self.assertEqual(results[0].target, "https://example.com/steve-jobs")

    def test_currency_query_returns_direct_tcmb_card(self):
        results = FakeCurrencyProvider().search("dolar kuru")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].result_type, "live")
        self.assertIn("47,3751", results[0].title)
        self.assertIn("TCMB", results[0].subtitle)


if __name__ == "__main__":
    unittest.main()
