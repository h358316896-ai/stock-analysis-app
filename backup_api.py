"""轻量备份 API — 独立 Blueprint，不污染主 backend 全局导入"""
import os, json, io, zipfile, hashlib, hmac, time
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file

backup_bp = Blueprint('backup', __name__)

_PERSIST_DIR = os.getenv("PERSIST_DIR", "/data")

@backup_bp.route("/api/backup/download", methods=["GET"])
def admin_backup():
    token = request.headers.get("X-Backup-Token", "")
    secret = os.getenv("FLASK_SECRET_KEY", "")
    expected = hashlib.sha256((secret + "backup").encode()).hexdigest()[:32]
    if not token or not hmac.compare_digest(token, expected):
        return jsonify({"error": "unauthorized"}), 403

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Database
        db_path = os.path.join(_PERSIST_DIR, "app.db")
        if os.path.exists(db_path):
            zf.write(db_path, "app.db")

        # Persist files
        for fname in ["market_cache.json", "margin_snapshot.json",
                       "sector_flow_snapshot.json", "northbound_daily.json"]:
            fpath = os.path.join(_PERSIST_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, fname)

        # DB backups
        backup_dir = os.path.join(_PERSIST_DIR, "backups")
        if os.path.isdir(backup_dir):
            for fn in sorted(os.listdir(backup_dir))[-5:]:
                zf.write(os.path.join(backup_dir, fn), f"backups/{fn}")

        # Env snapshot (safe keys only)
        env_safe = {}
        SAFE_KEYS = {'PUBLIC_URL', 'RAILWAY_PROJECT_ID', 'RAILWAY_ENVIRONMENT',
                      'EASTMONEY_PROXY', 'XORPAY_AID', 'FLASK_SECRET_KEY',
                      'XORPAY_SECRET', 'DEEPSEEK_API_KEY', 'WXPUSHER_APP_TOKEN',
                      'PYTHON_VERSION', 'TZ', 'LANG', 'RAILWAY_SERVICE_ID'}
        for k, v in sorted(os.environ.items()):
            if k in SAFE_KEYS:
                env_safe[k] = v[:6] + '***' if any(s in k.upper() for s in ['SECRET','KEY','TOKEN','PASS']) and len(v)>8 else v
            else:
                env_safe[k] = '***REDACTED***'
        zf.writestr("env_snapshot.json", json.dumps(env_safe, indent=2, ensure_ascii=False))

    buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name=f"stockai_backup_{ts}.zip")
