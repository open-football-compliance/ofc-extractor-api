from datetime import datetime
import re
import pdfplumber
import io

from domain.models import MatchDayFinancialReport
from parsers.base_extractor import MatchDayExtractor
import parsers.utils as utils

class FPFStandardExtractor(MatchDayExtractor):
    """
    Estratégia concreta para extrair relatórios financeiros de jogos padrão CBF / FPF-PE (Borderôs).
    Utiliza uma abordagem híbrida: Regex para o cabeçalho e varredura inteligente de tabelas para as finanças.
    """

    def _extract_cost_type(self, cell: str) -> str:
        """
        Identifica o tipo de custo com base no conteúdo da célula.
        """
        if "B1" in cell:
            return "B1"
        elif "B2" in cell:
            return "B2"
        elif "B3" in cell:
            return "B3"
        else:
            return None
    
    def extract(self, file_bytes: bytes) -> MatchDayFinancialReport:
        parsed_date = None
        home_club = "Mandante Desconhecido"
        away_club = "Visitante Desconhecido"
        paying_attendance = 0
        total_attendance = 0
        gross_revenue = 0.0
        operating_expenses = 0.0
        net_revenue = 0.0

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()

                for table in tables:
                    for row in table:
                        row_cleaned = [str(cell).strip() if cell is not None else "" for cell in row]

                        for idx, cell in enumerate(row_cleaned):
                            cell_upper = cell.upper()
                            cost_type = self._extract_cost_type(cell_upper)

                            if "JOGO" in cell_upper and "X" in row_cleaned[idx + 1] :
                                teams = row_cleaned[idx + 1].split("X")
                                home_club = teams[0].strip() if len(teams) > 0 else "Mandante Desconhecido"
                                away_club = teams[1].strip() if len(teams) > 1 else "Visitante Desconhecido"
                            
                            if "DATA" in cell_upper and idx + 1 < len(row_cleaned):
                                match_date_str = re.search(r"(\d{2}/\d{2}/\d{4})", row_cleaned[idx + 1])
                                if match_date_str:
                                    parsed_date = datetime.strptime(match_date_str.group(1), "%d/%m/%Y").date()
                            
                            if "TOTAL" in cell_upper:
                                if len(row_cleaned) > 3:
                                    total_attendance = utils.clean_int(row_cleaned[idx + 3] if idx + 3 < len(row_cleaned) else "0")
                                    gross_revenue = utils.clean_currency(row_cleaned[idx + 5] if idx + 5 < len(row_cleaned) else "0")
                                
                                if "DESPESAS" in cell_upper:
                                    operating_expenses = utils.clean_currency(row_cleaned[idx + 1] if idx + 1 < len(row_cleaned) else "0")
                            
                            if "RENDA" in cell_upper and len(row_cleaned) < 3:
                                net_revenue = utils.clean_currency(row_cleaned[idx + 1]) if idx + 1 < len(row_cleaned) else 0.0

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