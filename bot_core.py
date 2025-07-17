

import time
import logging
from datetime import datetime, timedelta
import importlib
import os
import sys

try:
    from iq_option_connection import IQOptionConnection
    from risk_management import RiskManagement
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
            # Tenta carregar do diretório atual como fallback
            strategy_folder = base_path 
            self.log(f"INFO: Pasta 'strategies' não encontrada. Procurando estratégias no diretório principal.")

        # Garante que o diretório das estratégias esteja no path
        sys.path.insert(0, os.path.dirname(strategy_folder))
        
        for filename in os.listdir(strategy_folder):
            if filename.startswith('strategy_') and filename.endswith('.py'):
                module_name = f"{os.path.basename(strategy_folder)}.{filename[:-3]}" if os.path.basename(strategy_folder) != '.' else filename[:-3]
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
        # O mercado OTC geralmente abre na sexta-feira à noite e fecha no domingo à noite.
        now = datetime.utcnow()
        # Sexta (4) 21:00 UTC até Domingo (6) 21:00 UTC
        is_friday_night = now.weekday() == 4 and now.hour >= 21
        is_saturday = now.weekday() == 5
        is_sunday_day = now.weekday() == 6 and now.hour < 21
        
        return 'OTC' if is_friday_night or is_saturday or is_sunday_day else 'REGULAR'


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
                # Para OTC, o nome do ativo para trading e para velas é o mesmo
                if iq_conn.is_asset_available_for_trading(asset, 'binary') and iq_conn.is_asset_supported_by_library(asset):
                    active_assets.append({'name': asset, 'type': 'binary'})
                    self.log(f"✓ Ativo Encontrado: {asset}")

        if not active_assets:
            self.log("Nenhum ativo preferido encontrado. Buscando por quaisquer ativos abertos (Plano B)...")
            # Fallback para qualquer ativo binário/turbo aberto
            for asset in all_open_binary.keys():
                 if iq_conn.is_asset_available_for_trading(asset, 'binary'):
                    base_asset_for_candles = asset.split('-')[0]
                    if iq_conn.is_asset_supported_by_library(base_asset_for_candles):
                        active_assets.append({'name': asset, 'type': 'binary'})
                        self.log(f"✓ Fallback: {asset} (Base p/ velas: {base_asset_for_candles})")
                        if len(active_assets) >= 5: break # Limita para não monitorar muitos

        return active_assets


    def run(self):
        self.log("Iniciando o núcleo do robô...")
        iq = IQOptionConnection(self.email, self.password)
        if not iq.connect():
            self.log("ERRO: Falha na conexão."); self.update_ui({'status': 'Erro de Conexão'}); return

        iq.api.change_balance(self.account_type)
        balance = iq.get_balance()
        if balance is None:
            self.log(f"ERRO: Saldo não encontrado na conta {self.account_type}. Verifique o tipo de conta."); self.update_ui({'status': 'Erro de Saldo'}); return

        self.update_ui({'balance': f"${balance:.2f}"}); self.log(f"Saldo inicial ({self.account_type}): ${balance:.2f}")
        
        risk_manager = RiskManagement(balance, self.settings)
        strategies = self.load_strategies()
        if not strategies:
            self.log("ERRO: Nenhuma estratégia carregada."); self.update_ui({'status': 'Erro de Estratégia'}); return

        self.update_ui({'status': 'Rodando'})
        while not self.stop_event.is_set():
            if risk_manager.check_stop_loss():
                self.log(f"STOP LOSS atingido. Encerrando."); break
            if risk_manager.check_take_profit():
                self.log(f"TAKE PROFIT atingido. Encerrando."); break

            market_type = self.get_market_type()
            active_assets = self.find_active_assets(market_type, iq)

            if not active_assets:
                self.log("Nenhum ativo operacional encontrado. Aguardando 1 minuto."); self.stop_event.wait(60); continue

            self.log(f"Monitorando: {[a['name'] for a in active_assets]}"); now = datetime.now()
            wait_seconds = 60 - now.second
            if wait_seconds > 0: self.stop_event.wait(wait_seconds)
            
            if self.stop_event.is_set(): break

            for asset_info in active_assets:
                asset_name = asset_info['name']
                candle_asset_name = asset_name.split('-')[0] if market_type == 'REGULAR' else asset_name

                if self.stop_event.is_set(): break
                
                df_m1 = iq.get_candles(candle_asset_name, self.TIMEFRAME, 110, time.time())
                if df_m1 is None or len(df_m1) < 100:
                    self.log(f"Dados insuficientes para {candle_asset_name} (M1). Pulando."); continue

                current_candle_timestamp = df_m1.index[-1]
                last_time = self.last_candle_times.get(asset_name, datetime.min)

                if current_candle_timestamp > last_time:
                    self.last_candle_times[asset_name] = current_candle_timestamp
                    signal_found = False

                    for name, strategy_func in strategies.items():
                        signal = None
                        try:
                            # Passa df_m1 e df_m5 (se necessário) para a estratégia
                            if 'df_m5' in strategy_func.__code__.co_varnames:
                                df_m5 = iq.get_candles(candle_asset_name, 300, 50, time.time())
                                if df_m5 is not None:
                                    signal = strategy_func(df_m1.copy(), df_m5=df_m5.copy())
                            else:
                                signal = strategy_func(df_m1.copy(), df_m5=None)
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
                                
                                # Informa o gerenciador de risco sobre o resultado para que ele lide com a lógica de Soros
                                risk_manager.register_trade_result(profit)
                                
                                result_msg = "WIN" if profit > 0 else "LOSS" if profit < 0 else "DRAW"
                                self.log(f"Resultado: {result_msg} | Valor: ${profit:.2f}. P/L Dia: ${risk_manager.daily_profit_loss:.2f}")
                                self.update_ui({
                                    'pnl': f"${risk_manager.daily_profit_loss:.2f}",
                                    'wins': risk_manager.wins,
                                    'losses': risk_manager.losses,
                                    'assertiveness': f"{risk_manager.get_assertiveness():.2f}%",
                                    'balance': f"${risk_manager.current_balance:.2f}"
                                })
                                signal_found = True
                                self.stop_event.wait(5) # Pequena pausa pós-operação
                                break 
                    if signal_found: break

        self.log("Núcleo do robô finalizado."); self.update_ui({'status': 'Parado'})