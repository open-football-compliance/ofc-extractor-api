from pydantic import BaseModel, Field, field_validator
from datetime import date

class MatchDayFinancialReport(BaseModel):
    match_date: date = Field(..., description="Data do jogo para ordenação temporal")
    home_club_name: str
    away_club_name: str
    
    total_attendance: int = Field(ge=0, description="Número total de espectadores")
    paying_attendance: int = Field(ge=0, description="Número total de pagantes")
    gross_revenue: float = Field(ge=0.0, description="Receita bruta total do dia do jogo")
    operating_expenses: float = Field(description="Custo operacional do dia do jogo")
    net_revenue: float = Field(description="Balanço financeiro do dia do jogo (Receita Bruta - Despesas Operacionais)")

    @field_validator('net_revenue')
    def validate_financial_balance(cls, value: float, values: dict):
        """
        Garante a integridade matemática do relatório financeiro.
        Receita Bruta - Despesas Operacionais DEVE ser igual à Receita Líquida.
        """
        if 'gross_revenue' in values.data and 'operating_expenses' in values.data:
            expected_net = values.data['gross_revenue'] - values.data['operating_expenses']
            
            if abs(expected_net - value) > 1.0:
                raise ValueError(
                    f"Inconsistência financeira detectada. "
                    f"Receita Líquida esperada: {expected_net}, Receita Líquida reportada: {value}"
                )
        return value