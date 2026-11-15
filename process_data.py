import pandas as pd
import requests
import json
from datetime import datetime

def fetch_and_process_eco_data(lat, lon, start_date, end_date):
    """
    Quy trình chuẩn: Trích xuất, làm sạch, chuẩn hóa dữ liệu NASA POWER & PhenoCam sang JSON.
    """
    print("=" * 50)
    print("[1/4] Đang trích xuất dữ liệu từ API NASA POWER...")
    
    # Gọi API NASA POWER (Lấy nhiệt độ 2m và bức xạ mặt trời sóng ngắn)
    nasa_url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"parameters=T2M,ALLSKY_SFC_SW_DWN&community=AG&"
        f"longitude={lon}&latitude={lat}&start={start_date}&end={end_date}&format=JSON"
    )
    
    response = requests.get(nasa_url)
    if response.status_code == 200:
        nasa_data = response.json()
        power_dict = nasa_data['properties']['parameter']
        
        # Chuyển đổi thành Pandas DataFrame
        df_nasa = pd.DataFrame(power_dict)
        df_nasa.index = pd.to_datetime(df_nasa.index, format='%Y%m%d')
        df_nasa.index.name = 'date'
        df_nasa.reset_index(inplace=True)
    else:
        raise Exception(f"Lỗi khi kết nối NASA POWER API: {response.status_code}")

    print("[2/4] Đang nạp và chuẩn bị dữ liệu PhenoCam (Chỉ số GCC)...")
    # Tạo chuỗi thời gian tương ứng để giả lập/đồng bộ dữ liệu PhenoCam mẫu
    date_range = pd.date_range(start=start_date, end=end_date)
    df_pheno = pd.DataFrame({
        'date': date_range,
        'gcc_90': [0.35 + (i % 30) * 0.002 for i in range(len(date_range))] # Chỉ số xanh mô phỏng
    })

    print("[3/4] Tiến hành làm sạch, xử lý giá trị lỗi và kết hợp dữ liệu...")
    
    # Ghép nối (Merge) 2 tập dữ liệu theo mốc thời gian 'date'
    df_merged = pd.merge(df_nasa, df_pheno, on='date', how='inner')
    
    # Làm sạch: Thay thế mã lỗi đặc trưng của NASA (-999, -99.9) thành giá trị thiếu (NA)
    df_merged.replace([-999, -99.9], pd.NA, inplace=True)
    
    # Nội suy tuyến tính để lấp đầy các khoảng trống nhỏ, sau đó điền giá trị 0 cho phần còn thiếu
    df_merged.interpolate(method='linear', inplace=True)
    df_merged.fillna(0, inplace=True)
    
    # Chuẩn hóa định dạng ngày tháng thành chuẩn ISO (YYYY-MM-DD)
    df_merged['date'] = df_merged['date'].dt.strftime('%Y-%m-%d')
    
    # Đổi tên các cột cho trực quan, dễ quản lý
    df_merged.rename(columns={
        'T2M': 'temperature_2m',
        'ALLSKY_SFC_SW_DWN': 'solar_radiation',
        'gcc_90': 'phenocam_gcc'
    }, inplace=True)

    print("[4/4] Xuất dữ liệu đã chuẩn hóa sang định dạng JSON...")
    
    # Chuyển DataFrame thành chuỗi JSON dạng danh sách bản ghi (records)
    json_output_str = df_merged.to_json(orient='records', date_format='iso', indent=4)
    
    # Lưu vào file cục bộ
    output_filename = "nasa_phenocam_standardized.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(json_output_str)
        
    print(f"Thành công! File JSON đã được lưu tại: '{output_filename}'")
    print("=" * 50)
    
    return json_output_str

# --- Thực thi chương trình ---
if __name__ == "__main__":
    # Tọa độ mẫu và khoảng thời gian (YYYYMMDD)
    LATITUDE = 21.0285
    LONGITUDE = 105.8542
    START = "20260101"
    END = "20260131"
    
    fetch_and_process_eco_data(LATITUDE, LONGITUDE, START, END)
