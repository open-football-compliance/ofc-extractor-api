from parsers.base_extractor import MatchDayExtractor
from parsers.cbf_extractor import CBFStandardExtractor
from parsers.fpf_extractor import FPFStandardExtractor

class ExtractorFactory:
    """
    Padrão de projeto Factory para instanciar o extrator correto com base no tipo de federação.
    """

    FEDERATION_TYPES = {
        "CBF": CBFStandardExtractor,
        "FPF-PE": FPFStandardExtractor
    }


    @staticmethod
    def get_extractor(federation_type: str = "CBF") -> MatchDayExtractor:
        federation_type = federation_type.upper()
        
        if federation_type in ["CBF", "FPF-PE"]:
            return ExtractorFactory.FEDERATION_TYPES[federation_type]()
            
        raise ValueError(f"Extractor for federation type '{federation_type}' is not supported yet.")