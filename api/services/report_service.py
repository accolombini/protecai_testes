"""
Report Service - Geração de Relatórios Multi-Formato
===================================================

Service robusto para geração de relatórios com:
- Exportação CSV, XLSX, PDF
- Filtros avançados
- Metadados dinâmicos
"""

import logging
import csv
import io
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ReportService:
    """Service para geração de relatórios de equipamentos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_dynamic_metadata(self) -> Dict[str, Any]:
        """
        Obtém metadados dinâmicos do banco de dados
        Retorna fabricantes, modelos, barramentos reais
        """
        try:
            # Usar connection com context manager
            from api.core.database import engine
            
            with engine.connect() as conn:
                # Total de equipamentos
                total_query = text("""
                    SELECT COUNT(*) as total FROM protec_ai.relay_equipment
                """)
                total_result = conn.execute(total_query).fetchone()
                
                # Fabricantes únicos (corrigido para usar tabelas existentes)
                manufacturers_query = text("""
                    SELECT DISTINCT f.nome_completo as name, 
                           COUNT(DISTINCT re.id) as count
                    FROM protec_ai.fabricantes f
                    LEFT JOIN protec_ai.relay_models rm ON f.id = rm.manufacturer_id
                    LEFT JOIN protec_ai.relay_equipment re ON rm.id = re.relay_model_id
                    GROUP BY f.nome_completo
                    HAVING COUNT(DISTINCT re.id) > 0
                    ORDER BY count DESC
                """)
                manufacturers = conn.execute(manufacturers_query).fetchall()
                
                # Modelos únicos (corrigido)
                # Modelos únicos
                models_query = text("""
                    SELECT DISTINCT rm.model_name, 
                           f.nome_completo as manufacturer,
                           COUNT(*) as count
                    FROM protec_ai.relay_equipment re
                    JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                    JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                    GROUP BY rm.model_name, f.nome_completo
                    ORDER BY count DESC
                """)
                models = conn.execute(models_query).fetchall()
                
                # Barramentos únicos (usar coluna correta)
                busbars_query = text("""
                    SELECT DISTINCT bay_name, COUNT(*) as count
                    FROM protec_ai.relay_equipment
                    WHERE bay_name IS NOT NULL AND bay_name != '' AND bay_name != 'Unknown'
                    GROUP BY bay_name
                    ORDER BY count DESC
                """)
                busbars = conn.execute(busbars_query).fetchall()
            
            return {
                "total_equipments": total_result.total if total_result else 0,
                "manufacturers": [
                    {"name": m.name, "count": m.count} 
                    for m in manufacturers
                ],
                "models": [
                    {
                        "name": m.model_name,
                        "manufacturer": m.manufacturer,
                        "count": m.count
                    }
                    for m in models
                ],
                "busbars": [
                    {"name": b.bay_name, "count": b.count}
                    for b in busbars
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting dynamic metadata: {e}")
            return {
                "total_equipments": 0,
                "manufacturers": [],
                "models": [],
                "busbars": []
            }
    
    async def get_manufacturers(self) -> List[Dict[str, Any]]:
        """Retorna lista de fabricantes únicos"""
        metadata = await self.get_dynamic_metadata()
        return metadata.get("manufacturers", [])
    
    async def get_models(self, manufacturer: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna lista de modelos (com filtro opcional por fabricante)"""
        metadata = await self.get_dynamic_metadata()
        models = metadata.get("models", [])
        
        if manufacturer:
            models = [m for m in models if m["manufacturer"].lower() == manufacturer.lower()]
        
        return models
    
    async def get_families(self) -> List[Dict[str, str]]:
        """
        Infere famílias de relés baseado nos nomes dos modelos
        """
        models = await self.get_models()
        families = {}
        
        for model in models:
            model_name = model["name"].upper()
            
            # Inferir família pelo nome
            if "SEPAM" in model_name:
                family = "SEPAM"
            elif "MICOM" in model_name or "P12" in model_name or "P14" in model_name:
                family = "MICOM"
            elif "7S" in model_name or "SIEMENS" in model_name:
                family = "SIEMENS_7S"
            elif "SEL" in model_name:
                family = "SEL"
            elif "REF" in model_name:
                family = "ABB_REF"
            elif "MULTILIN" in model_name:
                family = "GE_MULTILIN"
            else:
                family = "OUTROS"
            
            if family not in families:
                families[family] = {"name": family, "count": 0}
            families[family]["count"] += model.get("count", 0)
        
        return list(families.values())
    
    async def get_busbars(self) -> List[Dict[str, Any]]:
        """Retorna lista de barramentos únicos"""
        metadata = await self.get_dynamic_metadata()
        return metadata.get("busbars", [])
    
    async def get_filtered_equipments(
        self,
        filters: Dict[str, Any],
        page: int = 1,
        size: int = 100
    ) -> Tuple[List[Dict], int]:
        """
        Busca equipamentos com filtros aplicados
        """
        try:
            from api.core.database import engine
            
            # Construir query base
            where_clauses = []
            params = {}
            
            if filters.get("manufacturer"):
                where_clauses.append("f.nome_completo ILIKE :manufacturer")
                params["manufacturer"] = f"%{filters['manufacturer']}%"
            
            if filters.get("model"):
                where_clauses.append("rm.model_name ILIKE :model")
                params["model"] = f"%{filters['model']}%"
            
            if filters.get("status"):
                where_clauses.append("re.status = :status")
                params["status"] = filters["status"]
            
            if filters.get("busbar"):
                where_clauses.append("re.bay_name ILIKE :busbar")
                params["busbar"] = f"%{filters['busbar']}%"
            
            # Filtro por família (inferido do nome do modelo)
            if filters.get("family"):
                family = filters["family"]
                if family == "SEPAM":
                    where_clauses.append("rm.model_name ILIKE '%SEPAM%'")
                elif family == "MICOM":
                    where_clauses.append("(rm.model_name ILIKE '%MICOM%' OR rm.model_name ILIKE '%P12%')")
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            with engine.connect() as conn:
                # Count total
                count_query = text(f"""
                    SELECT COUNT(*) as total
                    FROM protec_ai.relay_equipment re
                    JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                    JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                    WHERE {where_sql}
                """)
                total_result = conn.execute(count_query, params).fetchone()
                total = total_result.total if total_result else 0
                
                # Fetch data
                offset = (page - 1) * size
                data_query = text(f"""
                    SELECT 
                        re.id,
                        re.equipment_tag,
                        re.serial_number,
                        re.bay_name,
                        re.status,
                        re.position_description,
                        rm.model_name,
                        rm.technology as model_type,
                        f.nome_completo as manufacturer_name,
                        f.pais_origem as manufacturer_country,
                        re.created_at
                    FROM protec_ai.relay_equipment re
                    JOIN protec_ai.relay_models rm ON re.relay_model_id = rm.id
                    JOIN protec_ai.fabricantes f ON rm.manufacturer_id = f.id
                    WHERE {where_sql}
                    ORDER BY re.id
                    LIMIT :size OFFSET :offset
                """)
                params["size"] = size
                params["offset"] = offset
                
                results = conn.execute(data_query, params).fetchall()
                
                data = [
                    {
                        "id": r.id,
                        "tag": r.equipment_tag,
                        "serial_number": r.serial_number,
                        "bay": r.bay_name,
                        "status": r.status,
                        "description": r.position_description,
                        "model": r.model_name,
                        "model_type": r.model_type,
                        "manufacturer": r.manufacturer_name,
                        "country": r.manufacturer_country,
                        "created_at": r.created_at.isoformat() if r.created_at else None
                    }
                    for r in results
                ]
                
                return data, total
                
        except Exception as e:
            logger.error(f"Error getting filtered equipments: {e}")
            return [], 0
    
    async def export_to_csv(self, filters: Dict[str, Any]) -> Tuple[bytes, str]:
        """Exporta relatório para CSV"""
        try:
            equipments, _ = await self.get_filtered_equipments(filters, page=1, size=10000)
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'ID', 'Tag', 'Serial Number', 'Model', 'Manufacturer', 
                'Bay', 'Status', 'Description', 'Created At'
            ])
            
            # Data
            for eq in equipments:
                writer.writerow([
                    eq['id'],
                    eq['tag'],
                    eq['serial_number'],
                    eq['model'],
                    eq['manufacturer'],
                    eq['bay'],
                    eq['status'],
                    eq['description'],
                    eq['created_at']
                ])
            
            filename = f"relay_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            content = output.getvalue().encode('utf-8')
            
            return content, filename
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            raise
    
    async def export_to_xlsx(self, filters: Dict[str, Any]) -> Tuple[bytes, str]:
        """Exporta relatório para Excel (XLSX)"""
        try:
            # Importar openpyxl apenas quando necessário
            try:
                from openpyxl import Workbook
                from openpyxl.styles import Font, PatternFill, Alignment
            except ImportError:
                logger.error("openpyxl not installed - falling back to CSV")
                return await self.export_to_csv(filters)
            
            equipments, _ = await self.get_filtered_equipments(filters, page=1, size=10000)
            
            # Criar workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Relay Equipment Report"
            
            # Header com formatação
            headers = ['ID', 'Tag', 'Serial Number', 'Model', 'Manufacturer', 
                      'Bay', 'Status', 'Description', 'Created At']
            ws.append(headers)
            
            # Estilizar header
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Data
            for eq in equipments:
                ws.append([
                    eq['id'],
                    eq['tag'],
                    eq['serial_number'],
                    eq['model'],
                    eq['manufacturer'],
                    eq['bay'],
                    eq['status'],
                    eq['description'],
                    eq['created_at']
                ])
            
            # Auto-ajustar largura das colunas
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            
            # Salvar em bytes
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            filename = f"relay_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return output.getvalue(), filename
            
        except Exception as e:
            logger.error(f"Error exporting to XLSX: {e}")
            raise
    
    async def export_to_pdf(self, filters: Dict[str, Any]) -> Tuple[bytes, str]:
        """Exporta relatório para PDF"""
        try:
            # Importar reportlab apenas quando necessário
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
            except ImportError:
                logger.error("reportlab not installed - falling back to CSV")
                return await self.export_to_csv(filters)
            
            equipments, _ = await self.get_filtered_equipments(filters, page=1, size=10000)
            
            # Criar PDF
            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=landscape(A4))
            elements = []
            
            # Estilos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#366092'),
                spaceAfter=30,
                alignment=1  # Center
            )
            
            # Título
            title = Paragraph("Relatório de Equipamentos de Proteção", title_style)
            elements.append(title)
            elements.append(Spacer(1, 0.25*inch))
            
            # Info
            info_text = f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>"
            info_text += f"Total de equipamentos: {len(equipments)}"
            info = Paragraph(info_text, styles['Normal'])
            elements.append(info)
            elements.append(Spacer(1, 0.5*inch))
            
            # Tabela
            table_data = [
                ['Tag', 'Serial', 'Model', 'Manufacturer', 'Bay', 'Status']
            ]
            
            for eq in equipments[:100]:  # Limitar a 100 para não explodir o PDF
                table_data.append([
                    eq['tag'][:20],
                    eq['serial_number'][:15],
                    eq['model'][:25],
                    eq['manufacturer'][:20],
                    eq['bay'][:15] if eq['bay'] else '',
                    eq['status']
                ])
            
            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#366092')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            output.seek(0)
            
            filename = f"relay_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            return output.getvalue(), filename
            
        except Exception as e:
            logger.error(f"Error exporting to PDF: {e}")
            raise
