from .db import get_db
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel:

    @staticmethod
    def find_by_username(username):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username=%s", (username,))
            return cur.fetchone()

    @staticmethod
    def find_by_id(user_id):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            return cur.fetchone()

    @staticmethod
    def get_all():
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT id, username, full_name, ma_canbo, role, khu_vuc, nhan_vien_id FROM users ORDER BY id")
            return cur.fetchall()

    @staticmethod
    def create(username, password, full_name, ma_canbo=None, role='nv', khu_vuc=None, sdt=None):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cur.fetchone():
                return None, 'Tên đăng nhập đã tồn tại'

            # Auto-create nhan_vien for nv/canbo roles
            nhan_vien_id = None
            if role in ('nv', 'canbo'):
                cur.execute(
                    "INSERT INTO nhan_vien (ho_ten, ma_nv, sdt, khu_vuc) VALUES (%s, %s, %s, %s)",
                    (full_name, ma_canbo or '', sdt or '', khu_vuc or '')
                )
                nhan_vien_id = cur.lastrowid

            cur.execute(
                "INSERT INTO users (username, password_hash, full_name, ma_canbo, role, khu_vuc, nhan_vien_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (username, generate_password_hash(password), full_name, ma_canbo, role, khu_vuc, nhan_vien_id)
            )
        db.commit()
        return cur.lastrowid, None

    @staticmethod
    def update_role(user_id, role):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
        db.commit()

    @staticmethod
    def delete(user_id):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()

    @staticmethod
    def verify_password(user, password):
        if user and check_password_hash(user['password_hash'], password):
            return True
        return False

    @staticmethod
    def get_leaderboard():
        """Top 10 can bo by approved submissions (diem)"""
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.full_name, u.ma_canbo, u.khu_vuc,
                       COUNT(h.id) as diem
                FROM users u
                LEFT JOIN ho_kinh_doanh h ON h.user_cap_nhat_id = u.id AND h.trang_thai = 'da_dang_ky'
                WHERE u.role IN ('nv', 'canbo')
                GROUP BY u.id
                ORDER BY diem DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
        for r in rows:
            r['diem'] = int(r['diem'])
        return rows
