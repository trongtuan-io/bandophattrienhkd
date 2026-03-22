from flask import Blueprint, request, jsonify, session
from models import UserModel
from controllers.auth import login_required, admin_required

user_bp = Blueprint('user', __name__)


@user_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    users = UserModel.get_all()
    return jsonify(users)


@user_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password') or not data.get('full_name'):
        return jsonify({'error': 'Thiếu thông tin'}), 400

    new_id, error = UserModel.create(
        username=data['username'],
        password=data['password'],
        full_name=data['full_name'],
        ma_canbo=data.get('ma_canbo'),
        role=data.get('role', 'nv'),
        khu_vuc=data.get('khu_vuc'),
        sdt=data.get('sdt')
    )
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'message': 'Đã tạo tài khoản'})


@user_bp.route('/api/users/<int:user_id>/role', methods=['PUT'])
@login_required
@admin_required
def update_user_role(user_id):
    data = request.get_json()
    role = data.get('role')
    if role not in ('nv', 'canbo', 'kiem_duyet', 'admin', 'viewer'):
        return jsonify({'error': 'Role không hợp lệ'}), 400

    if user_id == session.get('user_id') and role != 'admin':
        return jsonify({'error': 'Không thể thay đổi role của chính mình'}), 400

    UserModel.update_role(user_id, role)
    return jsonify({'message': 'Đã cập nhật quyền'})


@user_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return jsonify({'error': 'Không thể xóa chính mình'}), 400

    UserModel.delete(user_id)
    return jsonify({'message': 'Đã xóa'})
