# gui.py

import customtkinter as ctk
import threading
import queue
import logging
from datetime import datetime

try:
    from bot_core import BotCore
except ImportError:
    print("ERRO: O arquivo 'bot_core.py' não foi encontrado na mesma pasta.")
    input("Pressione Enter para fechar...")
    exit()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Robô Trader IQ Option")
        self.geometry("850x700")
        self.minsize(800, 650)
        
        # --- Configuração de Cores ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.configure(fg_color="#0F0F0F")

        self.bot_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.update_queue = queue.Queue()

        self.soros_level_vars = []

        self.grid_columnconfigure(0, weight=1, minsize=300)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.create_left_frame()
        self.create_right_frame()

        self.process_log_queue()
        self.process_update_queue()
        
        # Define o estado inicial dos widgets de estratégia de capital
        self.toggle_capital_strategy_widgets()

    def toggle_capital_strategy_widgets(self):
        """Ativa/desativa os widgets de configuração de Soros/Martingale."""
        strategy = self.capital_strategy_var.get()
        
        # Widgets de Soros
        soros_state = "normal" if strategy == "soros" else "disabled"
        for checkbox in self.soros_checkboxes:
            checkbox.configure(state=soros_state)

        # Widgets de Martingale
        martingale_state = "normal" if strategy == "martingale" else "disabled"
        self.martingale_multiplier_label.configure(state=martingale_state)
        self.martingale_multiplier_entry.configure(state=martingale_state)

    def update_soros_levels(self, level_clicked):
        level_index = level_clicked - 1
        
        if self.soros_level_vars[level_index].get():
            for i in range(level_index + 1):
                self.soros_level_vars[i].set(True)
        else:
            for i in range(level_index, len(self.soros_level_vars)):
                self.soros_level_vars[i].set(False)

    def create_left_frame(self):
        self.left_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#0E0E0E")
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        settings_scroll_frame = ctk.CTkScrollableFrame(self.left_frame, label_text="Configurações", label_font=ctk.CTkFont(size=16, weight="bold"))
        settings_scroll_frame.grid(row=0, column=0, padx=5, pady=0, sticky="nsew")
        settings_scroll_frame.grid_columnconfigure(1, weight=1)

        row_index = 0
        NEON_GREEN = "#00FF00"
        BUTTON_GREEN = "#00A108"
        BUTTON_GREEN_HOVER = "#1B5E20"

        credential_label = ctk.CTkLabel(settings_scroll_frame, text="Credenciais", font=ctk.CTkFont(weight="bold"))
        credential_label.grid(row=row_index, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w"); row_index += 1
        
        self.email_entry = ctk.CTkEntry(settings_scroll_frame, placeholder_text="Email")
        self.email_entry.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="ew"); row_index += 1

        self.password_entry = ctk.CTkEntry(settings_scroll_frame, placeholder_text="Senha", show="*")
        self.password_entry.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="ew"); row_index += 1
        
        ctk.CTkFrame(settings_scroll_frame, height=1).grid(row=row_index, column=0, columnspan=2, pady=10, sticky="ew"); row_index += 1
        
        account_type_label = ctk.CTkLabel(settings_scroll_frame, text="Tipo de Conta", font=ctk.CTkFont(weight="bold"))
        account_type_label.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="w"); row_index += 1

        self.account_type_var = ctk.StringVar(value="PRACTICE")
        ctk.CTkRadioButton(settings_scroll_frame, text="DEMO", variable=self.account_type_var, value="PRACTICE", fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=row_index, column=0, padx=20, pady=5, sticky="w")
        ctk.CTkRadioButton(settings_scroll_frame, text="REAL", variable=self.account_type_var, value="REAL", fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=row_index, column=1, padx=10, pady=5, sticky="w"); row_index += 1

        ctk.CTkFrame(settings_scroll_frame, height=1).grid(row=row_index, column=0, columnspan=2, pady=10, sticky="ew"); row_index += 1

        stake_label = ctk.CTkLabel(settings_scroll_frame, text="Valor da Entrada", font=ctk.CTkFont(weight="bold"))
        stake_label.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="w"); row_index += 1

        self.stake_mode_var = ctk.StringVar(value="percentage")
        ctk.CTkRadioButton(settings_scroll_frame, text="Porcentagem (%)", variable=self.stake_mode_var, value="percentage", fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=row_index, column=0, columnspan=2, padx=20, pady=5, sticky="w"); row_index += 1
        self.percentage_entry = ctk.CTkEntry(settings_scroll_frame, placeholder_text="Ex: 1.0")
        self.percentage_entry.insert(0, "1.0")
        self.percentage_entry.grid(row=row_index, column=0, columnspan=2, padx=40, pady=(0, 10), sticky="ew"); row_index += 1

        ctk.CTkRadioButton(settings_scroll_frame, text="Valor Fixo ($)", variable=self.stake_mode_var, value="fixed", fg_color=NEON_GREEN, hover_color=NEON_GREEN).grid(row=row_index, column=0, columnspan=2, padx=20, pady=5, sticky="w"); row_index += 1
        self.fixed_entry = ctk.CTkEntry(settings_scroll_frame, placeholder_text="Ex: 5.00")
        self.fixed_entry.grid(row=row_index, column=0, columnspan=2, padx=40, pady=(0, 10), sticky="ew"); row_index += 1

        ctk.CTkFrame(settings_scroll_frame, height=1).grid(row=row_index, column=0, columnspan=2, pady=10, sticky="ew"); row_index += 1
        
        capital_strategy_label = ctk.CTkLabel(settings_scroll_frame, text="Estratégia de Capital", font=ctk.CTkFont(weight="bold"))
        capital_strategy_label.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="w"); row_index += 1
        
        self.capital_strategy_var = ctk.StringVar(value="none")
        strategy_frame = ctk.CTkFrame(settings_scroll_frame, fg_color="transparent")
        strategy_frame.grid(row=row_index, column=0, columnspan=2, padx=15, pady=5, sticky="ew")
        
        ctk.CTkRadioButton(strategy_frame, text="Nenhuma", variable=self.capital_strategy_var, value="none", command=self.toggle_capital_strategy_widgets, fg_color=NEON_GREEN, hover_color=NEON_GREEN).pack(side="left", padx=5)
        ctk.CTkRadioButton(strategy_frame, text="Soros", variable=self.capital_strategy_var, value="soros", command=self.toggle_capital_strategy_widgets, fg_color=NEON_GREEN, hover_color=NEON_GREEN).pack(side="left", padx=5)
        ctk.CTkRadioButton(strategy_frame, text="Martingale", variable=self.capital_strategy_var, value="martingale", command=self.toggle_capital_strategy_widgets, fg_color=NEON_GREEN, hover_color=NEON_GREEN).pack(side="left", padx=5)
        row_index += 1
        
        # --- Configurações de Soros ---
        self.soros_checkboxes = []
        soros_levels_frame = ctk.CTkFrame(settings_scroll_frame, fg_color="transparent")
        soros_levels_frame.grid(row=row_index, column=0, columnspan=2, padx=20, pady=0, sticky="ew")
        MAX_SOROS_LEVELS = 2
        for i in range(MAX_SOROS_LEVELS):
            var = ctk.BooleanVar(value=False)
            self.soros_level_vars.append(var)
            checkbox = ctk.CTkCheckBox(soros_levels_frame, text=f"Nível {i+1}", variable=var, command=lambda level=i+1: self.update_soros_levels(level), font=ctk.CTkFont(size=11), fg_color=NEON_GREEN, hover_color=NEON_GREEN)
            checkbox.grid(row=0, column=i, padx=5, pady=(0, 5), sticky="w")
            self.soros_checkboxes.append(checkbox)
        row_index += 1
        
        # --- Configurações de Martingale ---
        martingale_frame = ctk.CTkFrame(settings_scroll_frame, fg_color="transparent")
        martingale_frame.grid(row=row_index, column=0, columnspan=2, padx=25, pady=(0, 10), sticky="ew")
        self.martingale_multiplier_label = ctk.CTkLabel(martingale_frame, text="Multiplicador:")
        self.martingale_multiplier_label.pack(side="left", padx=(0,5))
        self.martingale_multiplier_entry = ctk.CTkEntry(martingale_frame, placeholder_text="Ex: 2.0", width=80)
        self.martingale_multiplier_entry.insert(0, "2.0")
        self.martingale_multiplier_entry.pack(side="left")
        row_index +=1

        ctk.CTkFrame(settings_scroll_frame, height=1).grid(row=row_index, column=0, columnspan=2, pady=10, sticky="ew"); row_index += 1
        
        filters_label = ctk.CTkLabel(settings_scroll_frame, text="Filtros Adicionais", font=ctk.CTkFont(weight="bold"))
        filters_label.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="w"); row_index += 1
        
        self.filter_news_var = ctk.BooleanVar(value=True) 
        self.news_checkbox = ctk.CTkCheckBox(settings_scroll_frame, text="Pausar durante notícias", variable=self.filter_news_var, fg_color=NEON_GREEN, hover_color=NEON_GREEN)
        self.news_checkbox.grid(row=row_index, column=0, columnspan=2, padx=20, pady=5, sticky="w"); row_index += 1
        
        ctk.CTkFrame(settings_scroll_frame, height=1).grid(row=row_index, column=0, columnspan=2, pady=10, sticky="ew"); row_index += 1

        risk_label = ctk.CTkLabel(settings_scroll_frame, text="Gerenciamento Diário", font=ctk.CTkFont(weight="bold"))
        risk_label.grid(row=row_index, column=0, columnspan=2, padx=10, pady=5, sticky="w"); row_index += 1
        
        ctk.CTkLabel(settings_scroll_frame, text="Stop Loss (% do saldo)").grid(row=row_index, column=0, columnspan=2, padx=20, pady=(5,0), sticky="w"); row_index += 1
        self.stop_loss_entry = ctk.CTkEntry(settings_scroll_frame, placeholder_text="Ex: 10.0")
        self.stop_loss_entry.insert(0, "10.0")
        self.stop_loss_entry.grid(row=row_index, column=0, columnspan=2, padx=40, pady=(0, 10), sticky="ew"); row_index += 1

        ctk.CTkLabel(settings_scroll_frame, text="Take Profit (% do saldo)").grid(row=row_index, column=0, columnspan=2, padx=20, pady=(5,0), sticky="w"); row_index += 1
        self.take_profit_entry = ctk.CTkEntry(settings_scroll_frame, placeholder_text="Ex: 5.0")
        self.take_profit_entry.insert(0, "5.0")
        self.take_profit_entry.grid(row=row_index, column=0, columnspan=2, padx=40, pady=(0, 15), sticky="ew"); row_index += 1
        
        control_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        control_frame.grid(row=1, column=0, padx=5, pady=5, sticky="sew")
        control_frame.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(control_frame, text="Iniciar Robô", command=self.start_bot, height=40, fg_color=BUTTON_GREEN, hover_color=BUTTON_GREEN_HOVER)
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.stop_button = ctk.CTkButton(control_frame, text="Parar Robô", command=self.stop_bot, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C", height=40)
        self.stop_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.status_label = ctk.CTkLabel(control_frame, text="Status: Parado", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=2, column=0, padx=5, pady=10, sticky="ew")

    def create_right_frame(self):
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=(0, 10), pady=0, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        dashboard_frame = ctk.CTkFrame(self.right_frame, corner_radius=10, fg_color="#000000")
        dashboard_frame.grid(row=0, column=0, padx=0, pady=10, sticky="ew")
        dashboard_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        def create_metric_card(parent, col, title, initial_value):
            card = ctk.CTkFrame(parent, fg_color="transparent")
            card.grid(row=0, column=col, padx=5, pady=10, sticky="ew")
            card.grid_columnconfigure(0, weight=1)
            title_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"))
            title_label.grid(row=0, column=0, sticky="ew")
            value_label = ctk.CTkLabel(card, text=initial_value, font=ctk.CTkFont(size=18))
            value_label.grid(row=1, column=0, sticky="ew")
            return value_label

        self.balance_label = create_metric_card(dashboard_frame, 0, "SALDO", "$0.00")
        self.pnl_label = create_metric_card(dashboard_frame, 1, "P/L DIÁRIO", "$0.00")
        self.wins_label = create_metric_card(dashboard_frame, 2, "VITÓRIAS", "0")
        self.losses_label = create_metric_card(dashboard_frame, 3, "DERROTAS", "0")
        self.assertiveness_label = create_metric_card(dashboard_frame, 4, "ASSERTIVIDADE", "0.00%")
        
        self.log_textbox = ctk.CTkTextbox(self.right_frame, state="disabled", corner_radius=10, font=("Courier New", 12), fg_color="#000000")
        self.log_textbox.grid(row=1, column=0, padx=0, pady=(0, 10), sticky="nsew")

    def start_bot(self):
        try:
            settings = {
                'email': self.email_entry.get(), 'password': self.password_entry.get(),
                'account_type': self.account_type_var.get(), 'stake_mode': self.stake_mode_var.get(),
                'stop_loss': float(self.stop_loss_entry.get() or 10.0), 
                'take_profit': float(self.take_profit_entry.get() or 5.0),
                'filter_news': self.filter_news_var.get(),
                
                # Novas configurações de estratégia de capital
                'capital_strategy': self.capital_strategy_var.get(),
                'soros_levels': sum(1 for var in self.soros_level_vars if var.get()),
                'martingale_multiplier': float(self.martingale_multiplier_entry.get() or 2.0)
            }
            if settings['stake_mode'] == 'percentage':
                settings['stake_value'] = float(self.percentage_entry.get() or 1.0)
            else:
                settings['stake_value'] = float(self.fixed_entry.get() or 1.0)

            if not settings['email'] or not settings['password']:
                self.log_message("ERRO: Email e Senha são obrigatórios.")
                return

            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status_label.configure(text="Status: Iniciando...")
            self.stop_event.clear()
            self.bot_instance = BotCore(settings, self.log_queue, self.update_queue, self.stop_event)
            self.bot_thread = threading.Thread(target=self.bot_instance.run, daemon=True)
            self.bot_thread.start()

        except ValueError:
            self.log_message("ERRO: Valores de entrada ou risco inválidos. Use apenas números.")
        except Exception as e:
            self.log_message(f"ERRO ao iniciar: {e}")
    
    def stop_bot(self):
        if self.bot_thread and self.bot_thread.is_alive():
            self.status_label.configure(text="Status: Parando...")
            self.stop_event.set()
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="normal")

    def log_message(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{datetime.now().strftime('%H:%M:%S')} - {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def process_log_queue(self):
        try:
            while not self.log_queue.empty(): self.log_message(self.log_queue.get_nowait())
        finally:
            self.after(200, self.process_log_queue)

    def process_update_queue(self):
        try:
            while not self.update_queue.empty():
                data = self.update_queue.get_nowait()
                if 'status' in data:
                    self.status_label.configure(text=f"Status: {data['status']}")
                    if data['status'] in ['Parado', 'Meta Atingida', 'Stop Atingido', 'Erro de Conexão', 'Erro de Saldo', 'Erro de Estratégia', 'Erro']:
                        self.stop_button.configure(state="disabled")
                        self.start_button.configure(state="normal")
                if 'balance' in data: self.balance_label.configure(text=f"{data['balance']}")
                if 'pnl' in data: self.pnl_label.configure(text=f"{data['pnl']}")
                if 'wins' in data: self.wins_label.configure(text=f"{data['wins']}")
                if 'losses' in data: self.losses_label.configure(text=f"{data['losses']}")
                if 'assertiveness' in data: self.assertiveness_label.configure(text=f"{data['assertiveness']}")
        finally:
            self.after(200, self.process_update_queue)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename='robot_log.log', filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    app = App()
    app.mainloop()