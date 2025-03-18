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
        self.current_mining_thread = None  # Thêm biến để theo dõi thread đào hiện tại

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
        """Tạo tab Mạng với tính năng tự động phát hiện."""
        # Frame chính
        main_frame = ttk.Frame(self.network_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame trạng thái mạng
        status_frame = ttk.LabelFrame(main_frame, text="Trạng thái mạng", padding=10)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="Địa chỉ node:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.node_address_label = ttk.Label(status_frame, text=f"{self.node.host}:{self.node.port}")
        self.node_address_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(status_frame, text="Trạng thái discovery:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.discovery_status_label = ttk.Label(status_frame, text="Đang hoạt động")
        self.discovery_status_label.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Frame danh sách peers
        peers_frame = ttk.LabelFrame(main_frame, text="Danh sách node đã kết nối", padding=10)
        peers_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Container cho listbox và scrollbar
        list_container = ttk.Frame(peers_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        # Tạo Treeview thay vì Listbox để hiển thị thông tin chi tiết hơn
        self.peers_tree = ttk.Treeview(list_container, columns=("address", "status", "discovered"), show="headings")
        self.peers_tree.heading("address", text="Địa chỉ")
        self.peers_tree.heading("status", text="Trạng thái")
        self.peers_tree.heading("discovered", text="Phát hiện lúc")
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.peers_tree.yview)
        self.peers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.peers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame điều khiển kết nối thủ công
        manual_frame = ttk.LabelFrame(main_frame, text="Kết nối thủ công", padding=10)
        manual_frame.pack(fill=tk.X, pady=5)
        
        # Input địa chỉ IP
        ttk.Label(manual_frame, text="IP:").pack(side=tk.LEFT, padx=5)
        self.connect_ip_entry = ttk.Entry(manual_frame)
        self.connect_ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Input port
        ttk.Label(manual_frame, text="Port:").pack(side=tk.LEFT, padx=5)
        self.connect_port_entry = ttk.Entry(manual_frame, width=10)
        self.connect_port_entry.pack(side=tk.LEFT, padx=5)
        
        # Nút kết nối
        self.connect_button = ttk.Button(manual_frame, text="Kết nối", command=self.connect_to_peer)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        # Nút ngắt kết nối đã chọn
        self.disconnect_button = ttk.Button(manual_frame, text="Ngắt kết nối", command=self.disconnect_peer)
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

    def connect_to_peer(self):
        """Kết nối thủ công đến peer."""
        ip = self.connect_ip_entry.get().strip()
        port = self.connect_port_entry.get().strip()
        
        if not ip or not port:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ IP và Port")
            return
        
        try:
            port = int(port)
            success = self.node.connect_to_peer(ip, port)
            
            if success:
                messagebox.showinfo("Thành công", f"Đã kết nối đến {ip}:{port}")
                self.update_network_status()
            else:
                messagebox.showerror("Lỗi", f"Không thể kết nối đến {ip}:{port}")
        except ValueError:
            messagebox.showerror("Lỗi", "Port phải là số nguyên")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi kết nối: {str(e)}")

    def disconnect_peer(self):
        """Ngắt kết nối với peer đã chọn."""
        selection = self.peers_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một node để ngắt kết nối")
            return
        
        peer_address = self.peers_tree.item(selection[0])['values'][0]
        try:
            self.node.disconnect_peer(peer_address)
            self.update_network_status()
            messagebox.showinfo("Thành công", f"Đã ngắt kết nối với {peer_address}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể ngắt kết nối: {str(e)}")

    def update_network_status(self):
        """Cập nhật trạng thái mạng trong GUI."""
        # Xóa danh sách peers hiện tại
        for item in self.peers_tree.get_children():
            self.peers_tree.delete(item)
        
        # Thêm các peers mới
        for peer in self.node.peers:
            # Giả sử peer_info là dict chứa thông tin chi tiết về peer
            peer_info = self.node.get_peer_info(peer)  # Cần thêm method này vào Node class
            self.peers_tree.insert("", tk.END, values=(
                peer,
                peer_info.get("status", "Đã kết nối"),
                peer_info.get("discovered_time", "N/A")
            ))

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
            try:
                # Đào khối mới
                new_block = self.node.mine_block(wallet.address)
                
                if new_block:
                    self.root.after(0, lambda: messagebox.showinfo("Thành công", 
                        f"Đã đào được khối mới #{new_block.index}"))
                    self.root.after(0, self.update_ui)
                else:
                    logger.info("Đã dừng đào khối")
            except Exception as e:
                logger.error(f"Lỗi khi đào khối: {e}")
                self.root.after(0, lambda: messagebox.showerror("Lỗi", 
                    "Không thể đào khối mới"))
            finally:
                # Kích hoạt lại nút đào
                self.root.after(0, self._enable_mining_buttons)
                self.current_mining_thread = None
        
        # Dừng thread đào hiện tại nếu có
        self.stop_current_mining()
        
        # Bắt đầu thread đào mới
        self.current_mining_thread = threading.Thread(target=mining_thread, daemon=True)
        self.current_mining_thread.start()

    def stop_current_mining(self):
        """Dừng quá trình đào hiện tại."""
        if self.current_mining_thread and self.current_mining_thread.is_alive():
            self.node.blockchain.stop_mining()
            # Đợi thread dừng trong thời gian ngắn
            self.current_mining_thread.join(timeout=1.0)

    def _enable_mining_buttons(self):
        """Kích hoạt lại các nút đào."""
        self.start_mining_button["state"] = "normal"
        self.mine_button["state"] = "normal"

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

        # Thêm label hiển thị trạng thái
        self.transaction_status_label = ttk.Label(
            send_frame, 
            text="",
            foreground="blue"
        )
        self.transaction_status_label.pack(fill=tk.X, pady=5)

        # Frame lịch sử giao dịch
        history_frame = ttk.LabelFrame(main_frame, text="Lịch sử giao dịch", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Treeview cho lịch sử giao dịch
        self.transaction_history_tree = ttk.Treeview(
            history_frame,
            columns=("time", "type", "amount", "sender", "receiver", "status"),
            show="headings"
        )

        # Định nghĩa các cột
        self.transaction_history_tree.heading("time", text="Thời gian")
        self.transaction_history_tree.heading("type", text="Loại")
        self.transaction_history_tree.heading("amount", text="Số lượng")
        self.transaction_history_tree.heading("sender", text="Người gửi")
        self.transaction_history_tree.heading("receiver", text="Người nhận")
        self.transaction_history_tree.heading("status", text="Trạng thái")

        # Điều chỉnh độ rộng cột
        self.transaction_history_tree.column("time", width=150)
        self.transaction_history_tree.column("type", width=100)
        self.transaction_history_tree.column("amount", width=100)
        self.transaction_history_tree.column("sender", width=150)
        self.transaction_history_tree.column("receiver", width=150)
        self.transaction_history_tree.column("status", width=100)

        # Thêm scrollbar
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.transaction_history_tree.yview)
        self.transaction_history_tree.configure(yscrollcommand=scrollbar.set)

        # Pack các widget
        self.transaction_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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
        # 1. Kiểm tra ví
        wallet = self.wallet_manager.get_current_wallet()
        if not wallet:
            messagebox.showerror("Lỗi", "Vui lòng chọn ví trước khi giao dịch")
            return

        # 2. Kiểm tra input
        receiver = self.transaction_to_entry.get().strip()
        amount_str = self.transaction_amount_entry.get().strip()

        if not receiver:
            messagebox.showerror("Lỗi", "Vui lòng nhập địa chỉ ví người nhận")
            self.transaction_to_entry.focus()
            return

        if not amount_str:
            messagebox.showerror("Lỗi", "Vui lòng nhập số lượng TuCoin")
            self.transaction_amount_entry.focus()
            return

        # 3. Kiểm tra số lượng
        try:
            amount = float(amount_str)
        except ValueError:
            messagebox.showerror("Lỗi", "Số lượng TuCoin không hợp lệ")
            self.transaction_amount_entry.focus()
            return

        if amount <= 0:
            messagebox.showerror("Lỗi", "Số lượng TuCoin phải lớn hơn 0")
            self.transaction_amount_entry.focus()
            return

        # 4. Kiểm tra địa chỉ người nhận
        if receiver == wallet.address:
            messagebox.showerror("Lỗi", "Không thể gửi TuCoin cho chính mình")
            self.transaction_to_entry.focus()
            return

        # 5. Kiểm tra số dư
        balance = self.blockchain.get_balance(wallet.address)
        if amount > balance:
            messagebox.showerror(
                "Số dư không đủ", 
                f"Số dư hiện tại: {balance} TuCoin\n"
                f"Số lượng cần gửi: {amount} TuCoin\n"
                f"Còn thiếu: {amount - balance} TuCoin"
            )
            return

        # 6. Xác nhận giao dịch
        if not messagebox.askyesno(
            "Xác nhận giao dịch",
            f"Bạn có chắc chắn muốn gửi {amount} TuCoin đến:\n{receiver}?"
        ):
            return

        # 7. Thực hiện giao dịch
        try:
            # Hiển thị trạng thái "Đang xử lý"
            self.transaction_status_label["text"] = "Đang xử lý giao dịch..."
            self.root.update()

            success = self.node.add_transaction(wallet.address, receiver, amount)

            if success:
                # Xóa form
                self.transaction_to_entry.delete(0, tk.END)
                self.transaction_amount_entry.delete(0, tk.END)
                
                # Hiển thị thông báo thành công
                messagebox.showinfo(
                    "Giao dịch thành công",
                    f"Đã gửi: {amount} TuCoin\n"
                    f"Đến: {receiver}\n\n"
                    f"Số dư còn lại: {balance - amount} TuCoin"
                )
                
                # Cập nhật UI
                self.update_ui()
                self.update_transaction_history()
            else:
                messagebox.showerror(
                    "Giao dịch thất bại",
                    "Không thể thực hiện giao dịch.\n"
                    "Vui lòng thử lại sau."
                )
        except Exception as e:
            messagebox.showerror(
                "Lỗi giao dịch",
                f"Đã xảy ra lỗi khi thực hiện giao dịch:\n{str(e)}"
            )
        finally:
            # Xóa trạng thái "Đang xử lý"
            self.transaction_status_label["text"] = ""

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
        """Tạo tab đào coin."""
        # Frame chính
        main_frame = ttk.Frame(self.mining_frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame thông tin
        info_frame = ttk.LabelFrame(main_frame, text="Thông tin đào", padding=10)
        info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(info_frame, text="Địa chỉ ví:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.mining_address_label = ttk.Label(info_frame, text="Chưa chọn ví")
        self.mining_address_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # Nút bắt đầu/dừng đào tự động
        self.start_mining_button = ttk.Button(
            control_frame, 
            text="Bắt đầu đào tự động", 
            command=self.toggle_auto_mining
        )
        self.start_mining_button.pack(side=tk.LEFT, padx=5)

    def toggle_auto_mining(self):
        """Bật/tắt chế độ đào tự động."""
        wallet = self.wallet_manager.get_current_wallet()
        if not wallet:
            messagebox.showwarning("Cảnh báo", "Vui lòng tạo hoặc tải ví trước")
            return

        if not self.auto_mining:
            # Bắt đầu đào tự động
            self.auto_mining = True
            self.start_mining_button["text"] = "Dừng đào tự động"
            
            def auto_mining_thread():
                while self.auto_mining and self.running:
                    try:
                        new_block = self.node.mine_block(wallet.address)
                        if new_block:
                            self.root.after(0, self.update_ui)
                        elif not self.auto_mining:  # Kiểm tra nếu đã dừng
                            break
                        time.sleep(1)  # Đợi 1 giây trước khi đào khối tiếp
                    except Exception as e:
                        logger.error(f"Lỗi trong quá trình đào tự động: {e}")
                        self.auto_mining = False
                        break
                
                # Kích hoạt lại nút khi dừng đào tự động
                self.root.after(0, lambda: self.start_mining_button.configure(
                    text="Bắt đầu đào tự động",
                    state="normal"
                ))
            
            self.auto_mining_thread = threading.Thread(
                target=auto_mining_thread, 
                daemon=True
            )
            self.auto_mining_thread.start()
        else:
            # Dừng đào tự động
            self.auto_mining = False
            self.node.blockchain.stop_mining()
            self.start_mining_button["text"] = "Bắt đầu đào tự động"

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
            self.start_mining_button["state"] = "normal"
        else:
            self.mining_address_label["text"] = "Chưa chọn ví"
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
        self.update_network_status()
        
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






