from __future__ import annotations

from app.schemas.observability import SessionEventRecord, SessionTaskRecord


class ReviewSessionTaskService:
    def build_tasks(self, events: list[SessionEventRecord]) -> list[SessionTaskRecord]:
        tasks: list[SessionTaskRecord] = []
        session_task_id: str | None = None
        llm_task_ids_by_turn: dict[int, str] = {}
        task_by_runtime_id: dict[str, SessionTaskRecord] = {}

        for event in events:
            if event.event_type == "session_started":
                root_task = SessionTaskRecord(
                    task_id=f"task_session_{event.session_id}",
                    session_id=event.session_id,
                    source_event_id=event.event_id,
                    title="Review Session",
                    kind="session",
                    status="running",
                    created_at=event.timestamp,
                    updated_at=event.timestamp,
                    summary="会话执行中",
                )
                session_task_id = root_task.task_id
                tasks.append(root_task)
                continue

            if event.event_type == "model_call_started" and event.turn is not None:
                llm_task = SessionTaskRecord(
                    task_id=f"task_llm_turn_{event.turn}",
                    session_id=event.session_id,
                    parent_task_id=session_task_id,
                    source_event_id=event.event_id,
                    title=f"LLM Turn {event.turn}",
                    kind="llm_turn",
                    status="running",
                    created_at=event.timestamp,
                    updated_at=event.timestamp,
                    summary=f"第 {event.turn} 轮模型调用",
                )
                llm_task_ids_by_turn[event.turn] = llm_task.task_id
                if event.runtime_id:
                    task_by_runtime_id[event.runtime_id] = llm_task
                tasks.append(llm_task)
                continue

            if event.event_type == "tool_call_started" and event.runtime_id:
                tool_name = str(event.payload.get("tool_name") or "tool")
                tool_task = SessionTaskRecord(
                    task_id=f"task_{event.runtime_id}",
                    session_id=event.session_id,
                    parent_task_id=llm_task_ids_by_turn.get(event.turn or 0),
                    source_event_id=event.event_id,
                    title=tool_name,
                    kind="tool_call",
                    status="running",
                    created_at=event.timestamp,
                    updated_at=event.timestamp,
                    summary=f"调用 {tool_name}",
                )
                task_by_runtime_id[event.runtime_id] = tool_task
                tasks.append(tool_task)
                continue

            if event.event_type == "tool_call_completed" and event.runtime_id in task_by_runtime_id:
                tool_task = task_by_runtime_id[event.runtime_id]
                tool_task.status = "succeeded" if bool(event.payload.get("ok", True)) else "failed"
                tool_task.updated_at = event.timestamp
                continue

            if event.event_type == "model_call_completed" and event.runtime_id in task_by_runtime_id:
                llm_task = task_by_runtime_id[event.runtime_id]
                llm_task.status = "succeeded" if bool(event.payload.get("ok", True)) else "failed"
                llm_task.updated_at = event.timestamp
                continue

            if event.event_type == "session_completed" and session_task_id:
                root_task = next(task for task in tasks if task.task_id == session_task_id)
                root_task.status = "succeeded"
                root_task.updated_at = event.timestamp
                root_task.summary = str(event.payload.get("latest_summary") or "会话完成")

        return tasks
