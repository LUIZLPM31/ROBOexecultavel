
class RiskManagement:
    def __init__(self, initial_balance, settings):
        self.initial_balance = initial_balance if initial_balance is not None else 0.0
        self.current_balance = self.initial_balance
        
        # Configurações básicas
        self.stake_mode = settings.get('stake_mode', 'percentage')
        self.stake_value = settings.get('stake_value', 1.0)
        self.daily_stop_loss_percentage = settings.get('stop_loss', 10.0)
        self.daily_take_profit_percentage = settings.get('take_profit', 5.0)
        
        # Lógica de Soros
        self.use_soros = settings.get('use_soros', False)
        self.soros_max_levels = settings.get('soros_levels', 2)
        
        # Variáveis de estado para o ciclo de Soros
        self.soros_current_level = 0
        self.soros_initial_stake = 0.0
        self.soros_accumulated_profit = 0.0

        # Métricas gerais
        self.daily_profit_loss = 0.0
        self.wins = 0
        self.losses = 0
        self.operations = 0

    def calculate_initial_stake(self):
        """Calcula o valor da entrada inicial, seja para um trade normal ou para o início de um ciclo de Soros."""
        if self.current_balance <= 0: return 0
        
        if self.stake_mode == 'percentage':
            return self.current_balance * (self.stake_value / 100)
        elif self.stake_mode == 'fixed':
            return min(self.stake_value, self.current_balance)
        return 1.0

    def calculate_stake(self):
        """
        Calcula o valor da próxima entrada.
        Se um ciclo de Soros estiver ativo, usa o valor acumulado.
        Caso contrário, calcula o valor inicial.
        """
        # Se estamos em um ciclo de Soros (nível 1 em diante)
        if self.use_soros and self.soros_current_level > 0:
            stake = self.soros_initial_stake + self.soros_accumulated_profit
            return min(stake, self.current_balance) # Garante que não apostará mais do que o saldo

        # Se não estamos em Soros, ou estamos começando um novo ciclo
        initial_stake = self.calculate_initial_stake()
        
        # Se o Soros estiver habilitado, guardamos este valor como o inicial do ciclo
        if self.use_soros:
            self.soros_initial_stake = initial_stake
            
        return initial_stake

    def register_trade_result(self, profit_loss):
        """
        Registra o resultado de uma operação e atualiza o estado do Soros.
        Este método substitui a necessidade de chamar update_daily_profit_loss diretamente.
        """
        if profit_loss is None: profit_loss = 0
        
        # Atualiza métricas gerais
        self.daily_profit_loss += profit_loss
        self.current_balance += profit_loss
        self.operations += 1
        if profit_loss > 0:
            self.wins += 1
        elif profit_loss < 0:
            self.losses += 1

        # Atualiza o estado do Soros se estiver habilitado
        if self.use_soros:
            if profit_loss > 0: # VITÓRIA
                self.soros_accumulated_profit += profit_loss
                self.soros_current_level += 1
                # Se atingiu o nível máximo, completa o ciclo e reseta
                if self.soros_current_level >= self.soros_max_levels:
                    self.reset_soros_cycle("Ciclo de Soros Nível {} concluído com sucesso!".format(self.soros_max_levels))
            else: # DERROTA ou EMPATE
                self.reset_soros_cycle("Ciclo de Soros interrompido por perda/empate.")

    def reset_soros_cycle(self, reason=""):
        """Reseta as variáveis do ciclo de Soros."""
        # A razão é opcional, pode ser usada para log futuro
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