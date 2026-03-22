from datetime import date, datetime
from .db import get_db


class NhanVienModel:

    @staticmethod
    def get_all_with_stats():
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT nv.*,
                       COUNT(h.id) as so_ho_da_lam
                FROM nhan_vien nv
                LEFT JOIN ho_kinh_doanh h ON h.nhan_vien_id = nv.id AND h.trang_thai = 'da_dang_ky'
                WHERE nv.active = 1
                GROUP BY nv.id
                ORDER BY so_ho_da_lam DESC
            """)
            rows = cur.fetchall()

        for r in rows:
            r['so_ho_da_lam'] = int(r['so_ho_da_lam'])
            for k, v in r.items():
                if isinstance(v, (date, datetime)):
                    r[k] = v.isoformat()
        return rows

    @staticmethod
    def create(ho_ten, ma_nv=None, sdt=None, khu_vuc=None):
        db = get_db()
        with db.cursor() as cur:
            if ma_nv:
                cur.execute("SELECT id FROM nhan_vien WHERE ma_nv=%s", (ma_nv,))
                if cur.fetchone():
                    return None, 'Mã nhân viên đã tồn tại'
            cur.execute(
                "INSERT INTO nhan_vien (ho_ten, ma_nv, sdt, khu_vuc) VALUES (%s, %s, %s, %s)",
                (ho_ten, ma_nv or '', sdt or '', khu_vuc or '')
            )
        db.commit()
        return cur.lastrowid, None

    @staticmethod
    def delete(nv_id):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE nhan_vien SET active=0 WHERE id=%s", (nv_id,))
        db.commit()
