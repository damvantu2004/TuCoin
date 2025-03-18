import socket
import threading
import json
import time
from typing import List, Dict, Any, Set, Optional, Tuple
import logging

from tucoin_blockchain import Blockchain, Block

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TuCoin-Node')

class Node:
    """Quản lý kết nối P2P và đồng bộ hóa blockchain giữa các node."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000, 
                 blockchain: Optional[Blockchain] = None):
        """
        Khởi tạo một node mới.
        
        Args:
            host: Địa chỉ IP của node
            port: Cổng lắng nghe
            blockchain: Blockchain hiện có (nếu không có, tạo mới)
        """
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"
        self.blockchain = blockchain if blockchain else Blockchain()
        
        # Danh sách các node đã biết trong mạng
        self.peers: Set[str] = set()
        
        # Socket để lắng nghe kết nối
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Cờ để kiểm soát luồng
        self.running = False
        
        # Callback để cập nhật UI
        self.update_callback = None
    
    def start(self) -> None:
        """Khởi động node và bắt đầu lắng nghe kết nối."""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"Node đang lắng nghe tại {self.host}:{self.port}")
            
            # Bắt đầu thread lắng nghe kết nối
            threading.Thread(target=self._listen_for_connections, daemon=True).start()
            
            return True
        except Exception as e:
            logger.error(f"Không thể khởi động node: {e}")
            return False
    
    def stop(self) -> None:
        """Dừng node và lưu dữ liệu."""
        self.running = False
        # Lưu blockchain trước khi dừng
        self.blockchain.save_to_file()
        self.server_socket.close()
        logger.info("Node đã dừng")
    
    def connect_to_peer(self, host: str, port: int) -> bool:
        """
        Kết nối đến một node khác.
        
        Args:
            host: Địa chỉ IP của node đích
            port: Cổng của node đích
            
        Returns:
            True nếu kết nối thành công, False nếu không
        """
        peer_address = f"{host}:{port}"
        
        if peer_address == self.address:
            logger.warning("Không thể kết nối đến chính mình")
            return False
        
        if peer_address in self.peers:
            logger.info(f"Đã kết nối đến {peer_address} trước đó")
            return True
        
        try:
            # Kết nối đến peer
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((host, port))
            
            # Gửi thông điệp kết nối
            self._send_message(client_socket, {
                "type": "CONNECT",
                "data": {
                    "address": self.address
                }
            })
            
            # Nhận phản hồi
            response = self._receive_message(client_socket)
            
            if response and response.get("type") == "CONNECT_ACK":
                # Thêm peer vào danh sách
                self.peers.add(peer_address)
                
                # Lấy danh sách peers từ node đã kết nối
                if "peers" in response.get("data", {}):
                    for peer in response["data"]["peers"]:
                        if peer != self.address and peer not in self.peers:
                            host, port = peer.split(":")
                            threading.Thread(
                                target=self.connect_to_peer, 
                                args=(host, int(port)),
                                daemon=True
                            ).start()
                
                # Yêu cầu blockchain
                self._send_message(client_socket, {
                    "type": "GET_BLOCKCHAIN"
                })
                
                blockchain_response = self._receive_message(client_socket)
                
                if blockchain_response and blockchain_response.get("type") == "BLOCKCHAIN":
                    # Kiểm tra và cập nhật blockchain nếu cần
                    self._handle_blockchain_message(blockchain_response)
                
                client_socket.close()
                logger.info(f"Đã kết nối thành công đến {peer_address}")
                
                # Cập nhật UI nếu có callback
                if self.update_callback:
                    self.update_callback()
                
                return True
            
            client_socket.close()
            return False
            
        except Exception as e:
            logger.error(f"Không thể kết nối đến {peer_address}: {e}")
            return False
    
    def broadcast_transaction(self, transaction: Dict[str, Any]) -> None:
        """
        Phát sóng một giao dịch mới đến tất cả các peers.
        
        Args:
            transaction: Giao dịch cần phát sóng
        """
        message = {
            "type": "NEW_TRANSACTION",
            "data": transaction
        }
        
        self._broadcast_message(message)
    
    def broadcast_block(self, block: Block) -> None:
        """
        Phát sóng một khối mới đến tất cả các peers.
        
        Args:
            block: Khối cần phát sóng
        """
        message = {
            "type": "NEW_BLOCK",
            "data": block.to_dict()
        }
        
        self._broadcast_message(message)
    
    def mine_block(self, miner_address: str) -> Optional[Block]:
        """Đào khối mới."""
        try:
            new_block = self.blockchain.mine_block(miner_address)
            # Phát sóng khối mới
            self.broadcast_block(new_block)
            return new_block
        except Exception as e:
            logger.error(f"Lỗi khi đào khối: {e}")
            return None
    
    def add_transaction(self, sender: str, receiver: str, amount: float) -> bool:
        """Thêm và phát sóng giao dịch mới."""
        success = self.blockchain.add_transaction(sender, receiver, amount)
        if success:
            # Phát sóng giao dịch
            self.broadcast_transaction(sender, receiver, amount)
        return success
    
    def set_update_callback(self, callback) -> None:
        """
        Đặt callback để cập nhật UI khi có thay đổi.
        
        Args:
            callback: Hàm callback không có tham số
        """
        self.update_callback = callback
    
    def _listen_for_connections(self) -> None:
        """Lắng nghe các kết nối đến từ các node khác."""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                
                # Xử lý kết nối trong một thread riêng
                threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, address),
                    daemon=True
                ).start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Lỗi khi lắng nghe kết nối: {e}")
    
    def _handle_connection(self, client_socket: socket.socket, address: Tuple[str, int]) -> None:
        """
        Xử lý một kết nối đến.
        
        Args:
            client_socket: Socket của client
            address: Địa chỉ của client (host, port)
        """
        try:
            # Nhận thông điệp
            message = self._receive_message(client_socket)
            
            if not message:
                client_socket.close()
                return
            
            # Xử lý thông điệp dựa trên loại
            message_type = message.get("type")
            
            if message_type == "CONNECT":
                self._handle_connect_message(client_socket, message)
            elif message_type == "GET_BLOCKCHAIN":
                self._handle_get_blockchain_message(client_socket)
            elif message_type == "NEW_TRANSACTION":
                self._handle_new_transaction_message(message)
            elif message_type == "NEW_BLOCK":
                self._handle_new_block_message(message)
            
            client_socket.close()
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý kết nối: {e}")
            client_socket.close()
    
    def _handle_connect_message(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """
        Xử lý thông điệp kết nối.
        
        Args:
            client_socket: Socket của client
            message: Thông điệp nhận được
        """
        peer_address = message.get("data", {}).get("address")
        
        if peer_address and peer_address != self.address:
            # Thêm peer vào danh sách
            self.peers.add(peer_address)
            
            # Gửi phản hồi
            self._send_message(client_socket, {
                "type": "CONNECT_ACK",
                "data": {
                    "address": self.address,
                    "peers": list(self.peers)
                }
            })
            
            logger.info(f"Đã kết nối với peer mới: {peer_address}")
            
            # Cập nhật UI nếu có callback
            if self.update_callback:
                self.update_callback()
    
    def _handle_get_blockchain_message(self, client_socket: socket.socket) -> None:
        """
        Xử lý yêu cầu lấy blockchain.
        
        Args:
            client_socket: Socket của client
        """
        # Gửi blockchain
        self._send_message(client_socket, {
            "type": "BLOCKCHAIN",
            "data": self.blockchain.to_dict()
        })
    
    def _handle_blockchain_message(self, message: Dict[str, Any]) -> None:
        """
        Xử lý thông điệp blockchain.
        
        Args:
            message: Thông điệp nhận được
        """
        blockchain_data = message.get("data")
        
        if blockchain_data:
            # Tạo blockchain từ dữ liệu
            received_blockchain = Blockchain.from_dict(blockchain_data)
            
            # Kiểm tra và thay thế blockchain nếu cần
            if len(received_blockchain.chain) > len(self.blockchain.chain):
                if received_blockchain.is_chain_valid():
                    self.blockchain = received_blockchain
                    logger.info("Đã cập nhật blockchain từ peer")
                    
                    # Cập nhật UI nếu có callback
                    if self.update_callback:
                        self.update_callback()
    
    def _handle_new_transaction_message(self, message: Dict[str, Any]) -> None:
        """
        Xử lý thông điệp giao dịch mới.
        
        Args:
            message: Thông điệp nhận được
        """
        transaction = message.get("data")
        
        if transaction:
            # Thêm giao dịch vào pending
            self.blockchain.add_transaction(
                transaction["sender"],
                transaction["receiver"],
                transaction["amount"]
            )
            
            logger.info(f"Đã nhận giao dịch mới: {transaction['sender']} -> {transaction['receiver']}: {transaction['amount']}")
            
            # Cập nhật UI nếu có callback
            if self.update_callback:
                self.update_callback()
    
    def _handle_new_block_message(self, message: Dict[str, Any]) -> None:
        """
        Xử lý thông điệp khối mới.
        
        Args:
            message: Thông điệp nhận được
        """
        block_data = message.get("data")
        
        if block_data:
            # Tạo khối từ dữ liệu
            new_block = Block.from_dict(block_data)
            
            # Kiểm tra tính hợp lệ của khối
            if (new_block.index == len(self.blockchain.chain) and
                new_block.previous_hash == self.blockchain.last_block.hash and
                self.blockchain.valid_proof(self.blockchain.last_block.proof, new_block.proof)):
                
                # Thêm khối vào blockchain
                self.blockchain.chain.append(new_block)
                
                # Xóa các giao dịch đã được thêm vào khối
                for transaction in new_block.transactions:
                    if transaction in self.blockchain.pending_transactions:
                        self.blockchain.pending_transactions.remove(transaction)
                
                logger.info(f"Đã nhận và thêm khối mới: {new_block.hash}")
                
                # Cập nhật UI nếu có callback
                if self.update_callback:
                    self.update_callback()
    
    def _broadcast_message(self, message: Dict[str, Any]) -> None:
        """
        Phát sóng một thông điệp đến tất cả các peers.
        
        Args:
            message: Thông điệp cần phát sóng
        """
        for peer in self.peers:
            try:
                host, port = peer.split(":")
                port = int(port)
                
                # Kết nối đến peer
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((host, port))
                
                # Gửi thông điệp
                self._send_message(client_socket, message)
                
                client_socket.close()
                
            except Exception as e:
                logger.error(f"Không thể phát sóng đến {peer}: {e}")
                # Xóa peer không kết nối được
                self.peers.remove(peer)
    
    def _send_message(self, client_socket: socket.socket, message: Dict[str, Any]) -> None:
        """
        Gửi một thông điệp đến một socket.
        
        Args:
            client_socket: Socket đích
            message: Thông điệp cần gửi
        """
        try:
            # Chuyển đổi thông điệp thành JSON
            message_json = json.dumps(message).encode()
            
            # Gửi độ dài thông điệp trước (4 bytes)
            message_length = len(message_json)
            client_socket.sendall(message_length.to_bytes(4, byteorder='big'))
            
            # Gửi thông điệp
            client_socket.sendall(message_json)
            
        except Exception as e:
            logger.error(f"Lỗi khi gửi thông điệp: {e}")
    
    def _receive_message(self, client_socket: socket.socket) -> Optional[Dict[str, Any]]:
        """
        Nhận một thông điệp từ một socket.
        
        Args:
            client_socket: Socket nguồn
            
        Returns:
            Thông điệp nhận được hoặc None nếu có lỗi
        """
        try:
            # Nhận độ dài thông điệp (4 bytes)
            message_length_bytes = client_socket.recv(4)
            if not message_length_bytes:
                return None
            
            message_length = int.from_bytes(message_length_bytes, byteorder='big')
            
            # Nhận thông điệp
            message_json = b''
            bytes_received = 0
            
            while bytes_received < message_length:
                chunk = client_socket.recv(min(message_length - bytes_received, 4096))
                if not chunk:
                    return None
                
                message_json += chunk
                bytes_received += len(chunk)
            
            # Chuyển đổi JSON thành dictionary
            return json.loads(message_json.decode())
            
        except Exception as e:
            logger.error(f"Lỗi khi nhận thông điệp: {e}")
            return None


if __name__ == "__main__":
    # Kiểm tra nhanh
    node = Node(host='127.0.0.1', port=5000)
    node.start()
    
    print(f"Node đang chạy tại {node.address}")
    print("Nhấn Ctrl+C để dừng...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.stop()
        print("Node đã dừng")
