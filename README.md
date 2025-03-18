# TuCoin Blockchain

TuCoin là một hệ thống blockchain đơn giản được xây dựng bằng Python, cho phép các máy trong mạng nội bộ kết nối với nhau, đào coin và thực hiện giao dịch.

## Tổng quan

- **Tên đồng coin**: TuCoin
- **Phần thưởng đào khối**: 100 TuCoin cho mỗi khối hợp lệ
- **Kiến trúc**: Hệ thống hoạt động trên mạng ngang hàng (Peer-to-Peer - P2P)
- **Cơ chế đồng thuận**: Proof of Work (PoW) trong phiên bản hiện tại

## Cài đặt

### Yêu cầu hệ thống

- Python 3.7 trở lên
- Các thư viện Python: `socket`, `threading`, `tkinter`, `json`, `hashlib`, `datetime`

### Cài đặt các thư viện cần thiết

```bash
pip install -r requirements.txt
```

## Cấu trúc dự án

```
tucoin/
├── README.md
├── requirements.txt
├── tucoin_blockchain.py   # Lớp Blockchain, Block, Transaction
├── tucoin_node.py         # Lớp Node quản lý kết nối P2P
├── tucoin_wallet.py       # Lớp Wallet quản lý khóa và địa chỉ
└── tucoin_gui.py          # Giao diện người dùng
```

## Cách sử dụng

### 1. Khởi động ứng dụng

```bash
python tucoin_gui.py
```

### 2. Tạo ví mới hoặc nhập ví hiện có

Khi khởi động lần đầu, ứng dụng sẽ tạo một ví mới cho bạn. Bạn có thể lưu thông tin ví để sử dụng lại sau này.

### 3. Kết nối với các node khác

- Nhập địa chỉ IP và cổng của node khác trong mạng
- Nhấn "Connect" để kết nối

### 4. Đào coin

- Nhấn nút "Mine" để bắt đầu đào khối mới
- Khi đào thành công, bạn sẽ nhận được 100 TuCoin

### 5. Gửi coin

- Nhập địa chỉ người nhận
- Nhập số lượng TuCoin muốn gửi
- Nhấn "Send" để tạo giao dịch

## Cách thức hoạt động

### Block

Mỗi khối trong blockchain chứa:
- Index: Số thứ tự của khối
- Timestamp: Thời gian khối được tạo
- Transactions: Danh sách các giao dịch
- Proof: Giá trị nonce (trong PoW)
- Previous Hash: Hash của khối trước đó
- Hash: Hash của khối hiện tại

### Giao dịch

Mỗi giao dịch chứa:
- Sender: Địa chỉ của người gửi
- Receiver: Địa chỉ của người nhận
- Amount: Số lượng TuCoin
- Timestamp: Th���i gian giao dịch

### Proof of Work

- Thuật toán đào tìm một giá trị nonce sao cho hash của khối bắt đầu bằng một số lượng số 0 nhất định
- Độ khó có thể điều chỉnh bằng cách thay đổi số lượng số 0 yêu cầu

### Mạng P2P

- Mỗi node lưu trữ một bản sao đầy đủ của blockchain
- Khi một node đào được khối mới, nó sẽ phát sóng khối đó đến tất cả các node khác
- Các node khác sẽ xác thực khối và thêm vào blockchain của họ nếu hợp lệ

## Thiết lập mạng nội bộ

### Chạy nhiều node trên cùng một máy (cho mục đích thử nghiệm)

1. Mở nhiều cửa sổ terminal
2. Trong mỗi cửa sổ, chạy lệnh với cổng khác nhau:

```bash
python tucoin_gui.py --port 5000
python tucoin_gui.py --port 5001
python tucoin_gui.py --port 5002
```

### Chạy trên nhiều máy trong mạng nội bộ

1. Xác định địa chỉ IP của mỗi máy trong mạng nội bộ
2. Trên mỗi máy, chạy:

```bash
python tucoin_gui.py --host YOUR_IP_ADDRESS --port 5000
```

3. Kết nối các node với nhau bằng cách nhập địa chỉ IP và cổng của các node khác

## Lưu ý

- Đây là một hệ thống blockchain đơn giản cho mục đích học tập
- Không sử d���ng trong môi trường sản xuất thực tế
- Không có cơ chế bảo mật mạnh như các blockchain thương mại

## Phát triển trong tương lai

- Chuyển từ Proof of Work sang Proof of Stake
- Cải thiện giao diện người dùng
- Thêm tính năng khôi phục ví
- Tối ưu hóa hiệu suất mạng

## Đóng góp

Mọi đóng góp đều được hoan nghênh! Vui lòng tạo issue hoặc pull request.

## Giấy phép

Dự án này được phân phối dưới giấy phép MIT.