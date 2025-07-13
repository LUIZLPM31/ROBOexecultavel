# Robô de Negociação para IQ Option

Este projeto implementa um robô de negociação automatizado para a plataforma IQ Option, utilizando a linguagem Python e as bibliotecas `iqoptionapi`, `pandas` e `pandas-ta`. O robô opera com base em uma estratégia que combina as Bandas de Bollinger e o Índice de Força Relativa (RSI), além de incorporar um sistema de gerenciamento de risco.

## Estratégia de Negociação

A estratégia se baseia na análise de duas condições principais para gerar sinais de compra (CALL) ou venda (PUT) no momento da abertura de uma nova vela (candle).

### Sinal de COMPRA (CALL)

Para que um sinal de COMPRA seja válido, ambas as condições a seguir devem ser verdadeiras exatamente no momento da abertura de uma nova vela:

1.  **Condição da Banda de Bollinger:** O preço de abertura da vela atual precisa ser **menor** que a linha da Banda de Bollinger Inferior.
    `Preço de Abertura < Banda Inferior`

2.  **Condição do RSI:** O valor do RSI (calculado com base no fechamento da vela anterior) precisa estar na zona de sobrevenda.
    `RSI < 15`

**Em resumo (CALL):** Se uma nova vela abrir abaixo da banda inferior **E** o RSI estiver abaixo de 15, o robô executa uma ordem de compra.

### Sinal de VENDA (PUT)

Para que um sinal de VENDA seja válido, ambas as condições a seguir devem ser verdadeiras exatamente no momento da abertura de uma nova vela:

1.  **Condição da Banda de Bollinger:** O preço de abertura da vela atual precisa ser **maior** que a linha da Banda de Bollinger Superior.
    `Preço de Abertura > Banda Superior`

2.  **Condição do RSI:** O valor do RSI (calculado com base no fechamento da vela anterior) precisa estar na zona de sobrecompra.
    `RSI > 85`

**Em resumo (PUT):** Se uma nova vela abrir acima da banda superior **E** o RSI estiver acima de 85, o robô executa uma ordem de venda.

## Gerenciamento de Risco (Obrigatório)

O robô incorpora regras rígidas de gerenciamento de risco para proteger o capital:

*   **Valor da Entrada (Stake):** Um percentual pequeno do seu capital total é definido para cada operação (configurável em `main_robot.py`).
*   **Stop Loss Diário:** Um valor máximo de perda diária é estabelecido. Ao ser atingido, o robô para de operar no dia.
*   **Meta de Ganhos Diária (Take Profit):** Um valor de ganho diário é definido. Ao ser atingido, o robô desliga.

## Estrutura do Projeto

O projeto é organizado nos seguintes arquivos:

*   `main_robot.py`: O script principal que orquestra a conexão, a obtenção de dados, a aplicação da estratégia e o gerenciamento de risco.
*   `iq_option_connection.py`: Contém a classe `IQOptionConnection` para gerenciar a conexão com a API da IQ Option e realizar operações como obter velas e executar ordens.
*   `indicators.py`: Define a função `calculate_indicators` para calcular as Bandas de Bollinger e o RSI usando `pandas-ta`.
*   `strategy.py`: Implementa a função `check_signal` que aplica a lógica da estratégia de negociação com base nos indicadores.
*   `risk_management.py`: Contém a classe `RiskManagement` para gerenciar o stake, stop loss diário e take profit diário.

## Como Usar

### 1. Configuração do Ambiente

Certifique-se de ter o Python 3 instalado. Em seguida, instale as bibliotecas necessárias:

```bash
pip install iqoptionapi pandas pandas-ta
```

### 2. Configuração das Credenciais e Parâmetros

Abra o arquivo `main_robot.py` e preencha suas credenciais da IQ Option, bem como os parâmetros de negociação e gerenciamento de risco:

```python
# --- Configurações do Robô --- #
EMAIL = "SEU_EMAIL_AQUI"
PASSWORD = "SUA_SENHA_AQUI"

# Configurações de negociação
ASSET = "EURUSD"  # Ativo a ser negociado
TIMEFRAME = 60     # Tempo de vela em segundos (60 para 1 minuto)
EXPIRATION_TIME = 1 # Tempo de expiração da ordem em minutos

# Configurações de gerenciamento de risco
INITIAL_BALANCE = 1000.0 # Saldo inicial para cálculo de risco (pode ser o saldo real da conta)
STAKE_PERCENTAGE = 1.0   # Percentual do capital para cada entrada (ex: 1.0 para 1%)
DAILY_STOP_LOSS_PERCENTAGE = 5.0 # Percentual de perda máxima diária (ex: 5.0 para 5%)
DAILY_TAKE_PROFIT_PERCENTAGE = 10.0 # Percentual de ganho diário para parar (ex: 10.0 para 10%)
```

**ATENÇÃO:** É altamente recomendável usar variáveis de ambiente ou um arquivo de configuração seguro para suas credenciais, em vez de codificá-las diretamente no script.

### 3. Execução do Robô

Para iniciar o robô, execute o script `main_robot.py` a partir do seu terminal:

```bash
python3 main_robot.py
```

O robô começará a monitorar o mercado, calcular os indicadores e executar ordens de acordo com a estratégia e as regras de gerenciamento de risco definidas.

## Observações Importantes

*   **Resultados de Trades:** A `iqoptionapi` não fornece um callback imediato para o resultado de uma operação. O `main_robot.py` inclui um comentário sobre onde você precisaria implementar a lógica para verificar o resultado real de cada trade (ganho ou perda) e atualizar o `RiskManagement` de acordo. Isso geralmente envolve consultar o histórico de trades da sua conta após o tempo de expiração da ordem.
*   **Testes:** Recomenda-se testar o robô em uma conta de demonstração antes de utilizá-lo com dinheiro real.
*   **Conexão:** Certifique-se de que sua conexão com a internet esteja estável para evitar interrupções na operação do robô.
*   **Legalidade:** Verifique a legalidade de robôs de negociação automatizados em sua jurisdição e com a IQ Option.

Este robô é fornecido como um exemplo e ponto de partida. Adaptações e melhorias podem ser necessárias para atender às suas necessidades específicas e condições de mercado.

