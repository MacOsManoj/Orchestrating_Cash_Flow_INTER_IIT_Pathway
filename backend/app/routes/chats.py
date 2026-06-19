from fastapi import APIRouter, HTTPException, status
from bson import ObjectId
from datetime import datetime, timezone
from typing import List

from app.models.chat import Chat, ChatCreate
from app.database import get_database

router = APIRouter(prefix="/chats", tags=["chats"])


def serialize_chat(doc: dict) -> Chat:
    """
    Convert a MongoDB chat document into a Chat Pydantic model.
    Handles ObjectId -> str conversions.
    """
    if not doc:
        raise ValueError("Cannot serialize empty chat document")

    # _id -> string
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])

    # currentVersionId -> string (if present and not None)
    if "currentVersionId" in doc and isinstance(doc["currentVersionId"], ObjectId):
        doc["currentVersionId"] = str(doc["currentVersionId"])

    return Chat(**doc)


@router.get("/", response_model=List[Chat])
async def get_all_chats():
    """Get all chats"""
    try:
        db = get_database()
        chats_collection = db["chats"]

        docs = await chats_collection.find().to_list(length=None)
        chats = [serialize_chat(doc) for doc in docs]

        print(f"📚 Retrieved {len(chats)} chats")
        return chats
    except Exception as e:
        print(f"❌ Error fetching chats: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch chats: {str(e)}")


@router.post("/", response_model=Chat, status_code=status.HTTP_201_CREATED)
async def create_chat(data: ChatCreate):
    """Create a new chat"""
    try:
        db = get_database()
        chats_collection = db["chats"]

        now = datetime.now(timezone.utc)

        chat_doc = {
            "title": data.title,
            "createdAt": now,
            "updatedAt": now,
            "currentVersionId": None,
            "messageCount": 0,
            "isActive": True,
        }

        result = await chats_collection.insert_one(chat_doc)
        print(f"✅ Created chat: {result.inserted_id}")

        created_doc = await chats_collection.find_one({"_id": result.inserted_id})
        if not created_doc:
            raise HTTPException(status_code=500, detail="Failed to fetch created chat")

        return serialize_chat(created_doc)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error creating chat: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")


@router.get("/{chat_id}", response_model=Chat)
async def get_chat(chat_id: str):
    """Get single chat"""
    try:
        db = get_database()
        chats_collection = db["chats"]

        try:
            obj_id = ObjectId(chat_id)
        except Exception:
            obj_id = chat_id  # in case you ever use non-ObjectId IDs

        doc = await chats_collection.find_one({"_id": obj_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Chat not found")

        return serialize_chat(doc)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{chat_id}/title", response_model=Chat)
async def update_chat_title(chat_id: str, data: dict):
    """Update chat title"""
    try:
        db = get_database()
        chats_collection = db["chats"]

        try:
            obj_id = ObjectId(chat_id)
        except Exception:
            obj_id = chat_id

        result = await chats_collection.update_one(
            {"_id": obj_id},
            {
                "$set": {
                    "title": data.get("title"),
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Chat not found")

        updated_doc = await chats_collection.find_one({"_id": obj_id})
        if not updated_doc:
            raise HTTPException(status_code=404, detail="Chat not found after update")

        return serialize_chat(updated_doc)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating chat title {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str):
    """Delete chat"""
    try:
        db = get_database()
        chats_collection = db["chats"]

        try:
            obj_id = ObjectId(chat_id)
        except Exception:
            obj_id = chat_id

        result = await chats_collection.delete_one({"_id": obj_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Chat not found")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting chat {chat_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
