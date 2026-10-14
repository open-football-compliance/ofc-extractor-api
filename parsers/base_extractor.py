from abc import ABC, abstractmethod
from domain.models import MatchDayFinancialReport

class MatchDayExtractor(ABC):
    """
    Classe Abstrata Base para todos os Extratores de PDF de Dia de Jogo.
    Garante que, independentemente do layout do PDF, a saída siga estritamente o padrão OFC.
    """
    
    @abstractmethod
    def extract(self, file_bytes: bytes) -> MatchDayFinancialReport:
        pass