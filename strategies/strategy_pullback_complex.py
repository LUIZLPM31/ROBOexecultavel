import pandas as pd
import pandas_ta as ta  # Alterado de 'ta' para 'pandas_ta'
from typing import Dict, Optional
from datetime import datetime
import logging

class PullbackStrategy:
    """
    Estratégia de Pullback para Opções Binárias - Gráfico 1 minuto
    
    Lógica:
    - Identifica tendência principal usando EMA 20 e 50
    - Detecta pullbacks usando RSI e Estocástico
    - Confirma entrada com volume e padrão de candlestick
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'ema_fast': 20,
            'ema_slow': 50,
            'rsi_period': 14,
            'stoch_k': 14,
            'stoch_d': 3,
            'volume_threshold': 1.2,  # Volume 20% acima da média de 20 períodos
            'min_pullback_size': 0.0003, # Pullback mínimo (ajustado para ser uma fração do preço)
            'max_pullback_size': 0.0080, # Pullback máximo
            'time_between_signals_seconds': 300, # 5 minutos entre sinais
        }
        
        self.last_signal_time = None
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos os indicadores necessários usando pandas_ta"""
        
        # EMAs
        df.ta.ema(length=self.config['ema_fast'], append=True, col_names=(f'ema_{self.config["ema_fast"]}',))
        df.ta.ema(length=self.config['ema_slow'], append=True, col_names=(f'ema_{self.config["ema_slow"]}',))
        
        # RSI
        df.ta.rsi(length=self.config['rsi_period'], append=True, col_names=(f'rsi_{self.config["rsi_period"]}',))
        
        # Estocástico
        stoch = df.ta.stoch(k=self.config['stoch_k'], d=self.config['stoch_d'], append=True)
        
        # Volume
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Padrões de candlestick
        df['body_size'] = abs(df['close'] - df['open'])
        df['total_range'] = df['high'] - df['low']
        
        return df
    
    def identify_trend(self, df: pd.DataFrame) -> str:
        """Identifica a tendência principal na última vela"""
        ema_fast_col = f'ema_{self.config["ema_fast"]}'
        ema_slow_col = f'ema_{self.config["ema_slow"]}'
        
        ema_fast = df[ema_fast_col].iloc[-1]
        ema_slow = df[ema_slow_col].iloc[-1]
        price = df['close'].iloc[-1]
        
        # Confirma com inclinação da EMA rápida
        ema_fast_prev = df[ema_fast_col].iloc[-6:-1].mean()
        
        if ema_fast > ema_slow and price > ema_fast and ema_fast > ema_fast_prev:
            return 'uptrend'
        elif ema_fast < ema_slow and price < ema_fast and ema_fast < ema_fast_prev:
            return 'downtrend'
        
        return 'neutral'
    
    def detect_pullback(self, df: pd.DataFrame, trend: str) -> Dict:
        """Detecta pullbacks válidos na última vela"""
        current_price = df['close'].iloc[-1]
        rsi_col = f'rsi_{self.config["rsi_period"]}'
        stoch_k_col = f'STOCHk_{self.config["stoch_k"]}_{self.config["stoch_d"]}_3'

        rsi = df[rsi_col].iloc[-1]
        stoch_k = df[stoch_k_col].iloc[-1]
        
        pullback_info = {'valid': False}
        
        if trend == 'uptrend':
            high_5_bars = df['high'].iloc[-6:-1].max()
            pullback_size = (high_5_bars - current_price)
            
            if self.config['min_pullback_size'] <= pullback_size <= self.config['max_pullback_size'] and rsi < 50 and stoch_k < 50:
                pullback_info = {'valid': True, 'direction': 'CALL'}
        
        elif trend == 'downtrend':
            low_5_bars = df['low'].iloc[-6:-1].min()
            pullback_size = (current_price - low_5_bars)
            
            if self.config['min_pullback_size'] <= pullback_size <= self.config['max_pullback_size'] and rsi > 50 and stoch_k > 50:
                pullback_info = {'valid': True, 'direction': 'PUT'}
        
        return pullback_info
    
    def confirm_entry(self, df: pd.DataFrame) -> bool:
        """Confirma a entrada com base em volume e padrão de vela na última vela"""
        volume_ok = df['volume_ratio'].iloc[-1] > self.config['volume_threshold']
        
        total_range = df['total_range'].iloc[-1]
        body_size = df['body_size'].iloc[-1]
        body_ratio = body_size / total_range if total_range > 0 else 0
        candle_ok = body_ratio > 0.6
        
        time_ok = True
        if self.last_signal_time:
            time_diff = datetime.now() - self.last_signal_time
            time_ok = time_diff.total_seconds() > self.config['time_between_signals_seconds']
        
        return volume_ok and candle_ok and time_ok
        
    def generate_signal(self, df: pd.DataFrame) -> Optional[str]:
        """Gera o sinal final ('CALL' ou 'PUT') para o robô"""
        if len(df) < self.config['ema_slow']:
            return None
        
        trend = self.identify_trend(df)
        if trend == 'neutral':
            return None
            
        pullback_info = self.detect_pullback(df, trend)
        if not pullback_info['valid']:
            return None
            
        if not self.confirm_entry(df):
            return None
            
        # Se todas as condições foram atendidas, retorna a direção e atualiza o tempo
        self.last_signal_time = datetime.now()
        return pullback_info.get('direction')


# =============================================================================
# Bloco de Integração com o Robô
# =============================================================================

# Cria uma única instância da classe para manter o estado (last_signal_time)
_strategy_instance = PullbackStrategy()

def check_signal(df_m1, df_m5=None):
    """
    Função wrapper que o bot_core irá chamar.
    Ela utiliza a instância da classe para gerar o sinal.
    """
    try:
        # 1. Calcula os indicadores necessários
        data_with_indicators = _strategy_instance.calculate_indicators(df_m1.copy())
        
        # 2. Gera o sinal
        signal = _strategy_instance.generate_signal(data_with_indicators)
        
        if signal:
            logging.warning(f"SINAL {signal} DETECTADO! [Pullback Complexo]")
            
        return signal
        
    except Exception as e:
        logging.error(f"[Pullback Complexo] Erro ao analisar sinal: {e}")
        return None