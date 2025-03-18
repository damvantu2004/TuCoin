import socket
import threading
import json
import time
from typing import List, Dict, Any, Set, Optional, Tuple
import logging
import struct
import uuid
import requests

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
        
        # Thêm các thuộc tính mới cho LAN Discovery
        self.discovery_port = 5500  # Port dùng cho UDP broadcast
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Cờ để kiểm soát luồng
        self.running = False
        
        # Callback để cập nhật UI
        self.update_callback = None

        self.pending_transactions_pool = set()  # Pool giao dịch chưa xác nhận
        
        self.mining_lock = threading.Lock()
        self.current_mining_block = None
        self.received_blocks = {}  # {block_index: [blocks]}
    
    def start(self) -> None:
        """Khởi động node và bắt đầu lắng nghe kết nối."""
        try:
            # Khởi động TCP server như cũ
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            # Thêm khởi động UDP discovery
            self.discovery_socket.bind(('', self.discovery_port))
            
            # Thread lắng nghe TCP connections
            threading.Thread(target=self._listen_for_connections, daemon=True).start()
            
            # Thread mới cho LAN discovery
            threading.Thread(target=self._listen_for_discovery, daemon=True).start()
            threading.Thread(target=self._broadcast_presence, daemon=True).start()
            
            logger.info(f"Node đang lắng nghe tại {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Không thể khởi động node: {e}")
            return False
    
    def stop(self) -> None:
        """Dừng node và lưu dữ liệu."""
        self.running = False
        self.blockchain.save_to_file()
        self.server_socket.close()
        self.discovery_socket.close()
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

    def verify_transaction(self, transaction: Dict) -> bool:
        """Xác thực giao dịch."""
        # Kiểm tra chữ ký số
        # Kiểm tra số dư
        # Kiểm tra định dạng giao dịch
        return True

    def consensus(self) -> None:
        """Cơ chế đồng thuận."""
        # Lấy blockchain từ tất cả các node
        all_chains = self._get_chains_from_peers()
        
        # Tìm chain dài nhất và hợp lệ
        longest_chain = None
        max_length = len(self.blockchain.chain)
        
        for chain in all_chains:
            if len(chain) > max_length and self.blockchain.is_chain_valid(chain):
                longest_chain = chain
                max_length = len(chain)
        
        # Cập nhật chain nếu tìm thấy chain tốt hơn
        if longest_chain:
            self.blockchain.chain = longest_chain
            return True
            
        return False

    def handle_fork(self) -> None:
        """Xử lý khi có nhánh."""
        # Lưu trữ các nhánh
        forks = []
        
        # Chọn nhánh có tổng độ khó cao nhất
        best_fork = max(forks, key=lambda x: self._calculate_total_difficulty(x))
        
        # Chuyển sang nhánh tốt nhất
        if self._calculate_total_difficulty(best_fork) > self._calculate_total_difficulty(self.blockchain.chain):
            self.blockchain.chain = best_fork

    def _calculate_total_difficulty(self, chain: List[Block]) -> int:
        """Tính tổng độ khó của một chain."""
        return sum(block.difficulty for block in chain)

    def mine_block(self, miner_address: str) -> Optional[Block]:
        """
        Đào một khối mới.
        
        Args:
            miner_address: Địa chỉ ví của thợ đào
        
        Returns:
            Block mới nếu đào thành công, None nếu thất bại
        """
        new_block = self.blockchain.mine_block(miner_address)
        
        if new_block:
            # Phát sóng block mới đến các peers
            self._broadcast_new_block(new_block)
            
            # Xóa các giao dịch đã được đưa vào block
            self.blockchain.pending_transactions = []
            
            # Cập nhật UI nếu có callback
            if self.update_callback:
                self.update_callback()
        
        return new_block

    def handle_new_block(self, block_data: Dict) -> None:
        """Xử lý khi nhận được block mới từ node khác."""
        new_block = Block.from_dict(block_data)
        
        with self.mining_lock:
            # Nếu đang đào block cùng index, dừng lại
            if (self.current_mining_block and 
                self.current_mining_block["index"] == new_block.index):
                self.blockchain.stop_mining()
            
            # Lưu block đã nhận
            if new_block.index not in self.received_blocks:
                self.received_blocks[new_block.index] = []
            self.received_blocks[new_block.index].append(new_block)
            
            # Xác thực và thêm block
            if self.blockchain.add_block(new_block):
                # Broadcast lại cho các node khác
                self._broadcast_new_block(new_block)
                
                # Dọn dẹp received_blocks
                self._cleanup_received_blocks(new_block.index)

    def _is_better_block(self, new_block: Block, other_blocks: List[Block]) -> bool:
        """So sánh block mới với các block đã nhận."""
        # Ưu tiên theo:
        # 1. Độ khó cao hơn
        # 2. Timestamp sớm hơn
        # 3. Hash nhỏ hơn
        for block in other_blocks:
            if block.difficulty > new_block.difficulty:
                return False
            if (block.difficulty == new_block.difficulty and 
                block.timestamp < new_block.timestamp):
                return False
            if (block.difficulty == new_block.difficulty and
                block.timestamp == new_block.timestamp and
                block.hash < new_block.hash):
                return False
        return True

    def _cleanup_received_blocks(self, confirmed_index: int) -> None:
        """Xóa các block đã xác nhận khỏi received_blocks."""
        keys_to_remove = [k for k in self.received_blocks.keys() if k <= confirmed_index]
        for k in keys_to_remove:
            del self.received_blocks[k]
    
    def check_receiver_exists(self, receiver_address: str) -> bool:
        """
        Kiểm tra xem địa chỉ nhận có tồn tại trên các máy trong mạng không.
        
        Args:
            receiver_address: Địa chỉ ví cần kiểm tra
        
        Returns:
            bool: True nếu địa chỉ tồn tại trên ít nhất một máy, False nếu không
        """
        try:
            # Tạo message kiểm tra địa chỉ
            check_message = {
                "type": "CHECK_WALLET",
                "data": {
                    "address": receiver_address
                }
            }
            
            # Gửi kiểm tra đến tất cả các peers
            for peer in self.peers:
                try:
                    host, port = peer.split(":")
                    port = int(port)
                    
                    # Kết nối đến peer
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((host, port))
                    
                    # Gửi yêu cầu kiểm tra
                    self._send_message(client_socket, check_message)
                    
                    # Nhận phản hồi
                    response = self._receive_message(client_socket)
                    client_socket.close()
                    
                    if response and response.get("type") == "WALLET_CHECK_RESPONSE":
                        if response.get("data", {}).get("exists", False):
                            return True
                        
                except Exception as e:
                    logger.error(f"Không thể kiểm tra với peer {peer}: {e}")
                    continue
                
            return False
        
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra địa chỉ: {e}")
            return False
    
    def add_transaction(self, sender: str, receiver: str, amount: float) -> bool:
        try:
            # Kiểm tra các điều kiện cơ bản
            if not sender or not receiver:
                logger.error("Địa chỉ người gửi hoặc người nhận không được để trống")
                return False
            
            if amount <= 0:
                logger.error("Số lượng coin phải lớn hơn 0")
                return False
            
            # Kiểm tra số dư của người gửi
            sender_balance = self.blockchain.get_balance(sender)
            if sender_balance < amount:
                logger.error(f"Số dư không đủ. Hiện có: {sender_balance}, Cần: {amount}")
                return False
            
            # Chỉ kiểm tra tính hợp lệ của địa chỉ
            if not self._is_valid_address(receiver):
                logger.error(f"Địa chỉ nhận không hợp lệ: {receiver}")
                return False
            
            # Tạo giao dịch
            transaction = {
                "id": str(uuid.uuid4()),
                "sender": sender,
                "receiver": receiver,
                "amount": amount,
                "timestamp": time.time()
            }
            
            # Thêm vào blockchain và broadcast
            if self.blockchain.add_transaction(sender, receiver, amount):
                self.broadcast_transaction(transaction)
                logger.info(f"Giao dịch thành công: {sender} -> {receiver}: {amount}")
                return True
            
            return False

        except Exception as e:
            logger.error(f"Lỗi khi tạo giao dịch: {e}")
            return False

   
    
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
            elif message_type == "CHECK_WALLET":
                self._handle_check_wallet(message, client_socket)
            
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
        """Xử lý khi nhận giao dịch mới."""
        try:
            transaction = message.get("data")
            if not transaction:
                logger.error("Nhận được giao dịch không hợp lệ")
                return

            sender = transaction.get("sender")
            receiver = transaction.get("receiver")
            amount = transaction.get("amount")

            if not all([sender, receiver, amount]):
                logger.error("Thiếu thông tin giao dịch")
                return

            success = self.blockchain.add_transaction(sender, receiver, amount)
            if success:
                logger.info(f"Đã nhận giao dịch mới: {sender} -> {receiver}: {amount}")
                if self.update_callback:
                    self.update_callback()
            else:
                logger.error("Không thể thêm giao dịch nhận được")

        except Exception as e:
            logger.error(f"Lỗi khi xử lý giao dịch mới: {e}")
    
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

    def _handle_check_wallet(self, message: Dict[str, Any], client_socket: socket.socket) -> None:
        """
        Xử lý yêu cầu kiểm tra ví.
        
        Args:
            message: Thông điệp yêu cầu kiểm tra
            client_socket: Socket của client gửi yêu cầu
        """
        try:
            address = message.get("data", {}).get("address")
            # Kiểm tra xem địa chỉ có tồn tại trong ví local không
            exists = self.wallet_manager.check_wallet_exists(address)
            
            response = {
                "type": "WALLET_CHECK_RESPONSE",
                "data": {
                    "exists": exists
                }
            }
            
            self._send_message(client_socket, response)
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý kiểm tra ví: {e}")

    def _listen_for_discovery(self) -> None:
        """Lắng nghe các gói tin discovery từ các node khác."""
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message["type"] == "DISCOVERY":
                    # Nhận được broadcast từ node khác
                    peer_host = message["host"]
                    peer_port = message["port"]
                    
                    if f"{peer_host}:{peer_port}" != self.address:
                        # Kết nối với node mới tìm thấy
                        threading.Thread(
                            target=self.connect_to_peer,
                            args=(peer_host, peer_port),
                            daemon=True
                        ).start()
                        
                        # Gửi phản hồi trực tiếp
                        response = {
                            "type": "DISCOVERY_ACK",
                            "host": self.host,
                            "port": self.port
                        }
                        self.discovery_socket.sendto(
                            json.dumps(response).encode(),
                            (peer_host, self.discovery_port)
                        )
                
            except Exception as e:
                if self.running:
                    logger.error(f"Lỗi trong quá trình discovery: {e}")

    def _broadcast_presence(self) -> None:
        """Định kỳ broadcast sự hiện diện của node trong mạng LAN."""
        while self.running:
            try:
                message = {
                    "type": "DISCOVERY",
                    "host": self.host,
                    "port": self.port
                }
                
                # Broadcast đến tất cả các máy trong mạng
                self.discovery_socket.sendto(
                    json.dumps(message).encode(),
                    ('<broadcast>', self.discovery_port)
                )
                
                # Đợi 30 giây trước khi broadcast tiếp
                time.sleep(30)
                
            except Exception as e:
                if self.running:
                    logger.error(f"Lỗi khi broadcast presence: {e}")

    def _get_valid_transactions(self) -> List[Dict]:
        """Lấy danh sách các giao dịch hợp lệ để đưa vào block mới."""
        valid_transactions = []
        used_transactions = set()  # Để theo dõi các giao dịch đã được xử lý
        
        # Lấy tất cả giao dịch đang chờ từ blockchain
        pending_transactions = self.blockchain.pending_transactions.copy()
        
        for transaction in pending_transactions:
            # Bỏ qua nếu giao dịch đã được xử lý
            if transaction["id"] in used_transactions:
                continue
                
            # Kiểm tra tính hợp lệ của giao dịch
            if self._validate_transaction(transaction):
                valid_transactions.append(transaction)
                used_transactions.add(transaction["id"])
                
            # Giới hạn số lượng giao dịch trong một block
            if len(valid_transactions) >= self.MAX_TRANSACTIONS_PER_BLOCK:
                break
                
        return valid_transactions
        
    def _validate_transaction(self, transaction: Dict) -> bool:
        """Kiểm tra tính hợp lệ của một giao dịch."""
        try:
            # Kiểm tra các trường bắt buộc
            required_fields = ["id", "sender", "receiver", "amount", "timestamp"]
            if not all(field in transaction for field in required_fields):
                logger.error(f"Giao dịch thiếu trường bắt buộc: {transaction}")
                return False
            
            # Bỏ qua kiểm tra với giao dịch coinbase (phần thưởng đào block)
            if transaction["sender"] == "0":
                return True
                
            # Kiểm tra số dư
            sender_balance = self.blockchain.get_balance(transaction["sender"])
            if sender_balance < transaction["amount"]:
                logger.error(f"Số dư không đủ. Cần: {transaction['amount']}, Có: {sender_balance}")
                return False
                
            # Kiểm tra số lượng
            if transaction["amount"] <= 0:
                logger.error("Số lượng coin phải lớn hơn 0")
                return False
                
            # Kiểm tra địa chỉ người nhận
            if not self._is_valid_address(transaction["receiver"]):
                logger.error(f"Địa chỉ người nhận không hợp lệ: {transaction['receiver']}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi xác thực giao dịch: {e}")
            return False

    # Thêm hằng số cho số lượng giao dịch tối đa trong một block
    MAX_TRANSACTIONS_PER_BLOCK = 100

    def _broadcast_new_block(self, block: Block) -> None:
        """
        Phát sóng block mới đến tất cả các peers.
        
        Args:
            block: Block cần phát sóng
        """
        message = {
            "type": "NEW_BLOCK",
            "data": block.to_dict()
        }
        
        self._broadcast_message(message)

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







