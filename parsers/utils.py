import re
import datetime

def clean_currency(value: str) -> float:
    """Converte formato BRL (1.234,56) para float do Python (1234.56)"""
    if not value: return 0.0

    is_negative = '-' in value
    clean = re.sub(r'[^\d,-]', '', str(value))
    
    if not clean: return 0.0
    clean = clean.replace('.', '').replace(',', '.')
    try:
        value = float(clean)
        return value
    except ValueError:
        return 0.0

def clean_int(value: str) -> int:
    """Remove tudo o que não for número e devolve um inteiro"""
    if not value: return 0
    clean = re.sub(r'[^\d]', '', str(value))
    return int(clean) if clean else 0
    