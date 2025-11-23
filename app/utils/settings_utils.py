import os
from flask import current_app

def get_org_settings():
    """Return resolved organization settings with priority:
    1) AppSettings (DB)
    2) Environment variables
    3) sensible defaults

    Returns a dict with keys:
      org_name, org_address, org_email, payment_email, org_phone,
      logo_b64, logo_url, logo_path
    """
    defaults = {
        'org_name': 'My Organization',
        'org_address': 'Organization Address',
        'org_email': 'no-reply@example.com',
        'payment_email': 'payments@example.com',
        'org_phone': '',
    }

    s = None
    try:
        from app.models import AppSettings
        s = AppSettings.get()
    except Exception:
        s = None

    def _env(name):
        return os.environ.get(name)

    org_name = (s.org_name if s and getattr(s, 'org_name', None) else _env('ORG_NAME') or defaults['org_name'])
    org_address = (s.org_address if s and getattr(s, 'org_address', None) else _env('ORG_ADDRESS') or defaults['org_address'])
    org_email = (s.org_email if s and getattr(s, 'org_email', None) else _env('ORG_EMAIL') or defaults['org_email'])
    payment_email = (s.payment_email if s and getattr(s, 'payment_email', None) else _env('PAYMENT_EMAIL') or defaults['payment_email'])
    org_phone = (s.org_phone if s and getattr(s, 'org_phone', None) else _env('ORG_PHONE') or defaults['org_phone'])

    # Resolve logo: prefer DB-stored path (s.logo_path), then env vars LOGO_BASE64, LOGO_URL, LOGO_PATH
    logo_b64 = None
    logo_url = None
    # logo_file_uri is a file:// URI suitable for server-side PDF rendering
    logo_file_uri = None
    # logo_web_path is a web-safe path (e.g. /static/images/logo.png) suitable for <img src=> in browsers
    logo_web_path = None

    try:
        # Helper to convert an on-disk path to file URI and web path (if under app/static)
        def _resolve_local_path(lp_raw):
            lp = lp_raw
            if not os.path.isabs(lp):
                lp = os.path.join(current_app.root_path, lp)
            try:
                from pathlib import Path
                p = Path(lp)
                if p.exists():
                    try:
                        file_uri = p.as_uri()
                    except Exception:
                        file_uri = lp
                else:
                    file_uri = lp
            except Exception:
                file_uri = lp

            web_path = None
            try:
                # if the file is under the application's static folder, expose as /static/...
                static_root = os.path.join(current_app.root_path, 'static')
                if str(lp).startswith(static_root):
                    rel = os.path.relpath(lp, static_root)
                    # use forward slashes for URL
                    web_path = '/' + os.path.join('static', rel).replace('\\', '/')
            except Exception:
                web_path = None

            return file_uri, web_path

        if s and getattr(s, 'logo_path', None):
            lp = s.logo_path
            file_uri, web_path = _resolve_local_path(lp)
            logo_file_uri = file_uri
            logo_web_path = web_path
        else:
            logo_base64_env = _env('LOGO_BASE64')
            logo_url_env = _env('LOGO_URL')
            logo_path_env = _env('LOGO_PATH')
            if logo_base64_env:
                if logo_base64_env.strip().startswith('data:'):
                    logo_b64 = logo_base64_env.strip()
                else:
                    logo_b64 = f"data:image/png;base64,{logo_base64_env.strip()}"
            elif logo_url_env:
                logo_url = logo_url_env
            elif logo_path_env:
                file_uri, web_path = _resolve_local_path(logo_path_env)
                logo_file_uri = file_uri
                logo_web_path = web_path
    except Exception:
        # best-effort: ignore issues loading logo
        logo_b64 = None
        logo_url = None
        logo_file_uri = None
        logo_web_path = None

    return {
        'org_name': org_name,
        'org_address': org_address,
        'org_email': org_email,
        'payment_email': payment_email,
        'org_phone': org_phone,
        'logo_b64': logo_b64,
        'logo_url': logo_url,
        'logo_file_uri': logo_file_uri,
        'logo_web_path': logo_web_path,
        'appsettings': s,
    }
