import pandas as pd
import logging
import pandas_ta as ta

def check_signal(df_m1, df_m5=None):
    """
    Estratégia Berman: Reversão com Bandas de Bollinger e SMA.
    """
    # A estratégia precisa de pelo menos 20 velas para os indicadores
    if df_m1.empty or len(df_m1) < 21:
        return None

    # --- Cálculo dos Indicadores ---
    try:
        df_m1.ta.bbands(close='close', length=20, std=2.0, append=True)
        df_m1.ta.sma(length=20, append=True)
    except Exception as e:
        logging.error(f"[Berman] Erro ao calcular indicadores: {e}")
        return None

    # Nomes das colunas geradas pelo pandas-ta
    bb_lower_col = 'BBL_20_2.0'
    bb_upper_col = 'BBU_20_2.0'
    sma_col = 'SMA_20'

    if not all(col in df_m1.columns for col in [bb_lower_col, bb_upper_col, sma_col]):
        logging.error("[Berman] Falha ao calcular indicadores. Colunas não encontradas.")
        return None

    # --- Coleta dos Dados para a Lógica ---
    # Vela atual (a última da lista)
    current_candle = df_m1.iloc[-1]
    open_price_current = current_candle['open']
    close_price_current = current_candle['close']
    sma_current = current_candle[sma_col]

    # Vela anterior (penúltima da lista)
    previous_candle = df_m1.iloc[-2]
    close_price_prev = previous_candle['close']
    bb_lower_prev = previous_candle[bb_lower_col]
    bb_upper_prev = previous_candle[bb_upper_col]
    
    logging.info(f"[DEBUG Berman] Fech. Anterior: {close_price_prev:.5f} | "
                 f"Abertura Atual: {open_price_current:.5f} | Fech. Atual: {close_price_current:.5f} | "
                 f"SMA Atual: {sma_current:.5f} | B. Sup: {bb_upper_prev:.5f} | B. Inf: {bb_lower_prev:.5f}")

    signal = None

    # --- Regras de Entrada ---
    
    # Condição de Compra (CALL)
    # 1. Vela anterior fechou abaixo da banda inferior.
    # 2. Vela atual abriu e fechou acima da SMA 20.
    if close_price_prev < bb_lower_prev and \
       open_price_current > sma_current and \
       close_price_current > sma_current:
        signal = "CALL"
        logging.warning(f"SINAL DE COMPRA (CALL) DETECTADO! [Estratégia Berman]")

    # Condição de Venda (PUT)
    # 1. Vela anterior fechou acima da banda superior.
    # 2. Vela atual abriu e fechou abaixo da SMA 20.
    if close_price_prev > bb_upper_prev and \
       open_price_current < sma_current and \
       close_price_current < sma_current:
        signal = "PUT"
        logging.warning(f"SINAL DE VENDA (PUT) DETECTADO! [Estratégia Berman]")

    return signal