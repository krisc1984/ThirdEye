from __future__ import annotations

from app.agents.sdk_runtime import run_text_agent
from app.schemas.model_provider import ModelProviderConfig
from app.schemas.review import ReviewConversationSession, ReviewReportAssistantResponse
from app.services.playbook_loader import LoadedPlaybook


def _build_report_writer_instructions() -> str:
    return (
        "你是 ThirdEye 的评审报告助手。\n"
        "你必须始终使用中文回复。\n"
        "你的任务是根据当前 Markdown 报告草稿、最新评审结论、历史关键会话和用户编辑指令，"
        "输出两部分内容：\n"
        "1. 简洁说明你做了哪些改写建议；\n"
        "2. 一份完整的 Markdown 报告成稿。\n"
        "不要输出 JSON，不要省略章节，不要只给提纲。"
    )


def _build_report_writer_prompt(
    *,
    session: ReviewConversationSession,
    playbook: LoadedPlaybook,
    markdown: str,
    instruction: str,
) -> str:
    messages = [
        f"- {message.role}: {message.content}"
        for message in session.messages
        if message.role in {"user", "assistant"}
    ]
    evidence = [f"- {item.path}: {item.summary}" for item in playbook.evidence[:8]]
    review = session.last_review
    return f"""[当前 Markdown 草稿]
{markdown}

[用户编辑指令]
{instruction}

[最新评审结论]
总体判断：{review.overall_judgement if review else '待确认'}
关键风险：{'；'.join(review.key_risks[:5]) if review and review.key_risks else '无'}
建议变更：{'；'.join(review.suggested_changes[:5]) if review and review.suggested_changes else '无'}
待验证事项：{'；'.join(review.required_validation[:5]) if review and review.required_validation else '无'}

[会话摘要]
{session.latest_summary or '无'}

[历史关键会话]
{chr(10).join(messages[-10:]) or '(无)'}

[证据引用]
{chr(10).join(evidence) or '(无)'}

[输出格式要求]
先输出“编辑说明”小节，再输出“Markdown 成稿”小节。
在“Markdown 成稿”小节里给出完整 Markdown 正文。
"""


def _extract_markdown(reply: str, fallback_markdown: str) -> str:
    marker = "## Markdown 成稿"
    if marker not in reply:
        return fallback_markdown
    _, content = reply.split(marker, 1)
    content = content.strip()
    if content.startswith("```markdown"):
        content = content[len("```markdown") :].strip()
    elif content.startswith("```"):
        content = content[3:].strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    return content or fallback_markdown


async def generate_review_report_reply(
    *,
    session: ReviewConversationSession,
    playbook: LoadedPlaybook,
    markdown: str,
    instruction: str,
    provider_config: ModelProviderConfig | None,
) -> ReviewReportAssistantResponse:
    if provider_config is None:
        reply = (
            "## 编辑说明\n"
            "当前没有可用模型配置，因此我先保留草稿不自动改写。建议先配置或选择可用 provider，再继续生成正式报告。\n\n"
            "## Markdown 成稿\n"
            f"{markdown}"
        )
        return ReviewReportAssistantResponse(
            reply=reply,
            suggested_markdown=markdown,
            execution_mode="deterministic",
            resolved_provider_id=None,
            execution_note="No available provider for report writer.",
        )

    result = await run_text_agent(
        name="ThirdEye Review Report Writer",
        instructions=_build_report_writer_instructions(),
        user_input=_build_report_writer_prompt(
            session=session,
            playbook=playbook,
            markdown=markdown,
            instruction=instruction,
        ),
        provider_config=provider_config,
    )
    reply = result.output_text.strip()
    return ReviewReportAssistantResponse(
        reply=reply,
        suggested_markdown=_extract_markdown(reply, markdown),
        execution_mode="llm",
        resolved_provider_id=provider_config.id,
        execution_note="Review report assistant completed via OpenAI Agents SDK.",
    )
