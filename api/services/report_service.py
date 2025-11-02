"""
Report Service - Sistema Robusto de Relatórios Multi-formato
============================================================

Service para geração de relatórios em CSV, XLSX e PDF com:
- Metadados dinâmicos (fabricantes, modelos, status, etc)
- Filtros avançados (família, barramento, sistema de proteção)
- Exportação multi-formato
- Performance otimizada com indexes DB

CAUSA RAIZ: Relatórios precisam ser flexíveis, não hardcoded.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
import csv
import io
from enum import Enum
import re

logger = logging.getLogger(__name__)


def generate_report_filename(
    format: str,
    manufacturer: Optional[str] = None,
    model: Optional[str] = None,
    bay: Optional[str] = None,
    status: Optional[str] = None,
    substation: Optional[str] = None
) -> str:
    """
    🎯 Gera nome de arquivo descritivo e único para relatórios
    
    Formato: REL_[FILTERS]_[DATE]_[TIME].[ext]
    
    Exemplos:
        - REL_SCHN-P220_20251102_150530.csv (Schneider + P220)
        - REL_GE-ALL_20251102_150531.xlsx (GE, todos modelos)
        - REL_ALL-BAY52MF02A_20251102_150532.pdf (Todos, bay específico)
        - REL_ALL-ALL-ACTIVE_20251102_150533.csv (Todos, status Active)
    
    Args:
        format: Extensão do arquivo (csv, xlsx, pdf)
        manufacturer: Nome do fabricante (opcional)
        model: Modelo do equipamento (opcional)
        bay: Nome do barramento (opcional)
        status: Status do equipamento (opcional)
        substation: Nome da subestação (opcional)
    
    Returns:
        Nome de arquivo único e descritivo
    """
    # Timestamp no formato ISO-like
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    
    def sanitize(text: Optional[str], max_len: int = 8, default: str = "ALL") -> str:
        """Remove caracteres especiais e limita tamanho"""
        if not text or text.strip() == "":
            return default
        # Remover caracteres especiais, manter apenas alfanuméricos
        clean = re.sub(r'[^A-Za-z0-9]', '', str(text).upper())
        return clean[:max_len] if clean else default
    
    # Componentes do nome (ordem de prioridade)
    parts = []
    
    # Manufacturer (máx 4 chars) - SCHN, GE, ABB, SIEM
    mfr = sanitize(manufacturer, max_len=4)
    parts.append(mfr)
    
    # Model (máx 8 chars) - P220, P122, REF615
    mdl = sanitize(model, max_len=8)
    parts.append(mdl)
    
    # Bay (se especificado, adiciona prefixo BAY)
    if bay and bay.strip():
        bay_clean = sanitize(bay, max_len=10)
        if bay_clean != "ALL":
            parts.append(f"BAY{bay_clean}")
    
    # Substation (se especificado, adiciona prefixo SUB)
    if substation and substation.strip():
        sub_clean = sanitize(substation, max_len=8)
        if sub_clean != "ALL":
            parts.append(f"SUB{sub_clean}")
    
    # Status (se especificado, máx 3 chars) - ACT, BLQ, CRT
    if status and status.strip():
        status_clean = sanitize(status, max_len=6)
        if status_clean != "ALL":
            parts.append(status_clean)
    
    # Montar string de filtros
    filter_str = "-".join(parts)
    
    # Nome final: REL_[FILTERS]_[DATE]_[TIME].[ext]
    filename = f"REL_{filter_str}_{date_str}_{time_str}.{format.lower()}"
    
    logger.info(f"📄 Filename gerado: {filename} (mfr={manufacturer}, model={model}, bay={bay}, status={status})")
    
    return filename


class EquipmentStatus(str, Enum):
    """Status canônicos de equipamentos"""
    ACTIVE = "ACTIVE"
    BLOQUEIO = "BLOQUEIO"
    EM_CORTE = "EM_CORTE"
    MANUTENCAO = "MANUTENCAO"
    DECOMMISSIONED = "DECOMMISSIONED"


class ExportFormat(str, Enum):
    """Formatos de exportação suportados"""
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ReportService:
    """
    Service robusto para geração de relatórios
    Integra dados de protec_ai e relay_configs
    """
    
    def __init__(self, db: Session):
        self.db = db
        from api.core.database import engine
        self.engine = engine
    
    def _build_filters_description(
        self, 
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        bay: Optional[str] = None,
        status: Optional[str] = None,
        substation: Optional[str] = None
    ) -> str:
        """Constrói descrição legível dos filtros aplicados"""
        parts = []
        if manufacturer:
            parts.append(f"Fabricante: {manufacturer}")
        if model:
            parts.append(f"Modelo: {model}")
        if bay:
            parts.append(f"Barramento: {bay}")
        if status:
            parts.append(f"Status: {status}")
        if substation:
            parts.append(f"Subestação: {substation}")
        
        return " | ".join(parts) if parts else "Todos os equipamentos"
    
    async def get_metadata(self) -> Dict[str, Any]:
        """
        📊 Retorna metadados para popular dropdowns
        
        ROBUSTEZ: Query dinâmica dos dados reais, não hardcoded
        """
        try:
            logger.info("Iniciando busca de metadados...")
            with self.engine.connect() as conn:
                # Manufacturers with equipment count
                # Keep all manufacturers present in `fabricantes`, counts may be zero.
                manufacturers_query = text("""
                    SELECT f.codigo_fabricante as code,
                           f.nome_completo as name,
                           COUNT(DISTINCT re.id) as count
                    FROM protec_ai.fabricantes f
                    LEFT JOIN protec_ai.relay_models rm ON rm.manufacturer_id = f.id
                    LEFT JOIN protec_ai.relay_equipment re ON re.relay_model_id = rm.id
                    GROUP BY f.codigo_fabricante, f.nome_completo
                    ORDER BY f.nome_completo
                """)
                manufacturers = conn.execute(manufacturers_query).fetchall()

                # Models with equipment count and manufacturer code
                # Use LEFT JOIN so models with zero equipment are still present in relay_models
                # We'll deduplicate/normalize similar model names in Python to avoid redundant entries
                models_query = text("""
                    SELECT rm.model_code as code,
                           rm.model_name as name,
                           f.codigo_fabricante as manufacturer_code,
                           COUNT(DISTINCT re.id) as count
                    FROM protec_ai.relay_models rm
                    LEFT JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                    LEFT JOIN protec_ai.relay_equipment re ON re.relay_model_id = rm.id
                    GROUP BY rm.model_code, rm.model_name, f.codigo_fabricante
                    ORDER BY f.codigo_fabricante, rm.model_name
                """)
                raw_models = conn.execute(models_query).fetchall()

                # Post-process models to deduplicate near-duplicates like 'SEPAM S40' vs 'SEPAM_S40'
                models_map: Dict[str, Dict[str, Any]] = {}
                for m in raw_models:
                    code = (m.code or '').strip()
                    name = (m.name or '').strip()
                    mfr_code = (m.manufacturer_code or '').strip()
                    count = int(m.count or 0)

                    # Normalize key: uppercase, replace _ with space, remove extra spaces
                    norm_key = ' '.join(code.replace('_', ' ').upper().split())
                    
                    # Skip unknown/empty models with zero count
                    if (not norm_key or norm_key == 'UNKNOWN MODEL') and count == 0:
                        continue

                    if norm_key not in models_map:
                        # First occurrence
                        models_map[norm_key] = {
                            'code': code,
                            'name': name,
                            'manufacturer_code': mfr_code,
                            'count': count
                        }
                    else:
                        # Duplicate found - aggregate
                        models_map[norm_key]['count'] += count
                        
                        # Prefer longer, more descriptive name (e.g., "Schneider Electric SEPAM S40" over "SEPAM S40")
                        if len(name) > len(models_map[norm_key]['name']):
                            models_map[norm_key]['name'] = name
                            models_map[norm_key]['code'] = code  # Update code too

                # Convert map to sorted list
                # IMPORTANTE: NÃO filtramos count=0 aqui - mantemos TODOS os modelos para flexibilidade
                # O frontend decidirá quais mostrar baseado em count > 0
                models = list(models_map.values())
                models = sorted(models, key=lambda x: (x.get('manufacturer_code') or '', x.get('name') or ''))

                # Bays with equipment count
                bays_query = text("""
                    SELECT COALESCE(re.bay_name, '') as name,
                           COUNT(*) as count
                    FROM protec_ai.relay_equipment re
                    WHERE re.bay_name IS NOT NULL AND re.bay_name != ''
                    GROUP BY re.bay_name
                    ORDER BY re.bay_name
                """)
                bays = conn.execute(bays_query).fetchall()

                # Statuses with counts (ensure canonical list present)
                statuses_query = text("""
                    SELECT re.status as code,
                           COUNT(*) as count
                    FROM protec_ai.relay_equipment re
                    GROUP BY re.status
                """)
                statuses = {row.code: row.count for row in conn.execute(statuses_query).fetchall()}

                # Map status codes to labels (pt-BR)
                status_labels = {
                    EquipmentStatus.ACTIVE.value: "Ativo",
                    EquipmentStatus.BLOQUEIO.value: "Bloqueio",
                    EquipmentStatus.EM_CORTE.value: "Em Corte",
                    EquipmentStatus.MANUTENCAO.value: "Manutenção",
                    EquipmentStatus.DECOMMISSIONED.value: "Descomissionado",
                }

                result_statuses = []
                for code, label in status_labels.items():
                    count = int(statuses.get(code, 0))
                    if count > 0:  # FILTER: Only statuses with equipment
                        result_statuses.append({
                            "code": code,
                            "label": label,
                            "count": count
                        })

                logger.info(f"Metadados carregados: {len(manufacturers)} fabricantes, {len(models)} modelos, {len(bays)} barramentos")
                
                return {
                    "manufacturers": [
                        {"code": m.code, "name": m.name, "count": int(m.count)}
                        for m in manufacturers
                        if int(m.count) > 0  # FILTER: Only manufacturers with equipment
                    ],
                    "models": models,  # Already dictionaries from models_map
                    "bays": [
                        {"name": b.name, "count": int(b.count)}
                        for b in bays
                    ],
                    "statuses": result_statuses
                }
                
        except Exception as e:
            logger.error(f"Erro ao buscar metadados: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Erro ao buscar metadados: {str(e)}")
    
    async def get_filtered_equipments(
        self,
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        bay: Optional[str] = None,
        substation: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        🔍 Busca equipamentos com filtros robustos
        
        CAUSA RAIZ: Filtros devem ser server-side (WHERE clauses), não client-side
        """
        try:
            # Construir query dinâmica com filtros
            base_query = """
                SELECT 
                    re.id,
                    re.equipment_tag,
                    re.serial_number,
                    re.substation_name,
                    re.bay_name,
                    re.status,
                    re.position_description,
                    rm.model_name,
                    rm.model_code,
                    rm.voltage_class,
                    rm.technology,
                    f.nome_completo as manufacturer_name,
                    f.pais_origem as manufacturer_country,
                    re.created_at
                FROM protec_ai.relay_equipment re
                JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                WHERE 1=1
            """
            
            params = {}
            
            if manufacturer:
                base_query += " AND f.nome_completo ILIKE :manufacturer"
                params["manufacturer"] = f"%{manufacturer}%"
            
            if model:
                base_query += " AND rm.model_name ILIKE :model"
                params["model"] = f"%{model}%"
            
            if bay:
                base_query += " AND re.bay_name ILIKE :bay"
                params["bay"] = f"%{bay}%"
            
            if substation:
                base_query += " AND re.substation_name ILIKE :substation"
                params["substation"] = f"%{substation}%"
            
            if status:
                base_query += " AND re.status ILIKE :status"
                params["status"] = f"%{status}%"
            
            base_query += " ORDER BY re.equipment_tag"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(base_query), params).fetchall()
                
                return [
                    {
                        "id": row.id,
                        "tag_reference": row.equipment_tag,
                        "serial_number": row.serial_number,
                        "substation": row.substation_name,
                        "bay": row.bay_name,
                        "status": row.status,
                        "description": row.position_description,
                        "model": {
                            "name": row.model_name,
                            "code": row.model_code,
                            "voltage_class": row.voltage_class,
                            "technology": row.technology
                        },
                        "manufacturer": {
                            "name": row.manufacturer_name,
                            "country": row.manufacturer_country
                        },
                        "created_at": row.created_at.isoformat() if row.created_at else None
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"Erro ao filtrar equipamentos: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao filtrar equipamentos: {str(e)}")
    
    async def export_to_csv(self, equipments: List[Dict[str, Any]]) -> str:
        """
        📄 Exporta para CSV
        
        ROBUSTEZ: CSV bem formatado com headers corretos
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Tag', 'Serial Number', 'Model', 'Model Code', 'Voltage Class', 'Technology',
            'Manufacturer', 'Country', 'Bay', 'Substation', 'Status',
            'Description', 'Created At'
        ])
        
        # Data rows
        for eq in equipments:
            writer.writerow([
                eq['tag_reference'],
                eq['serial_number'],
                eq['model']['name'],
                eq['model']['code'],
                eq['model'].get('voltage_class', ''),
                eq['model'].get('technology', ''),
                eq['manufacturer']['name'],
                eq['manufacturer']['country'],
                eq['bay'],
                eq['substation'],
                eq['status'],
                eq['description'],
                eq['created_at']
            ])
        
        return output.getvalue()
    
    async def export_to_xlsx(
        self, 
        equipments: List[Dict[str, Any]],
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        bay: Optional[str] = None,
        status: Optional[str] = None,
        substation: Optional[str] = None
    ) -> bytes:
        """
        📊 Exporta para XLSX com formatação profissional
        
        IMPLEMENTADO: Usa openpyxl para criar arquivo Excel formatado
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from openpyxl.utils import get_column_letter
        from datetime import datetime
        import io
        
        logger.info(f"Exportando {len(equipments)} equipamentos para XLSX")
        
        # Criar workbook e worksheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Relay Equipment"
        
        # Título e Filtros (linhas 1-3)
        ws.merge_cells('A1:M1')
        title_cell = ws['A1']
        title_cell.value = "Relatório de Equipamentos de Proteção"
        title_cell.font = Font(bold=True, size=14, color="1a237e")
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Filtros aplicados (linha 2)
        filters_text = self._build_filters_description(manufacturer, model, bay, status, substation)
        ws.merge_cells('A2:M2')
        filters_cell = ws['A2']
        filters_cell.value = f"Filtros: {filters_text}"
        filters_cell.font = Font(size=10, italic=True)
        filters_cell.alignment = Alignment(horizontal="center")
        
        # Data de geração (linha 3)
        ws.merge_cells('A3:M3')
        date_cell = ws['A3']
        date_cell.value = f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}"
        date_cell.font = Font(size=9, italic=True)
        date_cell.alignment = Alignment(horizontal="center")
        
        # Headers (linha 5, pula linha 4 vazia)
        headers = [
            'Tag', 'Serial Number', 'Model', 'Model Code', 'Voltage Class',
            'Technology', 'Manufacturer', 'Country', 'Bay', 'Substation',
            'Status', 'Description', 'Created At'
        ]
        
        # Escrever headers com formatação
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=5, column=col_num)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Escrever dados (começa na linha 6)
        for row_num, eq in enumerate(equipments, 6):
            ws.cell(row=row_num, column=1, value=eq['tag_reference'])
            ws.cell(row=row_num, column=2, value=eq['serial_number'])
            ws.cell(row=row_num, column=3, value=eq['model']['name'])
            ws.cell(row=row_num, column=4, value=eq['model']['code'])
            ws.cell(row=row_num, column=5, value=eq['model']['voltage_class'])
            ws.cell(row=row_num, column=6, value=eq['model']['technology'])
            ws.cell(row=row_num, column=7, value=eq['manufacturer']['name'])
            ws.cell(row=row_num, column=8, value=eq['manufacturer']['country'])
            ws.cell(row=row_num, column=9, value=eq['bay'])
            ws.cell(row=row_num, column=10, value=eq['substation'])
            ws.cell(row=row_num, column=11, value=eq['status'])
            ws.cell(row=row_num, column=12, value=eq['description'])
            ws.cell(row=row_num, column=13, value=eq['created_at'])
        
        # Auto-ajustar largura das colunas
        for col_num in range(1, len(headers) + 1):
            column_letter = get_column_letter(col_num)
            max_length = 0
            for cell in ws[column_letter]:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)  # Max 50 caracteres
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Congelar primeira linha (headers)
        ws.freeze_panes = 'A2'
        
        # Salvar em bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        logger.info("XLSX exportado com sucesso")
        return output.getvalue()
    
    async def export_to_pdf(
        self, 
        equipments: List[Dict[str, Any]],
        manufacturer: Optional[str] = None,
        model: Optional[str] = None,
        bay: Optional[str] = None,
        status: Optional[str] = None,
        substation: Optional[str] = None
    ) -> bytes:
        """
        📑 Exporta para PDF com formatação profissional
        
        Usa ReportLab para gerar PDF com tabela formatada
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from io import BytesIO
            from datetime import datetime
            
            # Buffer para PDF
            buffer = BytesIO()
            
            # Criar documento (landscape para mais colunas)
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                rightMargin=30,
                leftMargin=30,
                topMargin=50,
                bottomMargin=30
            )
            
            # Elementos do documento
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1a237e'),
                spaceAfter=12,
                alignment=1  # Center
            )
            title = Paragraph("Relatório de Equipamentos de Proteção", title_style)
            elements.append(title)
            
            # Filtros aplicados
            filters_text = self._build_filters_description(manufacturer, model, bay, status, substation)
            if filters_text:
                filters_style = ParagraphStyle(
                    'FiltersStyle',
                    parent=styles['Normal'],
                    fontSize=10,
                    textColor=colors.HexColor('#424242'),
                    alignment=1,  # Center
                    spaceAfter=12
                )
                filters_para = Paragraph(f"<b>Filtros aplicados:</b> {filters_text}", filters_style)
                elements.append(filters_para)
            
            # Data/hora de geração
            timestamp = Paragraph(
                f"<b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
                styles['Normal']
            )
            elements.append(timestamp)
            elements.append(Spacer(1, 0.3*inch))
            
            # Preparar dados da tabela
            data = [[
                'Tag', 'Modelo', 'Código', 'Fabricante', 
                'Bay', 'Status', 'Classe Tensão'
            ]]
            
            for eq in equipments:
                data.append([
                    eq['tag_reference'][:25],  # Limitar tamanho
                    eq['model']['name'][:20],
                    eq['model']['code'][:10],
                    eq['manufacturer']['name'][:20],
                    (eq['bay'] or '')[:15],
                    eq['status'],
                    (eq['model'].get('voltage_class') or '')[:15]
                ])
            
            # Criar tabela
            table = Table(data, repeatRows=1)
            
            # Estilo da tabela
            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Body
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            
            # Rodapé
            elements.append(Spacer(1, 0.3*inch))
            footer = Paragraph(
                f"<i>Total de equipamentos: {len(equipments)}</i>",
                styles['Normal']
            )
            elements.append(footer)
            
            # Gerar PDF
            doc.build(elements)
            
            # Retornar bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()
            
            logger.info(f"PDF gerado com sucesso: {len(equipments)} equipamentos")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")
