

import src.manage_targets as mt


def test_load_save_targets_roundtrip(tmp_path):
    path = tmp_path / "targets.yml"
    data = {"settings": {}, "sites": [{"site_name": "Amazon_JP", "products": []}]}
    mt.save_targets_config(data, path)

    loaded = mt.load_targets_config(path)
    assert loaded["sites"][0]["site_name"] == "Amazon_JP"


def test_build_canonical_url_amazon():
    url = mt.build_canonical_url("https://example.com/whatever", "Amazon_JP", "B0TEST1234")
    assert url == "https://www.amazon.co.jp/dp/B0TEST1234"


def test_fetch_amazon_title_uses_requests(monkeypatch):
    class DummyResp:
        text = "<html><head><title>Product X | Amazon.co.jp</title></head></html>"

        def raise_for_status(self):
            return None

    def fake_get(url, timeout):
        return DummyResp()

    monkeypatch.setattr(mt.requests, "get", fake_get)
    title = mt.fetch_amazon_title("https://www.amazon.co.jp/dp/B0TEST1234")
    assert title == "Product X"
