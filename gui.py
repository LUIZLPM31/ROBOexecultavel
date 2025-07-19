# gui.py (Interface Corrigida - Layout Ajustado)

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

        self.title("IQ Option Trading Bot Pro")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # --- Tema Moderno ---
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Cores modernas
        self.colors = {
            'bg_primary': '#000000',      # Azul escuro profissional
            'bg_secondary': '#0F0F23',    # Azul médio
            'bg_card': '#232347',         # Cards
            'bg_input': '#2D2E54',        # Inputs
            'accent_primary': '#00D4FF',  # Cyan moderno
            'accent_secondary': '#4ECDC4', # Verde-azulado
            'success': '#00E676',         # Verde sucesso
            'warning': '#FF9800',         # Laranja aviso
            'danger': '#FF5252',          # Vermelho erro
            'text_primary': '#FFFFFF',    # Texto principal
            'text_secondary': '#B0BEC5', # Texto secundário
        }
        
        self.configure(fg_color=self.colors['bg_primary'])

        self.bot_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.update_queue = queue.Queue()
        self.soros_level_vars = []

        # Layout principal corrigido
        self.grid_rowconfigure(0, weight=0, minsize=70)  # Header fixo
        self.grid_rowconfigure(1, weight=1)  # Conteúdo principal
        self.grid_columnconfigure(0, weight=1, minsize=400)  # Painel esquerdo
        self.grid_columnconfigure(1, weight=2, minsize=600)  # Painel direito

        # Criar componentes na ordem correta
        self.create_header()
        self.create_main_content()

        # Inicializar processamento de filas
        self.process_log_queue()
        self.process_update_queue()
        self.toggle_capital_strategy_widgets()

    def create_header(self):
        """Cria cabeçalho moderno com logo e informações"""
        header_frame = ctk.CTkFrame(
            self, 
            height=70, 
            corner_radius=0, 
            fg_color=self.colors['bg_secondary']
        )
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Logo/Título
        logo_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        title_label = ctk.CTkLabel(
            logo_frame, 
            text="⚡ IQ OPTION TRADING BOT", 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['accent_primary']
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            logo_frame, 
            text="Professional Automated Trading System", 
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_secondary']
        )
        subtitle_label.pack()
        
        # Status geral no header
        self.main_status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.main_status_frame.grid(row=0, column=2, padx=20, pady=15, sticky="e")
        
        # Label de status inicial
        self.header_status_label = ctk.CTkLabel(
            self.main_status_frame,
            text="⚪ Sistema Parado",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors['text_secondary']
        )
        self.header_status_label.pack()

    def create_main_content(self):
        """Cria o conteúdo principal da aplicação"""
        # Container principal para o conteúdo
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=0)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1, minsize=400)
        main_container.grid_columnconfigure(1, weight=2, minsize=600)

        self.create_left_panel(main_container)
        self.create_right_panel(main_container)

    def create_left_panel(self, parent):
        """Painel esquerdo com configurações"""
        self.left_frame = ctk.CTkFrame(
            parent, 
            corner_radius=15, 
            fg_color=self.colors['bg_secondary']
        )
        self.left_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        # Scroll frame moderno
        settings_scroll = ctk.CTkScrollableFrame(
            self.left_frame, 
            label_text="⚙️ CONFIGURAÇÕES",
            label_font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="transparent",
            label_text_color=self.colors['accent_primary']
        )
        settings_scroll.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        settings_scroll.grid_columnconfigure(0, weight=1)

        # Estilos modernos
        self.fonts = {
            'heading': ctk.CTkFont(size=14, weight="bold"),
            'subheading': ctk.CTkFont(size=12, weight="bold"),
            'body': ctk.CTkFont(size=11),
            'small': ctk.CTkFont(size=10)
        }

        # Criar seções de configuração
        self.create_credentials_section(settings_scroll, 0)
        self.create_account_section(settings_scroll, 1)
        self.create_stake_section(settings_scroll, 2)
        self.create_strategy_section(settings_scroll, 3)
        self.create_filters_section(settings_scroll, 4)
        self.create_risk_section(settings_scroll, 5)
        
        # Seção de controle na parte inferior
        self.create_control_section()

    def create_modern_card(self, parent, title, icon="", row=0):
        """Cria card moderno com gradiente sutil"""
        card = ctk.CTkFrame(
            parent, 
            fg_color=self.colors['bg_card'],
            corner_radius=12,
            border_width=1,
            border_color=self.colors['accent_primary']
        )
        card.grid(row=row, column=0, padx=5, pady=8, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        
        # Header do card
        header = ctk.CTkFrame(card, fg_color="transparent", height=40)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 5))
        header.grid_propagate(False)
        
        title_label = ctk.CTkLabel(
            header, 
            text=f"{icon} {title}",
            font=self.fonts['heading'],
            text_color=self.colors['text_primary'],
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        return card

    def create_credentials_section(self, parent, row):
        card = self.create_modern_card(parent, "CREDENCIAIS", "🔐", row)
        
        self.email_entry = ctk.CTkEntry(
            card, 
            placeholder_text="📧 Digite seu email",
            font=self.fonts['body'],
            height=40,
            fg_color=self.colors['bg_input'],
            border_color=self.colors['accent_secondary'],
            border_width=1
        )
        self.email_entry.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.password_entry = ctk.CTkEntry(
            card, 
            placeholder_text="🔒 Digite sua senha",
            show="*",
            font=self.fonts['body'],
            height=40,
            fg_color=self.colors['bg_input'],
            border_color=self.colors['accent_secondary'],
            border_width=1
        )
        self.password_entry.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")

    def create_account_section(self, parent, row):
        card = self.create_modern_card(parent, "TIPO DE CONTA", "💼", row)
        
        radio_frame = ctk.CTkFrame(card, fg_color="transparent")
        radio_frame.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="ew")
        radio_frame.grid_columnconfigure((0, 1), weight=1)

        self.account_type_var = ctk.StringVar(value="PRACTICE")
        
        demo_radio = ctk.CTkRadioButton(
            radio_frame, 
            text="🎯 DEMONSTRAÇÃO",
            variable=self.account_type_var,
            value="PRACTICE",
            fg_color=self.colors['accent_secondary'],
            hover_color=self.colors['accent_primary'],
            font=self.fonts['body']
        )
        demo_radio.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        real_radio = ctk.CTkRadioButton(
            radio_frame, 
            text="💰 CONTA REAL",
            variable=self.account_type_var,
            value="REAL",
            fg_color=self.colors['warning'],
            hover_color=self.colors['danger'],
            font=self.fonts['body']
        )
        real_radio.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    def create_stake_section(self, parent, row):
        card = self.create_modern_card(parent, "VALOR DE ENTRADA", "💵", row)
        
        self.stake_mode_var = ctk.StringVar(value="percentage")
        
        # Modo porcentagem
        perc_frame = ctk.CTkFrame(card, fg_color="transparent")
        perc_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        
        perc_radio = ctk.CTkRadioButton(
            perc_frame,
            text="📊 Porcentagem do Saldo (%)",
            variable=self.stake_mode_var,
            value="percentage",
            fg_color=self.colors['success'],
            hover_color=self.colors['accent_primary'],
            font=self.fonts['body']
        )
        perc_radio.pack(anchor="w")
        
        self.percentage_entry = ctk.CTkEntry(
            card,
            placeholder_text="Ex: 1.0",
            font=self.fonts['body'],
            height=35,
            fg_color=self.colors['bg_input']
        )
        self.percentage_entry.insert(0, "1.0")
        self.percentage_entry.grid(row=2, column=0, padx=30, pady=(0, 10), sticky="ew")
        
        # Modo fixo
        fixed_frame = ctk.CTkFrame(card, fg_color="transparent")
        fixed_frame.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        
        fixed_radio = ctk.CTkRadioButton(
            fixed_frame,
            text="💲 Valor Fixo ($)",
            variable=self.stake_mode_var,
            value="fixed",
            fg_color=self.colors['success'],
            hover_color=self.colors['accent_primary'],
            font=self.fonts['body']
        )
        fixed_radio.pack(anchor="w")
        
        self.fixed_entry = ctk.CTkEntry(
            card,
            placeholder_text="Ex: 5.00",
            font=self.fonts['body'],
            height=35,
            fg_color=self.colors['bg_input']
        )
        self.fixed_entry.grid(row=4, column=0, padx=30, pady=(0, 15), sticky="ew")

    def create_strategy_section(self, parent, row):
        card = self.create_modern_card(parent, "ESTRATÉGIAS DE CAPITAL", "🧠", row)
        
        self.capital_strategy_var = ctk.StringVar(value="none")
        
        # Radio buttons para estratégias
        strategy_frame = ctk.CTkFrame(card, fg_color="transparent")
        strategy_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        
        strategies = [
            ("🚫 Nenhuma", "none", self.colors['text_secondary']),
            ("📈 Soros", "soros", self.colors['accent_primary']),
            ("🎲 Martingale", "martingale", self.colors['warning'])
        ]
        
        for i, (text, value, color) in enumerate(strategies):
            radio = ctk.CTkRadioButton(
                strategy_frame,
                text=text,
                variable=self.capital_strategy_var,
                value=value,
                command=self.toggle_capital_strategy_widgets,
                fg_color=color,
                font=self.fonts['body']
            )
            radio.pack(anchor="w", pady=2)
        
        # Configurações específicas
        config_frame = ctk.CTkFrame(card, fg_color="transparent")
        config_frame.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")
        config_frame.grid_columnconfigure(0, weight=1)
        config_frame.grid_columnconfigure(1, weight=1)
        
        # Soros
        soros_frame = ctk.CTkFrame(config_frame, fg_color=self.colors['bg_input'], corner_radius=8)
        soros_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        soros_label = ctk.CTkLabel(soros_frame, text="Níveis Soros", font=self.fonts['subheading'])
        soros_label.pack(pady=(8, 5))
        
        self.soros_checkboxes = []
        for i in range(2):
            var = ctk.BooleanVar(value=False)
            self.soros_level_vars.append(var)
            checkbox = ctk.CTkCheckBox(
                soros_frame,
                text=f"Nível {i+1}",
                variable=var,
                command=lambda level=i+1: self.update_soros_levels(level),
                font=self.fonts['small'],
                fg_color=self.colors['accent_primary']
            )
            checkbox.pack(pady=2)
            self.soros_checkboxes.append(checkbox)
        
        # Martingale
        martingale_frame = ctk.CTkFrame(config_frame, fg_color=self.colors['bg_input'], corner_radius=8)
        martingale_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        self.martingale_multiplier_label = ctk.CTkLabel(
            martingale_frame, 
            text="Multiplicador", 
            font=self.fonts['subheading']
        )
        self.martingale_multiplier_label.pack(pady=(8, 5))
        
        self.martingale_multiplier_entry = ctk.CTkEntry(
            martingale_frame,
            placeholder_text="2.0",
            font=self.fonts['body'],
            height=30,
            width=80
        )
        self.martingale_multiplier_entry.insert(0, "2.0")
        self.martingale_multiplier_entry.pack(pady=(0, 8))

    def create_filters_section(self, parent, row):
        card = self.create_modern_card(parent, "FILTROS INTELIGENTES", "🎯", row)
        
        self.filter_news_var = ctk.BooleanVar(value=True)
        
        news_checkbox = ctk.CTkCheckBox(
            card,
            text="📰 Pausar durante notícias importantes",
            variable=self.filter_news_var,
            fg_color=self.colors['accent_secondary'],
            font=self.fonts['body']
        )
        news_checkbox.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="w")

    def create_risk_section(self, parent, row):
        card = self.create_modern_card(parent, "GERENCIAMENTO DE RISCO", "⚖️", row)
        
        # Stop Loss
        stop_frame = ctk.CTkFrame(card, fg_color="transparent")
        stop_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            stop_frame, 
            text="🛑 Stop Loss (% do saldo)",
            font=self.fonts['body'],
            text_color=self.colors['danger']
        ).pack(anchor="w")
        
        self.stop_loss_entry = ctk.CTkEntry(
            card,
            placeholder_text="10.0",
            font=self.fonts['body'],
            height=35,
            fg_color=self.colors['bg_input']
        )
        self.stop_loss_entry.insert(0, "10.0")
        self.stop_loss_entry.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        
        # Take Profit
        profit_frame = ctk.CTkFrame(card, fg_color="transparent")
        profit_frame.grid(row=3, column=0, padx=15, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            profit_frame, 
            text="🎯 Take Profit (% do saldo)",
            font=self.fonts['body'],
            text_color=self.colors['success']
        ).pack(anchor="w")
        
        self.take_profit_entry = ctk.CTkEntry(
            card,
            placeholder_text="5.0",
            font=self.fonts['body'],
            height=35,
            fg_color=self.colors['bg_input']
        )
        self.take_profit_entry.insert(0, "5.0")
        self.take_profit_entry.grid(row=4, column=0, padx=15, pady=(0, 15), sticky="ew")

    def create_control_section(self):
        """Seção de controle com botões modernos"""
        control_frame = ctk.CTkFrame(
            self.left_frame, 
            fg_color="transparent",
            height=120
        )
        control_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_propagate(False)
        control_frame.grid_columnconfigure(0, weight=1)
        
        # Botão Iniciar
        self.start_button = ctk.CTkButton(
            control_frame,
            text="🚀 INICIAR ROBÔ",
            command=self.start_bot,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['success'],
            hover_color=self.colors['accent_primary'],
            corner_radius=12
        )
        self.start_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        # Botão Parar
        self.stop_button = ctk.CTkButton(
            control_frame,
            text="⏹️ PARAR ROBÔ",
            command=self.stop_bot,
            state="disabled",
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=self.colors['danger'],
            hover_color="#B71C1C",
            corner_radius=12
        )
        self.stop_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # Status
        self.status_label = ctk.CTkLabel(
            control_frame,
            text="⚪ Status: Parado",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['text_secondary']
        )
        self.status_label.grid(row=2, column=0, padx=5, pady=5)

    def create_right_panel(self, parent):
        """Painel direito com dashboard e logs"""
        self.right_frame = ctk.CTkFrame(
            parent, 
            fg_color="transparent"
        )
        self.right_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        self.create_dashboard()
        self.create_log_section()

    def create_dashboard(self):
        """Dashboard com métricas"""
        dashboard_frame = ctk.CTkFrame(
            self.right_frame, 
            corner_radius=15,
            fg_color=self.colors['bg_secondary'],
            height=180
        )
        dashboard_frame.grid(row=0, column=0, padx=0, pady=(0, 10), sticky="ew")
        dashboard_frame.grid_propagate(False)
        dashboard_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        # Header do dashboard
        header_label = ctk.CTkLabel(
            dashboard_frame,
            text="📊 DASHBOARD EM TEMPO REAL",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['accent_primary']
        )
        header_label.grid(row=0, column=0, columnspan=5, pady=(15, 10))

        # Métricas
        metrics = [
            ("💰", "SALDO", "$0.00", self.colors['accent_primary']),
            ("📈", "P/L DIÁRIO", "$0.00", self.colors['success']),
            ("✅", "VITÓRIAS", "0", self.colors['success']),
            ("❌", "DERROTAS", "0", self.colors['danger']),
            ("🎯", "ASSERTIVIDADE", "0.00%", self.colors['accent_secondary'])
        ]
        
        self.metric_labels = {}
        for i, (icon, title, value, color) in enumerate(metrics):
            card = self.create_metric_card(dashboard_frame, i, icon, title, value, color)
            key = title.lower().replace(" ", "_").replace("/", "")
            self.metric_labels[key] = card

    def create_metric_card(self, parent, col, icon, title, value, color):
        """Cria card de métrica moderno"""
        card_frame = ctk.CTkFrame(
            parent, 
            fg_color=self.colors['bg_card'],
            corner_radius=10,
            border_width=1,
            border_color=color
        )
        card_frame.grid(row=1, column=col, padx=8, pady=15, sticky="ew")
        
        icon_label = ctk.CTkLabel(
            card_frame,
            text=icon,
            font=ctk.CTkFont(size=20)
        )
        icon_label.pack(pady=(10, 2))
        
        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.colors['text_secondary']
        )
        title_label.pack()
        
        value_label = ctk.CTkLabel(
            card_frame,
            text=value,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=color
        )
        value_label.pack(pady=(2, 10))
        
        return value_label

    def create_log_section(self):
        """Seção de logs moderna"""
        log_frame = ctk.CTkFrame(
            self.right_frame,
            corner_radius=15,
            fg_color=self.colors['bg_secondary']
        )
        log_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        # Header dos logs
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent", height=50)
        log_header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 0))
        log_header.grid_propagate(False)
        
        header_label = ctk.CTkLabel(
            log_header,
            text="📋 LOGS DO SISTEMA",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['accent_primary']
        )
        header_label.pack(side="left")
        
        # Área de logs
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            state="disabled",
            corner_radius=12,
            font=("JetBrains Mono", 10),
            fg_color=self.colors['bg_primary'],
            border_width=1,
            border_color=self.colors['accent_secondary']
        )
        self.log_textbox.grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

    def toggle_capital_strategy_widgets(self):
        """Ativa/desativa widgets de estratégia"""
        strategy = self.capital_strategy_var.get()
        
        # Soros widgets
        soros_state = "normal" if strategy == "soros" else "disabled"
        for checkbox in self.soros_checkboxes:
            checkbox.configure(state=soros_state)

        # Martingale widgets
        martingale_state = "normal" if strategy == "martingale" else "disabled"
        self.martingale_multiplier_label.configure(state=martingale_state)
        self.martingale_multiplier_entry.configure(state=martingale_state)

    def update_soros_levels(self, level_clicked):
        """Atualiza níveis Soros"""
        level_index = level_clicked - 1
        
        if self.soros_level_vars[level_index].get():
            for i in range(level_index + 1):
                self.soros_level_vars[i].set(True)
        else:
            for i in range(level_index, len(self.soros_level_vars)):
                self.soros_level_vars[i].set(False)

    def start_bot(self):
        """Inicia o robô"""
        try:
            settings = {
                'email': self.email_entry.get(),
                'password': self.password_entry.get(),
                'account_type': self.account_type_var.get(),
                'stake_mode': self.stake_mode_var.get(),
                'stop_loss': float(self.stop_loss_entry.get() or 10.0),
                'take_profit': float(self.take_profit_entry.get() or 5.0),
                'filter_news': self.filter_news_var.get(),
                'capital_strategy': self.capital_strategy_var.get(),
                'soros_levels': sum(1 for var in self.soros_level_vars if var.get()),
                'martingale_multiplier': float(self.martingale_multiplier_entry.get() or 2.0)
            }
            
            if settings['stake_mode'] == 'percentage':
                settings['stake_value'] = float(self.percentage_entry.get() or 1.0)
            else:
                settings['stake_value'] = float(self.fixed_entry.get() or 1.0)

            if not settings['email'] or not settings['password']:
                self.log_message("❌ ERRO: Email e Senha são obrigatórios.")
                return

            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status_label.configure(text="🟡 Status: Iniciando...", text_color=self.colors['warning'])
            self.header_status_label.configure(text="🟡 Sistema Iniciando...", text_color=self.colors['warning'])
            
            self.stop_event.clear()
            self.bot_instance = BotCore(settings, self.log_queue, self.update_queue, self.stop_event)
            self.bot_thread = threading.Thread(target=self.bot_instance.run, daemon=True)
            self.bot_thread.start()

        except ValueError:
            self.log_message("❌ ERRO: Valores inválidos. Use apenas números.")
        except Exception as e:
            self.log_message(f"❌ ERRO ao iniciar: {e}")

    def stop_bot(self):
        """Para o robô"""
        if self.bot_thread and self.bot_thread.is_alive():
            self.status_label.configure(text="🟠 Status: Parando...", text_color=self.colors['warning'])
            self.stop_event.set()
        
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="normal")

    def log_message(self, message):
        """Adiciona mensagem ao log com cores"""
        self.log_textbox.configure(state="normal")
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_textbox.insert("end", formatted_message)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def process_log_queue(self):
        """Processa fila de logs"""
        try:
            while not self.log_queue.empty():
                self.log_message(self.log_queue.get_nowait())
        finally:
            self.after(200, self.process_log_queue)

    def process_update_queue(self):
        """Processa atualizações da interface"""
        try:
            while not self.update_queue.empty():
                data = self.update_queue.get_nowait()
                
                if 'status' in data:
                    status_icons = {
                        'Conectado': '🟢',
                        'Operando': '🔄',
                        'Parado': '⚪',
                        'Meta Atingida': '🎯',
                        'Stop Atingido': '🛑',
                        'Erro de Conexão': '🔴',
                        'Erro de Saldo': '💸',
                        'Erro de Estratégia': '⚠️',
                        'Erro': '❌'
                    }
                    
                    status = data['status']
                    icon = status_icons.get(status, '⚪')
                    
                    # Define cor baseada no status
                    if status in ['Conectado', 'Operando']:
                        color = self.colors['success']
                    elif status in ['Meta Atingida']:
                        color = self.colors['accent_primary']
                    elif 'Erro' in status or status == 'Stop Atingido':
                        color = self.colors['danger']
                    else:
                        color = self.colors['text_secondary']
                    
                    self.status_label.configure(
                        text=f"{icon} Status: {status}",
                        text_color=color
                    )
                    
                    # Reabilita botões se necessário
                    if status in ['Parado', 'Meta Atingida', 'Stop Atingido', 'Erro de Conexão', 'Erro de Saldo', 'Erro de Estratégia', 'Erro']:
                        self.stop_button.configure(state="disabled")
                        self.start_button.configure(state="normal")
                
                # Atualiza métricas do dashboard
                if 'balance' in data:
                    self.metric_labels['saldo'].configure(text=f"{data['balance']}")
                if 'pnl' in data:
                    pnl_color = self.colors['success'] if '+' in str(data['pnl']) else self.colors['danger']
                    self.metric_labels['p_l_diário'].configure(text=f"{data['pnl']}", text_color=pnl_color)
                if 'wins' in data:
                    self.metric_labels['vitórias'].configure(text=f"{data['wins']}")
                if 'losses' in data:
                    self.metric_labels['derrotas'].configure(text=f"{data['losses']}")
                if 'assertiveness' in data:
                    assertiveness_val = float(data['assertiveness'].replace('%', ''))
                    color = self.colors['success'] if assertiveness_val >= 70 else self.colors['warning'] if assertiveness_val >= 50 else self.colors['danger']
                    self.metric_labels['assertividade'].configure(text=f"{data['assertiveness']}", text_color=color)
                    
        finally:
            self.after(200, self.process_update_queue)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        filename='robot_log.log',
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Configuração adicional para melhor aparência no Windows
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Esconde a janela padrão do tkinter
        
        # Configura DPI awareness no Windows
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
    except:
        pass
    
    app = App()
    app.mainloop()