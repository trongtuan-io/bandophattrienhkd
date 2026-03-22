import pymysql
from pymysql.cursors import DictCursor
from flask import g
from werkzeug.security import generate_password_hash
import config


def get_connection(**kwargs):
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset=config.DB_CHARSET,
        cursorclass=DictCursor,
        **kwargs
    )


def get_db():
    if 'db' not in g:
        g.db = get_connection(database=config.DB_NAME)
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db:
        db.close()


def init_db():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.close()

    conn = get_connection(database=config.DB_NAME)
    with conn.cursor() as cur:
        _create_tables(cur)
        _seed_data(cur)
    conn.commit()
    conn.close()
    print("[OK] Database bandothue initialized.")


def _create_tables(cur):
    # nhan_vien MUST be created before users (FK dependency)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nhan_vien (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ho_ten VARCHAR(200) NOT NULL,
            ma_nv VARCHAR(50) UNIQUE,
            sdt VARCHAR(20),
            khu_vuc VARCHAR(100),
            active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(200) NOT NULL,
            ma_canbo VARCHAR(50),
            role VARCHAR(20) NOT NULL DEFAULT 'nv',
            khu_vuc VARCHAR(100),
            nhan_vien_id INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    # Migration: add ma_canbo column if not exists
    try:
        cur.execute("ALTER TABLE users ADD COLUMN ma_canbo VARCHAR(50) AFTER full_name")
    except Exception:
        pass

    # Migration: add nhan_vien_id to users if not exists
    try:
        cur.execute("ALTER TABLE users ADD COLUMN nhan_vien_id INT, ADD FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien(id) ON DELETE SET NULL")
    except Exception:
        pass

    # Migration: add user_cap_nhat_id to ho_kinh_doanh if not exists
    try:
        cur.execute("ALTER TABLE ho_kinh_doanh ADD COLUMN user_cap_nhat_id INT, ADD FOREIGN KEY (user_cap_nhat_id) REFERENCES users(id) ON DELETE SET NULL")
    except Exception:
        pass

    # Migration: add cccd, sdt, so_tai_khoan to ho_kinh_doanh
    for col, coldef in [('cccd', 'VARCHAR(20)'), ('sdt', 'VARCHAR(20)'), ('so_tai_khoan', 'VARCHAR(50)')]:
        try:
            cur.execute(f"ALTER TABLE ho_kinh_doanh ADD COLUMN {col} {coldef}")
        except Exception:
            pass

    cur.execute('''
        CREATE TABLE IF NOT EXISTS ho_kinh_doanh (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ten_chu_ho VARCHAR(200) NOT NULL,
            ten_cua_hang VARCHAR(200),
            mst VARCHAR(50),
            dia_chi VARCHAR(300),
            phuong_xa VARCHAR(100),
            quan_huyen VARCHAR(100),
            lat DOUBLE NOT NULL,
            lng DOUBLE NOT NULL,
            trang_thai VARCHAR(30) NOT NULL DEFAULT 'chua_dang_ky',
            nhan_vien_id INT,
            user_cap_nhat_id INT,
            ngay_hoan_thanh DATETIME,
            ngay_tao DATE DEFAULT (CURDATE()),
            ngay_cap_nhat DATETIME,
            ghi_chu TEXT,
            hinh_anh VARCHAR(300),
            cccd VARCHAR(20),
            sdt VARCHAR(20),
            so_tai_khoan VARCHAR(50),
            FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien(id) ON DELETE SET NULL,
            FOREIGN KEY (user_cap_nhat_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS lich_su (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ho_id INT NOT NULL,
            user_id INT,
            nhan_vien_id INT,
            hanh_dong VARCHAR(300) NOT NULL,
            ghi_chu TEXT,
            thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ho_id) REFERENCES ho_kinh_doanh(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (nhan_vien_id) REFERENCES nhan_vien(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS lich_su_duyet (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ho_id INT NOT NULL,
            user_id INT NOT NULL,
            hanh_dong VARCHAR(50) NOT NULL,
            ghi_chu TEXT,
            thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ho_id) REFERENCES ho_kinh_doanh(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    ''')


def _seed_data(cur):
    # Nhan vien seed first (users depends on it)
    cur.execute("SELECT COUNT(*) as c FROM nhan_vien")
    if cur.fetchone()['c'] == 0:
        cur.executemany(
            "INSERT INTO nhan_vien (ho_ten, ma_nv, sdt, khu_vuc) VALUES (%s, %s, %s, %s)",
            [
                ('Trần Văn Hùng', 'NV001', '0901234567', 'Ba Đình'),
                ('Lê Thị Mai', 'NV002', '0901234568', 'Ba Đình'),
                ('Phạm Đức Toàn', 'NV003', '0901234569', 'Đống Đa'),
                ('Nguyễn Hoàng Nam', 'NV004', '0901234570', 'Đống Đa'),
                ('Võ Thị Hạnh', 'NV005', '0901234571', 'Hai Bà Trưng'),
            ]
        )

    # Admin
    cur.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
            ('admin', generate_password_hash('admin123', method='pbkdf2:sha256'), 'Admin', 'admin')
        )

    # Canbo - auto-create nhan_vien and link
    cur.execute("SELECT id FROM users WHERE username='canbo_badinh'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO nhan_vien (ho_ten, ma_nv, sdt, khu_vuc) VALUES (%s, %s, %s, %s)",
            ('Cán bộ Thái Hòa', 'CB001', '', 'Thái Hòa')
        )
        nv_id = cur.lastrowid
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, ma_canbo, role, khu_vuc, nhan_vien_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            ('canbo_badinh', generate_password_hash('123456'), 'Cán bộ Thái Hòa', 'CB001', 'nv', 'Thái Hòa', nv_id)
        )

    # Kiem duyet
    cur.execute("SELECT id FROM users WHERE username='kiemduyetvien'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (username, password_hash, full_name, ma_canbo, role) VALUES (%s, %s, %s, %s, %s)",
            ('kiemduyetvien', generate_password_hash('123456'), 'Người Kiểm Duyệt', 'KD001', 'kiem_duyet')
        )
