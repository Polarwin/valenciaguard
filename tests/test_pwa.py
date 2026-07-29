"""PWA basics: service worker, manifest and icons are served correctly."""


def test_service_worker(client):
    resp = client.get("/sw.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
    assert resp.headers["service-worker-allowed"] == "/"
    assert "vg-static" in resp.text


def test_manifest(client):
    resp = client.get("/static/manifest.webmanifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "ValenciaGuard"
    assert data["display"] == "standalone"
    assert any("192" in i["sizes"] for i in data["icons"])


def test_icons(client):
    for size in (192, 512):
        resp = client.get(f"/static/icon-{size}.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
