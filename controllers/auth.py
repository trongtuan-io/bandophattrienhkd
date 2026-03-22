from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import UserModel

auth_bp = Blueprint('auth', __name__)


# ── Decorators ───────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Chưa đăng nhập'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Không có quyền'}), 403
            flash('Bạn không có quyền truy cập.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def reviewer_or_admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') not in ('admin', 'kiem_duyet'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Không có quyền kiểm duyệt'}), 403
            flash('Bạn không có quyền truy cập.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def get_current_user():
    if 'user_id' in session:
        return UserModel.find_by_id(session['user_id'])
    return None


# ── Routes ───────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = UserModel.find_by_username(username)
        if UserModel.verify_password(user, password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            session['khu_vuc'] = user['khu_vuc']
            session['nhan_vien_id'] = user.get('nhan_vien_id')
            return redirect(url_for('index'))
        flash('Sai tên đăng nhập hoặc mật khẩu.', 'error')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
