# TaskFlow – Quản lý công việc cá nhân (PySide6 + SQLite)

## Chạy ứng dụng
```bash
pip install -r requirements.txt
python main.py
```
Hoặc nhấp đúp `run.bat` (Windows) / chạy `./run.sh` (Linux, macOS) – tự tạo môi trường ảo và cài thư viện.
Yêu cầu: Python 3.9+.

## Tính năng
- **Công việc**: thêm / sửa / xóa (nút, chuột phải, phím `Delete`), nhiều dòng cùng lúc.
- **Tìm kiếm** không phân biệt hoa-thường và dấu tiếng Việt ("hoan thien" tìm được "Hoàn thiện").
- **Phân loại** theo phân loại (tự tạo), **mức ưu tiên** (Thấp / Trung bình / Cao / Khẩn cấp), trạng thái; lọc + sắp xếp.
- **Công việc con (checklist)**: chia nhỏ mỗi công việc thành các bước, tích từng bước trong hộp thoại.
  Tiến độ = số việc con đã xong (hiện `3/5` + thanh tiến độ); tích đủ thì công việc tự chuyển *Hoàn thành*,
  tích một phần thì *Đang thực hiện*. Menu chuột phải có *Chuyển trạng thái*.
- **Dashboard**: tỷ lệ hoàn thành, thẻ số liệu, biểu đồ trạng thái / ưu tiên / 7 ngày qua, việc sắp đến hạn, tiến độ theo phân loại.
- **Nhắc nhở hạn**: chọn nhắc trước 15 phút … 2 ngày; thông báo nổi trong app + thông báo khay hệ thống; chuông 🔔 ở thanh trên.
  Đóng cửa sổ sẽ thu nhỏ xuống khay hệ thống để tiếp tục nhắc (chuột phải biểu tượng → Thoát).
- **Lập kế hoạch** theo **Ngày / Tuần / Tháng**: điều hướng ‹ ›, nhấp ngày để xem chi tiết, tick để hoàn thành nhanh.
- Giao diện **sáng / tối** (lưu lại lựa chọn).

Phím tắt: `Ctrl+N` thêm việc · `Ctrl+F` tìm kiếm · `Ctrl+1/2/3` chuyển trang.

## Cấu trúc
```
TaskFlow/
├── main.py              # điểm khởi chạy
├── requirements.txt
├── run.bat / run.sh
├── data/taskflow.db     # tự tạo khi chạy lần đầu (SQLite)
└── app/
    ├── database.py      # truy vấn SQLite, thống kê
    ├── models.py        # Task, hằng số, hàm tiện ích
    ├── reminder.py      # dịch vụ nhắc nhở (QTimer)
    ├── styles.py        # bảng màu sáng/tối + QSS
    ├── icon.py          # biểu tượng vẽ bằng code
    └── ui/
        ├── main_window.py     # cửa sổ chính, sidebar, khay hệ thống
        ├── dashboard_page.py  # Dashboard
        ├── task_page.py       # danh sách công việc
        ├── planner_page.py    # lịch ngày/tuần/tháng
        ├── task_dialog.py     # hộp thoại thêm/sửa
        └── widgets.py         # biểu đồ, thẻ, toast
```

## Ghi chú
- Lần chạy đầu có vài công việc **mẫu** để xem thử; xóa chúng hoặc xóa `data/taskflow.db` để bắt đầu mới.
- Sao lưu dữ liệu = sao chép file `data/taskflow.db`.
