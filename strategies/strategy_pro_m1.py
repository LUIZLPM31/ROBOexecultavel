import pandas as pd
import logging
import pandas_ta as ta

def check_signal(df_m1, df_m5):
    """
    Estratégia profissional para M1 com confirmação em M5.
    Combina Volume, Suporte/Resistência (S/R) e Médias Móveis.
    """
    if df_m1.empty or len(df_m1) < 25 or df_m5.empty or len(df_m5) < 25:
        return None

    # --- Análise e Indicadores em M1 ---
    df_m1.ta.ema(length=9, append=True)
    df_m1['volume_ema'] = df_m1['volume'].ewm(span=5, adjust=False).mean()

    # Simplificação de S/R: usando os últimos 10 candles
    last_10_candles = df_m1.tail(10)
    resistance = last_10_candles['high'].max()
    support = last_10_candles['low'].min()

    # Dados da vela atual (a última da lista)
    current_candle = df_m1.iloc[-1]
    open_price = current_candle['open']
    close_price = current_candle['close']
    high_price = current_candle['high']
    low_price = current_candle['low']
    current_volume = current_candle['volume']
    
    # Dados da vela anterior
    previous_candle = df_m1.iloc[-2]
    previous_volume = previous_candle['volume']
    previous_ema9 = previous_candle['EMA_9']
    
    # --- Análise e Indicadores em M5 (para tendência) ---
    df_m5.ta.ema(length=9, append=True, col_names=('EMA_9_M5',))
    df_m5.ta.ema(length=25, append=True, col_names=('EMA_25_M5',))
    
    m5_ema9 = df_m5['EMA_9_M5'].iloc[-1]
    m5_ema25 = df_m5['EMA_25_M5'].iloc[-1]
    
    m5_trend_is_up = m5_ema9 > m5_ema25
    m5_trend_is_down = m5_ema9 < m5_ema25

    logging.info(f"[DEBUG Pro M1] Preço: {close_price:.5f} | EMA9(M1): {previous_ema9:.5f} | "
                 f"Volume: {current_volume:.0f} | Tendência M5: {'Alta' if m5_trend_is_up else 'Baixa'}")

    signal = None

    # --- Regras de Entrada para CALL (Alta) ---
    if m5_trend_is_up: # Filtro: Só entra em CALL se a tendência em M5 for de alta
        # 1. Vela verde fecha acima da EMA 9
        candle_closed_above_ema = close_price > previous_ema9 and close_price > open_price
        # 2. Volume crescente
        increasing_volume = current_volume > previous_volume * 1.1 # Volume 10% maior que o anterior
        # 3. Rompimento de resistência
        breakout_resistance = close_price > resistance

        if candle_closed_above_ema and increasing_volume and breakout_resistance:
            signal = "CALL"
            logging.warning(f"SINAL DE COMPRA (CALL) DETECTADO! [Pro M1]")

    # --- Regras de Entrada para PUT (Baixa) ---
    if m5_trend_is_down: # Filtro: Só entra em PUT se a tendência em M5 for de baixa
        # 1. Vela vermelha fecha abaixo da EMA 9
        candle_closed_below_ema = close_price < previous_ema9 and close_price < open_price
        # 2. Volume crescente
        increasing_volume = current_volume > previous_volume * 1.1
        # 3. Quebra de suporte
        breakdown_support = close_price < support
        
        if candle_closed_below_ema and increasing_volume and breakdown_support:
            signal = "PUT"
            logging.warning(f"SINAL DE VENDA (PUT) DETECTADO! [Pro M1]")

    return signal