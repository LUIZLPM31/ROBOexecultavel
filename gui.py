
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
        self.geometry("800x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.bot_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.update_queue = queue.Queue()

        self.soros_level_vars = []

        # Configuração do grid principal para ser responsivo
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.create_left_frame()
        self.create_right_frame()

        self.process_log_queue()
        self.process_update_queue()

    def update_soros_levels(self, level_clicked):
        """Garante que os níveis de Soros sejam marcados ou desmarcados em sequência."""
        level_index = level_clicked - 1
        
        if self.soros_level_vars[level_index].get():
            for i in range(level_index + 1):
                self.soros_level_vars[i].set(True)
        else:
            for i in range(level_index, len(self.soros_level_vars)):
                self.soros_level_vars[i].set(False)

    def create_left_frame(self):
        self.left_frame = ctk.CTkFrame(self, width=250, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        settings_frame = ctk.CTkScrollableFrame(self.left_frame, label_text="Configurações", label_font=ctk.CTkFont(size=16, weight="bold"))
        settings_frame.grid(row=0, column=0, padx=5, pady=0, sticky="nsew")
        
        # --- Widgets dentro da área de rolagem ---
        
        # Credenciais
        email_label = ctk.CTkLabel(settings_frame, text="Credenciais")
        email_label.pack(pady=(5,0), padx=10, fill="x")
        self.email_entry = ctk.CTkEntry(settings_frame, placeholder_text="Email")
        self.email_entry.pack(pady=5, padx=10, fill="x")
        self.password_entry = ctk.CTkEntry(settings_frame, placeholder_text="Senha", show="*")
        self.password_entry.pack(pady=(5,10), padx=10, fill="x")

        # Tipo de Conta
        account_type_label = ctk.CTkLabel(settings_frame, text="Tipo de Conta")
        account_type_label.pack(pady=(5,0), padx=10, fill="x")
        self.account_type_var = ctk.StringVar(value="PRACTICE")
        ctk.CTkRadioButton(settings_frame, text="DEMO", variable=self.account_type_var, value="PRACTICE").pack(pady=5, padx=20, anchor="w")
        ctk.CTkRadioButton(settings_frame, text="REAL", variable=self.account_type_var, value="REAL").pack(pady=(0,10), padx=20, anchor="w")

        # Valor da Entrada
        stake_label = ctk.CTkLabel(settings_frame, text="Valor da Entrada")
        stake_label.pack(pady=(5,0), padx=10, fill="x")
        self.stake_mode_var = ctk.StringVar(value="percentage")
        ctk.CTkRadioButton(settings_frame, text="Porcentagem (%)", variable=self.stake_mode_var, value="percentage").pack(pady=5, padx=20, anchor="w")
        self.percentage_entry = ctk.CTkEntry(settings_frame, placeholder_text="Ex: 1.0")
        self.percentage_entry.insert(0, "1.0")
        self.percentage_entry.pack(pady=(0,5), padx=40, fill="x")
        ctk.CTkRadioButton(settings_frame, text="Valor Fixo ($)", variable=self.stake_mode_var, value="fixed").pack(pady=5, padx=20, anchor="w")
        self.fixed_entry = ctk.CTkEntry(settings_frame, placeholder_text="Ex: 5.00")
        self.fixed_entry.pack(pady=(0,10), padx=40, fill="x")
        
        # Estratégia de Capital (Soros)
        capital_strategy_label = ctk.CTkLabel(settings_frame, text="Estratégia de Capital")
        capital_strategy_label.pack(pady=(5,0), padx=10, fill="x")
        
        self.use_soros_var = ctk.BooleanVar(value=False)
        self.soros_checkbox = ctk.CTkCheckBox(settings_frame, text="Habilitar Soros", variable=self.use_soros_var)
        self.soros_checkbox.pack(pady=5, padx=20, anchor="w")

        # <<< AJUSTE 1: Frame dos níveis alinhado com o checkbox acima (padx=20) >>>
        soros_levels_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        soros_levels_frame.pack(pady=0, padx=20, fill="x")

        MAX_SOROS_LEVELS = 3
        for i in range(1, MAX_SOROS_LEVELS + 1):
            var = ctk.BooleanVar(value=False)
            self.soros_level_vars.append(var)
            checkbox = ctk.CTkCheckBox(
            soros_levels_frame,
            text=f"Nível {i}",
            variable=var,
            command=lambda level=i: self.update_soros_levels(level),
            font=ctk.CTkFont(size=12) # <-- Tamanho da fonte e caixa reduzido
            )
            # <<< AJUSTE 2: Empacota os checkboxes lado a lado (horizontalmente) >>>
            checkbox.pack(side="left", padx=(0, 4))
        
        # Filtro de Notícias
        news_filter_label = ctk.CTkLabel(settings_frame, text="Filtros Adicionais")
        news_filter_label.pack(pady=(10,0), padx=10, fill="x")
        
        self.filter_news_var = ctk.BooleanVar(value=True) 
        self.news_checkbox = ctk.CTkCheckBox(
            settings_frame, 
            text="Pausar durante notícias", 
            variable=self.filter_news_var
        )
        self.news_checkbox.pack(pady=5, padx=20, anchor="w")

        # Gerenciamento de Risco
        risk_label = ctk.CTkLabel(settings_frame, text="Gerenciamento Diário")
        risk_label.pack(pady=(10,0), padx=10, fill="x")
        ctk.CTkLabel(settings_frame, text="Stop Loss (% do saldo inicial)").pack(fill="x", padx=20, pady=(5,0))
        self.stop_loss_entry = ctk.CTkEntry(settings_frame, placeholder_text="Ex: 10.0")
        self.stop_loss_entry.insert(0, "10.0")
        self.stop_loss_entry.pack(pady=(0,10), padx=40, fill="x")
        ctk.CTkLabel(settings_frame, text="Take Profit (% do saldo inicial)").pack(fill="x", padx=20, pady=(5,0))
        self.take_profit_entry = ctk.CTkEntry(settings_frame, placeholder_text="Ex: 5.0")
        self.take_profit_entry.insert(0, "5.0")
        self.take_profit_entry.pack(pady=(0,15), padx=40, fill="x")
        
        # ÁREA DE CONTROLE (BOTÕES)
        control_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        control_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.start_button = ctk.CTkButton(control_frame, text="Iniciar Robô", command=self.start_bot, height=40)
        self.start_button.pack(pady=5, padx=5, fill="x")
        self.stop_button = ctk.CTkButton(control_frame, text="Parar Robô", command=self.stop_bot, state="disabled", fg_color="#D32F2F", hover_color="#B71C1C", height=40)
        self.stop_button.pack(pady=(0,5), padx=5, fill="x")
        self.status_label = ctk.CTkLabel(control_frame, text="Status: Parado", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=5)

    def create_right_frame(self):
        self.right_frame = ctk.CTkFrame(self, corner_radius=10)
        self.right_frame.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        dashboard_frame = ctk.CTkFrame(self.right_frame)
        dashboard_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        dashboard_frame.grid_columnconfigure((0,1,2,3,4), weight=1)
        
        self.balance_label = ctk.CTkLabel(dashboard_frame, text="Saldo\n$0.00", font=ctk.CTkFont(size=14)); self.balance_label.grid(row=0, column=0, padx=5, pady=5)
        self.pnl_label = ctk.CTkLabel(dashboard_frame, text="P/L Diário\n$0.00", font=ctk.CTkFont(size=14)); self.pnl_label.grid(row=0, column=1, padx=5, pady=5)
        self.wins_label = ctk.CTkLabel(dashboard_frame, text="Vitórias\n0", font=ctk.CTkFont(size=14)); self.wins_label.grid(row=0, column=2, padx=5, pady=5)
        self.losses_label = ctk.CTkLabel(dashboard_frame, text="Derrotas\n0", font=ctk.CTkFont(size=14)); self.losses_label.grid(row=0, column=3, padx=5, pady=5)
        self.assertiveness_label = ctk.CTkLabel(dashboard_frame, text="Assertividade\n0.00%", font=ctk.CTkFont(size=14)); self.assertiveness_label.grid(row=0, column=4, padx=5, pady=5)
        
        self.log_textbox = ctk.CTkTextbox(self.right_frame, state="disabled", corner_radius=10, font=("Courier New", 12)); self.log_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

    def start_bot(self):
        try:
            soros_levels_from_checkboxes = sum(1 for var in self.soros_level_vars if var.get())

            settings = {
                'email': self.email_entry.get(),
                'password': self.password_entry.get(),
                'account_type': self.account_type_var.get(),
                'stake_mode': self.stake_mode_var.get(),
                'stop_loss': float(self.stop_loss_entry.get() or 10.0), 
                'take_profit': float(self.take_profit_entry.get() or 5.0),
                'use_soros': self.use_soros_var.get(),
                'soros_levels': soros_levels_from_checkboxes,
                'filter_news': self.filter_news_var.get()
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
                    if data['status'] in ['Parado', 'Erro de Conexão', 'Erro de Saldo', 'Erro de Estratégia']:
                        self.stop_button.configure(state="disabled")
                        self.start_button.configure(state="normal")
                if 'balance' in data: self.balance_label.configure(text=f"Saldo\n{data['balance']}")
                if 'pnl' in data: self.pnl_label.configure(text=f"P/L Diário\n{data['pnl']}")
                if 'wins' in data: self.wins_label.configure(text=f"Vitórias\n{data['wins']}")
                if 'losses' in data: self.losses_label.configure(text=f"Derrotas\n{data['losses']}")
                if 'assertiveness' in data: self.assertiveness_label.configure(text=f"Assertividade\n{data['assertiveness']}")
        finally:
            self.after(200, self.process_update_queue)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, filename='robot_log.log', filemode='w',
                        format='%(asctime)s - %(levelname)s - %(message)s')
    app = App()
    app.mainloop()