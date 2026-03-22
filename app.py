"""
BanDoThue - Ban Do Phat Trien HKD
MVC Architecture
"""

import os
from flask import Flask, render_template, session, send_file, redirect, url_for
import config
from models import init_db, close_db
from controllers import all_blueprints
from controllers.auth import login_required, get_current_user


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    # Register blueprints
    for bp in all_blueprints:
        app.register_blueprint(bp)

    # Teardown
    app.teardown_appcontext(close_db)

    # ── Page routes ──────────────────────────────────────

    @app.route('/')
    @login_required
    def index():
        return render_template('index.html',
                               user=get_current_user(),
                               role=session.get('role', 'viewer'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        return render_template('dashboard.html',
                               user=get_current_user(),
                               role=session.get('role'))

    @app.route('/duyet')
    @login_required
    def duyet_page():
        role = session.get('role')
        if role not in ('admin', 'kiem_duyet'):
            return redirect(url_for('index'))
        return render_template('duyet.html',
                               user=get_current_user(),
                               role=role)

    @app.route('/lich-su-duyet')
    @login_required
    def lich_su_duyet_page():
        role = session.get('role')
        if role not in ('admin', 'kiem_duyet'):
            return redirect(url_for('index'))
        return render_template('lich_su_duyet.html',
                               user=get_current_user(),
                               role=role)

    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_file(os.path.join(config.UPLOAD_FOLDER, filename))

    return app


if __name__ == '__main__':
    init_db()
    app = create_app()
    print("=" * 50)
    print("  Bản Đồ Phát Triển HKD - http://localhost:5000")
    print("  Admin: admin / admin123")
    print("  Cán bộ: canbo_badinh / 123456")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)
