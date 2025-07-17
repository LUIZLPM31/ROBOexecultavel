# strategies/strategy_bollinger_rsi.py (Versão Final Corrigida)

import pandas as pd
import logging
import pandas_ta as ta

def check_signal(df_m1, df_m5=None):
    """Estratégia 1: Reversão com Bandas de Bollinger e RSI."""
    if df_m1.empty or len(df_m1) < 21:
        return None

    # --- CÁLCULO DOS INDICADORES ---
    df_m1.ta.bbands(close='close', length=20, std=2.5, append=True) # std 2.5 é o padrão
    df_m1.ta.rsi(close='close', length=4, append=True)

    # Nomes das colunas devem corresponder EXATAMENTE ao cálculo acima
    bb_lower_col = 'BBL_20_2.5'
    bb_upper_col = 'BBU_20_2.5'
    rsi_col = 'RSI_4'

    if not all([bb_lower_col in df_m1.columns, bb_upper_col in df_m1.columns, rsi_col in df_m1.columns]):
        logging.error("[Bollinger+RSI] Falha ao calcular indicadores.")
        return None

    open_price_current = df_m1["open"].iloc[-1]
    bb_lower_current = df_m1[bb_lower_col].iloc[-1]
    bb_upper_current = df_m1[bb_upper_col].iloc[-1]
    rsi_previous = df_m1[rsi_col].iloc[-2]

    logging.info(f"[DEBUG Bollinger+RSI] Abertura: {open_price_current:.5f} | RSI(-1): {rsi_previous:.2f} | B. Sup: {bb_upper_current:.5f} | B. Inf: {bb_lower_current:.5f}")

    signal = None
    
    # Condição de Compra (CALL) com RSI < 20
    is_below_band = open_price_current < bb_lower_current
    is_oversold = rsi_previous < 20 # Nível padrão de sobrevenda
    if is_below_band and is_oversold:
        signal = "CALL"
        logging.warning(f"SINAL DE COMPRA (CALL) DETECTADO! [Bollinger+RSI]")

    # Condição de Venda (PUT) com RSI > 80
    is_above_band = open_price_current > bb_upper_current
    is_overbought = rsi_previous > 80 # Nível padrão de sobrecompra
    if is_above_band and is_overbought:
        signal = "PUT"
        logging.warning(f"SINAL DE VENDA (PUT) DETECTADO! [Bollinger+RSI]")

    return signal