"""
Equipment Enums - Enumerações para Equipamentos de Proteção
==========================================================

Definições robustas de enums para status, famílias e classificações.
"""

from enum import Enum
from typing import List, Dict, Any

class EquipmentStatus(str, Enum):
    """Status operacional do equipamento"""
    ACTIVE = "ACTIVE"                    # Equipamento ativo e operacional
    BLOQUEIO = "BLOQUEIO"               # Equipamento bloqueado (lockout)
    EM_CORTE = "EM_CORTE"               # Equipamento em corte (outage)
    MANUTENCAO = "MANUTENCAO"           # Em manutenção preventiva/corretiva
    TESTE = "TESTE"                      # Em fase de testes
    DESCOMISSIONADO = "DESCOMISSIONADO" # Fora de operação permanente
    RESERVA = "RESERVA"                  # Equipamento reserva (standby)
    
    @classmethod
    def get_display_name(cls, status: str) -> str:
        """Retorna nome amigável para exibição"""
        display_names = {
            cls.ACTIVE: "Ativo",
            cls.BLOQUEIO: "Bloqueado",
            cls.EM_CORTE: "Em Corte",
            cls.MANUTENCAO: "Manutenção",
            cls.TESTE: "Em Teste",
            cls.DESCOMISSIONADO: "Descomissionado",
            cls.RESERVA: "Reserva"
        }
        return display_names.get(status, status)
    
    @classmethod
    def get_color(cls, status: str) -> str:
        """Retorna cor para UI"""
        colors = {
            cls.ACTIVE: "green",
            cls.BLOQUEIO: "red",
            cls.EM_CORTE: "orange",
            cls.MANUTENCAO: "yellow",
            cls.TESTE: "blue",
            cls.DESCOMISSIONADO: "gray",
            cls.RESERVA: "purple"
        }
        return colors.get(status, "gray")

class RelayFamily(str, Enum):
    """Famílias de relés"""
    SEPAM = "SEPAM"                     # Schneider SEPAM Series
    MICOM = "MICOM"                     # Schneider MiCOM Series
    SIEMENS_7S = "SIEMENS_7S"          # Siemens 7S Series
    SEL = "SEL"                         # SEL Protection Relays
    ABB_REF = "ABB_REF"                # ABB REF Series
    GE_MULTILIN = "GE_MULTILIN"        # GE Multilin
    ALSTOM = "ALSTOM"                   # Alstom/GE Grid
    OUTROS = "OUTROS"                   # Outros fabricantes
    
    @classmethod
    def get_manufacturer(cls, family: str) -> str:
        """Retorna fabricante da família"""
        manufacturers = {
            cls.SEPAM: "Schneider Electric",
            cls.MICOM: "Schneider Electric",
            cls.SIEMENS_7S: "Siemens",
            cls.SEL: "Schweitzer Engineering",
            cls.ABB_REF: "ABB",
            cls.GE_MULTILIN: "General Electric",
            cls.ALSTOM: "Alstom",
            cls.OUTROS: "Diversos"
        }
        return manufacturers.get(family, "Desconhecido")

class ProtectionSystem(str, Enum):
    """Sistemas de proteção"""
    PRINCIPAL = "PRINCIPAL"             # Sistema principal de proteção
    RETAGUARDA = "RETAGUARDA"           # Sistema de retaguarda (backup)
    FALHA_DISJUNTOR = "FALHA_DISJUNTOR" # Proteção de falha de disjuntor
    BARRA = "BARRA"                     # Proteção de barra
    LINHA = "LINHA"                     # Proteção de linha
    TRANSFORMADOR = "TRANSFORMADOR"     # Proteção de transformador
    GERADOR = "GERADOR"                 # Proteção de gerador
    MOTOR = "MOTOR"                     # Proteção de motor
    OUTROS = "OUTROS"                   # Outros sistemas

class VoltageLevel(str, Enum):
    """Níveis de tensão"""
    BAIXA = "BAIXA"                     # Baixa tensão (< 1kV)
    MEDIA = "MEDIA"                     # Média tensão (1kV - 72.5kV)
    ALTA = "ALTA"                       # Alta tensão (72.5kV - 242kV)
    EXTRA_ALTA = "EXTRA_ALTA"          # Extra alta tensão (> 242kV)
    
    @classmethod
    def get_range(cls, level: str) -> str:
        """Retorna faixa de tensão"""
        ranges = {
            cls.BAIXA: "< 1kV",
            cls.MEDIA: "1kV - 72.5kV",
            cls.ALTA: "72.5kV - 242kV",
            cls.EXTRA_ALTA: "> 242kV"
        }
        return ranges.get(level, "N/A")

class ExportFormat(str, Enum):
    """Formatos de exportação de relatórios"""
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"
    JSON = "json"
    
    @classmethod
    def get_mime_type(cls, format: str) -> str:
        """Retorna MIME type para download"""
        mime_types = {
            cls.CSV: "text/csv",
            cls.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            cls.PDF: "application/pdf",
            cls.JSON: "application/json"
        }
        return mime_types.get(format, "application/octet-stream")
    
    @classmethod
    def get_file_extension(cls, format: str) -> str:
        """Retorna extensão do arquivo"""
        return f".{format}"

def get_all_enums() -> Dict[str, List[Dict[str, Any]]]:
    """
    Retorna todos os enums em formato JSON para frontend
    """
    return {
        "status": [
            {
                "value": status.value,
                "label": EquipmentStatus.get_display_name(status.value),
                "color": EquipmentStatus.get_color(status.value)
            }
            for status in EquipmentStatus
        ],
        "families": [
            {
                "value": family.value,
                "label": family.value,
                "manufacturer": RelayFamily.get_manufacturer(family.value)
            }
            for family in RelayFamily
        ],
        "protection_systems": [
            {
                "value": system.value,
                "label": system.value
            }
            for system in ProtectionSystem
        ],
        "voltage_levels": [
            {
                "value": level.value,
                "label": level.value,
                "range": VoltageLevel.get_range(level.value)
            }
            for level in VoltageLevel
        ],
        "export_formats": [
            {
                "value": format.value,
                "label": format.value.upper(),
                "mime_type": ExportFormat.get_mime_type(format.value)
            }
            for format in ExportFormat
        ]
    }
