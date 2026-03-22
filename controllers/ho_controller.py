import os
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from models import HoKinhDoanhModel, LichSuModel, LichSuDuyetModel
from controllers.auth import login_required
import config

ho_bp = Blueprint('ho', __name__)


@ho_bp.route('/api/ho', methods=['GET'])
@login_required
def get_ho():
    role = session.get('role', 'viewer')
    khu_vuc = session.get('khu_vuc')

    filters = {
        'quan_huyen': request.args.get('quan_huyen'),
        'phuong_xa': request.args.get('phuong_xa'),
        'trang_thai': request.args.get('trang_thai'),
        'search': request.args.get('search', '').strip() or None,
        'thang': request.args.get('thang'),
        'nhan_vien_id': request.args.get('nhan_vien_id'),
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v}

    data = HoKinhDoanhModel.get_all(filters=filters, role=role, khu_vuc=khu_vuc)
    return jsonify(data)


@ho_bp.route('/api/ho', methods=['POST'])
@login_required
def create_ho():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Không có quyền'}), 403

    data = request.get_json()
    if not data or not data.get('ten_chu_ho') or not data.get('lat') or not data.get('lng'):
        return jsonify({'error': 'Thiếu thông tin bắt buộc'}), 400

    new_id = HoKinhDoanhModel.create(data)
    return jsonify({'id': new_id, 'message': 'Đã thêm hộ kinh doanh'})


@ho_bp.route('/api/ho/<int:ho_id>', methods=['PUT'])
@login_required
def update_ho(ho_id):
    role = session.get('role')
    if role not in ('admin', 'nv', 'canbo', 'kiem_duyet'):
        return jsonify({'error': 'Không có quyền'}), 403

    data = request.get_json()
    ho = HoKinhDoanhModel.find_by_id(ho_id)
    if not ho:
        return jsonify({'error': 'Không tìm thấy'}), 404

    # Canbo/nv can only update in their area
    if role in ('nv', 'canbo') and session.get('khu_vuc') and ho['quan_huyen'] != session['khu_vuc']:
        return jsonify({'error': 'Ngoài khu vực quản lý'}), 403

    trang_thai = data.get('trang_thai', ho['trang_thai'])
    ghi_chu = data.get('ghi_chu', ho['ghi_chu'])
    nhan_vien_id = ho.get('nhan_vien_id')
    user_cap_nhat_id = ho.get('user_cap_nhat_id')

    # Save so_tai_khoan if provided
    so_tai_khoan = data.get('so_tai_khoan')
    if so_tai_khoan is not None:
        HoKinhDoanhModel.update_info(ho_id, {'so_tai_khoan': so_tai_khoan})
        # Refresh ho data
        ho = HoKinhDoanhModel.find_by_id(ho_id)

    # NV/Canbo submits for review -> auto-use their own nhan_vien_id
    if role in ('nv', 'canbo') and trang_thai == 'da_dang_ky':
        trang_thai = 'cho_duyet'
        user_cap_nhat_id = session['user_id']
        nhan_vien_id = session.get('nhan_vien_id') or nhan_vien_id

    # Only admin/kiem_duyet can approve (cho_duyet -> da_dang_ky)
    if trang_thai == 'da_dang_ky' and ho['trang_thai'] == 'cho_duyet':
        if role not in ('admin', 'kiem_duyet'):
            return jsonify({'error': 'Chỉ kiểm duyệt viên hoặc admin mới được duyệt'}), 403

    # Only admin/kiem_duyet can directly set da_dang_ky from chua_dang_ky
    if trang_thai == 'da_dang_ky' and ho['trang_thai'] == 'chua_dang_ky':
        if role not in ('admin', 'kiem_duyet'):
            trang_thai = 'cho_duyet'
            user_cap_nhat_id = session['user_id']
            nhan_vien_id = session.get('nhan_vien_id') or nhan_vien_id

    # Validate so_tai_khoan required before submitting for review
    if trang_thai == 'cho_duyet':
        if not ho.get('so_tai_khoan'):
            return jsonify({'error': 'Vui lòng nhập số tài khoản trước khi gửi duyệt'}), 400

    HoKinhDoanhModel.update_status(ho_id, trang_thai, ghi_chu, nhan_vien_id, old_ho=ho, user_cap_nhat_id=user_cap_nhat_id)
    LichSuModel.create(ho_id, session['user_id'], f'Cập nhật trạng thái: {trang_thai}', ghi_chu, nhan_vien_id)

    # Record approval history
    if trang_thai == 'cho_duyet' and ho['trang_thai'] == 'chua_dang_ky':
        LichSuDuyetModel.create(ho_id, session['user_id'], 'gui_duyet', ghi_chu)

    msg = 'Đã cập nhật'
    if trang_thai == 'cho_duyet':
        msg = 'Đã gửi yêu cầu duyệt. Chờ kiểm duyệt viên phê duyệt.'
    elif trang_thai == 'da_dang_ky' and ho['trang_thai'] == 'cho_duyet':
        msg = 'Đã duyệt thành công'

    return jsonify({'message': msg})


