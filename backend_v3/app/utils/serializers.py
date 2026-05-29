"""
MongoDB document serializers for API responses.
"""
from datetime import datetime

try:
    from bson import ObjectId
except Exception:  # pragma: no cover
    ObjectId = None


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()

    if ObjectId is not None and isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, list):
        return [_serialize_value(item) for item in value]

    if isinstance(value, dict):
        return serialize_mongodb_document(value)

    return value


def serialize_mongodb_document(doc):
    """Remove Mongo internal _id and recursively normalize values for JSON."""
    if not doc:
        return doc

    serialized = {}
    for key, value in dict(doc).items():
        if key == "_id":
            continue
        serialized[key] = _serialize_value(value)
    return serialized


def serialize_list(docs):
    """Serialize a list of MongoDB documents."""
    return [serialize_mongodb_document(doc) for doc in docs]
