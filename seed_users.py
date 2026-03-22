import pandas as pd
import pymysql
from werkzeug.security import generate_password_hash

def seed_users():
    # 1. Đọc file Excel .xlsx
    file_path = 'data/thongtincanbo.xlsx' 
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        print(f"[1] Đã đọc file: {file_path}")
        
        # Chuẩn hóa tên cột (xóa khoảng trắng thừa)
        df.columns = [c.strip().lower() for c in df.columns]
        
        if 'macb' not in df.columns or 'hoten' not in df.columns:
            print(f"Lỗi: File Excel phải có cột 'macb' và 'hoten'. Cột hiện có: {df.columns.tolist()}")
            return
            
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return

    # 2. Kết nối Database
    db_name = 'bandothue'
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='', # XAMPP mặc định để trống
            database=db_name,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        print(f"[2] Kết nối database '{db_name}' thành công")

        # Mật khẩu mặc định và mã băm chuẩn cho Mac
        default_password = "bidv@123"
        hashed_pw = generate_password_hash(default_password, method='pbkdf2:sha256')

        # 3. SQL INSERT (Khớp 5 cột: username, password_hash, full_name, ma_canbo, role)
        sql = """
        INSERT INTO users (username, password_hash, full_name, ma_canbo, role) 
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            full_name = VALUES(full_name),
            password_hash = VALUES(password_hash),
            ma_canbo = VALUES(ma_canbo)
        """

        count = 0
        # CHỈ DÙNG 1 VÒNG LẶP DUY NHẤT
        for index, row in df.iterrows():
            ma_cb = str(row['macb']).strip()
            ten_cb = str(row['hoten']).strip()
            username = ma_cb.lower()

            # Thực thi với đúng 5 tham số truyền vào tuple
            cursor.execute(sql, (username, hashed_pw, ten_cb, ma_cb, 'nv'))
            count += 1
        
        conn.commit()
        print(f"[3] Đã nạp thành công {count} cán bộ vào hệ thống!")
        print(f"🔑 Mật khẩu mặc định cho tất cả: {default_password}")

    except Exception as e:
        print(f"Lỗi database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    seed_users()