import pandas as pd
import pymysql
import random
import os

# ── Config ────────────────────────────────────
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'bandothue',
    'charset': 'utf8mb4'
}

# Danh sách các file Excel cần nạp
EXCEL_FILES = [
    'data/hộ kinh doanh dưới 200trđ thái hòa.xls',
    'data/HUYEN QUY HOP CU - (XA QUY HOP).xlsx',
    'data/HUYEN NGHIA DAN CU.xls',
    'data/THI XA THAI HOA CU.xls',
    'data/huyen_quynh_luu_cu.xlsx'
]

# --- BẢNG TỌA ĐỘ TRUNG TÂM CÁC PHƯỜNG XÃ ---
# Tọa độ trung tâm các Phường/Xã từ danh sách của Bảo
COORDS_MAP = {
    # Thị xã Thái Hòa
    'hòa hiếu': (19.3212, 105.4412),
    'quang phong': (19.3456, 105.4234),
    'quang tiến': (19.3289, 105.4456),
    'tây hiếu': (19.2945, 105.4278),
    'thái hòa': (19.3258, 105.4400),
    'vinh phú': (19.3123, 105.4567),
    'đông hiếu': (19.3156, 105.4821),
    'nghĩa thuận': (19.2834, 105.4612),

    # Huyện Quỳ Hợp
    'quỳ hợp': (19.3258, 105.1793),
    'thọ hợp': (19.3321, 105.1645), # Có trong ảnh dữ liệu của Bảo

    # Huyện Quỳnh Lưu
    'quỳnh thắng': (19.2558, 105.6025),
    
    # Mặc định
    'default': (19.3258, 105.1793)
}

def find_column(df, keywords):
    """Tìm tên cột thực tế trong dataframe dựa trên danh sách từ khóa gợi ý"""
    for col in df.columns:
        for kw in keywords:
            if kw.lower() in str(col).lower():
                return col
    return None

def get_coords_by_phuong(phuong_xa_name):
    """Tạo tọa độ ngẫu nhiên dựa trên tên phường xã"""
    name_low = str(phuong_xa_name).lower()
    
    # Tìm tọa độ trung tâm trong bảng COORDS_MAP
    center = COORDS_MAP['default']
    for key, coords in COORDS_MAP.items():
        if key in name_low:
            center = coords
            break
    
    # Tạo độ lệch ngẫu nhiên nhỏ để các hộ không đè lên nhau (bán kính ~800m)
    radius = 0.007 
    lat = center[0] + random.uniform(-radius, radius)
    lng = center[1] + random.uniform(-radius, radius)
    return round(lat, 6), round(lng, 6)

def main():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("[1] Kết nối database thành công")

        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        cur.execute("TRUNCATE TABLE ho_kinh_doanh")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")

        total_inserted = 0

        for file_path in EXCEL_FILES:
            if not os.path.exists(file_path):
                print(f"⚠️ File không tồn tại: {file_path}")
                continue

            print(f"\n🚀 Đang xử lý file: {file_path}")
            engine = 'xlrd' if file_path.endswith('.xls') else 'openpyxl'
            xls = pd.ExcelFile(file_path, engine=engine)
            
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=0) 
                
                col_mst = find_column(df, ['mst', 'mã số thuế','Mã số thuế','MST2'])
                col_ten = find_column(df, ['họ và tên', 'tên chủ', 'người đại diện','Họ và tên','Tên NNT'])
                col_cccd = find_column(df, ['cccd', 'căn cước', 'số định danh','CCCD', 'Số giấy tờ'])
                col_sdt = find_column(df, ['sđt', 'điện thoại', 'liên lạc','SDT','Điện thoại'])
                col_dc = find_column(df, ['địa chỉ', 'địa bàn', 'nơi kd','Địa chỉ KD','ĐCTS Số nhà/Đường phố'])
                col_phuong_xa = find_column(df, ['phường xã','Địa bàn','ĐCTS Tên Phường/Xã'])

                if not col_mst or not col_ten:
                    continue

                inserted_count = 0
                for _, row in df.iterrows():
                    mst = str(row[col_mst]).strip().replace('.0', '')
                    ten = str(row[col_ten]).strip()
                    
                    if not ten or ten == 'nan' or len(mst) < 5:
                        continue

                    dia_chi = str(row[col_dc]).strip() if col_dc else ""
                    phuong_xa = str(row[col_phuong_xa]).strip() if col_phuong_xa else ""

                    # --- CẬP NHẬT TỌA ĐỘ THEO PHƯỜNG XÃ ---
                    lat, lng = get_coords_by_phuong(phuong_xa)

                    sql = """INSERT INTO ho_kinh_doanh 
                             (ten_chu_ho, mst, dia_chi, phuong_xa, lat, lng, trang_thai) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s)
                             ON DUPLICATE KEY UPDATE ten_chu_ho=VALUES(ten_chu_ho)"""

                    cur.execute(sql, (ten, mst, dia_chi, phuong_xa, lat, lng, 'chua_dang_ky'))
                    inserted_count += 1
                
                conn.commit()
                print(f"   ✅ Đã nạp {inserted_count} hộ từ sheet [{sheet_name}]")
                total_inserted += inserted_count

        print(f"\n✨ Hoàn thành! Tổng cộng: {total_inserted} dòng.")

    except Exception as e:
        print(f"❌ Lỗi: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == '__main__':
    main()