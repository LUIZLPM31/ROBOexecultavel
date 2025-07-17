
import time
import logging
from datetime import datetime, timedelta
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
            if filename.startswith('strategy_') and filename.endswith('.py'):
                module_name = f"strategies.{filename[:-3]}"
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, 'check_signal'):
                        strategies[filename] = module.check_signal
                        self.log(f"Estratégia '{filename}' carregada.")
                except ImportError as e:
                    self.log(f"ERRO: Falha ao carregar a estratégia '{module_name}': {e}")
        sys.path.pop(0)
        return strategies

    def get_market_type(self):
        return 'OTC' if datetime.now().weekday() >= 5 else 'REGULAR'

    def find_active_assets(self, market_type, iq_conn):
        iq_conn.update_open_assets()
        active_assets = []
        self.log(f"--- MODO {market_type}: Buscando ativos ---")

        all_open_binary = iq_conn.open_binary_assets

        if market_type == 'REGULAR':
            for api_asset_name in all_open_binary.keys():
                if '-OTC' in api_asset_name:
                    continue

                for preferred_asset in self.PREFERRED_ASSETS:
                    if api_asset_name.startswith(preferred_asset):
                        is_tradable = iq_conn.is_asset_available_for_trading(api_asset_name, 'binary')
                        is_supported = iq_conn.is_asset_supported_by_library(preferred_asset)
                        
                        if is_tradable and is_supported:
                            active_assets.append({'name': api_asset_name, 'type': 'binary'})
                            self.log(f"✓ Ativo Encontrado: {api_asset_name} (Base p/ velas: {preferred_asset})")
                            break
        
        else: # market_type == 'OTC'
            for asset in self.OTC_ASSETS:
                if iq_conn.is_asset_available_for_trading(asset, 'binary') and iq_conn.is_asset_supported_by_library(asset):
                    active_assets.append({'name': asset, 'type': 'binary'})
                    self.log(f"✓ Ativo Encontrado: {asset}")

        if not active_assets and market_type == 'REGULAR':
            self.log("Nenhum ativo REGULAR preferido encontrado. PLANO C: Buscando por OTC disponíveis...")
            for asset in all_open_binary.keys():
                if '-OTC' in asset:
                    if iq_conn.is_asset_available_for_trading(asset, 'binary'):
                        active_assets.append({'name': asset, 'type': 'binary'})
                        self.log(f"✓ Fallback OTC: {asset} (Binary)")
                        if len(active_assets) >= 5: break

        return active_assets

    def run(self):
        self.log("Iniciando o núcleo do robô...")
        iq = IQOptionConnection(self.email, self.password)
        if not iq.connect():
            self.log("ERRO: Falha na conexão."); self.update_ui({'status': 'Erro de Conexão'}); return

        iq.api.change_balance(self.account_type)
        balance = iq.api.get_balance()
        if balance is None:
            self.log(f"ERRO: Saldo não encontrado."); self.update_ui({'status': 'Erro de Saldo'}); return

        self.update_ui({'balance': f"${balance:.2f}"}); self.log(f"Saldo inicial ({self.account_type}): ${balance:.2f}")
        
        risk_manager = RiskManagement(balance, self.settings)
        strategies = self.load_strategies()
        if not strategies:
            self.log("ERRO: Nenhuma estratégia carregada."); self.update_ui({'status': 'Erro de Estratégia'}); return

        news_checker = None
        if self.use_news_filter:
            news_checker = NewsFilter()
            self.log("Filtro de notícias de alto impacto está ATIVADO.")

        self.update_ui({'status': 'Rodando'})
        while not self.stop_event.is_set():
            if risk_manager.check_stop_loss() or risk_manager.check_take_profit():
                self.log(f"Meta de P/L atingida. Encerrando."); break

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
                
                if self.use_news_filter and news_checker:
                    if not news_checker.is_trading_safe(asset_name):
                        self.log(f"Análise para {asset_name} pulada devido a proximidade de notícia.")
                        continue

                df_m1 = iq.get_candles(asset_name, self.TIMEFRAME, 110, time.time())
                if df_m1 is None or len(df_m1) < 100:
                    self.log(f"Dados insuficientes para {asset_name} em M1. Pulando."); continue

                current_candle_timestamp = df_m1.index[-1]
                if asset_name not in self.last_candle_times or current_candle_timestamp > self.last_candle_times.get(asset_name, 0):
                    self.last_candle_times[asset_name] = current_candle_timestamp
                    signal_found = False

                    for name, strategy_func in strategies.items():
                        signal = None
                        try:
                            if 'df_m5' in strategy_func.__code__.co_varnames:
                                df_m5 = iq.get_candles(asset_name, 300, 50, time.time())
                                if df_m5 is not None: signal = strategy_func(df_m1.copy(), df_m5.copy())
                            else: signal = strategy_func(df_m1.copy())
                        except Exception as e: self.log(f"Erro na estratégia {name} para {asset_name}: {e}")

                        if signal:
                            stake = risk_manager.calculate_stake()
                            if stake <= 0: self.log("Valor de entrada é zero. Nenhuma ordem será aberta."); continue

                            soros_info = ""
                            if risk_manager.use_soros and risk_manager.soros_current_level > 0:
                                soros_info = f" (Soros Nível {risk_manager.soros_current_level})"
                            self.log(f"SINAL {signal} em {asset_name} por {name} | Entrada: ${stake:.2f}{soros_info}")
                            
                            order_id = iq.buy_binary(stake, asset_name, signal.lower(), self.EXPIRATION_TIME)
                            if order_id:
                                self.log(f"Ordem {order_id} enviada. Aguardando resultado...")
                                self.update_ui({'status': f"Operando em {asset_name}"})
                                profit = iq.check_win(order_id)
                                risk_manager.register_trade_result(profit)
                                result_msg = "WIN" if profit > 0 else "LOSS" if profit < 0 else "DRAW"
                                self.log(f"Resultado: {result_msg} | Valor: ${profit:.2f}. P/L Dia: ${risk_manager.daily_profit_loss:.2f}")
                                self.update_ui({'pnl': f"${risk_manager.daily_profit_loss:.2f}",'wins': risk_manager.wins,'losses': risk_manager.losses,'assertiveness': f"{risk_manager.get_assertiveness():.2f}%",'balance': f"${risk_manager.current_balance:.2f}"})
                                signal_found = True; self.stop_event.wait(5); break
                    if signal_found: break

        self.log("Núcleo do robô finalizado."); self.update_ui({'status': 'Parado'})