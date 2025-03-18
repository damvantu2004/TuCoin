import hashlib
import json
import os
import logging
import time
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime

# Thiết lập logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Block:
    """Đại diện cho một khối trong blockchain TuCoin."""
    
    def __init__(self, index: int, timestamp: float, transactions: List[Dict], 
                 proof: int, previous_hash: str):
        """
        Khởi tạo một khối mới.
        
        Args:
            index: Số thứ tự của khối
            timestamp: Thời gian tạo khối (Unix timestamp)
            transactions: Danh sách các giao dịch trong khối
            proof: Giá trị nonce (trong PoW)
            previous_hash: Hash của khối trước đó
        """
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.proof = proof
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Tính toán hash SHA-256 của khối."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "proof": self.proof,
            "previous_hash": self.previous_hash
        }, sort_keys=True).encode()
        
        return hashlib.sha256(block_string).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi block thành dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [tx.copy() for tx in self.transactions],
            "proof": self.proof,
            "previous_hash": self.previous_hash,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'Block':
        """Tạo block từ dictionary."""
        # Tạo bản sao của transactions để tránh tham chiếu
        transactions = block_dict["transactions"].copy() if block_dict.get("transactions") else []
        
        block = cls(
            index=block_dict["index"],
            timestamp=block_dict["timestamp"],
            transactions=transactions,
            proof=block_dict["proof"],
            previous_hash=block_dict["previous_hash"]
        )
        # Gán hash trực tiếp nếu có
        if "hash" in block_dict:
            block.hash = block_dict["hash"]
        return block


