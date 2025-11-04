# # app/routes/threads.py
# from typing import Any, Dict, List
# from fastapi import APIRouter, Depends, HTTPException, Body, Query
# from app.db.deps import get_sb
# from app.repository import threads as repo
# from app.schemas.thread import IngestRequest, IngestResponse, ThreadOut
# # 권장: 연결 세부 구현에 덜 의존하도록 supabase에서 예외 임포트
# from app.db.supabase import ConfigError  

# router = APIRouter(tags=["threads"])

# def _to_dict(model) -> Dict[str, Any]:
#     # pydantic v2/v1 호환 변환
#     if hasattr(model, "model_dump"):   # v2
#         return model.model_dump(by_alias=False)
#     return model.dict(by_alias=False)  # v1

# @router.post("/ingest", response_model=IngestResponse)
# def ingest(payload: IngestRequest = Body(...), sb=Depends(get_sb)):
#     try:
#         data = _to_dict(payload)  # {'title','owner_id','messages':[{'role','content'},...]}
#         tid = repo.insert_thread(sb, data)
#         repo.insert_messages(sb, tid, data["messages"])
#         return {"thread_id": tid, "status": "saved"}
#     except (ValueError, ConfigError) as e:
#         raise HTTPException(status_code=400, detail=f"Value/Config Error: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

# @router.get("/threads/{thread_id}", response_model=ThreadOut)
# def get_thread(thread_id: str, sb=Depends(get_sb)):
#     try:
#         data = repo.fetch_thread(sb, thread_id)
#         if data is None:
#             raise HTTPException(status_code=404, detail="Thread not found")
#         return data   # repo가 ThreadOut 스키마 키에 맞춰 dict를 반환해야 함
#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"fetch_thread failed: {e}")

# @router.get("/threads", response_model=List[ThreadOut])
# def get_threads(
#     owner_id: str = Query(...),
#     limit: int = Query(..., ge=1, le=1000),
#     offset: int = Query(..., ge=0),
#     sb=Depends(get_sb),
# ):
#     try:
#         return repo.list_threads(sb, owner_id=owner_id, limit=limit, offset=offset)
#         # 반환 형태는 List[ThreadOut] 키 스키마와 일치해야 함
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"list_threads failed: {e}")
