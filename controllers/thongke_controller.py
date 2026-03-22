from flask import Blueprint, jsonify, session
from models import get_db, UserModel
from controllers.auth import login_required

thongke_bp = Blueprint('thongke', __name__)


@thongke_bp.route('/api/thongke')
@login_required
def thongke():
    db = get_db()
    role = session.get('role')
    khu_vuc = session.get('khu_vuc')

    where = "WHERE 1=1"
    params = []
    if role in ('nv', 'canbo') and khu_vuc:
        where += " AND quan_huyen = %s"
        params.append(khu_vuc)

    with db.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) as c FROM ho_kinh_doanh {where}", params)
        total = cur.fetchone()['c']

        cur.execute(f"SELECT COUNT(*) as c FROM ho_kinh_doanh {where} AND trang_thai='da_dang_ky'", params)
        da_dk = cur.fetchone()['c']

        cur.execute(f"SELECT COUNT(*) as c FROM ho_kinh_doanh {where} AND trang_thai='cho_duyet'", params)
        cho_duyet = cur.fetchone()['c']

        chua_dk = total - int(da_dk) - int(cho_duyet)

        cur.execute(f"""
            SELECT phuong_xa, quan_huyen,
                   COUNT(*) as tong,
                   SUM(CASE WHEN trang_thai='chua_dang_ky' THEN 1 ELSE 0 END) as chua_dk
            FROM ho_kinh_doanh {where}
            GROUP BY phuong_xa, quan_huyen
            HAVING chua_dk > 0
            ORDER BY chua_dk DESC
            LIMIT 10
        """, params)
        top_phuong = cur.fetchall()

        cur.execute(f"""
            SELECT quan_huyen,
                   COUNT(*) as tong,
                   SUM(CASE WHEN trang_thai='da_dang_ky' THEN 1 ELSE 0 END) as da_dk,
                   SUM(CASE WHEN trang_thai='cho_duyet' THEN 1 ELSE 0 END) as cho_duyet,
                   SUM(CASE WHEN trang_thai='chua_dang_ky' THEN 1 ELSE 0 END) as chua_dk
            FROM ho_kinh_doanh {where}
            GROUP BY quan_huyen
            ORDER BY chua_dk DESC
        """, params)
        theo_quan = cur.fetchall()

        # Old nhan_vien leaderboard
        cur.execute("""
            SELECT nv.id, nv.ho_ten, nv.ma_nv, nv.khu_vuc,
                   COUNT(h.id) as so_ho_da_lam
            FROM nhan_vien nv
            LEFT JOIN ho_kinh_doanh h ON h.nhan_vien_id = nv.id AND h.trang_thai = 'da_dang_ky'
            WHERE nv.active = 1
            GROUP BY nv.id
            ORDER BY so_ho_da_lam DESC
        """)
        bang_xep_hang = cur.fetchall()

    for row in top_phuong:
        for k in ('tong', 'chua_dk'):
            row[k] = int(row[k])
    for row in theo_quan:
        for k in ('tong', 'da_dk', 'cho_duyet', 'chua_dk'):
            row[k] = int(row[k])
    for row in bang_xep_hang:
        row['so_ho_da_lam'] = int(row['so_ho_da_lam'])

    # Top 10 can bo leaderboard (by approved points)
    top_canbo = UserModel.get_leaderboard()

    # Count pending approvals for kiem_duyet/admin
    pending_count = 0
    if role in ('admin', 'kiem_duyet'):
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) as c FROM ho_kinh_doanh WHERE trang_thai='cho_duyet'")
            pending_count = cur.fetchone()['c']

    return jsonify({
        'tong': total,
        'da_dang_ky': int(da_dk),
        'cho_duyet': int(cho_duyet),
        'chua_dang_ky': int(chua_dk),
        'top_phuong': top_phuong,
        'theo_quan': theo_quan,
        'bang_xep_hang_nv': bang_xep_hang,
        'top_canbo': top_canbo,
        'pending_count': pending_count,
    })
