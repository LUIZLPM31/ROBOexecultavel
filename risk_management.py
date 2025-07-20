# risk_management.py (CORRIGIDO NOVAMENTE COM LÓGICA DE SOROS REFINADA)

import csv
import os
from datetime import datetime

class RiskManagement:
    def __init__(self, initial_balance, settings):
        self.initial_balance = initial_balance if initial_balance is not None else 0.0
        self.current_balance = self.initial_balance
        
        self.stake_mode = settings.get('stake_mode', 'percentage')
        self.stake_value = settings.get('stake_value', 1.0)
        
        self.daily_stop_loss_percentage = settings.get('stop_loss', 10.0)
        self.daily_take_profit_percentage = settings.get('take_profit', 5.0)
        
        self.capital_strategy = settings.get('capital_strategy', 'none')
        
        # --- MUDANÇA 1: Simplificação das variáveis de Soros ---
        self.soros_max_levels = settings.get('soros_levels', 2)
        self.soros_current_level = 0
        self.soros_initial_stake = 0.0
        self.soros_profit_to_reinvest = 0.0 # Usaremos esta variável em vez de 'accumulated_profit'
        
        self.martingale_multiplier = settings.get('martingale_multiplier', 2.0)
        self.martingale_current_level = 0
        self.martingale_base_stake = 0.0

        self.daily_profit_loss = 0.0
        self.wins = 0
        self.losses = 0
        self.operations = 0
        
        self.csv_filename = "trade_history.csv"
        self._initialize_csv()

    def _initialize_csv(self):
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Timestamp", "Ativo", "Ação", "Entrada ($)", "Resultado", 
                    "Lucro/Perda ($)", "P/L Diário ($)", "Estratégia", "Nível"
                ])

    def log_trade_to_csv(self, asset, action, stake, result, profit_loss):
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
        
        # --- MUDANÇA 2: A fórmula de cálculo dos Soros foi corrigida ---
        if self.capital_strategy == 'soros' and self.soros_current_level > 0:
            # A próxima entrada é o VALOR INICIAL do ciclo + o LUCRO da operação anterior.
            stake = self.soros_initial_stake + self.soros_profit_to_reinvest
            return min(stake, self.current_balance)

        if self.capital_strategy == 'martingale' and self.martingale_current_level > 0:
            stake = self.martingale_base_stake * (self.martingale_multiplier ** self.martingale_current_level)
            return min(stake, self.current_balance)

        initial_stake = self.calculate_initial_stake()
        
        if self.capital_strategy == 'soros':
            # Define o valor base que será usado durante todo o ciclo de Soros
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

        # --- MUDANÇA 3: A lógica de atualização do estado de Soros foi corrigida ---
        if self.capital_strategy == 'soros':
            if profit_loss > 0: # WIN
                # Guarda apenas o lucro da última operação para reinvestir
                self.soros_profit_to_reinvest = profit_loss
                self.soros_current_level += 1
                # Se atingiu o nível máximo de Soros, reseta o ciclo para pegar os lucros.
                if self.soros_current_level >= self.soros_max_levels:
                    self.reset_soros_cycle()
            else: # LOSS or DRAW
                # Se perder, o ciclo de Soros é interrompido imediatamente.
                self.reset_soros_cycle()
        
        elif self.capital_strategy == 'martingale':
            if profit_loss > 0:
                self.martingale_current_level = 0
            elif profit_loss < 0:
                self.martingale_current_level += 1

    def reset_soros_cycle(self):
        # --- MUDANÇA 4: A função de reset foi atualizada ---
        self.soros_current_level = 0
        self.soros_initial_stake = 0.0
        self.soros_profit_to_reinvest = 0.0 # Zera o lucro a ser reinvestido

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