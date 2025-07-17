import investpy
import pandas as pd
from datetime import datetime, timedelta
import logging

class NewsFilter:
    def __init__(self, impact_level=['high'], minutes_before=15, minutes_after=15):
        """
        Filtro de notícias econômicas.
        :param impact_level: Lista de níveis de impacto a serem considerados. Ex: ['high', 'medium'].
        :param minutes_before: Minutos de segurança antes da notícia.
        :param minutes_after: Minutos de segurança depois da notícia.
        """
        self.news_data = None
        self.last_fetch_date = None
        self.impact_level = impact_level
        self.minutes_before = minutes_before
        self.minutes_after = minutes_after
        self.countries = self._get_country_map()

    def _get_country_map(self):
        """Mapeia moedas para os nomes de países usados pela investpy."""
        # Este mapa pode ser expandido conforme necessário
        return {
            'USD': 'united states', 'EUR': 'euro zone', 'JPY': 'japan',
            'GBP': 'united kingdom', 'AUD': 'australia', 'CAD': 'canada',
            'CHF': 'switzerland', 'NZD': 'new zealand', 'CNY': 'china'
        }

    def _fetch_economic_calendar(self):
        """Busca e armazena o calendário econômico para o dia atual."""
        today = datetime.now().date()
        # Só busca as notícias uma vez por dia para evitar sobrecarregar o site
        if self.last_fetch_date == today and self.news_data is not None:
            return

        logging.info("FILTRO DE NOTÍCIAS: Buscando calendário econômico do dia...")
        try:
            # Pega a lista de todos os países disponíveis
            all_countries = list(self.countries.values())
            # Busca os dados
            df = investpy.news.economic_calendar(
                countries=all_countries,
                time_zone='GMT -03:00' # IMPORTANTE: Ajuste para o seu fuso horário se necessário
            )
            # Filtra apenas as notícias com o impacto desejado
            self.news_data = df[df['importance'].isin(self.impact_level)]
            self.last_fetch_date = today
            logging.info(f"FILTRO DE NOTÍCIAS: {len(self.news_data)} notícias de alto impacto encontradas para hoje.")
        except Exception as e:
            logging.error(f"FILTRO DE NOTÍCIAS: Erro ao buscar o calendário: {e}")
            self.news_data = pd.DataFrame() # Cria um DataFrame vazio em caso de erro

    def is_trading_safe(self, asset_name):
        """
        Verifica se é seguro operar um determinado ativo no horário atual.
        :param asset_name: O nome do ativo. Ex: 'EURUSD', 'GBPUSD-OTC'.
        :return: True se for seguro, False caso contrário.
        """
        self._fetch_economic_calendar()

        if self.news_data.empty:
            return True # Se não há notícias, é sempre seguro

        # Extrai as moedas do ativo (ex: EURUSD -> ['EUR', 'USD'])
        asset_clean = asset_name.upper().replace('-OTC', '')
        currencies_in_asset = [asset_clean[i:i+3] for i in (0, 3)]
        
        # Converte os nomes de moedas para países
        countries_in_asset = [self.countries.get(c) for c in currencies_in_asset if c in self.countries]
        if not countries_in_asset:
            return True # Se o ativo não tem moedas mapeadas (ex: cripto), permite a operação

        now = datetime.now()

        # Itera sobre as notícias de alto impacto do dia
        for index, news_item in self.news_data.iterrows():
            # Verifica se a notícia afeta alguma das moedas do par
            if news_item['zone'].lower() in countries_in_asset:
                news_time = news_item['date']
                
                # Define a janela de bloqueio
                blackout_start = news_time - timedelta(minutes=self.minutes_before)
                blackout_end = news_time + timedelta(minutes=self.minutes_after)

                # Se o horário atual está dentro da janela, não é seguro operar
                if blackout_start <= now <= blackout_end:
                    logging.warning(f"TRADE BLOQUEADO: Notícia '{news_item['event']}' para {news_item['currency']} às {news_time.strftime('%H:%M')}. Janela de bloqueio: {blackout_start.strftime('%H:%M')} - {blackout_end.strftime('%H:%M')}.")
                    return False
        
        return True # Se passou por todas as notícias sem conflito, é seguro