class Blockchain:
    """Quản lý blockchain TuCoin."""
    
    def __init__(self, difficulty: int = 5):  # Đặt số lượng số 0 ở đây
        """
        Khởi tạo blockchain mới.
        
        Args:
            difficulty: Số lượng số 0 đầu tiên trong hash (độ khó cố định)
        """
        self.chain: List[Block] = []    # Danh sách các khối
        self.pending_transactions: List[Dict] = []  # Danh sách các giao dịch đang chờ
        self.difficulty = difficulty  # Độ khó cố định
        self.data_file = "blockchain_data.json"  # Tên file lưu blockchain
        # Thêm flag để kiểm soát quá trình đào
        self._stop_mining = False      # Flag để dừng đào
        self.chain_lock = threading.Lock()
        self.mining_lock = threading.Lock()
        
        # Tải blockchain từ file nếu có
        if os.path.exists(self.data_file):
            try:
                self.load_from_file()
            except Exception as e:
                logger.error(f"Lỗi khi tải blockchain: {e}")
                self.create_genesis_block()
        else:
            self.create_genesis_block()

    def save_to_file(self) -> None:
        """Lưu blockchain vào file."""
        data = self.to_dict()
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Lỗi khi lưu blockchain: {e}")

    def load_from_file(self) -> None:
        """Tải blockchain từ file."""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Reset chain hiện tại
            self.chain = []
            self.pending_transactions = []
            
            # Tải các block
            for block_data in data["chain"]:
                block = Block(
                    index=block_data["index"],
                    timestamp=block_data["timestamp"],
                    transactions=block_data["transactions"],
                    proof=block_data["proof"],
                    previous_hash=block_data["previous_hash"]
                )
                block.hash = block_data["hash"]
                self.chain.append(block)
            
            # Tải các giao dịch đang chờ
            self.pending_transactions = data.get("pending_transactions", [])
            self.difficulty = data.get("difficulty", 5)  # Sử dụng độ khó từ file
            
        except Exception as e:
            logger.error(f"Lỗi khi tải blockchain: {e}")
            self.create_genesis_block()

    def create_genesis_block(self) -> None:
        """Tạo khối đầu tiên trong blockchain."""
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            proof=0,
            previous_hash="0"
        )
        self.chain.append(genesis_block)
    
    @property
    def last_block(self) -> Block:
        """Trả về khối cuối cùng trong blockchain."""
        return self.chain[-1]
    
    def add_transaction(self, sender: str, receiver: str, amount: float) -> bool:
        """
        Thêm giao dịch mới vào danh sách giao dịch đang chờ.
        
        Args:
            sender: Địa chỉ người gửi
            receiver: Địa chỉ người nhận
            amount: Số lượng TuCoin
            
        Returns:
            True nếu giao dịch hợp lệ và được thêm vào
        """
        # Kiểm tra số dư của người gửi (trừ khi là hệ thống)
        if sender != "0" and self.get_balance(sender) < amount:
            logger.warning(f"Số dư không đủ: {sender} chỉ có {self.get_balance(sender)} TuCoin")
            return False
        
        # Tạo giao dịch mới
        transaction = {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "timestamp": time.time()
        }
        
        # Thêm vào danh sách giao dịch đang chờ
        self.pending_transactions.append(transaction)
        
        # Lưu blockchain sau khi thêm giao dịch
        self.save_to_file()
        
        return True

    def proof_of_work(self, previous_hash: str, block_data: Dict) -> Optional[int]:
        """
        Thuật toán Proof of Work với khả năng dừng.
        Returns None nếu quá trình bị dừng.
        """
        proof = 0
        start_time = time.time()
        
        logger.info(f"Bắt đầu đào khối với độ khó {self.difficulty}...")
        
        while not self._stop_mining:
            block_with_proof = block_data.copy()
            block_with_proof["proof"] = proof
            block_with_proof["previous_hash"] = previous_hash
            
            block_string = json.dumps(block_with_proof, sort_keys=True).encode()
            hash_result = hashlib.sha256(block_string).hexdigest()
            
            if hash_result[:self.difficulty] == '0' * self.difficulty:
                elapsed = time.time() - start_time
                logger.info(f"Đã tìm thấy nonce hợp lệ: {proof} sau {elapsed:.2f} giây")
                return proof
            
            proof += 1
            
            # Log và nhường CPU định kỳ
            if proof % 100000 == 0:
                elapsed = time.time() - start_time
                logger.info(f"Đã thử {proof:,} nonce trong {elapsed:.2f} giây")
                time.sleep(0.001)
        
        logger.info("Đã dừng quá trình đào")
        return None

    def valid_proof(self, previous_hash: str, block_data: Dict, proof: int) -> bool:
        """
        Kiểm tra xem proof có hợp lệ không.
        
        Args:
            previous_hash: Hash của khối trước đó
            block_data: Dữ liệu của khối
            proof: Proof cần kiểm tra
            
        Returns:
            True nếu hash bắt đầu bằng số lượng số 0 bằng độ khó
        """
        # Tạo dữ liệu khối với proof
        block_with_proof = block_data.copy()
        block_with_proof["proof"] = proof
        block_with_proof["previous_hash"] = previous_hash
        
        # Tính hash của khối
        block_string = json.dumps(block_with_proof, sort_keys=True).encode()
        hash_result = hashlib.sha256(block_string).hexdigest()
        
        return hash_result[:self.difficulty] == '0' * self.difficulty
    
    def mine_block(self, miner_address: str) -> Optional[Block]:
        """
        Đào một khối mới với khả năng dừng.
        Returns None nếu quá trình bị dừng.
        """
        with self.mining_lock:
            self._stop_mining = False
            
            # Thêm giao dịch phần thưởng
            transactions = self.pending_transactions.copy()
            transactions.append({
                "sender": "0",  # "0" đại diện cho hệ thống
                "receiver": miner_address,
                "amount": 100.0,  # Phần thưởng 100 TuCoin
                "timestamp": time.time()
            })
            
            # Chuẩn bị dữ liệu khối
            block_data = {
                "index": len(self.chain),
                "timestamp": time.time(),
                "transactions": transactions
            }
            
            # Lấy hash của khối trước đó
            previous_hash = self.last_block.hash
            
            # Bắt đầu đào
            start_time = time.time()
            proof = self.proof_of_work(previous_hash, block_data)
            
            if proof is None:
                return None
            
            mining_time = time.time() - start_time
            
            # Tạo khối mới
            new_block = Block(
                index=block_data["index"],
                timestamp=block_data["timestamp"],
                transactions=block_data["transactions"],
                proof=proof,
                previous_hash=previous_hash
            )
            
            # Xóa các giao dịch đã được thêm vào khối
            self.pending_transactions = []
            
            # Thêm khối mới vào chuỗi
            with self.chain_lock:
                self.chain.append(new_block)
            
            # Ghi log thời gian đào
            self.adjust_difficulty(mining_time)
            
            # Lưu blockchain sau khi đào khối thành công
            self.save_to_file()
            
            return new_block

    def stop_mining(self):
        """Dừng quá trình đào hiện tại."""
        self._stop_mining = True

    def adjust_difficulty(self, mining_time: float) -> None:
        """
        Ghi log thời gian đào khối mà không điều chỉnh độ khó.
        
        Args:
            mining_time: Thời gian đã dùng để đào khối vừa rồi (giây)
        """
        logger.info(f"Thời gian đào khối: {mining_time:.2f} giây")

    def is_chain_valid(self) -> bool:
        """
        Kiểm tra tính hợp lệ của toàn bộ blockchain.
        
        Returns:
            True nếu blockchain hợp lệ
        """
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Kiểm tra hash của khối hiện tại
            if current_block.hash != current_block.calculate_hash():
                logger.error(f"Hash không khớp ở khối {i}")
                return False
            
            # Kiểm tra liên kết giữa các khối
            if current_block.previous_hash != previous_block.hash:
                logger.error(f"Liên kết hash không khớp ở khối {i}")
                return False
            
            # Kiểm tra proof of work
            block_data = {
                "index": current_block.index,
                "timestamp": current_block.timestamp,
                "transactions": current_block.transactions
            }
            
            if not self.valid_proof(current_block.previous_hash, block_data, current_block.proof):
                logger.error(f"Proof of work không hợp lệ ở khối {i}")
                return False
        
        return True
    
    def get_balance(self, address: str) -> float:
        """
        Tính số dư của một địa chỉ.
        
        Args:
            address: Địa chỉ cần kiểm tra số dư
            
        Returns:
            Số dư TuCoin của địa chỉ
        """
        balance = 0.0
        
        # Duyệt qua tất cả các khối
        for block in self.chain:
            # Duyệt qua tất cả các giao dịch trong khối
            for transaction in block.transactions:
                if transaction["sender"] == address:
                    balance -= transaction["amount"]
                if transaction["receiver"] == address:
                    balance += transaction["amount"]
        
        # Kiểm tra cả các giao dịch đang chờ
        for transaction in self.pending_transactions:
            if transaction["sender"] == address:
                balance -= transaction["amount"]
            if transaction["receiver"] == address:
                balance += transaction["amount"]
        
        return balance
    
    def to_dict(self) -> Dict[str, Any]:
        """Chuyển đổi blockchain thành dictionary để serialize."""
        return {
            "chain": [block.to_dict() for block in self.chain],
            "pending_transactions": [tx.copy() for tx in self.pending_transactions],
            "difficulty": self.difficulty
        }
    
    @classmethod
    def from_dict(cls, blockchain_dict: Dict[str, Any]) -> 'Blockchain':
        """Tạo blockchain từ dictionary."""
        blockchain = cls(difficulty=blockchain_dict.get("difficulty", 4))
        
        # Xóa khối genesis mặc định
        blockchain.chain = []
        
        # Thêm các khối từ dictionary
        for block_dict in blockchain_dict.get("chain", []):
            try:
                block = Block.from_dict(block_dict)
                blockchain.chain.append(block)
            except Exception as e:
                logger.error(f"Lỗi khi tạo block từ dict: {e}")
                raise
        
        # Thêm các giao dịch đang chờ
        blockchain.pending_transactions = [
            tx.copy() for tx in blockchain_dict.get("pending_transactions", [])
        ]
        
        return blockchain
    
    def replace_chain(self, new_chain: List[Block]) -> bool:
        """
        Thay thế blockchain hiện tại bằng một chuỗi mới dài hơn.
        
        Args:
            new_chain: Chuỗi mới để thay thế
            
        Returns:
            True nếu chuỗi được thay thế, False nếu không
        """
        # Tạo một blockchain tạm thời để kiểm tra tính hợp lệ
        temp_blockchain = Blockchain(self.difficulty)
        temp_blockchain.chain = new_chain
        
        # Kiểm tra xem chuỗi mới có dài hơn và hợp lệ không
        if len(new_chain) > len(self.chain) and temp_blockchain.is_chain_valid():
            self.chain = new_chain
            return True
        
        return False

    def add_block(self, block: Block) -> bool:
        """Thêm block với xử lý đồng thời."""
        with self.chain_lock:
            # Xác thực block
            if not self._validate_block(block):
                return False
            
            # Kiểm tra index
            if block.index != len(self.chain):
                # Xử lý fork nếu cần
                if block.index < len(self.chain):
                    self._handle_potential_fork(block)
                return False
            
            # Thêm block vào chain
            self.chain.append(block)
            self.save_to_file()
            return True
        
    def _validate_block(self, block: Block) -> bool:
        """Xác thực toàn diện một block."""
        # Kiểm tra cấu trúc
        if not self._validate_block_structure(block):
            return False
            
        # Kiểm tra proof of work
        if not self._validate_proof_of_work(block):
            return False
            
        # Kiểm tra các giao dịch trong block
        if not self._validate_block_transactions(block):
            return False
            
        return True
        
    def _handle_potential_fork(self, block: Block) -> None:
        """Xử lý khi phát hiện fork."""
        # Tạo nhánh mới
        new_fork = self.chain[:-1] + [block]
        
        # So sánh độ khó tích lũy
        if self._calculate_total_difficulty(new_fork) > self._calculate_total_difficulty(self.chain):
            # Chuyển sang nhánh mới
            self.chain = new_fork
            # Cập nhật giao dịch pool
            self._update_transaction_pool()


