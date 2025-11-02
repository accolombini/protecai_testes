"""
Serviço de geração de relatórios PDF para testes do sistema.
Gera relatórios profissionais com cabeçalho PETROBRAS, gráficos e métricas.
"""
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.flowables import Image
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class SystemTestReportService:
    """Serviço para geração de relatórios de teste do sistema em PDF."""
    
    # Cores PETROBRAS
    PETROBRAS_BLUE = colors.HexColor('#366092')
    PETROBRAS_GREEN = colors.HexColor('#00A859')
    PETROBRAS_YELLOW = colors.HexColor('#FDB913')
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Configura estilos customizados para o documento."""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=20,
            textColor=self.PETROBRAS_BLUE,
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica'
        ))
        
        # Cabeçalho de seção
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.PETROBRAS_BLUE,
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
    
    def generate_pdf_report(
        self,
        system_status: Dict[str, Any],
        logs: List[Dict[str, Any]],
        timestamp: str
    ) -> BytesIO:
        """
        Gera relatório PDF completo do teste do sistema.
        
        Args:
            system_status: Status dos componentes (backend, postgres, apis, equipment)
            logs: Lista de logs de execução dos testes
            timestamp: Timestamp ISO da execução
        
        Returns:
            BytesIO contendo o PDF gerado
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        story = []
        
        # Cabeçalho PETROBRAS
        story.extend(self._create_header(timestamp))
        
        # Resumo executivo
        story.extend(self._create_executive_summary(system_status))
        
        # Gráfico de status
        story.extend(self._create_status_chart(system_status))
        
        # Tabela de componentes
        story.extend(self._create_components_table(system_status))
        
        # Métricas de performance
        story.extend(self._create_performance_metrics(system_status))
        
        # Logs detalhados
        if logs:
            story.append(PageBreak())
            story.extend(self._create_logs_section(logs))
        
        # Gerar PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _create_header(self, timestamp: str) -> List:
        """Cria cabeçalho do relatório com branding PETROBRAS."""
        elements = []
        
        # Título
        title = Paragraph(
            "PETROBRAS - ProtecAI",
            self.styles['CustomTitle']
        )
        elements.append(title)
        
        # Subtítulo
        subtitle = Paragraph(
            "Relatório de Validação do Sistema",
            self.styles['CustomSubtitle']
        )
        elements.append(subtitle)
        
        # Data/hora
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        date_text = dt.strftime('%d/%m/%Y às %H:%M:%S')
        date_para = Paragraph(
            f"<i>Gerado em: {date_text}</i>",
            self.styles['Normal']
        )
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_executive_summary(self, system_status: Dict[str, Any]) -> List:
        """Cria resumo executivo com status geral."""
        elements = []
        
        # Título da seção
        elements.append(Paragraph("Resumo Executivo", self.styles['SectionHeader']))
        
        # Contar status
        components = ['backend', 'postgres', 'apis', 'equipment']
        total = len(components)
        passed = sum(1 for c in components if system_status.get(c, {}).get('status') == 'Operacional')
        failed = sum(1 for c in components if system_status.get(c, {}).get('status') == 'Offline')
        checking = sum(1 for c in components if system_status.get(c, {}).get('status') == 'Verificando...')
        
        # Tabela de resumo
        summary_data = [
            ['Componentes Totais', str(total)],
            ['Operacionais', str(passed)],
            ['Offline', str(failed)],
            ['Verificando', str(checking)],
        ]
        
        summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.PETROBRAS_BLUE),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_status_chart(self, system_status: Dict[str, Any]) -> List:
        """Cria gráfico de pizza com distribuição de status."""
        elements = []
        
        elements.append(Paragraph("Distribuição de Status", self.styles['SectionHeader']))
        
        # Contar status
        components = ['backend', 'postgres', 'apis', 'equipment']
        passed = sum(1 for c in components if system_status.get(c, {}).get('status') == 'Operacional')
        failed = sum(1 for c in components if system_status.get(c, {}).get('status') == 'Offline')
        checking = sum(1 for c in components if system_status.get(c, {}).get('status') == 'Verificando...')
        
        # Criar gráfico de pizza
        drawing = Drawing(400, 200)
        pie = Pie()
        pie.x = 150
        pie.y = 50
        pie.width = 150
        pie.height = 150
        
        pie.data = [passed, failed, checking]
        pie.labels = ['Operacional', 'Offline', 'Verificando']
        pie.slices.strokeWidth = 0.5
        pie.slices[0].fillColor = self.PETROBRAS_GREEN
        pie.slices[1].fillColor = colors.red
        pie.slices[2].fillColor = self.PETROBRAS_YELLOW
        
        drawing.add(pie)
        elements.append(drawing)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_components_table(self, system_status: Dict[str, Any]) -> List:
        """Cria tabela detalhada de componentes."""
        elements = []
        
        elements.append(Paragraph("Detalhamento dos Componentes", self.styles['SectionHeader']))
        
        # Dados da tabela
        data = [['Componente', 'Status', 'Tempo de Resposta (ms)']]
        
        component_names = {
            'backend': 'Backend FastAPI',
            'postgres': 'PostgreSQL Database',
            'apis': 'APIs REST',
            'equipment': 'Equipment Service'
        }
        
        for key, name in component_names.items():
            comp = system_status.get(key, {})
            status = comp.get('status', 'N/A')
            response_time = comp.get('responseTime', 0)
            data.append([name, status, f"{response_time:.0f}" if response_time else 'N/A'])
        
        # Criar tabela
        table = Table(data, colWidths=[7*cm, 5*cm, 5*cm])
        table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), self.PETROBRAS_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            # Corpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Colorir linhas alternadas
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_performance_metrics(self, system_status: Dict[str, Any]) -> List:
        """Cria gráfico de barras com métricas de performance."""
        elements = []
        
        elements.append(Paragraph("Métricas de Performance", self.styles['SectionHeader']))
        
        # Dados para o gráfico
        components = ['Backend', 'PostgreSQL', 'APIs', 'Equipment']
        response_times = [
            system_status.get('backend', {}).get('responseTime', 0),
            system_status.get('postgres', {}).get('responseTime', 0),
            system_status.get('apis', {}).get('responseTime', 0),
            system_status.get('equipment', {}).get('responseTime', 0),
        ]
        
        # Criar gráfico de barras
        drawing = Drawing(400, 200)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300
        chart.data = [response_times]
        chart.categoryAxis.categoryNames = components
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = max(response_times) * 1.2 if max(response_times) > 0 else 100
        chart.bars[0].fillColor = self.PETROBRAS_BLUE
        
        drawing.add(chart)
        elements.append(drawing)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_logs_section(self, logs: List[Dict[str, Any]]) -> List:
        """Cria seção de logs detalhados."""
        elements = []
        
        elements.append(Paragraph("Logs de Execução", self.styles['SectionHeader']))
        
        # Criar tabela de logs
        data = [['Timestamp', 'Componente', 'Status', 'Mensagem']]
        
        for log in logs:
            timestamp = log.get('timestamp', '')
            component = log.get('component', '')
            status = log.get('status', '')
            message = log.get('message', '')
            
            # Formatar timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp_str = dt.strftime('%H:%M:%S')
            except:
                timestamp_str = timestamp
            
            data.append([
                timestamp_str,
                component,
                status,
                message[:50] + '...' if len(message) > 50 else message
            ])
        
        # Criar tabela
        table = Table(data, colWidths=[2.5*cm, 3.5*cm, 3*cm, 8*cm])
        table.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), self.PETROBRAS_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # Corpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        elements.append(table)
        
        return elements


# Singleton para reutilização
system_test_report_service = SystemTestReportService()
