# strategies/strategy_fibonacci_ema.py

"""
Este arquivo encapsula a classe FibonacciEMAStrategy para que seja compatível
com o sistema de carregamento de estratégias do bot.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict, Any
import logging

class FibonacciEMAStrategy:
    """
    Estratégia de Opções Binárias - Fibonacci EMA (1 Minuto)
    
    Combina EMA 100 para filtro de tendência com retração de Fibonacci
    para identificar pontos de entrada precisos.
    """
    
    def __init__(self):
        self.ema_period = 100
        self.fib_levels = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        self.entry_zone_min = 0.382  # 38.2%
        self.entry_zone_max = 0.618  # 61.8%
        self.last_fibonacci_zone = None
        self.zone_entry_count = {}
        
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula a Média Móvel Exponencial"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def find_swing_points(self, data: pd.DataFrame, lookback: int = 10) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Identifica pontos de máxima e mínima recentes para traçar Fibonacci
        
        Args:
            data: DataFrame com OHLC
            lookback: Períodos para trás para buscar pontos significativos
        
        Returns:
            Tuple com (ponto_alto, ponto_baixo)
        """
        if len(data) < lookback * 2:
            return None, None
            
        # Últimas velas para análise
        recent_data = data.tail(lookback * 2)
        
        # Encontrar máxima e mínima recentes
        high_idx = recent_data['high'].idxmax()
        low_idx = recent_data['low'].idxmin()
        
        high_point = {
            'price': recent_data.loc[high_idx, 'high'],
            'index': high_idx
        }
        
        low_point = {
            'price': recent_data.loc[low_idx, 'low'],
            'index': low_idx
        }
        
        return high_point, low_point
    
    def calculate_fibonacci_levels(self, high_point: Dict, low_point: Dict, trend_direction: str) -> Dict[str, float]:
        """
        Calcula os níveis de Fibonacci baseado na direção da tendência
        
        Args:
            high_point: Ponto de máxima
            low_point: Ponto de mínima
            trend_direction: 'up' ou 'down'
        
        Returns:
            Dict com os níveis de Fibonacci
        """
        if trend_direction == 'up':
            # Para tendência de alta: Fibonacci do baixo para o alto
            price_range = high_point['price'] - low_point['price']
            base_price = high_point['price']
            
            levels = {}
            for level in self.fib_levels:
                levels[f'{level:.1%}'] = base_price - (price_range * level)
                
        else:  # trend_direction == 'down'
            # Para tendência de baixa: Fibonacci do alto para o baixo
            price_range = high_point['price'] - low_point['price']
            base_price = low_point['price']
            
            levels = {}
            for level in self.fib_levels:
                levels[f'{level:.1%}'] = base_price + (price_range * level)
        
        return levels
    
    def is_in_fibonacci_zone(self, price: float, fib_levels: Dict[str, float]) -> bool:
        """Verifica se o preço está dentro da zona de entrada (38.2% - 61.8%)"""
        level_382 = fib_levels['38.2%']
        level_618 = fib_levels['61.8%']
        
        min_level = min(level_382, level_618)
        max_level = max(level_382, level_618)
        
        return min_level <= price <= max_level
    
    def get_trend_direction(self, current_price: float, ema_value: float) -> str:
        """
        Determina a direção da tendência baseada na EMA 100
        
        Returns:
            'up' se preço acima da EMA, 'down' se abaixo, 'sideways' se muito próximo
        """
        # Adicionado para evitar divisão por zero se ema_value for 0
        if ema_value == 0:
            return 'sideways'
            
        price_ema_diff = abs(current_price - ema_value) / ema_value
        
        # Se muito próximo da EMA (menos de 0.1%), considerar lateral
        if price_ema_diff < 0.001:
            return 'sideways'
        
        return 'up' if current_price > ema_value else 'down'
    
    def generate_signal(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Gera sinal de entrada baseado na estratégia Fibonacci EMA
        
        Args:
            data: DataFrame com colunas ['open', 'high', 'low', 'close', 'timestamp']
        
        Returns:
            Dict com informações do sinal
        """
        signal_info = {
            'signal': None,  # 'CALL', 'PUT' ou None
            'confidence': 0.0,
            'entry_price': None,
            'reasoning': '',
            'fibonacci_levels': None,
            'trend_direction': None
        }
        
        if len(data) < self.ema_period + 20:
            signal_info['reasoning'] = 'Dados insuficientes para análise'
            return signal_info
        
        # Calcular EMA 100
        data = data.copy()
        data['ema_100'] = self.calculate_ema(data['close'], self.ema_period)
        
        # Preço e EMA atuais
        current_price = data['close'].iloc[-1]
        current_ema = data['ema_100'].iloc[-1]
        
        # Determinar direção da tendência
        trend_direction = self.get_trend_direction(current_price, current_ema)
        signal_info['trend_direction'] = trend_direction
        
        if trend_direction == 'sideways':
            signal_info['reasoning'] = 'Preço muito próximo à EMA 100 - zona de indecisão'
            return signal_info
        
        # Encontrar pontos de swing para Fibonacci
        high_point, low_point = self.find_swing_points(data)
        
        if not high_point or not low_point or high_point['price'] == low_point['price']:
            signal_info['reasoning'] = 'Pontos de swing inválidos ou não encontrados'
            return signal_info
        
        # Calcular níveis de Fibonacci
        fib_levels = self.calculate_fibonacci_levels(high_point, low_point, trend_direction)
        signal_info['fibonacci_levels'] = fib_levels
        
        # Verificar se a vela atual (última vela fechada) está na zona de Fibonacci
        # Corrigido para usar a vela mais recente
        last_closed_price = data['close'].iloc[-1]
        is_in_zone = self.is_in_fibonacci_zone(last_closed_price, fib_levels)
        
        if not is_in_zone:
            signal_info['reasoning'] = f'Preço fora da zona de Fibonacci (38.2% - 61.8%)'
            return signal_info
        
        # Criar identificador único para esta zona de Fibonacci
        zone_id = f"{high_point['index']}_{low_point['index']}_{trend_direction}"
        
        # Verificar se já houve entrada nesta zona (gatilho único)
        if zone_id in self.zone_entry_count:
            signal_info['reasoning'] = 'Já houve entrada nesta zona de Fibonacci'
            return signal_info
        
        # Verificar se esta é a primeira vela a fechar na zona
        lookback_candles = min(3, len(data) - 1)
        was_in_zone_before = False
        
        for i in range(1, lookback_candles + 1):
            past_price = data['close'].iloc[-(i + 1)]
            if self.is_in_fibonacci_zone(past_price, fib_levels):
                was_in_zone_before = True
                break
        
        if was_in_zone_before:
            signal_info['reasoning'] = 'Não é a primeira vela a fechar na zona de Fibonacci'
            return signal_info
        
        # Validações adicionais para confirmar o setup
        confidence = self.calculate_signal_confidence(data, fib_levels, trend_direction)
        
        if confidence < 0.6:  # Confiança mínima de 60%
            signal_info['reasoning'] = f'Confiança baixa no setup: {confidence:.1%}'
            return signal_info
        
        # Gerar sinal baseado na tendência
        if trend_direction == 'up':
            signal_info['signal'] = 'CALL'
            signal_info['reasoning'] = 'CALL: Preço acima EMA 100, primeira vela na zona Fibonacci'
        elif trend_direction == 'down':
            signal_info['signal'] = 'PUT'
            signal_info['reasoning'] = 'PUT: Preço abaixo EMA 100, primeira vela na zona Fibonacci'
        
        signal_info['confidence'] = confidence
        signal_info['entry_price'] = current_price
        
        # Marcar esta zona como utilizada
        self.zone_entry_count[zone_id] = 1
        
        return signal_info
    
    def calculate_signal_confidence(self, data: pd.DataFrame, fib_levels: Dict[str, float], trend_direction: str) -> float:
        """
        Calcula a confiança no sinal baseado em múltiplos fatores
        
        Returns:
            Valor entre 0.0 e 1.0 representando a confiança
        """
        confidence = 0.5  # Base
        
        current_price = data['close'].iloc[-1]
        current_ema = data['ema_100'].iloc[-1]
        
        # Fator 1: Distância da EMA (quanto mais distante, melhor para a tendência)
        if current_ema > 0:
            ema_distance = abs(current_price - current_ema) / current_ema
            confidence += min(ema_distance * 10, 0.2)  # Máximo +0.2
        
        # Fator 2: Posição na zona de Fibonacci (mais próximo ao centro é melhor)
        level_382 = fib_levels['38.2%']
        level_618 = fib_levels['61.8%']
        zone_middle = (level_382 + level_618) / 2
        
        zone_range = abs(level_618 - level_382)
        if zone_range > 0:
            distance_from_center = abs(current_price - zone_middle) / zone_range
            confidence += (1 - distance_from_center) * 0.2  # Máximo +0.2
        
        # Fator 3: Consistência da tendência (últimas 5 velas)
        if len(data) >= 5:
            recent_closes = data['close'].tail(5)
            recent_emas = data['ema_100'].tail(5)
            
            trend_consistency = 0
            for close, ema in zip(recent_closes, recent_emas):
                if trend_direction == 'up' and close > ema:
                    trend_consistency += 1
                elif trend_direction == 'down' and close < ema:
                    trend_consistency += 1
            
            confidence += (trend_consistency / 5) * 0.1  # Máximo +0.1
        
        return min(confidence, 1.0)
    
    def reset_fibonacci_zones(self):
        """Reset do controle de zonas de Fibonacci (usar no início de nova sessão)"""
        self.zone_entry_count.clear()
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Retorna informações sobre o status atual da estratégia"""
        return {
            'fibonacci_zones_used': len(self.zone_entry_count),
            'ema_period': self.ema_period,
            'entry_zone': f'{self.entry_zone_min:.1%} - {self.entry_zone_max:.1%}',
            'strategy_name': 'Fibonacci EMA Strategy'
        }

# =============================================================================
# Bloco de Integração com o Robô
# =============================================================================

# Cria uma única instância da classe para manter o estado (zone_entry_count)
# entre as chamadas da função check_signal.
_strategy_instance = FibonacciEMAStrategy()

def check_signal(df_m1, df_m5=None):
    """
    Função wrapper que o bot_core irá chamar.
    Ela utiliza a instância da classe para gerar o sinal.
    """
    try:
        # Gera o dicionário de sinal completo a partir da classe
        signal_dict = _strategy_instance.generate_signal(df_m1.copy())
        
        # Extrai o sinal ('CALL', 'PUT' ou None) para retornar ao bot_core
        signal = signal_dict.get('signal')
        
        if signal:
            # Loga a razão da entrada para melhor depuração
            reason = signal_dict.get('reasoning', 'N/A')
            confidence = signal_dict.get('confidence', 0)
            logging.warning(
                f"SINAL {signal} DETECTADO! [Fibonacci EMA] | "
                f"Razão: {reason} | Confiança: {confidence:.1%}"
            )
            
        return signal
    except Exception as e:
        logging.error(f"[Fibonacci EMA] Erro ao gerar sinal: {e}")
        return None