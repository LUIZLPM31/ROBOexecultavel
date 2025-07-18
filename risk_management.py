# risk_management.py

import csv
import os
from datetime import datetime

class RiskManagement:
    def __init__(self, initial_balance, settings):
        self.initial_balance = initial_balance if initial_balance is not None else 0.0
        self.current_balance = self.initial_balance
        
        # Configurações de entrada
        self.stake_mode = settings.get('stake_mode', 'percentage')
        self.stake_value = settings.get('stake_value', 1.0)
        
        # Configurações de gerenciamento diário
        self.daily_stop_loss_percentage = settings.get('stop_loss', 10.0)
        self.daily_take_profit_percentage = settings.get('take_profit', 5.0)
        
        # Lógica de Estratégia de Capital
        self.capital_strategy = settings.get('capital_strategy', 'none')
        
        # Soros
        self.soros_max_levels = settings.get('soros_levels', 2)
        self.soros_current_level = 0
        self.soros_initial_stake = 0.0
        self.soros_accumulated_profit = 0.0
        
        # Martingale
        self.martingale_multiplier = settings.get('martingale_multiplier', 2.0)
        self.martingale_current_level = 0
        self.martingale_base_stake = 0.0

        # Métricas gerais
        self.daily_profit_loss = 0.0
        self.wins = 0
        self.losses = 0
        self.operations = 0
        
        # Log CSV
        self.csv_filename = "trade_history.csv"
        self._initialize_csv()

    def _initialize_csv(self):
        """Cria o arquivo CSV com cabeçalho se ele não existir."""
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Ativo", "Ação", "Entrada ($)", "Resultado", 
                    "Lucro/Perda ($)", "P/L Diário ($)", "Estratégia", "Nível"
                ])

    def log_trade_to_csv(self, asset, action, stake, result, profit_loss):
        """Adiciona uma nova linha ao arquivo CSV com os detalhes da operação."""
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            strategy_name = self.capital_strategy.capitalize()
            level = 0
            if self.capital_strategy == 'soros':
                level = self.soros_current_level
            elif self.capital_strategy == 'martingale':
                level = self.martingale_current_level

            writer.writerow([
                timestamp, asset, action, f"{stake:.2f}", result,
                f"{profit_loss:.2f}", f"{self.daily_profit_loss:.2f}",
                strategy_name if strategy_name != 'None' else 'Normal', level
            ])

    def calculate_initial_stake(self):
        if self.current_balance <= 0: return 0
        
        if self.stake_mode == 'percentage':
            return self.current_balance * (self.stake_value / 100)
        elif self.stake_mode == 'fixed':
            return min(self.stake_value, self.current_balance)
        return 1.0

    def calculate_stake(self):
        """Calcula o valor da próxima entrada com base na estratégia de capital selecionada."""
        # Se estiver em um ciclo de Soros
        if self.capital_strategy == 'soros' and self.soros_current_level > 0:
            stake = self.soros_initial_stake + self.soros_accumulated_profit
            return min(stake, self.current_balance)

        # Se estiver em um ciclo de Martingale
        if self.capital_strategy == 'martingale' and self.martingale_current_level > 0:
            stake = self.martingale_base_stake * (self.martingale_multiplier ** self.martingale_current_level)
            return min(stake, self.current_balance)

        # Cálculo da entrada inicial (para todas as estratégias)
        initial_stake = self.calculate_initial_stake()
        
        if self.capital_strategy == 'soros':
            self.soros_initial_stake = initial_stake
        elif self.capital_strategy == 'martingale':
            self.martingale_base_stake = initial_stake
            
        return initial_stake

    def register_trade_result(self, profit_loss):
        if profit_loss is None: profit_loss = 0
        
        self.daily_profit_loss += profit_loss
        self.current_balance += profit_loss
        self.operations += 1
        if profit_loss > 0:
            self.wins += 1
        elif profit_loss < 0:
            self.losses += 1

        # --- Lógica de atualização da estratégia de capital ---
        if self.capital_strategy == 'soros':
            if profit_loss > 0: # WIN
                self.soros_accumulated_profit += profit_loss
                self.soros_current_level += 1
                if self.soros_current_level >= self.soros_max_levels:
                    self.reset_soros_cycle()
            else: # LOSS or DRAW
                self.reset_soros_cycle()
        
        elif self.capital_strategy == 'martingale':
            if profit_loss > 0: # WIN
                self.martingale_current_level = 0
            elif profit_loss < 0: # LOSS
                self.martingale_current_level += 1

    def reset_soros_cycle(self):
        self.soros_current_level = 0
        self.soros_initial_stake = 0.0
        self.soros_accumulated_profit = 0.0

    def get_assertiveness(self):
        if self.operations == 0: return 0.0
        return (self.wins / self.operations) * 100

    def check_stop_loss(self):
        if self.daily_profit_loss >= 0: return False
        max_loss = self.initial_balance * (self.daily_stop_loss_percentage / 100)
        return self.daily_profit_loss <= -max_loss

    def check_take_profit(self):
        if self.daily_profit_loss <= 0: return False
        min_profit = self.initial_balance * (self.daily_take_profit_percentage / 100)
        return self.daily_profit_loss >= min_profit