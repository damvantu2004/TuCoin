import hashlib
import json
import os
import base64
import secrets
from typing import Dict, Tuple, Optional

class Wallet:
    """Quản lý ví TuCoin với khóa và địa chỉ."""
    
    def __init__(self, private_key: Optional[str] = None):
        """
        Khởi tạo một ví mới hoặc từ khóa riêng tư hiện có.
        
        Args:
            private_key: Khóa riêng tư (nếu không có, tạo mới)
        """
        if private_key:
            self.private_key = private_key
        else:
            # Tạo khóa riêng tư mới (32 bytes ngẫu nhiên)
            self.private_key = secrets.token_hex(32)
        
        # Tạo địa chỉ từ khóa riêng tư
        self.address = self._generate_address()
    
    def _generate_address(self) -> str:
        """
        Tạo địa chỉ từ khóa riêng tư.
        
        Returns:
            Địa chỉ ví
        """
        # Tạo hash SHA-256 từ khóa riêng tư
        hash_object = hashlib.sha256(self.private_key.encode())
        hash_hex = hash_object.hexdigest()
        
        # Tạo địa chỉ bằng cách lấy 40 ký tự đầu tiên của hash
        # và thêm tiền tố "TU" để dễ nhận biết
        return "TU" + hash_hex[:40]
    
    def to_dict(self) -> Dict[str, str]:
        """
        Chuyển đổi ví thành dictionary để serialize.
        
        Returns:
            Dictionary chứa thông tin ví
        """
        return {
            "private_key": self.private_key,
            "address": self.address
        }
    
    @classmethod
    def from_dict(cls, wallet_dict: Dict[str, str]) -> 'Wallet':
        """
        Tạo ví từ dictionary.
        
        Args:
            wallet_dict: Dictionary chứa thông tin ví
            
        Returns:
            Đối tượng Wallet
        """
        return cls(private_key=wallet_dict["private_key"])
    
    def save_to_file(self, filename: str) -> bool:
        """
        Lưu ví vào file.
        
        Args:
            filename: Đường dẫn đến file
            
        Returns:
            True nếu lưu thành công, False nếu không
        """
        try:
            with open(filename, 'w') as file:
                json.dump(self.to_dict(), file)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu ví: {e}")
            return False
    
    @classmethod
    def load_from_file(cls, filename: str) -> Optional['Wallet']:
        """
        Tải ví từ file.
        
        Args:
            filename: Đường dẫn đến file
            
        Returns:
            Đối tượng Wallet hoặc None nếu có lỗi
        """
        try:
            if not os.path.exists(filename):
                return None
                
            with open(filename, 'r') as file:
                wallet_dict = json.load(file)
            
            return cls.from_dict(wallet_dict)
        except Exception as e:
            print(f"Lỗi khi tải ví: {e}")
            return None


class WalletManager:
    """Quản lý nhiều ví TuCoin."""
    
    def __init__(self, wallet_dir: str = "wallets"):
        """
        Khởi tạo quản lý ví.
        
        Args:
            wallet_dir: Thư mục chứa các file ví
        """
        self.wallet_dir = wallet_dir
        self.current_wallet = None
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(wallet_dir, exist_ok=True)
    
    def create_wallet(self) -> Wallet:
        """
        Tạo ví mới.
        
        Returns:
            Đối tượng Wallet mới
        """
        wallet = Wallet()
        self.current_wallet = wallet
        return wallet
    
    def load_wallet(self, address: str) -> Optional[Wallet]:
        """
        Tải ví từ địa chỉ.
        
        Args:
            address: Địa chỉ ví cần tải
            
        Returns:
            Đối tượng Wallet hoặc None nếu không tìm thấy
        """
        filename = os.path.join(self.wallet_dir, f"{address}.json")
        wallet = Wallet.load_from_file(filename)
        
        if wallet:
            self.current_wallet = wallet
        
        return wallet
    
    def save_wallet(self, wallet: Wallet) -> bool:
        """
        Lưu ví.
        
        Args:
            wallet: Đối tượng Wallet cần lưu
            
        Returns:
            True nếu lưu thành công, False nếu không
        """
        filename = os.path.join(self.wallet_dir, f"{wallet.address}.json")
        return wallet.save_to_file(filename)
    
    def list_wallets(self) -> list:
        """
        Liệt kê tất cả các ví đã lưu.
        
        Returns:
            Danh sách các địa chỉ ví
        """
        wallets = []
        
        for filename in os.listdir(self.wallet_dir):
            if filename.endswith(".json"):
                address = filename[:-5]  # Bỏ phần .json
                wallets.append(address)
        
        return wallets
    
    def get_current_wallet(self) -> Optional[Wallet]:
        """
        Lấy ví hiện tại.
        
        Returns:
            Đối tượng Wallet hiện tại hoặc None nếu chưa có
        """
        return self.current_wallet


if __name__ == "__main__":
    # Kiểm tra nhanh
    wallet_manager = WalletManager()
    
    # Tạo ví mới
    wallet = wallet_manager.create_wallet()
    print(f"Đã tạo ví mới với địa chỉ: {wallet.address}")
    
    # Lưu ví
    wallet_manager.save_wallet(wallet)
    print(f"Đã lưu ví")
    
    # Liệt kê các ví
    wallets = wallet_manager.list_wallets()
    print(f"Danh sách ví: {wallets}")
    
    # Tải ví
    loaded_wallet = wallet_manager.load_wallet(wallet.address)
    if loaded_wallet:
        print(f"Đã tải ví: {loaded_wallet.address}")
    else:
        print("Không thể tải ví")