from datetime import date, datetime
from flask import Blueprint, request, jsonify
from models import NhanVienModel
from controllers.auth import login_required, admin_required

nhanvien_bp = Blueprint('nhanvien', __name__)


@nhanvien_bp.route('/api/nhanvien', methods=['GET'])
def get_nhanvien():
    rows = NhanVienModel.get_all_with_stats()
    return jsonify(rows)


@nhanvien_bp.route('/api/nhanvien', methods=['POST'])
@login_required
@admin_required
def create_nhanvien():
    data = request.get_json()
    if not data or not data.get('ho_ten'):
        return jsonify({'error': 'Thiếu họ tên'}), 400

    new_id, error = NhanVienModel.create(
        ho_ten=data['ho_ten'],
        ma_nv=data.get('ma_nv'),
        sdt=data.get('sdt'),
        khu_vuc=data.get('khu_vuc')
    )
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'message': 'Đã thêm nhân viên'})


@nhanvien_bp.route('/api/nhanvien/<int:nv_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_nhanvien(nv_id):
    NhanVienModel.delete(nv_id)
    return jsonify({'message': 'Đã xóa nhân viên'})
