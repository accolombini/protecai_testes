# Tests - Análises e Validações

Esta pasta contém todos os testes, análises e validações do projeto.

## 📁 Estrutura

### `/audit/`
Scripts de auditoria e verificação:
- `audit_complete_pipeline.py` - Auditoria completa do pipeline
- `audit_database_vs_inputs.py` - Verificação banco vs inputs
- `audit_database_vs_pipeline.py` - Verificação banco vs pipeline

### `/analysis/`
Scripts de análise exploratória:
- Análise de checkboxes em PDFs
- Análise de glossários
- Análise de padrões de normalização
- Análise de estrutura de PDFs
- Análise de fontes e caracteres

### `/calibration/`
Scripts de calibração de detecção:
- `calibrate_checkbox_precision.py` - Calibração de precisão
- `calibrate_p922_checkboxes.py` - Calibração específica P922

### `/debug/`
Scripts de debug e diagnóstico:
- Debug de detecção de checkboxes
- Debug de extração de páginas específicas
- Debug de falsos positivos
- Diagnóstico de correlações

### Testes principais (raiz)
- `test_*.py` - Testes funcionais e de integração
- `validate_*.py` - Scripts de validação
- `conftest.py` - Configurações de pytest

## 🔧 Uso

Execute testes com pytest:
```bash
pytest tests/
```

Execute scripts de análise individualmente:
```bash
python tests/analysis/analyze_pdf_structure.py
```

---

**Última atualização**: 05/01/2026