@ho_bp.route('/api/ho/<int:ho_id>/edit', methods=['PATCH'])
@login_required
def edit_ho(ho_id):
    """Edit business info (NV/admin can edit all except ten_chu_ho and mst)"""
    role = session.get('role')
    if role not in ('admin', 'nv', 'canbo', 'kiem_duyet'):
        return jsonify({'error': 'Không có quyền'}), 403

    ho = HoKinhDoanhModel.find_by_id(ho_id)
    if not ho:
        return jsonify({'error': 'Không tìm thấy'}), 404

    if role in ('nv', 'canbo') and session.get('khu_vuc') and ho['quan_huyen'] != session['khu_vuc']:
        return jsonify({'error': 'Ngoài khu vực quản lý'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Thiếu dữ liệu'}), 400

    # Remove protected fields
    data.pop('ten_chu_ho', None)
    data.pop('mst', None)
    data.pop('id', None)
    data.pop('trang_thai', None)

    HoKinhDoanhModel.update_info(ho_id, data)
    LichSuModel.create(ho_id, session['user_id'], 'Sửa thông tin hộ kinh doanh', None, session.get('nhan_vien_id'))
    return jsonify({'message': 'Đã cập nhật thông tin'})


@ho_bp.route('/api/ho/<int:ho_id>/upload', methods=['POST'])
@login_required
def upload_image(ho_id):
    if 'file' not in request.files:
        return jsonify({'error': 'Không có file'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Chưa chọn file'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        return jsonify({'error': 'Chỉ chấp nhận file ảnh'}), 400

    filename = secure_filename(f"{ho_id}_{int(datetime.now().timestamp())}{ext}")
    filepath = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    HoKinhDoanhModel.update_image(ho_id, filename)
    return jsonify({'message': 'Đã upload', 'filename': filename})


@ho_bp.route('/api/ho/cho-duyet', methods=['GET'])
@login_required
def get_cho_duyet():
    """Get pending approval list for kiem_duyet/admin"""
    role = session.get('role')
    if role not in ('admin', 'kiem_duyet'):
        return jsonify({'error': 'Không có quyền'}), 403

    quan_huyen = request.args.get('quan_huyen')
    phuong_xa = request.args.get('phuong_xa')

    from models import get_db
    db = get_db()
    with db.cursor() as cur:
        query = """
            SELECT h.*, nv.ho_ten as nhan_vien_ten, nv.ma_nv as nhan_vien_ma,
                   u.full_name as nguoi_gui_ten, u.ma_canbo as nguoi_gui_ma
            FROM ho_kinh_doanh h
            LEFT JOIN nhan_vien nv ON h.nhan_vien_id = nv.id
            LEFT JOIN users u ON h.user_cap_nhat_id = u.id
            WHERE h.trang_thai = 'cho_duyet'
        """
        params = []

        if quan_huyen:
            query += " AND h.quan_huyen = %s"
            params.append(quan_huyen)
        if phuong_xa:
            query += " AND h.phuong_xa = %s"
            params.append(phuong_xa)

        query += " ORDER BY h.ngay_cap_nhat DESC"
        cur.execute(query, params)
        rows = cur.fetchall()

    from datetime import date, datetime
    result = []
    for r in rows:
        item = dict(r)
        for k, v in item.items():
            if isinstance(v, (date, datetime)):
                item[k] = v.isoformat()
        result.append(item)
    return jsonify(result)


@ho_bp.route('/api/ho/<int:ho_id>/duyet', methods=['POST'])
@login_required
def approve_ho(ho_id):
    """Approve a pending business (cho_duyet -> da_dang_ky)"""
    role = session.get('role')
    if role not in ('admin', 'kiem_duyet'):
        return jsonify({'error': 'Chỉ kiểm duyệt viên hoặc admin mới được duyệt'}), 403

    ho = HoKinhDoanhModel.find_by_id(ho_id)
    if not ho:
        return jsonify({'error': 'Không tìm thấy'}), 404
    if ho['trang_thai'] != 'cho_duyet':
        return jsonify({'error': 'Hộ này không ở trạng thái chờ duyệt'}), 400

    HoKinhDoanhModel.update_status(
        ho_id, 'da_dang_ky',
        ghi_chu=ho.get('ghi_chu'),
        nhan_vien_id=ho.get('nhan_vien_id'),
        old_ho=ho,
        user_cap_nhat_id=ho.get('user_cap_nhat_id')
    )
    LichSuModel.create(ho_id, session['user_id'], 'Duyệt thành công', None, ho.get('nhan_vien_id'))
    LichSuDuyetModel.create(ho_id, session['user_id'], 'duyet', None)

    return jsonify({'message': 'Đã duyệt thành công! +1 điểm cho cán bộ'})


@ho_bp.route('/api/ho/<int:ho_id>/tu-choi', methods=['POST'])
@login_required
def reject_ho(ho_id):
    """Reject a pending business (cho_duyet -> chua_dang_ky)"""
    role = session.get('role')
    if role not in ('admin', 'kiem_duyet'):
        return jsonify({'error': 'Chỉ kiểm duyệt viên hoặc admin mới được từ chối'}), 403

    ho = HoKinhDoanhModel.find_by_id(ho_id)
    if not ho:
        return jsonify({'error': 'Không tìm thấy'}), 404

    data = request.get_json() or {}
    ly_do = data.get('ly_do', '')

    HoKinhDoanhModel.update_status(
        ho_id, 'chua_dang_ky',
        ghi_chu=f"Từ chối: {ly_do}" if ly_do else ho.get('ghi_chu'),
        old_ho=ho
    )
    LichSuModel.create(ho_id, session['user_id'], f'Từ chối duyệt: {ly_do}', ly_do)
    LichSuDuyetModel.create(ho_id, session['user_id'], 'tu_choi', ly_do)

    return jsonify({'message': 'Đã từ chối'})


@ho_bp.route('/api/ho/<int:ho_id>/lich-su-duyet', methods=['GET'])
@login_required
def get_lich_su_duyet(ho_id):
    """Get approval history for a specific business"""
    history = LichSuDuyetModel.get_by_ho(ho_id)
    return jsonify(history)


@ho_bp.route('/api/lich-su-duyet', methods=['GET'])
@login_required
def get_all_lich_su_duyet():
    """Get all approval history with filters"""
    role = session.get('role')
    if role not in ('admin', 'kiem_duyet'):
        return jsonify({'error': 'Không có quyền'}), 403

    from models import get_db
    from datetime import date, datetime

    hanh_dong = request.args.get('hanh_dong', '')
    phuong_xa = request.args.get('phuong_xa', '')
    quan_huyen = request.args.get('quan_huyen', '')
    tu_ngay = request.args.get('tu_ngay', '')
    den_ngay = request.args.get('den_ngay', '')
    keyword = request.args.get('keyword', '')

    db = get_db()
    with db.cursor() as cur:
        sql = """
            SELECT ld.*,
                   u.full_name as nguoi_duyet_ten, u.ma_canbo as nguoi_duyet_ma,
                   h.ten_chu_ho, h.ten_cua_hang, h.phuong_xa, h.quan_huyen, h.mst,
                   u_gui.full_name as nguoi_gui_ten, u_gui.ma_canbo as nguoi_gui_ma
            FROM lich_su_duyet ld
            LEFT JOIN users u ON ld.user_id = u.id
            LEFT JOIN ho_kinh_doanh h ON ld.ho_id = h.id
            LEFT JOIN users u_gui ON h.user_cap_nhat_id = u_gui.id
            WHERE 1=1
        """
        params = []

        if hanh_dong:
            sql += " AND ld.hanh_dong = %s"
            params.append(hanh_dong)
        if phuong_xa:
            sql += " AND h.phuong_xa = %s"
            params.append(phuong_xa)
        if quan_huyen:
            sql += " AND h.quan_huyen = %s"
            params.append(quan_huyen)
        if tu_ngay:
            sql += " AND ld.thoi_gian >= %s"
            params.append(tu_ngay + ' 00:00:00')
        if den_ngay:
            sql += " AND ld.thoi_gian <= %s"
            params.append(den_ngay + ' 23:59:59')
        if keyword:
            sql += " AND (h.ten_chu_ho LIKE %s OR h.ten_cua_hang LIKE %s OR h.mst LIKE %s OR u.full_name LIKE %s)"
            kw = f'%{keyword}%'
            params.extend([kw, kw, kw, kw])

        sql += " ORDER BY ld.thoi_gian DESC LIMIT 500"
        cur.execute(sql, params)
        rows = cur.fetchall()

    result = []
    for r in rows:
        item = dict(r)
        for k, v in item.items():
            if isinstance(v, (date, datetime)):
                item[k] = v.isoformat()
        result.append(item)
    return jsonify(result)


@ho_bp.route('/api/filters')
@login_required
def get_filters():
    return jsonify(HoKinhDoanhModel.get_filters())
