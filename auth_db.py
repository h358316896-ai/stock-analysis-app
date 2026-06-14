# auth_db.py - 用户认证 & 自选股 & 提醒数据库
import sqlite3
import hashlib
import hmac
import secrets
import time
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")

# ==========================================================
# Token 认证（跨域Cookie替代方案）
# ==========================================================
_SECRET = None

def init_token_secret(secret_key: str):
    """Set the token signing secret explicitly (call once at app startup)."""
    global _SECRET
    _SECRET = (secret_key or secrets.token_hex(32)).encode()

def _get_secret():
    global _SECRET
    if _SECRET is None:
        _SECRET = secrets.token_hex(32).encode()
    return _SECRET

def create_token(user_id: int) -> str:
    """Generate a signed token: user_id:timestamp:signature"""
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(_get_secret(), payload.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{payload}:{sig}"

def verify_token(token: str) -> int | None:
    """Verify token and return user_id if valid. None if invalid."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id = int(parts[0])
        ts = int(parts[1])
        sig = parts[2]
        payload = f"{user_id}:{ts}"
        expected = hmac.new(_get_secret(), payload.encode(), hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        # Token expires after 30 days
        if time.time() - ts > 30 * 86400:
            return None
        return user_id
    except (ValueError, IndexError):
        return None

# ==========================================================
# 密码工具（不依赖外部包）
# ==========================================================
def hash_password(pwd: str, salt: str = None) -> tuple[str, str]:
    """返回 (hash_hex, salt)"""
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pwd.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()
    return pwd_hash, salt

def verify_password(pwd: str, stored_hash: str, salt: str) -> bool:
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pwd.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()
    return secrets.compare_digest(pwd_hash, stored_hash)

# ==========================================================
# 数据库初始化
# ==========================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.text_factory = str
    conn.execute("PRAGMA encoding = 'UTF-8'")
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    # 用户表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        pwd_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        membership TEXT DEFAULT 'free',
        membership_expires TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)
    # Migration: add membership columns if missing (for existing DB)
    try: cur.execute("ALTER TABLE users ADD COLUMN membership TEXT DEFAULT 'free'")
    except: pass
    try: cur.execute("ALTER TABLE users ADD COLUMN membership_expires TEXT DEFAULT ''")
    except: pass
    # 自选股表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        market TEXT NOT NULL DEFAULT 'cn',
        note TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(user_id, code, market),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    # 股价提醒表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        market TEXT NOT NULL DEFAULT 'cn',
        condition_type TEXT NOT NULL,  -- 'price_above', 'price_below', 'change_above', 'change_below'
        threshold REAL NOT NULL,
        active INTEGER DEFAULT 1,
        triggered INTEGER DEFAULT 0,
        last_notify TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    # 分析历史表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        market TEXT DEFAULT 'cn',
        aspect TEXT DEFAULT 'comprehensive',
        analysis TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================================
# 用户 CRUD
# ==========================================================
def create_user(username: str, email: str, password: str) -> dict:
    pwd_hash, salt = hash_password(password)
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, pwd_hash, salt) VALUES (?, ?, ?, ?)",
            (username, email, pwd_hash, salt)
        )
        conn.commit()
        user_id = cur.lastrowid
        return {"success": True, "user_id": user_id, "username": username}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            return {"error": "用户名已存在"}
        return {"error": "邮箱已存在"}
    finally:
        conn.close()

def verify_user(username: str, password: str) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, pwd_hash, salt FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"error": "用户不存在"}
    if not verify_password(password, row["pwd_hash"], row["salt"]):
        return {"error": "密码错误"}
    return {"success": True, "user_id": row["id"], "username": row["username"]}

def get_user_by_id(user_id: int) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

# ==========================================================
# 自选股 CRUD
# ==========================================================
def add_to_watchlist(user_id: int, code: str, name: str, market: str = "cn", note: str = "") -> dict:
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO watchlist (user_id, code, name, market, note) VALUES (?, ?, ?, ?, ?)",
            (user_id, code, name, market, note)
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid}
    except sqlite3.IntegrityError:
        return {"error": "已在自选股中"}
    finally:
        conn.close()

def remove_from_watchlist(user_id: int, code: str, market: str = "cn") -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist WHERE user_id = ? AND code = ? AND market = ?",
               (user_id, code, market))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return {"success": True, "deleted": deleted}

def get_watchlist(user_id: int) -> list:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, code, name, market, note, created_at FROM watchlist WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def is_in_watchlist(user_id: int, code: str, market: str = "cn") -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM watchlist WHERE user_id = ? AND code = ? AND market = ?",
               (user_id, code, market))
    row = cur.fetchone()
    conn.close()
    return row is not None

# ==========================================================
# 股价提醒 CRUD
# ==========================================================
def add_alert(user_id: int, code: str, name: str, market: str,
              condition_type: str, threshold: float) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO alerts (user_id, code, name, market, condition_type, threshold)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, code, name, market, condition_type, threshold)
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return {"success": True, "id": aid}

def remove_alert(alert_id: int, user_id: int) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return {"success": True, "deleted": deleted}

def get_alerts(user_id: int, active_only: bool = True) -> list:
    conn = get_db()
    cur = conn.cursor()
    sql = "SELECT * FROM alerts WHERE user_id = ?"
    args = [user_id]
    if active_only:
        sql += " AND active = 1"
    sql += " ORDER BY created_at DESC"
    cur.execute(sql, args)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def check_alerts(user_id: int, code: str, market: str, current_price: float, change_pct: float) -> list:
    """检查某只股票是否触发了用户的提醒，返回触发的提醒列表"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM alerts WHERE user_id = ? AND code = ? AND market = ? AND active = 1 AND triggered = 0",
        (user_id, code, market)
    )
    rows = cur.fetchall()
    triggered = []
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for r in rows:
        r = dict(r)
        hit = False
        if r["condition_type"] == "price_above" and current_price >= r["threshold"]:
            hit = True
        elif r["condition_type"] == "price_below" and current_price <= r["threshold"]:
            hit = True
        elif r["condition_type"] == "change_above" and change_pct >= r["threshold"]:
            hit = True
        elif r["condition_type"] == "change_below" and change_pct <= r["threshold"]:
            hit = True
        if hit:
            triggered.append(r)
            cur.execute("UPDATE alerts SET triggered = 1, last_notify = ? WHERE id = ?", (now, r["id"]))
    conn.commit()
    conn.close()
    return triggered

