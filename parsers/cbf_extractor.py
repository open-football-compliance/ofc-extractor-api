import re
from datetime import datetime
import pdfplumber
import io
from domain.models import MatchDayFinancialReport
from parsers.base_extractor import MatchDayExtractor

class CBFStandardExtractor(MatchDayExtractor):
    """
    Estratégia concreta para extrair relatórios financeiros de jogos padrão CBF / FPF-PE (Borderôs).
    Utiliza uma abordagem híbrida: Regex para o cabeçalho e varredura inteligente de tabelas para as finanças.
    """
    
    def _clean_currency(self, value: str) -> float:
        """Converte formato BRL (1.234,56) para float do Python (1234.56)"""
        if not value: return 0.0
        clean = re.sub(r'[^\d,-]', '', str(value))
        if not clean: return 0.0
        clean = clean.replace('.', '').replace(',', '.')
        try:
            return float(clean)
        except ValueError:
            return 0.0

    def _clean_int(self, value: str) -> int:
        """Remove tudo o que não for número e devolve um inteiro"""
        if not value: return 0
        clean = re.sub(r'[^\d]', '', str(value))
        return int(clean) if clean else 0

    def extract(self, file_bytes: bytes) -> MatchDayFinancialReport:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            first_page = pdf.pages[0]
            text = first_page.extract_text() or ""
            
            # Procura a Data (ex: Data: 15/05/2026)
            date_match = re.search(r"Data:\s*(\d{2}/\d{2}/\d{4})", text)
            if date_match:
                parsed_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()
            else:
                parsed_date = datetime.today().date()
            
            jogo_match = re.search(r"Jogo:\s*(.*?)\s*[Xx]\s*(.*?)\n", text)
            home_club = jogo_match.group(1).strip() if jogo_match else "Mandante Desconhecido"
            away_club = jogo_match.group(2).strip() if jogo_match else "Visitante Desconhecido"

            tables = first_page.extract_tables({
                "vertical_strategy": "lines",
                "horizontal_strategy": "lines"
            })

            paying_attendance = 0
            total_attendance = 0
            gross_revenue = 0.0
            operating_expenses = 0.0
            net_revenue = 0.0

            if tables:
                for table in tables:
                    for row in table:
                        # Limpa células vazias/None
                        clean_row = [str(cell).strip() for cell in row if cell]
                        if not clean_row: continue
                        
                        row_text = " ".join(clean_row).lower()

                        # --- MAPEAMENTO DE PÚBLICO ---
                        if "pagante" in row_text and paying_attendance == 0:
                            paying_attendance = self._clean_int(clean_row[-1])
                        
                        if ("total" in row_text and "público" in row_text) or ("público total" in row_text):
                            total_attendance = self._clean_int(clean_row[-1])

                        # --- MAPEAMENTO FINANCEIRO ---
                        if "renda bruta" in row_text or "arrecadação" in row_text:
                            # O valor costuma estar sempre na última coluna da linha
                            gross_revenue = self._clean_currency(clean_row[-1])
                        
                        if "total de despesas" in row_text or "total das despesas" in row_text:
                            operating_expenses = self._clean_currency(clean_row[-1])
                            
                        if "renda líquida" in row_text or "total líquido" in row_text:
                            net_revenue = self._clean_currency(clean_row[-1])

            if total_attendance == 0 and paying_attendance > 0:
                total_attendance = paying_attendance

            return MatchDayFinancialReport(
                match_date=parsed_date,
                home_club_name=home_club,
                away_club_name=away_club,
                paying_attendance=paying_attendance,
                total_attendance=total_attendance,
                gross_revenue=gross_revenue,
                operating_expenses=operating_expenses,
                net_revenue=net_revenue
            )