# iq_option_connection.py - VERSÃO DE DIAGNÓSTICO

from iqoptionapi.stable_api import IQ_Option
import logging
import pandas as pd
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IQOptionConnection:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.api = None
        self.open_binary_assets = {}
        self.open_digital_assets = {}
        self.supported_assets = []

    def connect(self):
        logging.info("Tentando conectar à IQ Option...")
        self.api = IQ_Option(self.email, self.password)
        check, reason = self.api.connect()

        if check:
            logging.info("Conexão bem-sucedida!")
            self.supported_assets = self.api.get_all_ACTIVES_OPCODE()
            return True
        else:
            logging.error(f"Falha na conexão: {reason}")
            return False

    def update_open_assets(self):
        """
        Função modificada para diagnóstico.
        Ela registrará no log a estrutura de dados exata retornada pela API.
        """
        logging.info("--- DIAGNÓSTICO: ATUALIZANDO ATIVOS ---")
        try:
            all_assets = self.api.get_all_open_time()

            # --- INÍCIO DO BLOCO DE DIAGNÓSTICO 1 ---
            if not all_assets or not isinstance(all_assets, dict):
                logging.error("DIAGNÓSTICO CRÍTICO: A chamada get_all_open_time() retornou um resultado vazio ou em formato inesperado!")
                self.open_binary_assets = {}
                self.open_digital_assets = {}
                return

            logging.info(f"DIAGNÓSTICO: API retornou as seguintes categorias de ativos: {list(all_assets.keys())}")
            # --- FIM DO BLOCO DE DIAGNÓSTICO 1 ---
            
            binary_assets = all_assets.get('binary', {})
            turbo_assets = all_assets.get('turbo', {})

            self.open_binary_assets = {**binary_assets, **turbo_assets}
            self.open_digital_assets = all_assets.get('digital', {})
            
            if not self.open_binary_assets:
                logging.warning("DIAGNÓSTICO: Nenhum ativo foi encontrado nas categorias 'binary' ou 'turbo'.")
            else:
                # --- INÍCIO DO BLOCO DE DIAGNÓSTICO 2 ---
                logging.info(f"DIAGNÓSTICO: Encontrados {len(self.open_binary_assets)} ativos no total (binários + turbo).")
                # Mostra uma amostra dos primeiros 15 ativos encontrados para ver a nomenclatura
                sample_assets = list(self.open_binary_assets.keys())[:15]
                logging.info(f"DIAGNÓSTICO: Amostra de nomes de ativos encontrados: {sample_assets}")
                # --- FIM DO BLOCO DE DIAGNÓSTICO 2 ---

        except Exception as e:
            logging.error(f"DIAGNÓSTICO: Exceção ao obter a lista de ativos abertos: {e}", exc_info=True)


    def is_asset_available_for_trading(self, asset_name, option_type):
        assets = self.open_binary_assets if option_type == 'binary' else self.open_digital_assets
        return asset_name in assets and assets.get(asset_name, {}).get('open', False)

    def is_asset_supported_by_library(self, asset_name):
        return asset_name.upper() in self.supported_assets

    def get_candles(self, asset, interval, count, endtime):
        candles = self.api.get_candles(asset, interval, count, endtime)
        if not candles: return None
        df = pd.DataFrame(candles)
        df.rename(columns={'max': 'high', 'min': 'low'}, inplace=True)
        required_cols = ['open', 'high', 'low', 'close', 'volume', 'from']
        if not all(col in df.columns for col in required_cols): return None
        df['from'] = pd.to_datetime(df['from'], unit='s')
        df.set_index('from', inplace=True)
        return df

    def buy_binary(self, amount, asset, action, duration):
        logging.info(f"ORDEM BINÁRIA/TURBO: {action} em {asset} | Valor: ${amount:.2f}")
        status, order_id = self.api.buy(amount, asset, action, duration)
        return order_id if status else None

    def buy_digital(self, amount, asset, action, duration):
        logging.info(f"ORDEM DIGITAL: {action} em {asset} | Valor: ${amount:.2f}")
        status, order_id = self.api.buy_digital_spot(asset, amount, action, duration)
        return order_id if status else None

    def check_win(self, order_id):
        status, profit = self.api.check_win_v4(order_id)
        while status == 'pending':
            time.sleep(1)
            status, profit = self.api.check_win_v4(order_id)
        return profit if profit is not None else 0

    def get_balance(self):
        try:
            balance = self.api.get_balance()
            return balance
        except Exception as e:
            logging.error(f"Erro ao obter saldo: {e}")
            return None