# ==========================================================
# 分析历史
# ==========================================================
def save_analysis(user_id: int, code: str, name: str, market: str, aspect: str, analysis: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO analysis_history (user_id, code, name, market, aspect, analysis)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, code, name, market, aspect, analysis)
    )
    conn.commit()
    conn.close()

def get_analysis_history(user_id: int, limit: int = 20):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM analysis_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ==========================================================
# 会员管理
# ==========================================================
def get_membership(user_id):
    """获取用户会员等级"""
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT membership, membership_expires FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row: return {"membership": "free", "expires": ""}
    return {"membership": row["membership"] or "free", "expires": row["membership_expires"] or ""}

def upgrade_membership(user_id, tier, months=1):
    """升级会员"""
    if tier not in ("vip", "svip"):
        return {"error": "invalid tier"}
    from datetime import datetime, timedelta
    current = get_membership(user_id)
    if current["membership"] == tier and current["expires"]:
        # Extend existing
        old_exp = datetime.strptime(current["expires"], "%Y-%m-%d")
        new_exp = old_exp + timedelta(days=30*months)
    else:
        new_exp = datetime.now() + timedelta(days=30*months)
    expires_str = new_exp.strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET membership = ?, membership_expires = ? WHERE id = ?",
                (tier, expires_str, user_id))
    conn.commit(); conn.close()
    return {"success": True, "membership": tier, "expires": expires_str}

def get_member_count():
    """统计各级会员数量"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT membership, COUNT(*) as cnt FROM users GROUP BY membership")
    rows = cur.fetchall()
    conn.close()
    result = {"free": 0, "vip": 0, "svip": 0}
    for tier, cnt in rows:
        if tier in result:
            result[tier] = cnt
    return result

# 初始化
init_db()
print("[auth_db] Database initialized at", DB_PATH)
