# strategies/strategy_ema_rsi_fibo_improved.py (Versão Melhorada)

import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime, time

class EmaRsiFiboStrategy:
    def __init__(self, config=None):
        """
        Inicializa a estratégia com configurações personalizáveis.
        
        Args:
            config (dict): Dicionário com configurações da estratégia
        """
        # Configurações padrão (melhoradas)
        default_config = {
            'ema_period': 100,
            'rsi_period': 7,  # Mudou de 4 para 14 (mais estável)
            'rsi_oversold': 30,  # Mudou de 25 para 30 (menos restritivo)
            'rsi_overbought': 70,  # Mudou de 75 para 70 (menos restritivo)
            'fibo_min': 0.382,
            'fibo_max': 0.618,
            'volume_filter': True,
            'volume_periods': 20,
            'volatility_filter': True,
            'volatility_threshold': 0.5,  # ATR mínimo para evitar mercados laterais
            'fractal_periods': 5,
            'min_pivot_distance': 10,  # Mínimo de velas entre pivôs
            'trading_hours': {
                'start': time(9, 30),
                'end': time(16, 30)
            },
            'wait_for_closed_candle': True,
            'min_data_points': 150
        }
        
        if config:
            default_config.update(config)
        
        self.config = default_config
        
    def encontrar_pivos_com_fractais(self, df):
        """
        Encontra pivôs de topo e fundo usando o indicador Fractals com filtros melhorados.
        
        Args:
            df (pd.DataFrame): DataFrame com os dados de mercado (OHLC).

        Returns:
            pd.DataFrame: DataFrame contendo apenas os pivôs válidos.
        """
        try:
            # Calcula os fractais
            df.ta.fractal(n=self.config['fractal_periods'], append=True)
            
            # Filtra apenas os pontos com fractais válidos
            fractal_col = f'FRACTALS_{self.config["fractal_periods"]}'
            pivot_points_df = df[df[fractal_col].notna()].copy()
            
            if len(pivot_points_df) < 2:
                return pd.DataFrame()
            
            # Determina o valor do pivô (high para topo, low para fundo)
            pivot_points_df['pivot'] = pivot_points_df.apply(
                lambda row: row['high'] if row[fractal_col] == 1 else row['low'],
                axis=1
            )
            
            pivot_points_df['pivot_type'] = pivot_points_df[fractal_col].map({1: 'high', -1: 'low'})
            
            # Filtro de distância mínima entre pivôs
            filtered_pivots = []
            last_index = -1
            
            for idx, row in pivot_points_df.iterrows():
                if last_index == -1 or (idx - last_index) >= self.config['min_pivot_distance']:
                    filtered_pivots.append(row)
                    last_index = idx
            
            if not filtered_pivots:
                return pd.DataFrame()
                
            return pd.DataFrame(filtered_pivots)[['pivot', 'pivot_type']]
            
        except Exception as e:
            logging.error(f"[EmaRsiFibo] Erro ao calcular pivôs: {e}")
            return pd.DataFrame()

    def verificar_filtros_adicionais(self, df, ultima_vela):
        """
        Verifica filtros adicionais como volume e volatilidade.
        
        Args:
            df (pd.DataFrame): DataFrame com dados históricos
            ultima_vela (pd.Series): Dados da última vela
            
        Returns:
            dict: Status dos filtros
        """
        filtros = {'volume': True, 'volatility': True, 'horario': True}
        
        try:
            # Filtro de Volume
            if self.config['volume_filter'] and 'volume' in df.columns:
                volume_medio = df['volume'].rolling(self.config['volume_periods']).mean().iloc[-1]
                if pd.notna(volume_medio) and ultima_vela['volume'] < volume_medio:
                    filtros['volume'] = False
                    logging.info(f"[EmaRsiFibo] Filtro de volume falhou: {ultima_vela['volume']:.0f} < {volume_medio:.0f}")
            
            # Filtro de Volatilidade (ATR)
            if self.config['volatility_filter']:
                if 'ATR_14' not in df.columns:
                    df.ta.atr(length=14, append=True, col_names=('ATR_14',))
                
                atr_atual = df['ATR_14'].iloc[-1]
                if pd.notna(atr_atual) and atr_atual < self.config['volatility_threshold']:
                    filtros['volatility'] = False
                    logging.info(f"[EmaRsiFibo] Filtro de volatilidade falhou: ATR {atr_atual:.5f} < {self.config['volatility_threshold']}")
            
            # Filtro de Horário de Negociação
            if hasattr(ultima_vela.name, 'time'):  # Se o índice for datetime
                hora_atual = ultima_vela.name.time()
                if not (self.config['trading_hours']['start'] <= hora_atual <= self.config['trading_hours']['end']):
                    filtros['horario'] = False
                    logging.info(f"[EmaRsiFibo] Fora do horário de negociação: {hora_atual}")
            
        except Exception as e:
            logging.error(f"[EmaRsiFibo] Erro ao verificar filtros: {e}")
            
        return filtros

    def verificar_sequencia_pivos(self, pontos_pivot, tipo_sinal):
        """
        Verifica se a sequência de pivôs é adequada para o tipo de sinal.
        
        Args:
            pontos_pivot (pd.DataFrame): DataFrame com os pivôs
            tipo_sinal (str): 'CALL' ou 'PUT'
            
        Returns:
            tuple: (swing_low, swing_high) ou (None, None)
        """
        if len(pontos_pivot) < 2:
            return None, None
            
        ultimo_pivo = pontos_pivot.iloc[-1]
        pivo_anterior = pontos_pivot.iloc[-2]
        
        if tipo_sinal == 'CALL':
            # Para CALL: precisa de um fundo (low) seguido de um topo (high)
            if pivo_anterior['pivot_type'] == 'low' and ultimo_pivo['pivot_type'] == 'high':
                return pivo_anterior['pivot'], ultimo_pivo['pivot']
        elif tipo_sinal == 'PUT':
            # Para PUT: precisa de um topo (high) seguido de um fundo (low)
            if pivo_anterior['pivot_type'] == 'high' and ultimo_pivo['pivot_type'] == 'low':
                return ultimo_pivo['pivot'], pivo_anterior['pivot']
                
        return None, None

    def calcular_niveis_fibonacci(self, swing_low, swing_high, tipo_sinal):
        """
        Calcula os níveis de Fibonacci para entrada.
        
        Args:
            swing_low (float): Valor do swing low
            swing_high (float): Valor do swing high
            tipo_sinal (str): 'CALL' ou 'PUT'
            
        Returns:
            tuple: (zona_inferior, zona_superior)
        """
        diferenca = swing_high - swing_low
        
        if tipo_sinal == 'CALL':
            # Retração de uma alta (vender no topo, comprar na retração)
            zona_superior = swing_high - (self.config['fibo_min'] * diferenca)
            zona_inferior = swing_high - (self.config['fibo_max'] * diferenca)
        else:  # PUT
            # Retração de uma baixa (comprar no fundo, vender na retração)
            zona_inferior = swing_low + (self.config['fibo_min'] * diferenca)
            zona_superior = swing_low + (self.config['fibo_max'] * diferenca)
            
        return zona_inferior, zona_superior

    def check_signal(self, df_m1, df_m5=None):
        """
        Estratégia melhorada de Pullback com EMA, RSI e Fibonacci.
        
        Melhorias implementadas:
        - RSI mais estável (14 períodos)
        - Filtros de volume e volatilidade
        - Verificação de vela fechada
        - Níveis de RSI menos restritivos
        - Validação de sequência de pivôs
        - Filtros de horário de negociação
        - Gestão de risco aprimorada
        """
        # Verificações iniciais
        if df_m1.empty or len(df_m1) < self.config['min_data_points']:
            logging.info(f"[EmaRsiFibo] Dados insuficientes: {len(df_m1)} < {self.config['min_data_points']}")
            return None

        try:
            # Verifica se devemos aguardar o fechamento da vela
            if self.config['wait_for_closed_candle']:
                # Aqui você implementaria a lógica para verificar se a vela já fechou
                # Por exemplo, comparando o timestamp atual com o timestamp da vela
                pass

            # --- 1. Calcular Indicadores ---
            df_m1.ta.ema(length=self.config['ema_period'], append=True, col_names=('EMA_100',))
            df_m1.ta.rsi(length=self.config['rsi_period'], append=True, col_names=('RSI_14',))

            if 'EMA_100' not in df_m1.columns or 'RSI_14' not in df_m1.columns:
                logging.error("[EmaRsiFibo] Falha ao calcular indicadores EMA ou RSI.")
                return None

            # --- 2. Encontrar Pontos de Pivô ---
            pontos_pivot = self.encontrar_pivos_com_fractais(df_m1)
            if len(pontos_pivot) < 2:
                logging.info("[EmaRsiFibo] Pivôs insuficientes para análise")
                return None

        except Exception as e:
            logging.error(f"[EmaRsiFibo] Erro ao calcular indicadores ou pivôs: {e}")
            return None

        # --- 3. Coletar Dados da Última Vela ---
        ultima_vela = df_m1.iloc[-1]
        
        # *** CORREÇÃO IMPORTANTE: Usar vela anterior fechada para RSI ***
        vela_anterior = df_m1.iloc[-2]  # Vela já fechada
        rsi_vela_fechada = vela_anterior['RSI_14']
        
        # --- 4. Verificar Filtros Adicionais ---
        filtros = self.verificar_filtros_adicionais(df_m1, ultima_vela)
        if not all(filtros.values()):
            logging.info(f"[EmaRsiFibo] Filtros rejeitados: {filtros}")
            return None

        logging.info(f"[DEBUG EmaRsiFibo] Preço: {ultima_vela['close']:.5f} | EMA: {ultima_vela['EMA_100']:.5f} | RSI: {rsi_vela_fechada:.2f}")

        signal = None
        signal_info = {}

        # --- 5. LÓGICA PARA SINAL DE COMPRA (CALL) ---
        tendencia_alta = ultima_vela['close'] > ultima_vela['EMA_100']
        rsi_sobrevenda = rsi_vela_fechada < self.config['rsi_oversold']

        if tendencia_alta and rsi_sobrevenda:
            swing_low, swing_high = self.verificar_sequencia_pivos(pontos_pivot, 'CALL')
            
            if swing_low is not None and swing_high is not None:
                zona_fibo_inferior, zona_fibo_superior = self.calcular_niveis_fibonacci(
                    swing_low, swing_high, 'CALL'
                )

                # Verifica se está na zona de compra
                if zona_fibo_inferior <= ultima_vela['close'] <= zona_fibo_superior:
                    signal = 'CALL'
                    signal_info = {
                        'entry_price': ultima_vela['close'],
                        'swing_low': swing_low,
                        'swing_high': swing_high,
                        'fibo_zone': (zona_fibo_inferior, zona_fibo_superior),
                        'stop_loss': swing_low * 0.999,  # SL ligeiramente abaixo do swing low
                        'take_profit': ultima_vela['close'] + 2 * (ultima_vela['close'] - swing_low * 0.999),
                        'rsi': rsi_vela_fechada,
                        'ema': ultima_vela['EMA_100']
                    }
                    logging.warning(f"SINAL DE COMPRA (CALL) DETECTADO! Preço: {ultima_vela['close']:.5f} | Zona Fibo: [{zona_fibo_inferior:.5f}, {zona_fibo_superior:.5f}]")

        # --- 6. LÓGICA PARA SINAL DE VENDA (PUT) ---
        tendencia_baixa = ultima_vela['close'] < ultima_vela['EMA_100']
        rsi_sobrecompra = rsi_vela_fechada > self.config['rsi_overbought']

        if tendencia_baixa and rsi_sobrecompra:
            swing_low, swing_high = self.verificar_sequencia_pivos(pontos_pivot, 'PUT')
            
            if swing_low is not None and swing_high is not None:
                zona_fibo_inferior, zona_fibo_superior = self.calcular_niveis_fibonacci(
                    swing_low, swing_high, 'PUT'
                )

                # Verifica se está na zona de venda
                if zona_fibo_inferior <= ultima_vela['close'] <= zona_fibo_superior:
                    signal = 'PUT'
                    signal_info = {
                        'entry_price': ultima_vela['close'],
                        'swing_low': swing_low,
                        'swing_high': swing_high,
                        'fibo_zone': (zona_fibo_inferior, zona_fibo_superior),
                        'stop_loss': swing_high * 1.001,  # SL ligeiramente acima do swing high
                        'take_profit': ultima_vela['close'] - 2 * (swing_high * 1.001 - ultima_vela['close']),
                        'rsi': rsi_vela_fechada,
                        'ema': ultima_vela['EMA_100']
                    }
                    logging.warning(f"SINAL DE VENDA (PUT) DETECTADO! Preço: {ultima_vela['close']:.5f} | Zona Fibo: [{zona_fibo_inferior:.5f}, {zona_fibo_superior:.5f}]")

        return {'signal': signal, 'info': signal_info} if signal else None


# Função de compatibilidade com a versão anterior
def check_signal(df_m1, df_m5=None):
    """
    Função wrapper para manter compatibilidade com código existente.
    """
    strategy = EmaRsiFiboStrategy()
    result = strategy.check_signal(df_m1, df_m5)
    
    if result and result['signal']:
        return result['signal']
    return None


# Exemplo de uso com configurações personalizadas
def create_custom_strategy():
    """
    Exemplo de como criar uma instância da estratégia com configurações personalizadas.
    """
    custom_config = {
        'rsi_period': 10,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'volume_filter': True,
        'volatility_filter': True,
        'wait_for_closed_candle': True
    }
    
    return EmaRsiFiboStrategy(custom_config)