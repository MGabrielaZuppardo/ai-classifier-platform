from datetime import UTC, datetime, timedelta


class GithubAccountTooNewError(Exception):
    def __init__(self, min_age_days: int) -> None:
        super().__init__(f"conta do GitHub com menos de {min_age_days} dias")
        self.min_age_days = min_age_days


def ensure_account_old_enough(
    created_at: datetime, *, min_age_days: int, now: datetime | None = None
) -> None:
    """Rejeita cadastro por contas do GitHub criadas há menos de `min_age_days`.

    `min_age_days=0` desativa a regra. Uma data futura (relógio fora de sincronia) é
    tratada como conta nova demais.
    """
    if min_age_days <= 0:
        return
    if created_at.tzinfo is None:
        raise ValueError("created_at deve ter fuso horário (o GitHub devolve UTC)")

    current = now or datetime.now(UTC)
    if current - created_at < timedelta(days=min_age_days):
        raise GithubAccountTooNewError(min_age_days)
