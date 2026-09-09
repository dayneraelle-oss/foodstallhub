"""Data access layer for MongoDB (orders, reviews, analytics)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING, DESCENDING, MongoClient

from app.config import get_settings

_client: Optional[MongoClient] = None
_db: Any = None


def get_mongo_db():
    """Lazily create and cache the shared MongoDB client/db handle."""
    global _client, _db
    if _client is None:
        settings = get_settings()
        _client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=3000,
        )
        _db = _client[settings.MONGO_DB_NAME]
        _ensure_indexes(_db)
    return _db


def _ensure_indexes(db) -> None:
    db.orders.create_index([("user_id", ASCENDING)])
    db.orders.create_index([("stall_id", ASCENDING)])
    db.orders.create_index([("stall_id", ASCENDING), ("status", ASCENDING)])
    db.orders.create_index([("created_at", DESCENDING)])
    db.reviews.create_index([("stall_id", ASCENDING)])
    db.reviews.create_index([("order_id", ASCENDING)], unique=True)
    db.reviews.create_index([("user_id", ASCENDING)])


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------- orders


def create_order(document: Dict[str, Any]) -> str:
    db = get_mongo_db()
    db.orders.insert_one(document)
    return str(document["_id"])


def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    return db.orders.find_one({"_id": order_id})


def list_orders_by_user(user_id: int, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    return (
        list(
            db.orders.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
    )


def list_orders_by_stall(
    stall_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    query: Dict[str, Any] = {"stall_id": stall_id}
    if status:
        query["status"] = status
    return list(
        db.orders.find(query)
        .sort("created_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )


def list_orders_by_stalls(
    stall_ids: List[int],
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    return (
        list(
            db.orders.find({"stall_id": {"$in": stall_ids}})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
    )


def update_order_status(order_id: str, status: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    result = db.orders.update_one(
        {"_id": order_id},
        {"$set": {"status": status, "updated_at": utc_now_iso()}},
    )
    if result.matched_count == 0:
        return None
    return db.orders.find_one({"_id": order_id})


def cancel_order(order_id: str) -> Optional[Dict[str, Any]]:
    return update_order_status(order_id, "cancelled")


def count_orders() -> int:
    db = get_mongo_db()
    return db.orders.count_documents({})


# ---------------------------------------------------------------- reviews


def create_review(document: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a review, overwriting any previous review for the same order."""
    db = get_mongo_db()
    db.reviews.replace_one(
        {"order_id": document["order_id"]},
        document,
        upsert=True,
    )
    return document


def get_review_by_order(order_id: str) -> Optional[Dict[str, Any]]:
    db = get_mongo_db()
    return db.reviews.find_one({"order_id": order_id})


def list_reviews_by_stall(
    stall_id: int,
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    return (
        list(
            db.reviews.find({"stall_id": stall_id})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
    )


def list_reviews_by_user(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    db = get_mongo_db()
    return (
        list(
            db.reviews.find({"user_id": user_id})
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
    )


def count_reviews_for_stall(stall_id: int) -> int:
    db = get_mongo_db()
    return db.reviews.count_documents({"stall_id": stall_id})


def average_rating_for_stall(stall_id: int) -> Optional[float]:
    db = get_mongo_db()
    pipeline = [
        {"$match": {"stall_id": stall_id}},
        {"$group": {"_id": None, "avg": {"$avg": "$rating"}}},
    ]
    result = list(db.reviews.aggregate(pipeline))
    if not result:
        return None
    return round(result[0]["avg"], 2)


# ---------------------------------------------------------------- analytics


# ---------------------------------------------------------------- delivery tracking


def upsert_rider_location(
    order_id: str,
    lat: float,
    lng: float,
) -> Optional[Dict[str, Any]]:
    """Append a live rider location point to an order's tracking history."""
    db = get_mongo_db()
    point = {
        "lat": lat,
        "lng": lng,
        "timestamp": utc_now_iso(),
    }
    result = db.orders.update_one(
        {"_id": order_id},
        {"$push": {"delivery_tracking": point}},
    )
    if result.matched_count == 0:
        return None
    return point


def get_delivery_tracking(order_id: str) -> Optional[List[Dict[str, Any]]]:
    """Return the rider's location history for an order (newest first)."""
    db = get_mongo_db()
    doc = db.orders.find_one({"_id": order_id}, {"delivery_tracking": 1})
    if doc is None:
        return None
    points = doc.get("delivery_tracking", [])
    return list(reversed(points))


def stall_stats(stall_id: int) -> Dict[str, Any]:
    """Orders, revenue, cancellation count and top items for one stall."""
    db = get_mongo_db()

    pipeline = [
        {"$match": {"stall_id": stall_id}},
        {
            "$group": {
                "_id": None,
                "orders_count": {"$sum": 1},
                "revenue": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", "cancelled"]},
                            0,
                            "$total",
                        ]
                    }
                },
                "cancelled": {
                    "$sum": {
                        "$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]
                    }
                },
            }
        },
    ]
    agg = list(db.orders.aggregate(pipeline))
    stats = agg[0] if agg else {}

    top_items_pipeline = [
        {"$match": {"stall_id": stall_id, "status": {"$ne": "cancelled"}}},
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$items.name",
                "quantity": {"$sum": "$items.quantity"},
                "revenue": {
                    "$sum": {
                        "$multiply": ["$items.price", "$items.quantity"]
                    }
                },
            }
        },
        {"$sort": {"quantity": DESCENDING}},
        {"$limit": 5},
    ]
    top_items = [
        {"name": row["_id"], "quantity": row["quantity"], "revenue": round(row["revenue"], 2)}
        for row in db.orders.aggregate(top_items_pipeline)
    ]

    return {
        "orders_count": int(stats.get("orders_count", 0)),
        "revenue": round(float(stats.get("revenue", 0.0)), 2),
        "cancelled_count": int(stats.get("cancelled", 0)),
        "top_items": top_items,
    }