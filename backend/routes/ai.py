import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from database import db
from auth import get_current_user
from helpers import init_default_categories, ai_categorize_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/ai-categorize")
async def ai_categorize_transactions(
    transaction_ids: List[str] = [],
    user: Dict = Depends(get_current_user)
):
    uid = user["user_id"]

    categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)
    if len(categories) == 0:
        await init_default_categories(uid)
        categories = await db.categories.find({"user_id": uid}, {"_id": 0}).to_list(200)

    query = {"user_id": uid, "category_id": None, "is_transfer": False}
    if transaction_ids:
        query["id"] = {"$in": transaction_ids}

    txns = await db.transactions.find(query, {"_id": 0}).to_list(5000)
    if not txns:
        return {"message": "No uncategorized transactions found", "categorized_count": 0}

    try:
        categorized_count = await ai_categorize_batch(uid, txns, categories)
        return {
            "message": f"Categorized {categorized_count} of {len(txns)} transactions",
            "categorized_count": categorized_count,
            "total_uncategorized": len(txns),
        }
    except Exception as e:
        logger.error(f"AI categorization error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI categorization failed: {str(e)}")
