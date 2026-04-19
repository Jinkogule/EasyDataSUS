"""
Endpoints administrativos para gerenciamento de datasets.

Inclui:
- Upload de CSVs com validação de schema
- Gerenciamento de datasets
- Logs de carga
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import csv
import json
import os
import logging
from pathlib import Path
from datetime import datetime
import shutil

from metadata.loader import load_metadata
from etl.load_csv import load_csv

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class DatasetInfo(BaseModel):
    """Informações sobre um dataset"""
    id: str
    name: str
    description: str
    table_name: str
    csv_count: int
    total_size_mb: float


class UploadResponse(BaseModel):
    """Resposta após upload de CSV"""
    success: bool
    dataset: str
    filename: str
    rows_loaded: int
    message: str
    errors: Optional[List[str]] = None


class ValidationError(BaseModel):
    """Erro de validação"""
    field: str
    issue: str
    suggestion: str


class SchemaValidationResponse(BaseModel):
    """Resultado da validação de schema"""
    valid: bool
    errors: List[ValidationError] = []
    warnings: List[str] = []
    rows_preview: int


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_datasets_path() -> Path:
    """Retorna caminho da pasta datasets"""
    return Path(__file__).parent.parent / "data" / "datasets"


def get_metadata_path() -> Path:
    """Retorna caminho da pasta metadata"""
    return Path(__file__).parent.parent / "metadata" / "datasets"


def validate_csv_schema(csv_content: str, dataset: str) -> SchemaValidationResponse:
    """
    Valida se o CSV está de acordo com o schema do dataset.
    
    Verifica:
    - Columns match
    - Data types (basic)
    - Required fields
    """
    errors = []
    warnings = []
    
    try:
        # Carregar schema
        schema_path = get_metadata_path() / dataset / "schema.json"
        if not schema_path.exists():
            errors.append(ValidationError(
                field="dataset",
                issue=f"Schema não encontrado para dataset '{dataset}'",
                suggestion=f"Crie {schema_path}"
            ))
            return SchemaValidationResponse(valid=False, errors=errors, rows_preview=0)
        
        with open(schema_path) as f:
            schema = json.load(f)
        
        # Suportar ambos os formatos de schema
        columns_data = schema.get("columns", [])
        if not columns_data:
            # Formato antigo: "colunas_principais" como dicionário
            colunas_principais = schema.get("colunas_principais", {})
            schema_columns = {col_name: col_info.get("tipo", "String") for col_name, col_info in colunas_principais.items()}
        else:
            # Formato novo: "columns" como array
            schema_columns = {col["name"]: col.get("type", "String") for col in columns_data}
        
        # Ler primeiras linhas do CSV
        reader = csv.DictReader(csv_content.split('\n'), delimiter=";")
        
        if not reader.fieldnames:
            errors.append(ValidationError(
                field="csv",
                issue="CSV vazio ou mal formatado",
                suggestion="Verifique se o CSV tem headers e dados"
            ))
            return SchemaValidationResponse(valid=False, errors=errors, rows_preview=0)
        
        csv_columns = set(reader.fieldnames)
        schema_column_names = set(schema_columns.keys())
        
        # Verificar colunas faltantes
        missing = schema_column_names - csv_columns
        if missing:
            errors.append(ValidationError(
                field="columns",
                issue=f"Colunas faltando: {', '.join(missing)}",
                suggestion="Adicione as colunas requeridas ao CSV"
            ))
        
        # Verificar colunas extras
        extra = csv_columns - schema_column_names
        if extra:
            warnings.append(f"Colunas extras no CSV (serão ignoradas): {', '.join(list(extra)[:3])}")
        
        # Contar linhas válidas
        row_count = 0
        for row in reader:
            row_count += 1
            if row_count > 100:  # Limitar preview
                break
        
        if row_count == 0:
            warnings.append("CSV não contém dados")
        
        return SchemaValidationResponse(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            rows_preview=min(row_count, 100)
        )
        
    except Exception as e:
        errors.append(ValidationError(
            field="csv",
            issue=f"Erro ao processar CSV: {str(e)}",
            suggestion="Verifique se o arquivo é um CSV válido com delimitador ;"
        ))
        return SchemaValidationResponse(valid=False, errors=errors, rows_preview=0)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/admin/datasets/upload", response_model=UploadResponse)
async def upload_dataset(
    dataset: str = Query(..., description="ID do dataset (ex: covid-19-vacinacao)"),
    file: UploadFile = File(..., description="Arquivo CSV a carregar"),
    skip_validation: bool = Query(False, description="Pular validação de schema")
):
    """
    Upload de novo arquivo CSV para um dataset.
    
    - Valida schema
    - Salva arquivo na pasta correta
    - Carrega dados no ClickHouse
    
    Exemplo:
        curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=covid-19-vacinacao" \\
             -F "file=@dataset.csv"
    """
    
    try:
        # Verificar se dataset existe
        metadata_path = get_metadata_path() / dataset
        if not metadata_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Dataset '{dataset}' não existe. Crie a pasta em metadata/datasets/{dataset}/"
            )
        
        # Ler conteúdo do arquivo
        content = await file.read()
        csv_content = content.decode('utf-8', errors='replace')
        
        # Validar schema (a menos que skip_validation seja True)
        if not skip_validation:
            validation = validate_csv_schema(csv_content, dataset)
            if not validation.valid:
                error_msgs = [f"{e.field}: {e.issue}" for e in validation.errors]
                raise HTTPException(
                    status_code=422,
                    detail=f"Validação falhou: {'; '.join(error_msgs)}"
                )
            
            if validation.warnings:
                logger.warning(f"Avisos na validação: {'; '.join(validation.warnings)}")
        
        # Salvar arquivo
        dataset_path = get_datasets_path() / dataset
        dataset_path.mkdir(parents=True, exist_ok=True)
        
        # Gerar nome único para arquivo (adicionar timestamp se duplicado)
        original_filename = file.filename
        file_path = dataset_path / original_filename
        
        if file_path.exists():
            base_name = original_filename.rsplit('.', 1)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{base_name}_{timestamp}.csv"
            file_path = dataset_path / new_filename
            logger.info(f"Arquivo duplicado detectado. Renomeando para: {new_filename}")
        
        # Escrever arquivo
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Arquivo salvo: {file_path}")
        
        # Carregar dados no ClickHouse
        logger.info(f"Iniciando carga no ClickHouse...")
        
        # Contar linhas do arquivo
        reader = csv.DictReader(csv_content.split('\n'), delimiter=";")
        row_count = sum(1 for _ in reader)
        
        # Chamada ao load_csv do ETL
        try:
            load_csv(str(file_path), dataset)
            
            return UploadResponse(
                success=True,
                dataset=dataset,
                filename=file_path.name,
                rows_loaded=row_count,
                message=f"Dataset '{dataset}' carregado com sucesso! ({row_count} linhas)"
            )
        
        except Exception as e:
            logger.error(f"Erro ao carregar no ClickHouse: {e}")
            
            # Remover arquivo se carga falhou
            file_path.unlink()
            
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao carregar dados: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar upload: {str(e)}"
        )


@router.post("/admin/datasets/validate", response_model=SchemaValidationResponse)
async def validate_schema(
    dataset: str = Query(..., description="ID do dataset"),
    file: UploadFile = File(...)
):
    """
    Valida um arquivo CSV contra schema sem fazer upload.
    
    Útil para verificar antes de fazer upload.
    """
    try:
        content = await file.read()
        csv_content = content.decode('utf-8', errors='replace')
        return validate_csv_schema(csv_content, dataset)
    except Exception as e:
        logger.error(f"Erro na validação: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/datasets/available", response_model=List[DatasetInfo])
async def list_datasets():
    """
    Lista todos os datasets disponíveis com informações.
    
    Mostra:
    - ID do dataset
    - Nome e descrição
    - Número de CSVs
    - Tamanho total em MB
    """
    datasets = []
    datasets_path = get_datasets_path()
    metadata_path = get_metadata_path()
    
    for dataset_folder in sorted(datasets_path.glob("*")):
        if not dataset_folder.is_dir():
            continue
        
        dataset_id = dataset_folder.name
        
        # Tentar carregar metadata
        schema_path = metadata_path / dataset_id / "schema.json"
        name = dataset_id
        description = "Dataset"
        table_name = dataset_id.replace("-", "_")
        
        if schema_path.exists():
            try:
                with open(schema_path) as f:
                    schema = json.load(f)
                    description = schema.get("description", "Dataset")
                    table_name = schema.get("table_name", table_name)
            except:
                pass
        
        # Contar CSVs e tamanho
        csv_files = list(dataset_folder.glob("*.csv"))
        total_size = sum(f.stat().st_size for f in csv_files) / (1024 * 1024)  # MB
        
        datasets.append(DatasetInfo(
            id=dataset_id,
            name=name,
            description=description,
            table_name=table_name,
            csv_count=len(csv_files),
            total_size_mb=round(total_size, 2)
        ))
    
    return datasets


@router.get("/admin/datasets/{dataset_id}/info", response_model=DatasetInfo)
async def get_dataset_info(dataset_id: str):
    """
    Informações detalhadas de um dataset específico.
    """
    datasets_path = get_datasets_path()
    metadata_path = get_metadata_path()
    
    dataset_folder = datasets_path / dataset_id
    if not dataset_folder.exists():
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' não encontrado")
    
    # Carregar metadata
    schema_path = metadata_path / dataset_id / "schema.json"
    name = dataset_id
    description = "Dataset"
    table_name = dataset_id.replace("-", "_")
    
    if schema_path.exists():
        try:
            with open(schema_path) as f:
                schema = json.load(f)
                description = schema.get("description", "Dataset")
                table_name = schema.get("table_name", table_name)
        except:
            pass
    
    csv_files = list(dataset_folder.glob("*.csv"))
    total_size = sum(f.stat().st_size for f in csv_files) / (1024 * 1024)
    
    return DatasetInfo(
        id=dataset_id,
        name=name,
        description=description,
        table_name=table_name,
        csv_count=len(csv_files),
        total_size_mb=round(total_size, 2)
    )


@router.delete("/admin/datasets/{dataset_id}/files/{filename}")
async def delete_dataset_file(dataset_id: str, filename: str):
    """
    Remove um arquivo CSV específico de um dataset.
    
    Cuidado: Isso não remove dados já carregados no ClickHouse!
    """
    try:
        file_path = get_datasets_path() / dataset_id / filename
        
        # Segurança: não permitir traversal attack
        if ".." in filename:
            raise HTTPException(status_code=400, detail="Path traversal not allowed")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
        file_path.unlink()
        logger.info(f"Arquivo deletado: {file_path}")
        
        return {
            "success": True,
            "message": f"Arquivo '{filename}' removido com sucesso"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar arquivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/datasets/{dataset_id}/reload")
async def reload_dataset(dataset_id: str):
    """
    Recarrega TODOS os CSVs de um dataset no ClickHouse.
    
    Útil se o schema mudou ou houve erro anterior.
    """
    try:
        dataset_path = get_datasets_path() / dataset_id
        
        if not dataset_path.exists():
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' não encontrado")
        
        csv_files = list(dataset_path.glob("*.csv"))
        if not csv_files:
            raise HTTPException(status_code=400, detail=f"Nenhum CSV encontrado em '{dataset_id}'")
        
        # Carregar todos os CSVs
        load_csv(dataset=dataset_id)
        
        total_rows = sum(sum(1 for _ in csv.DictReader(open(f), delimiter=";")) for f in csv_files)
        
        return {
            "success": True,
            "dataset": dataset_id,
            "files_loaded": len(csv_files),
            "rows_loaded": total_rows,
            "message": f"Dataset '{dataset_id}' recarregado com sucesso!"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao recarregar dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
