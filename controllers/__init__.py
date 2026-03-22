from .auth import auth_bp
from .ho_controller import ho_bp
from .nhanvien_controller import nhanvien_bp
from .thongke_controller import thongke_bp
from .export_controller import export_bp
from .user_controller import user_bp

all_blueprints = [auth_bp, ho_bp, nhanvien_bp, thongke_bp, export_bp, user_bp]
