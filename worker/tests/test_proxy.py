from worker.utils import proxy as proxy_module
from worker.utils.proxy import get_proxy_for_domain


class TestGetProxyForDomain:
    """Tests for per-domain proxy selection."""

    def test_returns_none_when_no_proxies_configured(self, monkeypatch):
        monkeypatch.setattr(proxy_module.settings, "proxy_urls", "")
        assert get_proxy_for_domain("example.com") is None

    def test_returns_a_configured_proxy(self, monkeypatch):
        monkeypatch.setattr(
            proxy_module.settings,
            "proxy_urls",
            "http://p1:8080,http://p2:8080",
        )
        result = get_proxy_for_domain("example.com")
        assert result in (
            {"server": "http://p1:8080"},
            {"server": "http://p2:8080"},
        )

    def test_assignment_is_deterministic_per_domain(self, monkeypatch):
        monkeypatch.setattr(
            proxy_module.settings,
            "proxy_urls",
            "http://p1:8080,http://p2:8080,http://p3:8080",
        )
        first = get_proxy_for_domain("example.com")
        second = get_proxy_for_domain("example.com")
        assert first == second

    def test_single_proxy_always_selected(self, monkeypatch):
        monkeypatch.setattr(proxy_module.settings, "proxy_urls", "http://only:8080")
        assert get_proxy_for_domain("a.com") == {"server": "http://only:8080"}
        assert get_proxy_for_domain("b.com") == {"server": "http://only:8080"}
