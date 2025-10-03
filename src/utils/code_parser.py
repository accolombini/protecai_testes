# -*- coding: utf-8 -*-
"""
Módulo para parsing e normalização de códigos multivalorados de proteção.

Este módulo detecta e segmenta padrões típicos encontrados em sistemas de proteção:
- Códigos ANSI com sufixos (52-MP-20, 67N-EF-01)
- Model numbers compactos (P241311B2M0600J, P220-2)
- Referências de planta (204-MF-02_rev.0)
- Códigos de proteção estruturados

Autor: Sistema ProtecAI
Data: 2025-10-03
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Union
from enum import Enum


class TokenType(Enum):
    """Tipos de tokens identificados no parsing."""
    ANSI_CODE = "ansi_code"
    PROTECTION_TYPE = "protection_type"
    SEQUENCE_NUMBER = "sequence_number"
    MODEL_PREFIX = "model_prefix"
    MODEL_SERIES = "model_series"
    MODEL_VARIANT = "model_variant"
    MODEL_SUFFIX = "model_suffix"
    PLANT_REFERENCE = "plant_reference"
    REVISION = "revision"
    FREQUENCY = "frequency"
    VOLTAGE_LEVEL = "voltage_level"
    UNKNOWN = "unknown"


@dataclass
class ParsedToken:
    """Representa um token extraído de um código multivalorado."""
    value: str
    token_type: TokenType
    meaning: str
    confidence: float  # 0.0 a 1.0
    position: int  # posição no valor original


@dataclass
class ParseResult:
    """Resultado completo do parsing de um valor."""
    original_value: str
    tokens: List[ParsedToken]
    is_atomic: bool  # True se o valor é atômico (não precisa normalização)
    pattern_detected: str  # padrão detectado para debug


class CodeParser:
    """Parser principal para códigos multivalorados."""
    
    def __init__(self):
        self._setup_mappings()
        self._setup_patterns()
    
    def _setup_mappings(self):
        """Configura dicionários de mapeamento de códigos conhecidos."""
        
        # Códigos ANSI/IEEE ampliados
        self.ansi_codes = {
            "25": "Synchronizing or synchronism-check device",
            "27": "Undervoltage relay",
            "27N": "Neutral undervoltage relay", 
            "32": "Directional power relay",
            "40": "Field relay",
            "46": "Reverse-phase or phase-balance current relay",
            "49": "Thermal relay (Machine or Transformer)",
            "50": "Instantaneous overcurrent relay",
            "50N": "Neutral instantaneous overcurrent relay",
            "51": "AC time overcurrent relay",
            "51N": "Neutral AC time overcurrent relay",
            "52": "AC circuit breaker",
            "59": "Overvoltage relay",
            "59N": "Neutral overvoltage relay",
            "64": "Ground detector relay",
            "67": "AC directional overcurrent relay",
            "67N": "Neutral directional overcurrent relay",
            "68": "Blocking or out-of-step relay",
            "79": "AC reclosing relay",
            "81": "Frequency relay (Over/Under)",
            "86": "Lockout relay",
            "87": "Differential protective relay",
            "94": "Tripping or trip-free relay",
        }
        
        # Tipos de proteção comuns
        self.protection_types = {
            "MP": "Motor Protection / Main Protection",
            "EF": "Earth Fault",
            "OC": "Overcurrent",
            "UV": "Undervoltage", 
            "OV": "Overvoltage",
            "DF": "Differential",
            "DIR": "Directional",
            "FREQ": "Frequency",
            "SYNC": "Synchronizing",
            "BF": "Breaker Failure",
            "LO": "Lockout",
            "REC": "Reclosing",
            "TH": "Thermal",
            "PH": "Phase",
            "GND": "Ground",
            "NEG": "Negative Sequence",
            "POS": "Positive Sequence",
            "ZERO": "Zero Sequence"
        }
        
        # Prefixos de model numbers conhecidos (Schneider, ABB, GE, etc.)
        self.model_prefixes = {
            "P1": "Schneider Electric - Série P1",
            "P2": "Schneider Electric - Série P2", 
            "P3": "Schneider Electric - Série P3",
            "P4": "Schneider Electric - Série P4",
            "M": "Schneider Electric - MiCOM",
            "REF": "ABB - Relé de Proteção",
            "RET": "ABB - Relé de Proteção",
            "F": "GE Multilin - Família F",
            "L": "GE Multilin - Família L",
            "SR": "GE Multilin - Família SR",
            "UR": "GE Multilin - Universal Relay"
        }
    
    def _setup_patterns(self):
        """Configura expressões regulares para diferentes padrões."""
        
        # Padrão ANSI com proteção e sequência: 52-MP-20, 67N-EF-01
        self.pattern_ansi_full = re.compile(
            r'^(\d{2}N?)-([A-Z]{2,4})-(\d{1,3})$', 
            re.IGNORECASE
        )
        
        # Padrão ANSI simples: 52, 67N
        self.pattern_ansi_simple = re.compile(
            r'^(\d{2}N?)$'
        )
        
        # Model numbers Schneider: P241311B2M0600J
        self.pattern_schneider_model = re.compile(
            r'^(P)(\d{1,2})(\d{2})(\d{2})([A-Z]\d[A-Z])(\d{4})([A-Z])$'
        )
        
        # Model numbers simples: P220-2, M220
        self.pattern_simple_model = re.compile(
            r'^([A-Z]+)(\d+)(?:-(\d+))?$'
        )
        
        # Referência de planta: 204-MF-02_rev.0
        self.pattern_plant_ref = re.compile(
            r'^(\d{3})-([A-Z]{2})-(\d{2})(?:_rev\.(\d+))?$'
        )
        
        # Frequência: 60Hz, 50Hz
        self.pattern_frequency = re.compile(
            r'^(\d{2,3})Hz?$', re.IGNORECASE
        )
        
        # Voltage: 13.8kV, 230V
        self.pattern_voltage = re.compile(
            r'^(\d+(?:\.\d+)?)k?V$', re.IGNORECASE
        )
    
    def parse_value(self, value: str) -> ParseResult:
        """
        Faz o parsing principal de um valor, tentando diferentes padrões.
        
        Args:
            value: String a ser analisada
            
        Returns:
            ParseResult com tokens extraídos
        """
        if not isinstance(value, str) or not value.strip():
            return ParseResult(
                original_value=value,
                tokens=[],
                is_atomic=True,
                pattern_detected="empty_or_invalid"
            )
        
        clean_value = value.strip()
        
        # Tentar diferentes padrões em ordem de especificidade
        patterns = [
            (self._parse_ansi_full, "ansi_full"),
            (self._parse_schneider_model, "schneider_model"),
            (self._parse_plant_reference, "plant_reference"),
            (self._parse_simple_model, "simple_model"),
            (self._parse_frequency, "frequency"),
            (self._parse_voltage, "voltage"),
            (self._parse_ansi_simple, "ansi_simple"),
            (self._parse_generic_tokens, "generic_tokens")
        ]
        
        for parser_func, pattern_name in patterns:
            result = parser_func(clean_value)
            if result and result.tokens:
                result.pattern_detected = pattern_name
                return result
        
        # Se nenhum padrão foi reconhecido, considerar atômico
        return ParseResult(
            original_value=clean_value,
            tokens=[],
            is_atomic=True,
            pattern_detected="atomic"
        )
    
    def _parse_ansi_full(self, value: str) -> Optional[ParseResult]:
        """Parse padrão ANSI completo: 52-MP-20"""
        match = self.pattern_ansi_full.match(value)
        if not match:
            return None
        
        ansi_code, protection, sequence = match.groups()
        tokens = []
        
        # Token ANSI
        ansi_meaning = self.ansi_codes.get(ansi_code.upper(), f"Código ANSI {ansi_code} (não mapeado)")
        tokens.append(ParsedToken(
            value=ansi_code,
            token_type=TokenType.ANSI_CODE,
            meaning=ansi_meaning,
            confidence=0.95 if ansi_code.upper() in self.ansi_codes else 0.7,
            position=0
        ))
        
        # Token de proteção
        prot_meaning = self.protection_types.get(protection.upper(), f"Tipo de proteção {protection} (não mapeado)")
        tokens.append(ParsedToken(
            value=protection,
            token_type=TokenType.PROTECTION_TYPE,
            meaning=prot_meaning,
            confidence=0.9 if protection.upper() in self.protection_types else 0.6,
            position=1
        ))
        
        # Token sequencial
        tokens.append(ParsedToken(
            value=sequence,
            token_type=TokenType.SEQUENCE_NUMBER,
            meaning=f"Identificador/índice do equipamento: {sequence}",
            confidence=0.8,
            position=2
        ))
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_schneider_model(self, value: str) -> Optional[ParseResult]:
        """Parse model number Schneider: P241311B2M0600J"""
        match = self.pattern_schneider_model.match(value)
        if not match:
            return None
        
        prefix, series, model, variant, config, code, suffix = match.groups()
        tokens = []
        
        # Prefixo (P)
        tokens.append(ParsedToken(
            value=prefix,
            token_type=TokenType.MODEL_PREFIX,
            meaning="Schneider Electric - Linha P (Proteção)",
            confidence=0.95,
            position=0
        ))
        
        # Série (24)
        tokens.append(ParsedToken(
            value=series,
            token_type=TokenType.MODEL_SERIES,
            meaning=f"Série do produto: {series}",
            confidence=0.8,
            position=1
        ))
        
        # Modelo (13)
        tokens.append(ParsedToken(
            value=model,
            token_type=TokenType.MODEL_VARIANT,
            meaning=f"Variante do modelo: {model}",
            confidence=0.8,
            position=2
        ))
        
        # Configuração (11)
        tokens.append(ParsedToken(
            value=variant,
            token_type=TokenType.MODEL_VARIANT,
            meaning=f"Configuração específica: {variant}",
            confidence=0.7,
            position=3
        ))
        
        # Código de configuração (B2M)
        tokens.append(ParsedToken(
            value=config,
            token_type=TokenType.MODEL_VARIANT,
            meaning=f"Código de configuração: {config}",
            confidence=0.7,
            position=4
        ))
        
        # Código produto (0600)
        tokens.append(ParsedToken(
            value=code,
            token_type=TokenType.MODEL_VARIANT,
            meaning=f"Código interno do produto: {code}",
            confidence=0.7,
            position=5
        ))
        
        # Sufixo (J)
        tokens.append(ParsedToken(
            value=suffix,
            token_type=TokenType.MODEL_SUFFIX,
            meaning=f"Sufixo de revisão/versão: {suffix}",
            confidence=0.6,
            position=6
        ))
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_plant_reference(self, value: str) -> Optional[ParseResult]:
        """Parse referência de planta: 204-MF-02_rev.0"""
        match = self.pattern_plant_ref.match(value)
        if not match:
            return None
        
        area, unit, number, revision = match.groups()
        tokens = []
        
        # Área/tag
        tokens.append(ParsedToken(
            value=area,
            token_type=TokenType.PLANT_REFERENCE,
            meaning=f"Área/seção da planta: {area}",
            confidence=0.9,
            position=0
        ))
        
        # Unidade
        tokens.append(ParsedToken(
            value=unit,
            token_type=TokenType.PLANT_REFERENCE,
            meaning=f"Unidade/equipamento: {unit}",
            confidence=0.9,
            position=1
        ))
        
        # Número
        tokens.append(ParsedToken(
            value=number,
            token_type=TokenType.SEQUENCE_NUMBER,
            meaning=f"Número sequencial: {number}",
            confidence=0.8,
            position=2
        ))
        
        # Revisão (se presente)
        if revision:
            tokens.append(ParsedToken(
                value=revision,
                token_type=TokenType.REVISION,
                meaning=f"Número da revisão: {revision}",
                confidence=0.8,
                position=3
            ))
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_simple_model(self, value: str) -> Optional[ParseResult]:
        """Parse model simples: P220-2, M220"""
        match = self.pattern_simple_model.match(value)
        if not match:
            return None
        
        prefix, base, variant = match.groups()
        tokens = []
        
        # Prefixo
        prefix_meaning = self.model_prefixes.get(prefix, f"Prefixo de modelo: {prefix}")
        tokens.append(ParsedToken(
            value=prefix,
            token_type=TokenType.MODEL_PREFIX,
            meaning=prefix_meaning,
            confidence=0.9 if prefix in self.model_prefixes else 0.6,
            position=0
        ))
        
        # Base do modelo
        tokens.append(ParsedToken(
            value=base,
            token_type=TokenType.MODEL_SERIES,
            meaning=f"Série/modelo base: {base}",
            confidence=0.8,
            position=1
        ))
        
        # Variante (se presente)
        if variant:
            tokens.append(ParsedToken(
                value=variant,
                token_type=TokenType.MODEL_VARIANT,
                meaning=f"Variante do modelo: {variant}",
                confidence=0.7,
                position=2
            ))
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_frequency(self, value: str) -> Optional[ParseResult]:
        """Parse frequência: 60Hz, 50Hz"""
        match = self.pattern_frequency.match(value)
        if not match:
            return None
        
        freq_value = match.group(1)
        tokens = [ParsedToken(
            value=freq_value,
            token_type=TokenType.FREQUENCY,
            meaning=f"Frequência da rede: {freq_value} Hz",
            confidence=0.95,
            position=0
        )]
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_voltage(self, value: str) -> Optional[ParseResult]:
        """Parse tensão: 13.8kV, 230V"""
        match = self.pattern_voltage.match(value)
        if not match:
            return None
        
        voltage_value = match.group(1)
        is_kv = 'k' in value.lower()
        
        tokens = [ParsedToken(
            value=voltage_value,
            token_type=TokenType.VOLTAGE_LEVEL,
            meaning=f"Nível de tensão: {voltage_value} {'kV' if is_kv else 'V'}",
            confidence=0.95,
            position=0
        )]
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_ansi_simple(self, value: str) -> Optional[ParseResult]:
        """Parse código ANSI simples: 52, 67N"""
        match = self.pattern_ansi_simple.match(value)
        if not match:
            return None
        
        ansi_code = match.group(1)
        meaning = self.ansi_codes.get(ansi_code.upper(), f"Código ANSI {ansi_code} (não mapeado)")
        
        tokens = [ParsedToken(
            value=ansi_code,
            token_type=TokenType.ANSI_CODE,
            meaning=meaning,
            confidence=0.95 if ansi_code.upper() in self.ansi_codes else 0.7,
            position=0
        )]
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )
    
    def _parse_generic_tokens(self, value: str) -> Optional[ParseResult]:
        """
        Parse genérico para valores que contêm separadores mas não seguem padrões específicos.
        Tenta segmentar em tokens básicos.
        """
        # Se não contém separadores, provavelmente é atômico
        if not any(sep in value for sep in ['-', '_', '.', '/', '\\']):
            return None
        
        # Segmentar por separadores comuns
        import re
        tokens_raw = re.split(r'[-_./ \\]', value)
        tokens_raw = [t.strip() for t in tokens_raw if t.strip()]
        
        if len(tokens_raw) <= 1:
            return None
        
        tokens = []
        for i, token_val in enumerate(tokens_raw):
            # Tentar classificar cada token
            token_type = TokenType.UNKNOWN
            meaning = f"Token genérico: {token_val}"
            confidence = 0.4
            
            # Heurísticas simples
            if token_val.upper() in self.ansi_codes:
                token_type = TokenType.ANSI_CODE
                meaning = self.ansi_codes[token_val.upper()]
                confidence = 0.8
            elif token_val.upper() in self.protection_types:
                token_type = TokenType.PROTECTION_TYPE
                meaning = self.protection_types[token_val.upper()]
                confidence = 0.8
            elif token_val.isdigit() and len(token_val) <= 3:
                token_type = TokenType.SEQUENCE_NUMBER
                meaning = f"Número sequencial: {token_val}"
                confidence = 0.6
            elif re.match(r'^[A-Z]+$', token_val) and len(token_val) <= 4:
                meaning = f"Código/abreviação: {token_val}"
                confidence = 0.5
            
            tokens.append(ParsedToken(
                value=token_val,
                token_type=token_type,
                meaning=meaning,
                confidence=confidence,
                position=i
            ))
        
        return ParseResult(
            original_value=value,
            tokens=tokens,
            is_atomic=False,
            pattern_detected=""
        )


# Função de conveniência para uso simples
def parse_code(value: str) -> ParseResult:
    """Função de conveniência para fazer parsing de um código."""
    parser = CodeParser()
    return parser.parse_value(value)


# Função para parsing em lote
def parse_codes_batch(values: List[str]) -> List[ParseResult]:
    """Faz parsing de uma lista de valores."""
    parser = CodeParser()
    return [parser.parse_value(v) for v in values]