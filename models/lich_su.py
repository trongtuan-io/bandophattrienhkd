from .db import get_db


class LichSuModel:

    @staticmethod
    def create(ho_id, user_id, hanh_dong, ghi_chu=None, nhan_vien_id=None):
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO lich_su (ho_id, user_id, nhan_vien_id, hanh_dong, ghi_chu) VALUES (%s, %s, %s, %s, %s)",
                (ho_id, user_id, nhan_vien_id, hanh_dong, ghi_chu)
            )
        db.commit()
