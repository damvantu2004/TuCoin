import hashlib
import json
import os
import logging
from time import time
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
    
    def __init__(self, difficulty: int = 4):
        """Khởi tạo blockchain mới."""
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty = difficulty
        self.data_file = "blockchain_data.json"
        
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
            self.difficulty = data.get("difficulty", 4)
            
        except Exception as e:
            logger.error(f"Lỗi khi tải blockchain: {e}")
            self.create_genesis_block()

    def create_genesis_block(self) -> None:
        """Tạo khối đầu tiên trong blockchain."""
        genesis_block = Block(
            index=0,
            timestamp=time(),
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
        """Thêm giao dịch mới."""
        success = super().add_transaction(sender, receiver, amount)
        if success:
            # Lưu blockchain sau khi thêm giao dịch
            self.save_to_file()
        return success

    def proof_of_work(self, last_proof: int) -> int:
        """
        Thuật toán Proof of Work.
        Tìm một số (nonce) sao cho hash của nó với proof trước đó
        có số lượng số 0 đầu tiên bằng độ khó.
        
        Args:
            last_proof: Proof của khối trước đó
            
        Returns:
            Giá trị nonce thỏa mãn điều kiện
        """
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        
        return proof
    
    def valid_proof(self, last_proof: int, proof: int) -> bool:
        """
        Kiểm tra xem proof có hợp lệ không.
        
        Args:
            last_proof: Proof của khối trước đó
            proof: Proof hiện tại cần kiểm tra
            
        Returns:
            True nếu hash bắt đầu bằng số lượng số 0 bằng độ khó
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        
        return guess_hash[:self.difficulty] == '0' * self.difficulty
    
    def mine_block(self, miner_address: str) -> Block:
        """Đào một khối mới."""
        # Thêm giao dịch phần thưởng
        self.pending_transactions.append({
            "sender": "0",  # "0" đại diện cho hệ thống
            "receiver": miner_address,
            "amount": 100.0,  # Phần thưởng 100 TuCoin
            "timestamp": time()
        })
        
        # Lấy proof của khối trước đó
        last_proof = self.last_block.proof
        
        # Tìm proof mới
        proof = self.proof_of_work(last_proof)
        
        # Tạo khối mới
        new_block = Block(
            index=len(self.chain),
            timestamp=time(),
            transactions=self.pending_transactions.copy(),
            proof=proof,
            previous_hash=self.last_block.hash
        )
        
        # Xóa các giao dịch đã được thêm vào khối
        self.pending_transactions = []
        
        # Thêm khối mới vào chuỗi
        self.chain.append(new_block)
        
        # Lưu blockchain sau khi đào khối thành công
        self.save_to_file()
        
        return new_block
    
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
                return False
            
            # Kiểm tra liên kết giữa các khối
            if current_block.previous_hash != previous_block.hash:
                return False
            
            # Kiểm tra proof of work
            if not self.valid_proof(previous_block.proof, current_block.proof):
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


if __name__ == "__main__":
    # Kiểm tra nhanh
    blockchain = Blockchain()
    
    # Thêm một số giao dịch
    blockchain.add_transaction("address1", "address2", 10)
    blockchain.add_transaction("address2", "address3", 5)
    
    # Đào khối
    miner_address = "miner_address"
    new_block = blockchain.mine_block(miner_address)
    
    print(f"Đã đào khối mới: {new_block.hash}")
    print(f"Số dư của người đào: {blockchain.get_balance(miner_address)}")



