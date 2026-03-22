from datetime import datetime, date
from .db import get_db


class HoKinhDoanhModel:

    @staticmethod
    def get_all(filters=None, role='viewer', khu_vuc=None):
        db = get_db()
        filters = filters or {}

        query = """SELECT h.*, nv.ho_ten as nhan_vien_ten, nv.ma_nv as nhan_vien_ma,
                          u_cap.full_name as nguoi_cap_nhat_ten
                   FROM ho_kinh_doanh h
                   LEFT JOIN nhan_vien nv ON h.nhan_vien_id = nv.id
                   LEFT JOIN users u_cap ON h.user_cap_nhat_id = u_cap.id
                   WHERE 1=1"""
        params = []

        if role in ('canbo', 'nv') and khu_vuc:
            query += " AND h.quan_huyen = %s"
            params.append(khu_vuc)

        if filters.get('quan_huyen'):
            query += " AND h.quan_huyen = %s"
            params.append(filters['quan_huyen'])

        if filters.get('phuong_xa'):
            query += " AND h.phuong_xa = %s"
            params.append(filters['phuong_xa'])

        if filters.get('trang_thai'):
            query += " AND h.trang_thai = %s"
            params.append(filters['trang_thai'])

        if filters.get('search'):
            query += " AND (h.ten_chu_ho LIKE %s OR h.ten_cua_hang LIKE %s OR h.mst LIKE %s)"
            params.extend([f'%{filters["search"]}%'] * 3)

        if filters.get('thang'):
            query += " AND DATE_FORMAT(h.ngay_tao, '%%Y-%%m') = %s"
            params.append(filters['thang'])

        if filters.get('nhan_vien_id'):
            query += " AND h.nhan_vien_id = %s"
            params.append(filters['nhan_vien_id'])

        with db.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        result = []
        for r in rows:
            item = dict(r)
            for k, v in item.items():
                if isinstance(v, (date, datetime)):
                    item[k] = v.isoformat()
            if role == 'viewer':
                item.pop('mst', None)
                item.pop('ghi_chu', None)
                item.pop('cccd', None)
                item.pop('sdt', None)
                item.pop('so_tai_khoan', None)
            result.append(item)
        return result

    @staticmethod
    def find_by_id(ho_id):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM ho_kinh_doanh WHERE id=%s", (ho_id,))
            return cur.fetchone()

    @staticmethod
    def create(data):
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                """INSERT INTO ho_kinh_doanh
                   (ten_chu_ho, ten_cua_hang, mst, dia_chi, phuong_xa, quan_huyen, lat, lng, trang_thai, cccd, sdt, so_tai_khoan)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (data['ten_chu_ho'], data.get('ten_cua_hang', ''), data.get('mst', ''),
                 data.get('dia_chi', ''), data.get('phuong_xa', ''), data.get('quan_huyen', ''),
                 float(data['lat']), float(data['lng']), 'chua_dang_ky',
                 data.get('cccd', ''), data.get('sdt', ''), data.get('so_tai_khoan', ''))
            )
            new_id = cur.lastrowid
        db.commit()
        return new_id

    @staticmethod
    def update_status(ho_id, trang_thai, ghi_chu=None, nhan_vien_id=None, old_ho=None, user_cap_nhat_id=None):
        db = get_db()
        now = datetime.now()

        ngay_ht = now if trang_thai == 'da_dang_ky' and old_ho and old_ho['trang_thai'] != 'da_dang_ky' else (old_ho or {}).get('ngay_hoan_thanh')

        if trang_thai == 'chua_dang_ky':
            nhan_vien_id = None
            ngay_ht = None
            user_cap_nhat_id = None
        elif trang_thai == 'cho_duyet':
            # When submitting for review, keep user_cap_nhat_id passed from controller
            user_cap_nhat_id = user_cap_nhat_id or (old_ho or {}).get('user_cap_nhat_id')
        elif trang_thai == 'da_dang_ky':
            # When approving, keep original submitter
            user_cap_nhat_id = user_cap_nhat_id or (old_ho or {}).get('user_cap_nhat_id')

        with db.cursor() as cur:
            cur.execute(
                """UPDATE ho_kinh_doanh
                   SET trang_thai=%s, ghi_chu=%s, ngay_cap_nhat=%s,
                       nhan_vien_id=%s, ngay_hoan_thanh=%s, user_cap_nhat_id=%s
                   WHERE id=%s""",
                (trang_thai, ghi_chu, now, nhan_vien_id, ngay_ht, user_cap_nhat_id, ho_id)
            )
        db.commit()

    @staticmethod
    def update_image(ho_id, filename):
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE ho_kinh_doanh SET hinh_anh=%s WHERE id=%s", (filename, ho_id))
        db.commit()

    @staticmethod
    def get_filters():
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT DISTINCT quan_huyen FROM ho_kinh_doanh ORDER BY quan_huyen")
            quan_list = cur.fetchall()
            cur.execute("SELECT DISTINCT phuong_xa, quan_huyen FROM ho_kinh_doanh ORDER BY phuong_xa")
            phuong_list = cur.fetchall()
        return {
            'quan_huyen': [r['quan_huyen'] for r in quan_list],
            'phuong_xa': [{'ten': r['phuong_xa'], 'quan': r['quan_huyen']} for r in phuong_list],
        }

    @staticmethod
    def update_info(ho_id, data):
        """Update editable fields (not ten_chu_ho, mst)"""
        db = get_db()
        allowed = ['ten_cua_hang', 'dia_chi', 'phuong_xa', 'quan_huyen', 'cccd', 'sdt', 'so_tai_khoan', 'lat', 'lng']
        sets = []
        params = []
        for key in allowed:
            if key in data:
                sets.append(f"{key}=%s")
                params.append(data[key])
        if not sets:
            return
        params.append(ho_id)
        with db.cursor() as cur:
            cur.execute(f"UPDATE ho_kinh_doanh SET {', '.join(sets)}, ngay_cap_nhat=NOW() WHERE id=%s", params)
        db.commit()

    @staticmethod
    def get_chua_dang_ky():
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT h.*, nv.ho_ten as nhan_vien_ten
                FROM ho_kinh_doanh h
                LEFT JOIN nhan_vien nv ON h.nhan_vien_id = nv.id
                WHERE h.trang_thai='chua_dang_ky'
                ORDER BY h.quan_huyen, h.phuong_xa
            """)
            return cur.fetchall()
