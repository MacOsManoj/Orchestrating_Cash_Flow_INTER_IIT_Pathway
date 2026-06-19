# app/routes/versions.py
from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Any, Dict, Tuple, Optional
from app.models.version import Version, VersionCreate
from app.database import get_database
from app.master_orchestrator import process_query

router = APIRouter(prefix="/chats", tags=["versions"])


async def generate_components_for_prompt(prompt: str) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Call the master orchestrator and normalize:
      - Return (message, components_list)
      - components_list is ALWAYS a list[dict]
    """
    try:
        result = await process_query(prompt)
    except Exception as e:
        # Return error message with empty components on failure
        return f"Error processing query: {str(e)}", []

    message: Optional[str] = result.get("message")
    components: List[Dict[str, Any]] = []

    comps = result.get("components", [])
    if isinstance(comps, list):
        components = comps
    elif isinstance(comps, dict):
        components = list(comps.values())

    return message, components


def serialize_version(doc: dict) -> Version:
    """
    Normalize DB doc to match Version model: ensure components is a list.
    """
    d = dict(doc)

    if "_id" in d and isinstance(d["_id"], ObjectId):
        d["_id"] = str(d["_id"])
    if "chatId" in d and isinstance(d["chatId"], ObjectId):
        d["chatId"] = str(d["chatId"])

    comps = d.get("components")

    # Normalize components → list
    if isinstance(comps, dict):
        inner = comps.get("components") if isinstance(comps, dict) else None
        if isinstance(inner, list):
            d["components"] = inner
        else:
            d["components"] = list(comps.values())
    elif not isinstance(comps, list):
        d["components"] = []

    # message just passes through (can be missing/None)
    return Version(**d)


@router.post(
    "/{chat_id}/versions", response_model=Version, status_code=status.HTTP_201_CREATED
)
async def create_version(chat_id: str, data: VersionCreate):
    try:
        db = get_database()
        versions_collection = db["versions"]

        now = datetime.now(timezone.utc)

        # NEW: get both message + components from the master orchestrator
        message, components = await generate_components_for_prompt(data.prompt)

        version_doc: Dict[str, Any] = {
            "chatId": chat_id,
            "versionNumber": data.versionNumber,
            "prompt": data.prompt,
            "message": message,        # ⬅️ store agent text
            "components": components,  # ⬅️ store components list
            "createdAt": now,
        }

        result = await versions_collection.insert_one(version_doc)
        created = await versions_collection.find_one({"_id": result.inserted_id})
        if not created:
            raise HTTPException(
                status_code=500, detail="Failed to fetch created version"
            )
        return serialize_version(created)
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}/versions", response_model=List[Version])
async def get_versions(chat_id: str):
    try:
        db = get_database()
        versions_collection = db["versions"]
        docs = (
            await versions_collection.find({"chatId": chat_id})
            .sort("versionNumber", -1)
            .to_list(length=None)
        )
        return [serialize_version(doc) for doc in docs]
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}/versions/latest", response_model=Version)
async def get_latest_version(chat_id: str):
    try:
        db = get_database()
        versions_collection = db["versions"]
        doc = await versions_collection.find_one(
            {"chatId": chat_id}, sort=[("versionNumber", -1)]
        )
        if not doc:
            raise HTTPException(status_code=404, detail="No versions found")
        return serialize_version(doc)
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
