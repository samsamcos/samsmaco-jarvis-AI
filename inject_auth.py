"""
Injects a lightweight access-token auth gate into /root/ai-browser/server.py.

How it works:
- Reads ACCESS_TOKEN from /root/.env
- Any request without a valid 'jv_access' cookie is shown a lock page
- GET /?access=TOKEN  or  GET /access?t=TOKEN sets the cookie and redirects
- /health, /api/*, /favicon*, /fix-*, /static/* are exempt (so API callers still work)
- LAN IPs (192.168.x.x, 10.x.x.x, 172.x.x.x, 127.x.x.x) bypass the gate entirely
"""

import pathlib, re

srv = pathlib.Path('/root/ai-browser/server.py')
txt = srv.read_text()

if 'jv_access' in txt:
    print('SKIP: auth already injected')
    exit(0)

AUTH_CODE = '''

# ── Access-token auth gate ────────────────────────────────────────────────────
import os as _os, re as _re
from flask import request as _req, make_response as _mkr, redirect as _redir

def _get_access_token():
    try:
        env = open('/root/.env').read()
        m = _re.search(r'^ACCESS_TOKEN=(.+)$', env, _re.MULTILINE)
        if m: return m.group(1).strip()
    except Exception:
        pass
    return _os.getenv('ACCESS_TOKEN', 'changeme')

_EXEMPT_PREFIXES = ('/api/', '/health', '/favicon', '/fix-widget', '/fix-extension',
                    '/solo.js', '/install.sh', '/v1/', '/run', '/stream/', '/fleet',
                    '/access', '/static/')

def _is_lan(ip):
    return bool(_re.match(r'^(127\.|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)', ip or ''))

_LOCK_PAGE = """<!DOCTYPE html><html>
<head><meta charset=UTF-8><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS — Access Required</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#07080d;color:#dde1f5;font-family:monospace;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.box{{background:#0d0f17;border:1px solid #1e2030;border-radius:12px;padding:36px 40px;max-width:380px;width:100%;text-align:center}}
.logo{{font-size:18px;font-weight:700;color:#fff;margin-bottom:6px}}span{{color:#5b9cf6}}
p{{color:#4a5568;font-size:11px;margin-bottom:22px}}
input{{width:100%;background:#07080d;border:1px solid #1e2030;border-radius:7px;padding:10px 14px;font-size:13px;color:#dde1f5;font-family:monospace;outline:none;margin-bottom:12px}}
input:focus{{border-color:#5b9cf6}}
button{{width:100%;background:#5b9cf6;color:#fff;border:none;border-radius:7px;padding:10px;font-size:13px;font-weight:700;cursor:pointer}}
button:hover{{opacity:.85}}
.err{{color:#f85149;font-size:11px;margin-top:8px;display:none}}
</style></head>
<body><div class="box">
<div class="logo">JAR<span>VIS</span></div>
<p>Enter your access code to continue</p>
<form method=GET action=/access>
  <input name=t type=password placeholder="Access code" autofocus autocomplete=off>
  <button type=submit>Unlock</button>
</form>
{err}
</div></body></html>"""

@app.before_request
def _auth_gate():
    path = _req.path
    ip   = _req.headers.get('X-Forwarded-For', _req.remote_addr or '').split(',')[0].strip()

    # LAN bypass
    if _is_lan(ip):
        return None

    # Exempt paths
    for prefix in _EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return None

    token = _get_access_token()

    # Cookie check
    if _req.cookies.get('jv_access') == token:
        return None

    # Deny — show lock page
    err = '<p class="err" style="display:block">Invalid access code</p>' if _req.args.get('err') else ''
    resp = _mkr(_LOCK_PAGE.format(err=err), 401)
    resp.headers['Content-Type'] = 'text/html'
    return resp

@app.route('/access')
def _access_gate():
    token = _get_access_token()
    t = _req.args.get('t', '')
    back = _req.args.get('back', '/')
    if t == token:
        resp = _redir(back)
        resp.set_cookie('jv_access', token, max_age=60*60*24*365, httponly=True, samesite='Lax')
        return resp
    return _redir('/access?err=1')

# ─────────────────────────────────────────────────────────────────────────────
'''

# Insert after the CORS setup (early in the file, before routes)
# Find first @app.route and insert before it
first_route = txt.find('\n@app.route(')
if first_route == -1:
    print('ERROR: could not find first @app.route')
    exit(1)

txt = txt[:first_route] + '\n' + AUTH_CODE + txt[first_route:]
srv.write_text(txt)
print('OK: auth gate injected')
