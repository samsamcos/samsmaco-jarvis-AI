import pathlib

srv = pathlib.Path('/root/ai-browser/server.py')
txt = srv.read_text()

if '/links' in txt and 'api/pages' in txt:
    print('SKIP: already exists')
    exit(0)

new_routes = '''

# ── /links + /api/pages + catch-all HTML router ──────────────────────────────

@app.route('/links')
def page_links():
    return send_from_directory(str(BASE), 'links.html')

@app.route('/api/pages')
def api_pages():
    import glob as _glob, os as _os
    html_files = sorted(_glob.glob(str(BASE / '*.html')))
    pages = [_os.path.basename(f).replace('.html', '') for f in html_files]
    return jsonify({'pages': pages, 'count': len(pages)})

@app.route('/<path:page_name>', methods=['GET'])
def catch_all_html(page_name):
    aliases = {
        'browser-jobs': 'browser_jobs',
        'overlay/rc': 'overlay_rc', 'overlay/big': 'overlay_big', 'overlay/popup': 'overlay_popup',
        'routing-rules': 'routing-rules', 'staff-accounts': 'staff_temp',
        'tools-page': 'tools', 'gemini-fleet': 'gemini-keys', 'travel-agent': 'travel',
        'jarvis/setup': 'jarvis_setup', 'jarvis-setup': 'jarvis_setup',
        'jarvis-chat': 'screen_jarvis', 'update': 'updates', 'fix': 'fix',
        'rules': 'routing-rules', 'stats': 'status', 'ha-setup': 'ha-setup',
        'browser': 'browser', 'vm': 'vm', 'nodes': 'nodes', 'network': 'network',
        'system': 'system', 'sites': 'sites', 'staff': 'staff', 'worker': 'worker',
        'mobile': 'mobile', 'search': 'search', 'jobs': 'jobs', 'demo': 'demo',
        'pipeline': 'pipeline', 'webhooks': 'webhooks', 'n8nflow': 'n8nflow',
        'status': 'status', 'manual': 'manual', 'about': 'about', 'mitos2': 'mitos2',
        'masterclass': 'masterclass', 'flights': 'flights', 'slaves': 'slaves',
        'vision': 'vision', 'sync': 'sync', 'new-node': 'new_node',
        'node-manager': 'node_manager', 'links': 'links',
    }
    fname = aliases.get(page_name, page_name)
    candidate = BASE / (fname + '.html')
    if candidate.is_file():
        return send_from_directory(str(BASE), fname + '.html')
    return 'Not found', 404

'''

marker = "if __name__ == '__main__':"
if marker in txt:
    txt = txt.replace(marker, new_routes + marker, 1)
    srv.write_text(txt)
    print('OK: injected')
else:
    print('ERROR: marker not found')
