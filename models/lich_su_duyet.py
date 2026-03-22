from .db import get_db


class LichSuDuyetModel:

    @staticmethod
    def create(ho_id, user_id, hanh_dong, ghi_chu=None):
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO lich_su_duyet (ho_id, user_id, hanh_dong, ghi_chu) VALUES (%s, %s, %s, %s)",
                (ho_id, user_id, hanh_dong, ghi_chu)
            )
        db.commit()

    @staticmethod
    def get_by_ho(ho_id):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT ld.*, u.full_name as nguoi_duyet_ten, u.ma_canbo as nguoi_duyet_ma
                FROM lich_su_duyet ld
                LEFT JOIN users u ON ld.user_id = u.id
                WHERE ld.ho_id = %s
                ORDER BY ld.thoi_gian DESC
            """, (ho_id,))
            rows = cur.fetchall()
        from datetime import date, datetime
        for r in rows:
            for k, v in r.items():
                if isinstance(v, (date, datetime)):
                    r[k] = v.isoformat()
        return rows
