"""Transaction read routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..queries import PAGE_SIZE
from ..reads import transaction_page
from .schemas import TransactionPage
from .serializers import transaction_response

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionPage)
def list_transactions(
    page: int = Query(default=1, ge=1),
) -> TransactionPage:
    result = transaction_page(page)
    return TransactionPage(
        items=[transaction_response(transaction) for transaction in result.items],
        total=result.total,
        page=page,
        page_size=PAGE_SIZE,
        total_pages=(result.total + PAGE_SIZE - 1) // PAGE_SIZE,
    )
