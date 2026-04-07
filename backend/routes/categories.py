from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from datetime import datetime
from database import db
from models import Category, CategoryCreate, DEFAULT_CATEGORIES
from auth import get_current_user
from helpers import init_default_categories

router = APIRouter(prefix="/api")


@router.post("/init")
async def initialize_defaults(user: Dict = Depends(get_current_user)):
    await init_default_categories(user["user_id"])
    return {"message": "Defaults initialized"}


@router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate, user: Dict = Depends(get_current_user)):
    cat = Category(**category.model_dump(), user_id=user["user_id"])
    doc = cat.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.categories.insert_one(doc)
    return cat


@router.get("/categories", response_model=List[Category])
async def get_categories(user: Dict = Depends(get_current_user)):
    categories = await db.categories.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    if len(categories) == 0:
        await init_default_categories(user["user_id"])
        categories = await db.categories.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    for cat in categories:
        if isinstance(cat.get('created_at'), str):
            cat['created_at'] = datetime.fromisoformat(cat['created_at'])
    return categories


@router.put("/categories/{category_id}", response_model=Category)
async def update_category(category_id: str, category: CategoryCreate, user: Dict = Depends(get_current_user)):
    update_data = category.model_dump()
    result = await db.categories.find_one_and_update(
        {"id": category_id, "user_id": user["user_id"]},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    if '_id' in result:
        del result['_id']
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Category(**result)


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str, user: Dict = Depends(get_current_user)):
    cat = await db.categories.find_one({"id": category_id, "user_id": user["user_id"]})
    if cat and cat.get('is_default'):
        raise HTTPException(status_code=400, detail="Cannot delete default category")
    result = await db.categories.delete_one({"id": category_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted"}


@router.post("/categories/restore-defaults")
async def restore_default_categories(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    restored = 0
    for cat_data in DEFAULT_CATEGORIES:
        existing = await db.categories.find_one({"name": cat_data["name"], "is_default": True, "user_id": uid})
        if not existing:
            cat = Category(**cat_data, user_id=uid)
            doc = cat.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.categories.insert_one(doc)
            restored += 1
    valid_cat_ids = set()
    async for c in db.categories.find({"user_id": uid}, {"id": 1, "_id": 0}):
        valid_cat_ids.add(c["id"])
    orphaned = await db.transactions.update_many(
        {"user_id": uid, "category_id": {"$ne": None, "$nin": list(valid_cat_ids)}},
        {"$set": {"category_id": None}}
    )
    return {"message": f"Restored {restored} default categories, cleared {orphaned.modified_count} orphaned references", "restored": restored, "orphaned_cleared": orphaned.modified_count}


@router.post("/categories/fix-orphaned")
async def fix_orphaned_categories(user: Dict = Depends(get_current_user)):
    uid = user["user_id"]
    valid_cat_ids = set()
    async for c in db.categories.find({"user_id": uid}, {"id": 1, "_id": 0}):
        valid_cat_ids.add(c["id"])
    result = await db.transactions.update_many(
        {"user_id": uid, "category_id": {"$ne": None, "$nin": list(valid_cat_ids)}},
        {"$set": {"category_id": None}}
    )
    return {"message": f"Cleared {result.modified_count} orphaned category references", "cleared": result.modified_count}
