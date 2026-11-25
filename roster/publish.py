"""Upload the viewer folder to Netlify (free static hosting).

One-time: make a free Netlify account, then User settings -> Applications ->
Personal access tokens -> New access token. Paste the token in the app.
The app creates the site on the first publish and remembers its ID.
"""
import io
import json
import os
import urllib.error
import urllib.request
import zipfile

API = "https://api.netlify.com/api/v1"


class PublishError(Exception):
    pass


def _request(method, url, token, body=None, content_type="application/json"):
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
        "User-Agent": "HO-Roster-app",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            raise PublishError("Netlify did not accept the access token - check it in Website settings.")
        if e.code == 404:
            raise PublishError("Netlify site not found - clear the Site ID in Website settings to make a new one.")
        if e.code == 422 and "name" in detail.lower():
            raise PublishError("That website name is already taken on Netlify - choose another in Website settings.")
        raise PublishError(f"Netlify error {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise PublishError(f"Could not reach Netlify - is the internet connected? ({e.reason})")


def create_site(token, name=""):
    body = json.dumps({"name": name} if name else {}).encode()
    site = _request("POST", f"{API}/sites", token, body)
    return site["id"], site.get("ssl_url") or site.get("url")


def _zip_dir(folder):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(folder):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, folder).replace(os.sep, "/"))
    return buf.getvalue()


def deploy(folder, token, site_id):
    """Upload `folder` as the new version of the site. Returns the site URL."""
    r = _request("POST", f"{API}/sites/{site_id}/deploys", token, _zip_dir(folder), "application/zip")
    return r.get("ssl_url") or r.get("url") or r.get("deploy_ssl_url")
