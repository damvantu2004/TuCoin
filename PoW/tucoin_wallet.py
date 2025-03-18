import hashlib
import json
import os
import base64
import secrets
from typing import Dict, Tuple, Optional, List
from datetime import datetime

class Wallet:
    """Quản lý ví TuCoin với khóa và địa chỉ."""
    
    def __init__(self, name: str, private_key: str = None):
        self.name = name
        self.private_key = private_key or secrets.token_hex(32)
        self.address = self._generate_address()
    
    def _generate_address(self) -> str:
        """Tạo địa chỉ ví từ private key."""
        # Sử dụng SHA-256 để tạo địa chỉ từ private key
        return hashlib.sha256(self.private_key.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, str]:
        """Chuyển đổi ví thành dictionary để serialize."""
        return {
            "name": self.name,
            "private_key": self.private_key,
            "address": self.address,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, wallet_dict: Dict[str, str]) -> 'Wallet':
        """Tạo ví từ dictionary."""
        wallet = cls(private_key=wallet_dict["private_key"], name=wallet_dict["name"])
        wallet.created_at = wallet_dict.get("created_at", datetime.now().isoformat())
        return wallet


class WalletManager:
    """Quản lý nhiều ví TuCoin."""
    
    def __init__(self):
        self.wallets_dir = "wallets"
        os.makedirs(self.wallets_dir, exist_ok=True)
        self.current_wallet = None

    def set_current_wallet(self, wallet: Wallet) -> None:
        """Set ví hiện tại."""
        self.current_wallet = wallet

    def get_current_wallet(self) -> Optional[Wallet]:
        """Lấy ví đang được chọn."""
        return self.current_wallet

    def create_wallet(self, name: str) -> Wallet:
        """Tạo ví mới với tên được chỉ định."""
        wallet = Wallet(name)
        return wallet
    
    def save_wallet(self, wallet: Wallet) -> None:
        """Lưu ví vào file."""
        wallet_data = {
            "name": wallet.name,
            "private_key": wallet.private_key,
            "address": wallet.address
        }
        
        filename = os.path.join(self.wallets_dir, f"{wallet.address}.json")
        with open(filename, "w") as f:
            json.dump(wallet_data, f, indent=4)
    
    def load_wallet(self, address: str) -> Optional[Wallet]:
        """Tải ví từ file theo địa chỉ."""
        try:
            filename = os.path.join(self.wallets_dir, f"{address}.json")
            with open(filename, "r") as f:
                data = json.load(f)
                wallet = Wallet(data["name"], data["private_key"])
                return wallet
        except:
            return None
    
    def list_wallets(self) -> List[Wallet]:
        """Lấy danh sách tất cả các ví."""
        wallets = []
        for filename in os.listdir(self.wallets_dir):
            if filename.endswith(".json"):
                address = filename[:-5]  # Remove .json
                wallet = self.load_wallet(address)
                if wallet:
                    wallets.append(wallet)
        return wallets

    def delete_wallet(self, address: str) -> None:
        """Xóa ví theo địa chỉ."""
        wallet_path = os.path.join(self.wallets_dir, f"{address}.json")
        if os.path.exists(wallet_path):
            os.remove(wallet_path)
        else:
            raise FileNotFoundError(f"Không tìm thấy ví: {address}")

    def check_wallet_exists(self, address: str) -> bool:
        """
        Kiểm tra xem địa chỉ ví có tồn tại trong hệ thống local không.
        
        Args:
            address: Địa chỉ ví cần kiểm tra
            
        Returns:
            bool: True nếu ví tồn tại, False nếu không
        """
        try:
            # Kiểm tra trong danh sách ví đã lưu
            # Implement theo cách lưu trữ ví của bạn
            return address in self.wallets
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra ví: {e}")
            return False


if __name__ == "__main__":
    # Kiểm tra nhanh
    wallet_manager = WalletManager()
    
    # Tạo ví mới
    wallet1 = wallet_manager.create_wallet("Ví Chính")
    print(f"Đã tạo ví mới: {wallet1.name} - {wallet1.address}")
    
    wallet2 = wallet_manager.create_wallet("Ví Phụ")
    print(f"Đã tạo ví mới: {wallet2.name} - {wallet2.address}")
    
    # Liệt kê các ví
    wallets = wallet_manager.list_wallets()
    print("\nDanh sách ví:")
    for wallet in wallets:
        print(f"- {wallet['name']}: {wallet['address']}")
    
    # Sao lưu ví
    if wallet_manager.backup_wallets("backups"):
        print("\nĐã sao lưu ví thành công")
    
    # Xóa ví
    if wallet_manager.delete_wallet(wallet2.address):
        print(f"\nĐã xóa ví: {wallet2.address}")

