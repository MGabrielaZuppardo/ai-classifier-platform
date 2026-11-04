from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.datasets.api.dependencies import get_dataset_catalog
from app.modules.datasets.application.catalog import (
    DatasetCatalog,
    DatasetNameTakenError,
    DatasetNotFoundError,
)
from app.modules.datasets.domain.dataset import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    Dataset,
)

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])

NOT_FOUND = "Dataset não encontrado"


class CreateDatasetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)


class DatasetResponse(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime

    @classmethod
    def from_entity(cls, dataset: Dataset) -> "DatasetResponse":
        return cls(
            id=dataset.id,
            name=dataset.name,
            description=dataset.description,
            created_at=dataset.created_at,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_dataset(
    body: CreateDatasetRequest,
    catalog: Annotated[DatasetCatalog, Depends(get_dataset_catalog)],
    session: Annotated[Session, Depends(get_session)],
) -> DatasetResponse:
    try:
        dataset = catalog.create(body.name, body.description)
    except DatasetNameTakenError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Você já tem um dataset com esse nome"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    session.commit()
    return DatasetResponse.from_entity(dataset)


@router.get("")
def list_datasets(
    catalog: Annotated[DatasetCatalog, Depends(get_dataset_catalog)],
) -> list[DatasetResponse]:
    return [DatasetResponse.from_entity(d) for d in catalog.list_all()]


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: UUID, catalog: Annotated[DatasetCatalog, Depends(get_dataset_catalog)]
) -> DatasetResponse:
    try:
        return DatasetResponse.from_entity(catalog.get(dataset_id))
    except DatasetNotFoundError as exc:
        # 404 também para dataset de outro usuário: não revela que o id existe.
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND) from exc


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: UUID,
    catalog: Annotated[DatasetCatalog, Depends(get_dataset_catalog)],
    session: Annotated[Session, Depends(get_session)],
) -> None:
    try:
        catalog.delete(dataset_id)
    except DatasetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND) from exc
    session.commit()
