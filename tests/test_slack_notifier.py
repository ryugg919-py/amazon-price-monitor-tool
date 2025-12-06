

import src.slack_notifier as sn


def test_notify_slack_uses_webhook(monkeypatch):
    called = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

    def fake_post(url, json, timeout):
        called["url"] = url
        called["json"] = json
        called["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    monkeypatch.setattr(sn, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/test")
    monkeypatch.setattr(sn.requests, "post", fake_post)

    sn.notify_slack("hello")
    assert called["url"].startswith("https://hooks.slack.com/")
    assert called["json"]["text"] == "hello"


def test_upload_chart_to_slack(monkeypatch, tmp_path):
    uploaded = {}

    class DummyClient:
        def files_upload_v2(self, channel, initial_comment, file, filename):
            uploaded["channel"] = channel
            uploaded["initial_comment"] = initial_comment
            uploaded["filename"] = filename

    dummy_chart = tmp_path / "chart.png"
    dummy_chart.write_bytes(b"fake")

    monkeypatch.setattr(sn, "slack_client", DummyClient())
    monkeypatch.setattr(sn, "SLACK_CHANNEL_ID", "C123")
    sn.upload_chart_to_slack(dummy_chart, message="chart upload")

    assert uploaded["channel"] == "C123"
    assert uploaded["initial_comment"] == "chart upload"
    assert uploaded["filename"] == "chart.png"
