import pandas as pd
import pandas_ta as ta
import logging

# --- Parâmetros da Estratégia ---
EMA_PERIOD = 100
RSI_PERIOD = 14
FIB_LOW = 0.382
FIB_HIGH = 0.618

# --- Funções Auxiliares ---

def _manual_fractal(df):
    """
    Calcula manualmente o indicador Fractal para identificar topos e fundos.
    Isso garante que a estratégia funcione independentemente da versão da biblioteca.
    """
    df['FRACTALS_5_high'] = None
    df['FRACTALS_5_low'] = None
    for i in range(2, len(df) - 2):
        is_high_fractal = (df['high'].iloc[i] > df['high'].iloc[i-2] and df['high'].iloc[i] > df['high'].iloc[i-1] and
                           df['high'].iloc[i] > df['high'].iloc[i+1] and df['high'].iloc[i] > df['high'].iloc[i+2])
        if is_high_fractal:
            df.loc[df.index[i], 'FRACTALS_5_high'] = df['high'].iloc[i]

        is_low_fractal = (df['low'].iloc[i] < df['low'].iloc[i-2] and df['low'].iloc[i] < df['low'].iloc[i-1] and
                          df['low'].iloc[i] < df['low'].iloc[i+1] and df['low'].iloc[i] < df['low'].iloc[i+2])
        if is_low_fractal:
            df.loc[df.index[i], 'FRACTALS_5_low'] = df['low'].iloc[i]
    return df

def _find_last_swing(df, trend_type):
    """
    Encontra o último swing de alta (low -> high) ou de baixa (high -> low) usando fractais.
    """
    fractal_highs = df[df['FRACTALS_5_high'].notna()]
    fractal_lows = df[df['FRACTALS_5_low'].notna()]
    
    if trend_type == 'bullish':
        if len(fractal_lows) < 1 or len(fractal_highs) < 1: return None, None
        last_high_time = fractal_highs.index[-1]
        relevant_lows = fractal_lows[fractal_lows.index < last_high_time]
        if relevant_lows.empty: return None, None
        last_low_time = relevant_lows.index[-1]
        return df.loc[last_low_time, 'low'], df.loc[last_high_time, 'high']

    elif trend_type == 'bearish':
        if len(fractal_lows) < 1 or len(fractal_highs) < 1: return None, None
        last_low_time = fractal_lows.index[-1]
        relevant_highs = fractal_highs[fractal_highs.index < last_low_time]
        if relevant_highs.empty: return None, None
        last_high_time = relevant_highs.index[-1]
        return df.loc[last_low_time, 'low'], df.loc[last_high_time, 'high']
        
    return None, None

def _calculate_fib(swing_high, swing_low):
    """
    Calcula os níveis de Fibonacci para um movimento de preço.
    """
    if swing_high is None or swing_low is None or swing_high == swing_low:
        return None
    diff = swing_high - swing_low
    return {
        'bullish_38_2': swing_high - FIB_LOW * diff,
        'bullish_61_8': swing_high - FIB_HIGH * diff,
        'bearish_38_2': swing_low + FIB_LOW * diff,
        'bearish_61_8': swing_low + FIB_HIGH * diff,
    }

# --- Função Principal da Estratégia ---

def check_signal(df_m1, df_m5=None):
    """
    Estratégia aprimorada que combina EMA, Fibonacci em swings de Fractais e RSI.
    """
    try:
        if len(df_m1) < EMA_PERIOD:
            return None

        df = df_m1.copy()
        
        # --- 1. Calcular Indicadores ---
        df.ta.ema(length=EMA_PERIOD, append=True, col_names=('EMA_100',))
        df.ta.rsi(length=RSI_PERIOD, append=True, col_names=('RSI_14',))
        df = _manual_fractal(df) # Usa nossa função manual de fractal

        # --- 2. Coletar Dados da Vela Atual ---
        current_close = df['close'].iloc[-1]
        current_ema = df['EMA_100'].iloc[-1]
        current_rsi = df['RSI_14'].iloc[-1]
        
        if pd.isna(current_ema) or pd.isna(current_rsi):
            return None

        # --- 3. Determinar a Tendência e Encontrar o Swing Relevante ---
        trend = 'bullish' if current_close > current_ema else 'bearish'
        swing_low, swing_high = _find_last_swing(df, trend)
        
        if swing_low is None or swing_high is None:
            return None # Não encontrou um swing válido para traçar Fibonacci

        # --- 4. Calcular Fibonacci com base no Swing ---
        fib_levels = _calculate_fib(swing_high, swing_low)
        if fib_levels is None:
            return None

        # --- 5. Verificar Condições de Entrada ---
        sinal = None
        if trend == 'bullish':
            in_fib_zone = fib_levels['bullish_61_8'] <= current_close <= fib_levels['bullish_38_2']
            rsi_ok = current_rsi < 60
            if in_fib_zone and rsi_ok:
                sinal = 'CALL'
                logging.warning(f"SINAL DE COMPRA (CALL) DETECTADO! [Fibo Fractal RSI] | Pullback em tendência de alta. RSI: {current_rsi:.2f}")

        elif trend == 'bearish':
            in_fib_zone = fib_levels['bearish_38_2'] <= current_close <= fib_levels['bearish_61_8']
            rsi_ok = current_rsi > 40
            if in_fib_zone and rsi_ok:
                sinal = 'PUT'
                logging.warning(f"SINAL de VENDA (PUT) DETECTADO! [Fibo Fractal RSI] | Pullback em tendência de baixa. RSI: {current_rsi:.2f}")
        
        return sinal

    except Exception as e:
        logging.error(f"[Fibo Fractal RSI] Erro ao analisar sinal: {e}")
        return None