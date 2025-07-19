# bot_core.py (VERSÃO MELHORADA)

import time
import logging
from datetime import datetime
import importlib
import os
import sys

try:
    from iq_option_connection import IQOptionConnection
    from risk_management import RiskManagement
    from news_filter import NewsFilter 
except ImportError as e:
    logging.critical(f"ERRO CRÍTICO: Não foi possível importar módulos essenciais: {e}")
    raise

class BotCore:
    def __init__(self, settings, log_queue, update_queue, stop_event):
        self.settings = settings
        self.email = settings.get('email')
        self.password = settings.get('password')
        self.account_type = settings.get('account_type')
        self.log_queue = log_queue
        self.update_queue = update_queue
        self.stop_event = stop_event
        self.PREFERRED_ASSETS = ["EURUSD", "EURJPY", "GBPUSD", "AUDCAD", "USDJPY", "EURGBP", "USDCAD"]
        self.OTC_ASSETS = [asset + "-OTC" for asset in self.PREFERRED_ASSETS]
        self.TIMEFRAME = 60
        self.EXPIRATION_TIME = 1
        self.last_candle_times = {}
        self.use_news_filter = settings.get('filter_news', False)

    def log(self, message):
        logging.info(message)
        self.log_queue.put(message)

    def update_ui(self, data):
        self.update_queue.put(data)

    def _establish_connection(self, max_attempts=5, delay_seconds=30):
        self.log("Tentando estabelecer conexão com a IQ Option...")
        for attempt in range(1, max_attempts + 1):
            if self.stop_event.is_set():
                self.log("Parada solicitada durante a tentativa de conexão.")
                return None
            self.log(f"Tentativa de conexão {attempt}/{max_attempts}...")
            iq_conn = IQOptionConnection(self.email, self.password)
            if iq_conn.connect():
                self.log("Conexão estabelecida com sucesso.")
                return iq_conn
            if attempt < max_attempts:
                self.log(f"Falha na conexão. Nova tentativa em {delay_seconds} segundos.")
                self.stop_event.wait(delay_seconds)
        self.log(f"ERRO CRÍTICO: Não foi possível conectar à IQ Option após {max_attempts} tentativas.")
        self.update_ui({'status': 'Erro de Conexão'})
        return None

    # <--- MUDANÇA: Lógica de carregamento de estratégias foi aprimorada --->
    def load_strategies(self):
        strategies = {}
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        strategy_folder = os.path.join(base_path, 'strategies')
        if not os.path.isdir(strategy_folder):
            self.log(f"ERRO: A pasta de estratégias '{strategy_folder}' não foi encontrada.")
            return strategies
            
        sys.path.insert(0, base_path)
        for filename in os.listdir(strategy_folder):
            # Procura por arquivos de estratégia que não sejam a versão melhorada para evitar duplicatas
            if filename.startswith('strategy_') and filename.endswith('.py') and 'improved' not in filename:
                module_name = f"strategies.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    
                    # Lógica de compatibilidade: Apenas carrega a função check_signal
                    if hasattr(module, 'check_signal'):
                        strategies[filename] = module.check_signal
                        self.log(f"Estratégia de FUNÇÃO '{filename}' carregada (modo de compatibilidade).")

                except ImportError as e:
                    self.log(f"ERRO: Falha ao carregar a estratégia '{module_name}': {e}")
        
        # Carrega a nova estratégia de CLASSE separadamente, passando as configurações
        try:
            from strategies.strategy_ema_rsi_fibo_improved import EmaRsiFiboStrategy
            # Instancia a classe com as configurações da GUI
            strategy_instance = EmaRsiFiboStrategy(self.settings)
            strategies['strategy_ema_rsi_fibo_improved.py'] = strategy_instance
            self.log("Estratégia de CLASSE 'EmaRsiFiboStrategy' carregada e configurada.")
        except ImportError:
            self.log("AVISO: A estratégia melhorada 'strategy_ema_rsi_fibo_improved.py' não foi encontrada.")
        
        sys.path.pop(0)
        return strategies


    def get_market_type(self):
        return 'OTC' if datetime.now().weekday() >= 5 else 'REGULAR'

    def find_active_assets(self, market_type, iq_conn):
        iq_conn.update_open_assets()
        active_assets = []
        self.log(f"--- MODO {market_type}: Buscando ativos ---")
        all_open_binary = iq_conn.open_binary_assets
        asset_list = self.PREFERRED_ASSETS if market_type == 'REGULAR' else self.OTC_ASSETS

        for asset in asset_list:
            if iq_conn.is_asset_available_for_trading(asset, 'binary'):
                active_assets.append({'name': asset, 'type': 'binary'})
                self.log(f"✓ Ativo Encontrado: {asset}")

        if not active_assets and market_type == 'REGULAR':
            self.log("Nenhum ativo REGULAR preferido encontrado. Buscando por OTC disponíveis...")
            for asset in self.OTC_ASSETS:
                 if iq_conn.is_asset_available_for_trading(asset, 'binary'):
                    active_assets.append({'name': asset, 'type': 'binary'})
                    self.log(f"✓ Fallback OTC: {asset}")
        
        return active_assets

    def run(self):
        self.log("Iniciando o núcleo do robô...")
        iq = self._establish_connection()
        if not iq:
            self.log("Encerrando o robô devido à falha na conexão."); self.update_ui({'status': 'Parado'}); return

        iq.api.change_balance(self.account_type)
        balance = iq.api.get_balance()
        if balance is None:
            self.log(f"ERRO: Saldo não encontrado."); self.update_ui({'status': 'Erro de Saldo'}); return

        self.update_ui({'balance': f"${balance:.2f}"}); self.log(f"Saldo inicial ({self.account_type}): ${balance:.2f}")
        
        risk_manager = RiskManagement(balance, self.settings)
        strategies = self.load_strategies()
        if not strategies:
            self.log("ERRO: Nenhuma estratégia carregada."); self.update_ui({'status': 'Erro de Estratégia'}); return

        news_checker = NewsFilter() if self.use_news_filter else None
        if self.use_news_filter: self.log("Filtro de notícias de alto impacto está ATIVADO.")

        self.update_ui({'status': 'Rodando'})
        while not self.stop_event.is_set():
            if risk_manager.check_stop_loss() or risk_manager.check_take_profit():
                status_msg = "Stop Loss" if risk_manager.check_stop_loss() else "Take Profit"
                self.log(f"{status_msg} atingido. Encerrando o dia."); self.update_ui({'status': f'{status_msg} Atingido'}); break

            market_type = self.get_market_type()
            active_assets = self.find_active_assets(market_type, iq)
            if not active_assets:
                self.log("Nenhum ativo operacional encontrado. Aguardando 1 minuto."); self.stop_event.wait(60); continue

            self.log(f"Monitorando: {[a['name'] for a in active_assets]}"); now = datetime.now()
            wait_seconds = 60 - now.second
            if wait_seconds > 0: self.stop_event.wait(wait_seconds)
            
            if self.stop_event.is_set(): break

            for asset_info in active_assets:
                if self.stop_event.is_set(): break
                asset_name = asset_info['name']
                
                if self.use_news_filter and news_checker and not news_checker.is_trading_safe(asset_name):
                    self.log(f"Análise para {asset_name} pulada devido a proximidade de notícia."); continue

                df_m1 = iq.get_candles(asset_name, self.TIMEFRAME, 200, time.time())
                if df_m1 is None or len(df_m1) < 150:
                    self.log(f"Dados insuficientes para {asset_name} em M1. Pulando."); continue

                current_candle_timestamp = df_m1.index[-1]
                if asset_name not in self.last_candle_times or current_candle_timestamp > self.last_candle_times.get(asset_name, 0):
                    self.last_candle_times[asset_name] = current_candle_timestamp
                    signal_found = False

                    for name, strategy_obj in strategies.items():
                        signal, info = None, {}
                        try:
                            # <--- MUDANÇA: Lida com ambos os tipos de estratégia (função ou classe) --->
                            if hasattr(strategy_obj, 'check_signal'): # É uma instância de classe
                                result = strategy_obj.check_signal(df_m1.copy())
                                if isinstance(result, dict):
                                    signal = result.get('signal')
                                    info = result.get('info', {})
                                else: # Mantém compatibilidade com a função wrapper
                                    signal = result
                            else: # É uma função simples
                                signal = strategy_obj(df_m1.copy())

                        except Exception as e: self.log(f"Erro na estratégia {name} para {asset_name}: {e}")

                        if signal:
                            stake = risk_manager.calculate_stake()
                            if stake <= 0: self.log("Valor de entrada é zero. Nenhuma ordem será aberta."); continue
                            
                            self.log(f"SINAL {signal} em {asset_name} por {name} | Entrada: ${stake:.2f}")
                            
                            # <--- MUDANÇA: Loga a informação de SL/TP se disponível --->
                            if info and 'stop_loss' in info and 'take_profit' in info:
                                self.log(f"  -> Info da Estratégia: SL: {info['stop_loss']:.5f} | TP: {info['take_profit']:.5f} (AVISO: SL/TP não aplicável para Opções Binárias)")
                            
                            # A execução continua sendo de Opção Binária
                            order_id = iq.buy_binary(stake, asset_name, signal.lower(), self.EXPIRATION_TIME)
                            if order_id:
                                self.update_ui({'status': f"Operando em {asset_name}"})
                                profit = iq.check_win(order_id)
                                risk_manager.register_trade_result(profit)
                                
                                result_msg = "WIN" if profit > 0 else "LOSS" if profit < 0 else "DRAW"
                                self.log(f"Resultado: {result_msg} | Valor: ${profit:.2f}. P/L Dia: ${risk_manager.daily_profit_loss:.2f}")
                                risk_manager.log_trade_to_csv(asset_name, signal, stake, result_msg, profit)

                                self.update_ui({
                                    'pnl': f"${risk_manager.daily_profit_loss:.2f}",
                                    'wins': risk_manager.wins, 'losses': risk_manager.losses,
                                    'assertiveness': f"{risk_manager.get_assertiveness():.2f}%",
                                    'balance': f"${risk_manager.current_balance:.2f}"
                                })
                                signal_found = True; self.stop_event.wait(5); break
                    if signal_found: break
        
        self.log(f"Histórico de operações salvo em: {risk_manager.csv_filename}")
        final_status = 'Parado'
        if risk_manager.check_stop_loss(): final_status = 'Stop Atingido'
        elif risk_manager.check_take_profit(): final_status = 'Meta Atingida'
        self.update_ui({'status': final_status})