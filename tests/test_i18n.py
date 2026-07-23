"""i18n: language switcher, per-language rendering, fallbacks."""
from app.i18n import translate, t


def _clear_lang(client):
    try:
        del client.cookies["vg_lang"]
    except KeyError:
        pass


def test_switcher_sets_cookie_and_redirects(client):
    resp = client.get("/set-language/en?next=/dashboard", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/dashboard"
    assert "vg_lang=en" in resp.headers["set-cookie"]


def test_switcher_rejects_open_redirect(client):
    resp = client.get("/set-language/en?next=//evil.com", follow_redirects=False)
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    resp = client.get("/set-language/en?next=https://evil.com", follow_redirects=False)
    assert resp.headers["location"] == "/"


def test_switcher_unknown_lang_defaults_es(client):
    resp = client.get("/set-language/klingon?next=/dashboard", follow_redirects=False)
    assert "vg_lang=es" in resp.headers["set-cookie"]


def _dashboard_in(admin_client, lang):
    admin_client.cookies.set("vg_lang", lang)
    resp = admin_client.get("/dashboard")
    assert resp.status_code == 200
    _clear_lang(admin_client)
    return resp.text


def test_dashboard_spanish(admin_client):
    html = _dashboard_in(admin_client, "es")
    assert "Centro de alertas" in html
    assert 'lang="es"' in html


def test_dashboard_english(admin_client):
    html = _dashboard_in(admin_client, "en")
    assert "Alert center" in html
    assert 'lang="en"' in html


def test_dashboard_chinese(admin_client):
    html = _dashboard_in(admin_client, "zh")
    assert "提醒中心" in html
    assert 'lang="zh"' in html


def _portal_in(owner_client, lang):
    owner_client.cookies.set("vg_lang", lang)
    resp = owner_client.get("/owner-portal")
    assert resp.status_code == 200
    _clear_lang(owner_client)
    return resp.text


def test_portal_chinese(owner_client):
    assert "我的房产" in _portal_in(owner_client, "zh")


def test_portal_spanish(owner_client):
    assert "Mis propiedades" in _portal_in(owner_client, "es")


def test_portal_english(owner_client):
    assert "My properties" in _portal_in(owner_client, "en")


def test_unknown_cookie_falls_back_to_spanish(owner_client):
    owner_client.cookies.set("vg_lang", "klingon")
    resp = owner_client.get("/owner-portal")
    _clear_lang(owner_client)
    assert resp.status_code == 200
    assert "Mis propiedades" in resp.text


def test_cookie_persists_across_requests(client):
    client.get("/set-language/zh?next=/login", follow_redirects=False)
    resp = client.get("/login")  # no explicit cookie set; jar carries vg_lang
    assert "物业管理" in resp.text


def test_missing_key_fallback():
    assert translate("en", "totally.missing.key") == "totally.missing.key"
    assert translate("zh", "totally.missing.key") == "totally.missing.key"


def test_translate_format_kwargs():
    assert translate("en", "users.confirm_delete", username="bob") == "Delete user bob?"
    assert "bob" in translate("zh", "portal.greeting", name="bob")
