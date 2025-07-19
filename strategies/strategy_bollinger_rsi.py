# strategies/strategy_bollinger_rsi.py (Versão Modificada)

import pandas as pd
import logging
import pandas_ta as ta

def check_signal(df_m1, df_m5=None):
    """Estratégia 1: Reversão com Bandas de Bollinger, RSI e filtro de tendência EMA."""
    if df_m1.empty or len(df_m1) < 101: # Aumentado para garantir dados para a EMA(100)
        return None

    # --- CÁLCULO DOS INDICADORES ---
    df_m1.ta.bbands(close='close', length=20, std=2.5, append=True)
    df_m1.ta.rsi(close='close', length=4, append=True, col_names=('RSI_4',))
    df_m1.ta.ema(length=100, append=True, col_names=('EMA_100',)) # Adicionada EMA de 100

    # Nomes das colunas
    bb_lower_col = 'BBL_20_2.5'
    bb_upper_col = 'BBU_20_2.5'
    rsi_col = 'RSI_4'
    ema_col = 'EMA_100'

    if not all(col in df_m1.columns for col in [bb_lower_col, bb_upper_col, rsi_col, ema_col]):
        logging.error("[Bollinger+RSI] Falha ao calcular indicadores.")
        return None

    # Coleta de dados da vela
    open_price_current = df_m1["open"].iloc[-1]
    bb_lower_current = df_m1[bb_lower_col].iloc[-1]
    bb_upper_current = df_m1[bb_upper_col].iloc[-1]
    ema_100_current = df_m1[ema_col].iloc[-1]
    rsi_previous = df_m1[rsi_col].iloc[-2] # Usando a vela anterior para o RSI

    logging.info(f"[DEBUG Bollinger+RSI] Abertura: {open_price_current:.5f} | EMA: {ema_100_current:.5f} | RSI(-1): {rsi_previous:.2f}")

    signal = None
    
    # --- LÓGICA DE SINAL ---

    # Condição de Compra (CALL)
    is_above_ema = open_price_current > ema_100_current # Filtro de tendência de alta
    is_below_band = open_price_current < bb_lower_current
    is_oversold = rsi_previous < 30 # Nível de sobrevenda ajustado para 30
    
    if is_above_ema and is_below_band and is_oversold:
        signal = "CALL"
        logging.warning(f"SINAL DE COMPRA (CALL) DETECTADO! [Bollinger+RSI]")

    # Condição de Venda (PUT)
    is_below_ema = open_price_current < ema_100_current # Filtro de tendência de baixa
    is_above_band = open_price_current > bb_upper_current
    is_overbought = rsi_previous > 70 # Nível de sobrecompra ajustado para 70
    
    if is_below_ema and is_above_band and is_overbought:
        signal = "PUT"
        logging.warning(f"SINAL DE VENDA (PUT) DETECTADO! [Bollinger+RSI]")

    return signal