from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.modules.datasets.application.catalog import DatasetCatalog
from app.modules.datasets.application.ports import DatasetRepository
from app.modules.datasets.infrastructure.repository import SqlAlchemyDatasetRepository
from app.modules.identity.api.dependencies import get_current_user
from app.modules.identity.domain.user import User


def get_dataset_repository(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> DatasetRepository:
    """O repositório nasce já preso ao usuário autenticado."""
    return SqlAlchemyDatasetRepository(session, user.id)


def get_dataset_catalog(
    user: Annotated[User, Depends(get_current_user)],
    datasets: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> DatasetCatalog:
    return DatasetCatalog(datasets, user.id)
