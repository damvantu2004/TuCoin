import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import argparse
import os
import json
from typing import Optional, List, Dict, Any
import socket

from tucoin_blockchain import Blockchain, Block
from tucoin_node import Node
from tucoin_wallet import Wallet, WalletManager

def get_local_ip():
    """Lấy địa chỉ IP local của máy."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

class TuCoinGUI:
    """Giao diện người dùng cho ứng dụng TuCoin."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        """
        Khởi tạo giao diện người dùng.
        
        Args:
            host: Địa chỉ IP của node
            port: Cổng lắng nghe
        """
        self.host = host
        self.port = port
        
        # Khởi tạo wallet manager
        self.wallet_manager = WalletManager()
        
        # Khởi tạo blockchain và node
        self.blockchain = Blockchain()
        self.node = Node(host=host, port=port, blockchain=self.blockchain)
        
        # Đặt callback cập nhật UI
        self.node.set_update_callback(self.update_ui)
        
        # Khởi tạo cửa sổ chính
        self.root = tk.Tk()
        self.root.title(f"TuCoin - Node {host}:{port}")
        self.root.geometry("1000x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Tạo giao diện
        self.create_gui()
        
        # Khởi động node
        if not self.node.start():
            messagebox.showerror("Lỗi", f"Không thể khởi động node tại {host}:{port}")
            self.root.destroy()
            return
        
        # Tải hoặc tạo ví
        self.load_or_create_wallet()
        
        # Cập nhật UI lần đầu
        self.update_ui()
        
        # Bắt đầu thread cập nhật UI định kỳ
        self.running = True
        threading.Thread(target=self.periodic_update, daemon=True).start()
    
    def create_gui(self):
        """Tạo các thành phần giao diện."""
        # Tạo notebook (tab control)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab Tổng quan
        self.overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.overview_frame, text="Tổng quan")
        self.create_overview_tab()
        
        # Tab Ví
        self.wallet_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.wallet_frame, text="Ví")
        self.create_wallet_tab()
        
        # Tab Đào coin
        self.mining_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.mining_frame, text="Đào coin")
        self.create_mining_tab()
        
        # Tab Giao dịch
        self.transaction_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.transaction_frame, text="Giao dịch")
        self.create_transaction_tab()
        
        # Tab Mạng
        self.network_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.network_frame, text="Mạng")
        self.create_network_tab()
        
        # Tab Blockchain
        self.blockchain_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.blockchain_frame, text="Blockchain")
        self.create_blockchain_tab()
        
        # Thanh trạng thái
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="Đang khởi động...")
        self.status_label.pack(side=tk.LEFT)
        
        self.node_info_label = ttk.Label(self.status_frame, text=f"Node: {self.host}:{self.port}")
        self.node_info_label.pack(side=tk.RIGHT)
    
    def create_overview_tab(self):
        """Tạo tab Tổng quan."""
        # Frame chính
        main_frame = ttk.Frame(self.overview_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thông tin ví
        wallet_frame = ttk.LabelFrame(main_frame, text="Thông tin ví", padding=10)
        wallet_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(wallet_frame, text="Địa chỉ:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.overview_address_label = ttk.Label(wallet_frame, text="Chưa có ví")
        self.overview_address_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(wallet_frame, text="Số dư:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.overview_balance_label = ttk.Label(wallet_frame, text="0 TuCoin")
        self.overview_balance_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Thông tin blockchain
        blockchain_frame = ttk.LabelFrame(main_frame, text="Thông tin blockchain", padding=10)
        blockchain_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(blockchain_frame, text="Số khối:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.overview_blocks_label = ttk.Label(blockchain_frame, text="0")
        self.overview_blocks_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(blockchain_frame, text="Giao dịch đang chờ:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.overview_pending_label = ttk.Label(blockchain_frame, text="0")
        self.overview_pending_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Thông tin mạng
        network_frame = ttk.LabelFrame(main_frame, text="Thông tin mạng", padding=10)
        network_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(network_frame, text="Số node đã kết nối:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.overview_peers_label = ttk.Label(network_frame, text="0")
        self.overview_peers_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Các nút thao tác nhanh
        actions_frame = ttk.LabelFrame(main_frame, text="Thao tác nhanh", padding=10)
        actions_frame.pack(fill=tk.X, pady=5)
        
        self.mine_button = ttk.Button(actions_frame, text="Đào khối mới", command=self.mine_block)
        self.mine_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.send_button = ttk.Button(actions_frame, text="Gửi TuCoin", command=self.show_send_dialog)
        self.send_button.grid(row=0, column=1, padx=5, pady=5)
        
        self.connect_button = ttk.Button(actions_frame, text="Kết nối node", command=self.show_connect_dialog)
        self.connect_button.grid(row=0, column=2, padx=5, pady=5)
    
    def create_wallet_tab(self):
        """Tạo tab Ví."""
        # Frame chính
        main_frame = ttk.Frame(self.wallet_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thông tin ví hiện tại
        current_wallet_frame = ttk.LabelFrame(main_frame, text="Ví hiện tại", padding=10)
        current_wallet_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(current_wallet_frame, text="Địa chỉ:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.wallet_address_label = ttk.Label(current_wallet_frame, text="Chưa có ví")
        self.wallet_address_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(current_wallet_frame, text="Khóa riêng tư:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.wallet_private_key_label = ttk.Label(current_wallet_frame, text="***")
        self.wallet_private_key_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(current_wallet_frame, text="Số dư:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.wallet_balance_label = ttk.Label(current_wallet_frame, text="0 TuCoin")
        self.wallet_balance_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Các nút thao tác ví
        wallet_actions_frame = ttk.Frame(current_wallet_frame)
        wallet_actions_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.create_wallet_button = ttk.Button(wallet_actions_frame, text="Tạo ví mới", command=self.create_new_wallet)
        self.create_wallet_button.grid(row=0, column=0, padx=5)
        
        self.show_private_key_button = ttk.Button(wallet_actions_frame, text="Hiện khóa riêng tư", command=self.toggle_show_private_key)
        self.show_private_key_button.grid(row=0, column=1, padx=5)
        
        self.copy_address_button = ttk.Button(wallet_actions_frame, text="Sao chép địa chỉ", command=self.copy_address_to_clipboard)
        self.copy_address_button.grid(row=0, column=2, padx=5)
        
        # Danh sách ví đã lưu
        saved_wallets_frame = ttk.LabelFrame(main_frame, text="Ví đã lưu", padding=10)
        saved_wallets_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo listbox và scrollbar
        wallets_frame = ttk.Frame(saved_wallets_frame)
        wallets_frame.pack(fill=tk.BOTH, expand=True)
        
        self.wallets_listbox = tk.Listbox(wallets_frame)
        self.wallets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        wallets_scrollbar = ttk.Scrollbar(wallets_frame, orient=tk.VERTICAL, command=self.wallets_listbox.yview)
        wallets_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.wallets_listbox.config(yscrollcommand=wallets_scrollbar.set)
        
        # Nút tải ví
        self.load_wallet_button = ttk.Button(saved_wallets_frame, text="Tải ví đã chọn", command=self.load_selected_wallet)
        self.load_wallet_button.pack(pady=5)
    
    def create_mining_tab(self):
        """Tạo tab Đào coin."""
        # Frame chính
        main_frame = ttk.Frame(self.mining_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thông tin đào
        mining_info_frame = ttk.LabelFrame(main_frame, text="Thông tin đào", padding=10)
        mining_info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mining_info_frame, text="Độ khó hiện tại:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.mining_difficulty_label = ttk.Label(mining_info_frame, text=f"{self.blockchain.difficulty} (số 0 đầu tiên)")
        self.mining_difficulty_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(mining_info_frame, text="Phần thưởng:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.mining_reward_label = ttk.Label(mining_info_frame, text="100 TuCoin")
        self.mining_reward_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(mining_info_frame, text="Địa chỉ nhận thưởng:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.mining_address_label = ttk.Label(mining_info_frame, text="Chưa có ví")
        self.mining_address_label.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Nút đào
        mining_actions_frame = ttk.Frame(main_frame)
        mining_actions_frame.pack(fill=tk.X, pady=10)
        
        self.start_mining_button = ttk.Button(mining_actions_frame, text="Đào khối mới", command=self.mine_block)
        self.start_mining_button.pack()
        
        # Lịch sử đào
        mining_history_frame = ttk.LabelFrame(main_frame, text="Lịch sử đào", padding=10)
        mining_history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo treeview và scrollbar
        mining_history_tree_frame = ttk.Frame(mining_history_frame)
        mining_history_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.mining_history_tree = ttk.Treeview(mining_history_tree_frame, columns=("block", "time", "transactions", "reward"))
        self.mining_history_tree.heading("#0", text="")
        self.mining_history_tree.heading("block", text="Khối")
        self.mining_history_tree.heading("time", text="Thời gian")
        self.mining_history_tree.heading("transactions", text="Số giao dịch")
        self.mining_history_tree.heading("reward", text="Phần thưởng")
        
        self.mining_history_tree.column("#0", width=0, stretch=tk.NO)
        self.mining_history_tree.column("block", width=50)
        self.mining_history_tree.column("time", width=150)
        self.mining_history_tree.column("transactions", width=100)
        self.mining_history_tree.column("reward", width=100)
        
        self.mining_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        mining_history_scrollbar = ttk.Scrollbar(mining_history_tree_frame, orient=tk.VERTICAL, command=self.mining_history_tree.yview)
        mining_history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.mining_history_tree.config(yscrollcommand=mining_history_scrollbar.set)
    
    def create_transaction_tab(self):
        """Tạo tab Giao dịch."""
        # Frame chính
        main_frame = ttk.Frame(self.transaction_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tạo giao dịch mới
        new_transaction_frame = ttk.LabelFrame(main_frame, text="Tạo giao dịch mới", padding=10)
        new_transaction_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(new_transaction_frame, text="Từ:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.transaction_from_label = ttk.Label(new_transaction_frame, text="Chưa có ví")
        self.transaction_from_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(new_transaction_frame, text="Đến:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.transaction_to_entry = ttk.Entry(new_transaction_frame, width=50)
        self.transaction_to_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(new_transaction_frame, text="Số lượng:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.transaction_amount_entry = ttk.Entry(new_transaction_frame, width=20)
        self.transaction_amount_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        self.send_transaction_button = ttk.Button(new_transaction_frame, text="Gửi", command=self.send_transaction)
        self.send_transaction_button.grid(row=3, column=1, sticky=tk.W, pady=10)
        
        # Giao dịch đang chờ
        pending_transactions_frame = ttk.LabelFrame(main_frame, text="Giao dịch đang chờ", padding=10)
        pending_transactions_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo treeview và scrollbar
        pending_tree_frame = ttk.Frame(pending_transactions_frame)
        pending_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.pending_transactions_tree = ttk.Treeview(pending_tree_frame, columns=("from", "to", "amount", "time"))
        self.pending_transactions_tree.heading("#0", text="")
        self.pending_transactions_tree.heading("from", text="Từ")
        self.pending_transactions_tree.heading("to", text="Đến")
        self.pending_transactions_tree.heading("amount", text="Số lượng")
        self.pending_transactions_tree.heading("time", text="Thời gian")
        
        self.pending_transactions_tree.column("#0", width=0, stretch=tk.NO)
        self.pending_transactions_tree.column("from", width=150)
        self.pending_transactions_tree.column("to", width=150)
        self.pending_transactions_tree.column("amount", width=100)
        self.pending_transactions_tree.column("time", width=150)
        
        self.pending_transactions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        pending_scrollbar = ttk.Scrollbar(pending_tree_frame, orient=tk.VERTICAL, command=self.pending_transactions_tree.yview)
        pending_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pending_transactions_tree.config(yscrollcommand=pending_scrollbar.set)
    
    def create_network_tab(self):
        """Tạo tab Mạng."""
        # Frame chính
        main_frame = ttk.Frame(self.network_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thông tin node
        node_info_frame = ttk.LabelFrame(main_frame, text="Thông tin node", padding=10)
        node_info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(node_info_frame, text="Địa chỉ IP:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.node_ip_label = ttk.Label(node_info_frame, text=self.host)
        self.node_ip_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(node_info_frame, text="Cổng:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.node_port_label = ttk.Label(node_info_frame, text=str(self.port))
        self.node_port_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Kết nối đến node khác
        connect_frame = ttk.LabelFrame(main_frame, text="Kết nối đến node khác", padding=10)
        connect_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(connect_frame, text="Địa chỉ IP:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.connect_ip_entry = ttk.Entry(connect_frame, width=20)
        self.connect_ip_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.connect_ip_entry.insert(0, "127.0.0.1")
        
        ttk.Label(connect_frame, text="Cổng:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.connect_port_entry = ttk.Entry(connect_frame, width=10)
        self.connect_port_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        self.connect_button = ttk.Button(connect_frame, text="Kết nối", command=self.connect_to_node)
        self.connect_button.grid(row=2, column=1, sticky=tk.W, pady=10)
        
        # Danh sách node đã kết nối
        peers_frame = ttk.LabelFrame(main_frame, text="Node đã kết nối", padding=10)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo listbox và scrollbar
        peers_list_frame = ttk.Frame(peers_frame)
        peers_list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.peers_listbox = tk.Listbox(peers_list_frame)
        self.peers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        peers_scrollbar = ttk.Scrollbar(peers_list_frame, orient=tk.VERTICAL, command=self.peers_listbox.yview)
        peers_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.peers_listbox.config(yscrollcommand=peers_scrollbar.set)
    
    def create_blockchain_tab(self):
        """Tạo tab Blockchain."""
        # Frame chính
        main_frame = ttk.Frame(self.blockchain_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thông tin blockchain
        blockchain_info_frame = ttk.LabelFrame(main_frame, text="Thông tin blockchain", padding=10)
        blockchain_info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(blockchain_info_frame, text="Số khối:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.blockchain_blocks_label = ttk.Label(blockchain_info_frame, text="0")
        self.blockchain_blocks_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(blockchain_info_frame, text="Độ khó:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.blockchain_difficulty_label = ttk.Label(blockchain_info_frame, text=f"{self.blockchain.difficulty} (số 0 đầu tiên)")
        self.blockchain_difficulty_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Danh sách các khối
        blocks_frame = ttk.LabelFrame(main_frame, text="Danh sách khối", padding=10)
        blocks_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Tạo treeview và scrollbar
        blocks_tree_frame = ttk.Frame(blocks_frame)
        blocks_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.blocks_tree = ttk.Treeview(blocks_tree_frame, columns=("index", "time", "transactions", "hash"))
        self.blocks_tree.heading("#0", text="")
        self.blocks_tree.heading("index", text="STT")
        self.blocks_tree.heading("time", text="Thời gian")
        self.blocks_tree.heading("transactions", text="Số giao dịch")
        self.blocks_tree.heading("hash", text="Hash")
        
        self.blocks_tree.column("#0", width=0, stretch=tk.NO)
        self.blocks_tree.column("index", width=50)
        self.blocks_tree.column("time", width=150)
        self.blocks_tree.column("transactions", width=100)
        self.blocks_tree.column("hash", width=300)
        
        self.blocks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        blocks_scrollbar = ttk.Scrollbar(blocks_tree_frame, orient=tk.VERTICAL, command=self.blocks_tree.yview)
        blocks_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.blocks_tree.config(yscrollcommand=blocks_scrollbar.set)
        
        # Xem chi tiết khối
        self.blocks_tree.bind("<Double-1>", self.show_block_details)
    
    def load_or_create_wallet(self):
        """Tải ví hiện có hoặc tạo ví mới."""
        # Lấy danh sách ví đã lưu
        wallets = self.wallet_manager.list_wallets()
        
        if wallets:
            # Tải ví đầu tiên
            self.wallet_manager.load_wallet(wallets[0])
        else:
            # Tạo ví mới
            wallet = self.wallet_manager.create_wallet()
            self.wallet_manager.save_wallet(wallet)
        
        # Cập nhật danh sách ví
        self.update_wallets_list()
    
    def update_wallets_list(self):
        """Cập nhật danh sách ví trong UI."""
        # Xóa danh sách hiện tại
        self.wallets_listbox.delete(0, tk.END)
        
        # Lấy danh sách ví
        wallets = self.wallet_manager.list_wallets()
        
        # Thêm vào listbox
        for wallet in wallets:
            self.wallets_listbox.insert(tk.END, wallet)
    
    def create_new_wallet(self):
        """Tạo ví mới."""
        # Tạo ví mới
        wallet = self.wallet_manager.create_wallet()
        
        # Lưu ví
        self.wallet_manager.save_wallet(wallet)
        
        # Cập nhật UI
        self.update_wallets_list()
        self.update_ui()
        
        messagebox.showinfo("Thành công", f"Đã tạo ví mới với địa chỉ: {wallet.address}")
    
    def load_selected_wallet(self):
        """Tải ví đã chọn."""
        # Lấy địa chỉ ví đã chọn
        selection = self.wallets_listbox.curselection()
        
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một ví")
            return
        
        address = self.wallets_listbox.get(selection[0])
        
        # Tải ví
        wallet = self.wallet_manager.load_wallet(address)
        
        if wallet:
            # Cập nhật UI
            self.update_ui()
            messagebox.showinfo("Thành công", f"Đã tải ví: {wallet.address}")
        else:
            messagebox.showerror("Lỗi", f"Không thể tải ví: {address}")
    
    def toggle_show_private_key(self):
        """Hiện/ẩn khóa riêng tư."""
        wallet = self.wallet_manager.get_current_wallet()
        
        if not wallet:
            return
            
        if self.wallet_private_key_label["text"] == "***":
            self.wallet_private_key_label["text"] = wallet.private_key
            self.show_private_key_button["text"] = "Ẩn khóa riêng tư"
        else:
            self.wallet_private_key_label["text"] = "***"
            self.show_private_key_button["text"] = "Hiện khóa riêng tư"

    def copy_address_to_clipboard(self):
        """Sao chép địa chỉ ví vào clipboard."""
        wallet = self.wallet_manager.get_current_wallet()
        if wallet:
            self.root.clipboard_clear()
            self.root.clipboard_append(wallet.address)
            messagebox.showinfo("Thành công", "Đã sao chép địa chỉ ví vào clipboard")

    def connect_to_node(self):
        """Kết nối đến node khác."""
        host = self.connect_ip_entry.get()
        port = self.connect_port_entry.get()
        
        try:
            port = int(port)
            if self.node.connect_to_peer(f"{host}:{port}"):
                messagebox.showinfo("Thành công", f"Đã kết nối đến node {host}:{port}")
                self.update_ui()
            else:
                messagebox.showerror("Lỗi", f"Không thể kết nối đến node {host}:{port}")
        except ValueError:
            messagebox.showerror("Lỗi", "Cổng không hợp lệ")

    def mine_block(self):
        """Đào khối mới."""
        wallet = self.wallet_manager.get_current_wallet()
        if not wallet:
            messagebox.showwarning("Cảnh báo", "Vui lòng tạo hoặc tải ví trước")
            return
            
        # Vô hiệu hóa nút đào
        self.start_mining_button["state"] = "disabled"
        self.mine_button["state"] = "disabled"
        
        def mining_thread():
            # Đào khối mới
            new_block = self.node.mine_block(wallet.address)
            
            # Kích hoạt lại nút đào
            self.start_mining_button["state"] = "normal"
            self.mine_button["state"] = "normal"
            
            if new_block:
                messagebox.showinfo("Thành công", f"Đã đào được khối mới #{new_block.index}")
                self.update_ui()
            else:
                messagebox.showerror("Lỗi", "Không thể đào khối mới")
        
        # Chạy đào trong thread riêng
        threading.Thread(target=mining_thread, daemon=True).start()

    def show_send_dialog(self):
        """Hiển thị hộp thoại gửi TuCoin."""
        wallet = self.wallet_manager.get_current_wallet()
        if not wallet:
            messagebox.showwarning("Cảnh báo", "Vui lòng tạo hoặc tải ví trước")
            return
        
        # Chuyển đến tab giao dịch
        self.notebook.select(self.transaction_frame)
        
        # Focus vào ô nhập địa chỉ người nhận
        self.transaction_to_entry.focus()

    def show_connect_dialog(self):
        """Hiển thị hộp thoại kết nối node."""
        # Chuyển đến tab mạng
        self.notebook.select(self.network_frame)
        
        # Focus vào ô nhập địa chỉ IP
        self.connect_ip_entry.focus()

    def send_transaction(self):
        """Gửi giao dịch mới."""
        if not self.wallet:
            messagebox.showerror("Lỗi", "Vui lòng tạo hoặc tải ví trước")
            return
        
        receiver = self.transaction_to_entry.get()
        amount_str = self.transaction_amount_entry.get()
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Số lượng phải lớn hơn 0")
            
            # Kiểm tra số dư
            balance = self.blockchain.get_balance(self.wallet.address)
            if amount > balance:
                messagebox.showerror("Lỗi", f"Số dư không đủ (hiện có {balance} TuCoin)")
                return
            
            # Tạo và gửi giao dịch
            success = self.node.add_transaction(self.wallet.address, receiver, amount)
            
            if success:
                # Xóa form
                self.transaction_to_entry.delete(0, tk.END)
                self.transaction_amount_entry.delete(0, tk.END)
                
                messagebox.showinfo("Thành công", f"Đã gửi {amount} TuCoin đến {receiver}")
                self.update_ui()
            else:
                messagebox.showerror("Lỗi", "Không thể gửi giao dịch")
        
        except ValueError as e:
            messagebox.showerror("Lỗi", str(e))

    def show_block_details(self, event):
        """Hiển thị chi tiết của khối được chọn."""
        selection = self.blocks_tree.selection()
        if not selection:
            return
            
        item = self.blocks_tree.item(selection[0])
        block_index = int(item["values"][0])
        
        block = self.blockchain.get_block(block_index)
        if not block:
            return
            
        # Tạo cửa sổ chi tiết
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Chi tiết khối #{block_index}")
        details_window.geometry("600x400")
        
        # Tạo text widget để hiển thị thông tin
        text_widget = tk.Text(details_window, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Thêm thông tin khối
        text_widget.insert(tk.END, f"Khối #{block.index}\n\n")
        text_widget.insert(tk.END, f"Thời gian: {block.timestamp}\n")
        text_widget.insert(tk.END, f"Hash: {block.hash}\n")
        text_widget.insert(tk.END, f"Hash khối trước: {block.previous_hash}\n")
        text_widget.insert(tk.END, f"Proof: {block.proof}\n\n")
        
        text_widget.insert(tk.END, "Giao dịch:\n\n")
        for tx in block.transactions:
            text_widget.insert(tk.END, f"Từ: {tx['sender']}\n")
            text_widget.insert(tk.END, f"Đến: {tx['receiver']}\n")
            text_widget.insert(tk.END, f"Số lượng: {tx['amount']} TuCoin\n")
            text_widget.insert(tk.END, f"Thời gian: {tx['timestamp']}\n")
            text_widget.insert(tk.END, "\n")
        
        text_widget.config(state=tk.DISABLED)

    def update_ui(self):
        """Cập nhật giao diện người dùng."""
        wallet = self.wallet_manager.get_current_wallet()
        
        # Cập nhật thông tin ví
        if wallet:
            address = wallet.address
            balance = self.blockchain.get_balance(address)
            
            self.overview_address_label["text"] = address
            self.overview_balance_label["text"] = f"{balance} TuCoin"
            self.wallet_address_label["text"] = address
            self.wallet_balance_label["text"] = f"{balance} TuCoin"
            self.transaction_from_label["text"] = address
            self.mining_address_label["text"] = address
        
        # Cập nhật thông tin blockchain
        chain_length = len(self.blockchain.chain)
        pending_count = len(self.blockchain.pending_transactions)
        
        self.overview_blocks_label["text"] = str(chain_length)
        self.overview_pending_label["text"] = str(pending_count)
        self.blockchain_blocks_label["text"] = str(chain_length)
        
        # Cập nhật thông tin mạng
        peers_count = len(self.node.peers)
        self.overview_peers_label["text"] = str(peers_count)
        
        # Cập nhật danh sách peers
        self.peers_listbox.delete(0, tk.END)
        for peer in self.node.peers:
            self.peers_listbox.insert(tk.END, peer)
        
        # Cập nhật danh sách khối
        self.blocks_tree.delete(*self.blocks_tree.get_children())
        for block in self.blockchain.chain:
            self.blocks_tree.insert("", tk.END, values=(
                block.index,
                block.timestamp,
                len(block.transactions),
                block.hash
            ))
        
        # Cập nhật danh sách giao dịch đang chờ
        self.pending_transactions_tree.delete(*self.pending_transactions_tree.get_children())
        for tx in self.blockchain.pending_transactions:
            self.pending_transactions_tree.insert("", tk.END, values=(
                tx["sender"],
                tx["receiver"],
                f"{tx['amount']} TuCoin",
                tx["timestamp"]
            ))

    def periodic_update(self):
        """Cập nhật UI định kỳ."""
        while self.running:
            self.update_ui()
            time.sleep(5)

    def on_close(self):
        """Xử lý khi đóng ứng dụng."""
        self.running = False
        self.node.stop()
        self.root.destroy()

def main():
    """Hàm main để khởi động ứng dụng."""
    parser = argparse.ArgumentParser(description="TuCoin GUI")
    parser.add_argument("--host", default=None, help="Địa chỉ IP của node (mặc định: tự động)")
    parser.add_argument("--port", type=int, default=5000, help="Cổng lắng nghe")
    
    args = parser.parse_args()
    
    # Tự động lấy IP nếu không được chỉ định
    host = args.host if args.host else get_local_ip()
    port = args.port
    
    print("="*50)
    print(f"Node address: {host}:{port}")
    print("Sử dụng địa chỉ này để kết nối từ máy khác")
    print("="*50)
    
    app = TuCoinGUI(host=host, port=port)
    app.root.mainloop()

if __name__ == "__main__":
    main()