import tkinter as tk
from tkinter import ttk, messagebox
import socket
import threading
import time
import argparse
import logging
from datetime import datetime

from tucoin_blockchain import Blockchain
from tucoin_node import Node
from tucoin_wallet import WalletManager

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TuCoin-GUI')

class TuCoinGUI:
    """Giao diện người dùng cho ứng dụng TuCoin."""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        """Khởi tạo giao diện người dùng."""
        # Khởi tạo biến điều khiển
        self.running = True
        self.auto_mining = False
        self.auto_mining_thread = None

        # Khởi tạo blockchain trước
        self.blockchain = Blockchain()
        
        # Khởi tạo các thành phần khác
        self.wallet_manager = WalletManager()
        self.node = Node(host=host, port=port, blockchain=self.blockchain)
        
        # Tạo giao diện
        self.root = tk.Tk()
        self.root.title("TuCoin")
        self.root.geometry("800x600")
        
        # Tạo các tab và components
        self.create_gui()
        
        # Xử lý khi đóng cửa sổ
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_gui(self):
        """Tạo giao diện người dùng."""
        # Tạo notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        
        # Tạo các frame cho từng tab
        self.overview_frame = ttk.Frame(self.notebook)
        self.wallet_frame = ttk.Frame(self.notebook)
        self.transaction_frame = ttk.Frame(self.notebook)
        self.mining_frame = ttk.Frame(self.notebook)
        self.network_frame = ttk.Frame(self.notebook)
        self.blockchain_frame = ttk.Frame(self.notebook)
        
        # Thêm các tab vào notebook
        self.notebook.add(self.overview_frame, text="Tổng quan")
        self.notebook.add(self.wallet_frame, text="Ví")
        self.notebook.add(self.transaction_frame, text="Giao dịch")
        self.notebook.add(self.mining_frame, text="Đào coin")
        self.notebook.add(self.network_frame, text="Mạng")
        self.notebook.add(self.blockchain_frame, text="Blockchain")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tạo nội dung cho các tab
        self.create_overview_tab()
        self.create_wallet_tab()
        self.create_transaction_tab()
        self.create_mining_tab()
        self.create_network_tab()
        self.create_blockchain_tab()
    
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

        # Frame tạo ví mới
        create_frame = ttk.LabelFrame(main_frame, text="Tạo ví mới", padding=10)
        create_frame.pack(fill=tk.X, pady=5)

        # Input tên ví
        ttk.Label(create_frame, text="Tên ví:").pack(side=tk.LEFT, padx=5)
        self.wallet_name_entry = ttk.Entry(create_frame)
        self.wallet_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Nút tạo ví
        ttk.Button(create_frame, text="Tạo ví", command=self.create_new_wallet).pack(side=tk.LEFT, padx=5)

        # Frame danh sách ví
        list_frame = ttk.LabelFrame(main_frame, text="Danh sách ví", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tạo Listbox và Scrollbar cho danh sách ví
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.wallets_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set)
        self.wallets_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.wallets_listbox.yview)

        # Frame cho các nút thao tác
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=5)

        # Nút chọn ví
        ttk.Button(button_frame, text="Chọn làm ví hiện tại", 
                   command=self.select_current_wallet).pack(side=tk.LEFT, padx=5)

        # Nút xóa ví
        ttk.Button(button_frame, text="Xóa ví", 
                   command=self.delete_wallet).pack(side=tk.LEFT, padx=5)

        # Cập nhật danh sách ví
        self.update_wallets_list()

    def select_current_wallet(self):
        """Chọn ví làm ví hiện tại."""
        selection = self.wallets_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một ví từ danh sách")
            return

        selected_address = self.wallets_listbox.get(selection[0])
        wallet = self.wallet_manager.load_wallet(selected_address)
        
        if wallet:
            self.wallet_manager.current_wallet = wallet
            messagebox.showinfo("Thành công", f"Đã chọn ví: {wallet.address}")
            # Cập nhật toàn bộ UI với ví hiện tại
            self.update_ui()
        else:
            messagebox.showerror("Lỗi", "Không thể tải ví đã chọn")

    def delete_wallet(self):
        """Xóa ví đã chọn."""
        selection = self.wallets_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một ví để xóa")
            return

        selected_address = self.wallets_listbox.get(selection[0])
        
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa ví này?"):
            try:
                self.wallet_manager.delete_wallet(selected_address)
                
                # Nếu xóa ví hiện tại, set current_wallet về None
                if (self.wallet_manager.current_wallet and 
                    self.wallet_manager.current_wallet.address == selected_address):
                    self.wallet_manager.current_wallet = None
                
                self.update_wallets_list()
                self.update_ui()
                messagebox.showinfo("Thành công", "Đã xóa ví")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa ví: {str(e)}")

    def update_wallets_list(self):
        """Cập nhật danh sách ví trong listbox."""
        self.wallets_listbox.delete(0, tk.END)
        wallets = self.wallet_manager.list_wallets()
        
        for wallet in wallets:
            self.wallets_listbox.insert(tk.END, wallet.address)
            # Highlight ví hiện tại nếu có
            if (self.wallet_manager.current_wallet and 
                wallet.address == self.wallet_manager.current_wallet.address):
                self.wallets_listbox.itemconfig(tk.END, {'bg': '#e6e6e6'})

    def load_or_create_wallet(self):
        """Tải danh sách ví."""
        self.update_wallets_list()

    def create_new_wallet(self):
        """Tạo ví mới từ tên được nhập."""
        wallet_name = self.wallet_name_entry.get().strip()
        
        if not wallet_name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập tên ví")
            return

        try:
            # Tạo ví mới với tên đã nhập
            wallet = self.wallet_manager.create_wallet(wallet_name)
            
            # Lưu ví
            self.wallet_manager.save_wallet(wallet)
            
            # Xóa nội dung input
            self.wallet_name_entry.delete(0, tk.END)
            
            # Cập nhật danh sách ví
            self.update_wallets_list()
            
            messagebox.showinfo("Thành công", f"Đã tạo ví mới:\nTên: {wallet_name}\nĐịa chỉ: {wallet.address}")
        
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tạo ví: {str(e)}")

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

    def create_network_tab(self):
        """Tạo tab Mạng."""
        # Frame chính
        main_frame = ttk.Frame(self.network_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame thông tin node
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin node", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        # Địa chỉ node
        address_frame = ttk.Frame(info_frame)
        address_frame.pack(fill=tk.X, pady=5)
        ttk.Label(address_frame, text="Địa chỉ node:").pack(side=tk.LEFT, padx=5)
        ttk.Label(address_frame, text=self.node.address).pack(side=tk.LEFT)

        # Frame kết nối
        connect_frame = ttk.LabelFrame(main_frame, text="Kết nối với node khác", padding=10)
        connect_frame.pack(fill=tk.X, pady=5)

        # IP và port để kết nối
        ip_frame = ttk.Frame(connect_frame)
        ip_frame.pack(fill=tk.X, pady=5)
        ttk.Label(ip_frame, text="Địa chỉ IP:").pack(side=tk.LEFT, padx=5)
        self.connect_ip_entry = ttk.Entry(ip_frame)
        self.connect_ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.connect_ip_entry.insert(0, "127.0.0.1")

        port_frame = ttk.Frame(connect_frame)
        port_frame.pack(fill=tk.X, pady=5)
        ttk.Label(port_frame, text="Cổng:").pack(side=tk.LEFT, padx=5)
        self.connect_port_entry = ttk.Entry(port_frame)
        self.connect_port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.connect_port_entry.insert(0, "5000")

        # Nút kết nối
        ttk.Button(
            connect_frame, 
            text="Kết nối", 
            command=self.connect_to_peer
        ).pack(pady=10)

        # Frame danh sách peers
        peers_frame = ttk.LabelFrame(main_frame, text="Danh sách các node đã kết nối", padding=10)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Listbox hiển thị danh sách peers
        self.peers_listbox = tk.Listbox(peers_frame)
        self.peers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar cho listbox
        scrollbar = ttk.Scrollbar(peers_frame, orient=tk.VERTICAL, command=self.peers_listbox.yview)
        self.peers_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def connect_to_peer(self):
        """Kết nối đến một node khác."""
        try:
            host = self.connect_ip_entry.get()
            port = int(self.connect_port_entry.get())
            
            if self.node.connect_to_peer(host, port):
                messagebox.showinfo("Thành công", f"Đã kết nối đến {host}:{port}")
                self.update_ui()
            else:
                messagebox.showerror("Lỗi", f"Không thể kết nối đến {host}:{port}")
        
        except ValueError:
            messagebox.showerror("Lỗi", "Cổng không hợp lệ")
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def update_peers_list(self):
        """Cập nhật danh sách peers trong UI."""
        # Xóa danh sách cũ
        self.peers_listbox.delete(0, tk.END)
        # Thêm các peers mới
        for peer in self.node.peers:
            self.peers_listbox.insert(tk.END, peer)
        # Cập nhật label số lượng peers
        self.overview_peers_label.config(text=str(len(self.node.peers)))

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

    def create_transaction_tab(self):
        """Tạo tab Giao dịch."""
        # Frame chính
        main_frame = ttk.Frame(self.transaction_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame gửi giao dịch
        send_frame = ttk.LabelFrame(main_frame, text="Gửi TuCoin", padding=10)
        send_frame.pack(fill=tk.X, pady=5)

        # Địa chỉ người gửi (ví hiện tại)
        from_frame = ttk.Frame(send_frame)
        from_frame.pack(fill=tk.X, pady=5)
        ttk.Label(from_frame, text="Từ:").pack(side=tk.LEFT, padx=5)
        self.transaction_from_label = ttk.Label(from_frame, text="Chưa chọn ví")
        self.transaction_from_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Địa chỉ người nhận
        to_frame = ttk.Frame(send_frame)
        to_frame.pack(fill=tk.X, pady=5)
        ttk.Label(to_frame, text="Đến:").pack(side=tk.LEFT, padx=5)
        self.transaction_to_entry = ttk.Entry(to_frame)
        self.transaction_to_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Số lượng TuCoin
        amount_frame = ttk.Frame(send_frame)
        amount_frame.pack(fill=tk.X, pady=5)
        ttk.Label(amount_frame, text="Số lượng:").pack(side=tk.LEFT, padx=5)
        self.transaction_amount_entry = ttk.Entry(amount_frame)
        self.transaction_amount_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(amount_frame, text="TuCoin").pack(side=tk.LEFT, padx=5)

        # Nút gửi
        ttk.Button(send_frame, text="Gửi", command=self.send_transaction).pack(pady=10)

        # Frame giao dịch đang chờ
        pending_frame = ttk.LabelFrame(main_frame, text="Giao dịch đang chờ", padding=10)
        pending_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Treeview cho giao dịch đang chờ
        self.pending_transactions_tree = ttk.Treeview(
            pending_frame,
            columns=("from", "to", "amount", "time"),
            show="headings"
        )

        # Định nghĩa các cột
        self.pending_transactions_tree.heading("from", text="Từ")
        self.pending_transactions_tree.heading("to", text="Đến")
        self.pending_transactions_tree.heading("amount", text="Số lượng")
        self.pending_transactions_tree.heading("time", text="Thời gian")

        # Điều chỉnh độ rộng cột
        self.pending_transactions_tree.column("from", width=150)
        self.pending_transactions_tree.column("to", width=150)
        self.pending_transactions_tree.column("amount", width=100)
        self.pending_transactions_tree.column("time", width=150)

        # Thêm scrollbar
        scrollbar = ttk.Scrollbar(pending_frame, orient=tk.VERTICAL, command=self.pending_transactions_tree.yview)
        self.pending_transactions_tree.configure(yscrollcommand=scrollbar.set)

        # Pack các widget
        self.pending_transactions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def send_transaction(self):
        """Gửi giao dịch mới."""
        wallet = self.wallet_manager.get_current_wallet()
        if not wallet:
            messagebox.showerror("Lỗi", "Vui lòng chọn ví trước")
            return
        
        receiver = self.transaction_to_entry.get()
        amount_str = self.transaction_amount_entry.get()
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Số lượng phải lớn hơn 0")
            
            # Kiểm tra số dư
            balance = self.blockchain.get_balance(wallet.address)
            if amount > balance:
                messagebox.showerror("Lỗi", f"Số dư không đủ (hiện có {balance} TuCoin)")
                return
            
            # Tạo và gửi giao dịch
            success = self.node.add_transaction(wallet.address, receiver, amount)
            
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
        text_widget.insert(tk.END, f"Thời gian: {datetime.fromtimestamp(block.timestamp)}\n")
        text_widget.insert(tk.END, f"Hash: {block.hash}\n")
        text_widget.insert(tk.END, f"Hash khối trước: {block.previous_hash}\n")
        text_widget.insert(tk.END, f"Proof: {block.proof}\n\n")
        
        text_widget.insert(tk.END, "Giao dịch:\n\n")
        for tx in block.transactions:
            text_widget.insert(tk.END, f"Từ: {tx['sender']}\n")
            text_widget.insert(tk.END, f"Đến: {tx['receiver']}\n")
            text_widget.insert(tk.END, f"Số lượng: {tx['amount']} TuCoin\n")
            text_widget.insert(tk.END, f"Thời gian: {datetime.fromtimestamp(tx['timestamp'])}\n")
            text_widget.insert(tk.END, "\n")
        
        text_widget.config(state=tk.DISABLED)

    def create_blockchain_tab(self):
        """Tạo tab Blockchain."""
        # Frame chính
        main_frame = ttk.Frame(self.blockchain_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame thông tin
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin blockchain", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        # Thông tin blockchain
        ttk.Label(info_frame, text="Số khối:").pack(side=tk.LEFT, padx=5)
        self.blockchain_blocks_label = ttk.Label(info_frame, text="")
        self.blockchain_blocks_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Frame danh sách khối
        list_frame = ttk.LabelFrame(main_frame, text="Danh sách khối", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Tạo Treeview và Scrollbar cho danh sách khối
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.blocks_tree = ttk.Treeview(list_container, yscrollcommand=scrollbar.set)
        self.blocks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.blocks_tree.yview)

        # Cập nhật danh sách khối
        self.update_blocks_list()

    def update_blocks_list(self):
        """Cập nhật danh sách các khối trong blockchain."""
        # Xóa tất cả các mục hiện có
        self.blocks_tree.delete(*self.blocks_tree.get_children())
        
        # Cấu hình các cột
        self.blocks_tree["columns"] = ("index", "timestamp", "transactions", "hash")
        self.blocks_tree["show"] = "headings"
        
        # Định dạng các cột
        self.blocks_tree.heading("index", text="STT")
        self.blocks_tree.heading("timestamp", text="Thời gian")
        self.blocks_tree.heading("transactions", text="Số giao dịch")
        self.blocks_tree.heading("hash", text="Hash")
        
        # Điều chỉnh độ rộng cột
        self.blocks_tree.column("index", width=50)
        self.blocks_tree.column("timestamp", width=150)
        self.blocks_tree.column("transactions", width=100)
        self.blocks_tree.column("hash", width=300)
        
        # Thêm các khối vào tree
        for block in self.blockchain.chain:
            self.blocks_tree.insert("", tk.END, values=(
                block.index,
                datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                len(block.transactions),
                block.hash[:50] + "..." if len(block.hash) > 50 else block.hash
            ))
        
        # Cập nhật label số lượng khối
        self.blockchain_blocks_label.config(text=str(len(self.blockchain.chain)))
        
        # Bind double-click event để xem chi tiết khối
        self.blocks_tree.bind("<Double-1>", self.show_block_details)

    def create_mining_tab(self):
        """Tạo tab Đào coin."""
        # Frame chính
        main_frame = ttk.Frame(self.mining_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Frame thông tin
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin đào coin", padding=10)
        info_frame.pack(fill=tk.X, pady=5)

        # Địa chỉ ví nhận thưởng
        address_frame = ttk.Frame(info_frame)
        address_frame.pack(fill=tk.X, pady=5)
        ttk.Label(address_frame, text="Địa chỉ ví:").pack(side=tk.LEFT, padx=5)
        self.mining_address_label = ttk.Label(address_frame, text="Chưa chọn ví")
        self.mining_address_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        # Nút đào một khối
        self.mine_button = ttk.Button(
            control_frame, 
            text="Đào một khối", 
            command=self.mine_block
        )
        self.mine_button.pack(side=tk.LEFT, padx=5)

        # Nút bắt đầu/dừng đào tự động
        self.start_mining_button = ttk.Button(
            control_frame, 
            text="Bắt đầu đào tự động", 
            command=self.toggle_auto_mining
        )
        self.start_mining_button.pack(side=tk.LEFT, padx=5)

    def toggle_auto_mining(self):
        """Bắt đầu/dừng đào tự động."""
        wallet = self.wallet_manager.get_current_wallet()
        if not wallet:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ví trước")
            return

        if not self.auto_mining:
            # Bắt đầu đào tự động
            self.auto_mining = True
            self.start_mining_button["text"] = "Dừng đào tự động"
            self.mine_button["state"] = "disabled"
            
            def auto_mining_thread():
                while self.auto_mining and self.running:
                    try:
                        success = self.node.mine_block(wallet.address)
                        if success:
                            # Cập nhật UI trong main thread
                            self.root.after(0, self.update_ui)
                        time.sleep(1)  # Đợi 1 giây trước khi đào khối tiếp
                    except Exception as e:
                        logger.error(f"Lỗi khi đào tự động: {e}")
                        time.sleep(5)  # Đợi lâu hơn nếu có lỗi
            
            self.auto_mining_thread = threading.Thread(
                target=auto_mining_thread, 
                daemon=True
            )
            self.auto_mining_thread.start()
        else:
            # Dừng đào tự động
            self.auto_mining = False
            self.start_mining_button["text"] = "Bắt đầu đào tự động"
            self.mine_button["state"] = "normal"
            if self.auto_mining_thread:
                self.auto_mining_thread.join()

    def update_ui(self):
        """Cập nhật toàn bộ giao diện."""
        wallet = self.wallet_manager.get_current_wallet()
        
        # Cập nhật tab Overview
        if wallet:
            self.overview_address_label["text"] = wallet.address
            balance = self.blockchain.get_balance(wallet.address)
            self.overview_balance_label["text"] = f"{balance} TuCoin"
        else:
            self.overview_address_label["text"] = "Chưa có ví"
            self.overview_balance_label["text"] = "0 TuCoin"

        # Cập nhật tab Mining
        if wallet:
            self.mining_address_label["text"] = wallet.address
            self.mine_button["state"] = "normal"
            self.start_mining_button["state"] = "normal"
        else:
            self.mining_address_label["text"] = "Chưa chọn ví"
            self.mine_button["state"] = "disabled"
            self.start_mining_button["state"] = "disabled"

        # Cập nhật tab Transaction
        if wallet:
            self.transaction_from_label["text"] = wallet.address
            self.transaction_to_entry["state"] = "normal"
            self.transaction_amount_entry["state"] = "normal"
            self.send_button["state"] = "normal"
        else:
            self.transaction_from_label["text"] = "Chưa chọn ví"
            self.transaction_to_entry["state"] = "disabled"
            self.transaction_amount_entry["state"] = "disabled"
            self.send_button["state"] = "disabled"

        # Cập nhật danh sách ví
        self.update_wallets_list()
        
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
                datetime.fromtimestamp(block.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                len(block.transactions),
                block.hash[:50] + "..." if len(block.hash) > 50 else block.hash
            ))
        
        # Cập nhật danh sách giao dịch đang chờ
        self.pending_transactions_tree.delete(*self.pending_transactions_tree.get_children())
        for tx in self.blockchain.pending_transactions:
            self.pending_transactions_tree.insert("", tk.END, values=(
                tx["sender"],
                tx["receiver"],
                f"{tx['amount']} TuCoin",
                datetime.fromtimestamp(tx["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            ))

    def periodic_update(self):
        """Cập nhật UI định kỳ."""
        while self.running:
            self.update_ui()
            time.sleep(5)

    def on_close(self):
        """Xử lý khi đóng chương trình."""
        try:
            # Dừng đào tự động nếu đang chạy
            self.auto_mining = False
            
            # Kiểm tra và join thread nếu tồn tại
            if hasattr(self, 'auto_mining_thread') and self.auto_mining_thread is not None:
                self.auto_mining_thread.join(timeout=1.0)  # Thêm timeout để tránh treo
            
            # Lưu blockchain
            self.blockchain.save_to_file()
            
            # Dừng node
            self.node.stop()
            
            # Đóng cửa sổ
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Lỗi khi đóng chương trình: {e}")
            self.root.destroy()

def get_local_ip():
    """Lấy địa chỉ IP local của máy."""
    try:
        # Tạo socket và kết nối đến một địa chỉ public (Google DNS)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

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



