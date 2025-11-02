"""
Router para endpoints de teste do sistema.
Fornece geração de relatórios PDF dos testes de validação.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime

from ..services.system_test_report_service import system_test_report_service

router = APIRouter(
    prefix="/api/v1/system-test",
    tags=["System Test"]
)


class TestLog(BaseModel):
    """Modelo para log de teste."""
    timestamp: str
    component: str
    status: str
    message: str


class SystemStatus(BaseModel):
    """Modelo para status de componente."""
    status: str
    responseTime: float = 0


class SystemTestReport(BaseModel):
    """Modelo para dados do relatório de teste."""
    timestamp: str
    systemStatus: Dict[str, SystemStatus]
    logs: List[TestLog]


@router.post("/export/pdf")
async def export_pdf_report(report_data: SystemTestReport):
    """
    Gera relatório PDF do teste do sistema.
    
    Args:
        report_data: Dados do relatório (status dos componentes e logs)
    
    Returns:
        StreamingResponse com arquivo PDF
    """
    try:
        # Converter SystemStatus para dict
        system_status_dict = {
            key: {
                'status': value.status,
                'responseTime': value.responseTime
            }
            for key, value in report_data.systemStatus.items()
        }
        
        # Converter TestLog para dict
        logs_dict = [
            {
                'timestamp': log.timestamp,
                'component': log.component,
                'status': log.status,
                'message': log.message
            }
            for log in report_data.logs
        ]
        
        # Gerar PDF
        pdf_buffer = system_test_report_service.generate_pdf_report(
            system_status=system_status_dict,
            logs=logs_dict,
            timestamp=report_data.timestamp
        )
        
        # Criar nome do arquivo com timestamp
        dt = datetime.fromisoformat(report_data.timestamp.replace('Z', '+00:00'))
        filename = f"ProtecAI_System_Test_{dt.strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Retornar PDF como stream
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório PDF: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Endpoint de health check para validação do serviço."""
    return {
        "status": "healthy",
        "service": "system-test",
        "timestamp": datetime.utcnow().isoformat()
    }
