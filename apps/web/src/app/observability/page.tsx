import Link from "next/link";

import { ObservabilitySessionList } from "@/components/ObservabilitySessionList";
import { listObservabilitySessions } from "@/lib/api";

export default async function ObservabilityPage() {
  const sessions = await listObservabilitySessions();

  return (
    <main className="observability-shell observability-shell--landing">
      <section className="observability-main">
        <header className="observability-header">
          <div>
            <span className="observability-kicker">Observability</span>
            <h1>Review Session Trace Console</h1>
            <p>左侧进入会话，详情页查看时间线、任务树、异常信号和完整事件落盘内容。</p>
          </div>
        </header>

        <section className="observability-stage">
          <div className="observability-stage__header">
            <div>
              <span className="observability-kicker">Session Index</span>
              <strong>已记录会话</strong>
            </div>
            <span>{sessions.length}</span>
          </div>
          <ObservabilitySessionList sessions={sessions} />
        </section>
      </section>

      <aside className="observability-inspector">
        <section className="observability-inspector__panel">
          <div className="observability-sidebar__header">
            <div>
              <span className="observability-kicker">Guide</span>
              <strong>这次设计重点</strong>
            </div>
          </div>
          <div className="observability-inspector__block">
            <p>主视图已经切到时间线思路，进入任意 session 后会看到更接近 tracing 工具的三栏工作台。</p>
          </div>
          <div className="observability-inspector__block">
            <div className="observability-panel__header">
              <strong>包含内容</strong>
            </div>
            <div className="observability-signal-list">
              <div className="observability-signal-card">
                <span>Timeline</span>
                <strong>行式事件轨迹</strong>
                <small>突出 llm/tool 运行顺序与状态</small>
              </div>
              <div className="observability-signal-card">
                <span>Inspector</span>
                <strong>完整详情检查器</strong>
                <small>保留 payload / raw event 落盘视角</small>
              </div>
              <div className="observability-signal-card">
                <span>Task Tree</span>
                <strong>执行节点层级</strong>
                <small>补充 session 内部任务链路</small>
              </div>
            </div>
          </div>
          {sessions[0] ? (
            <Link
              href={`/observability/sessions/${encodeURIComponent(sessions[0].session_id)}`}
              className="observability-open-link"
            >
              打开最近会话
            </Link>
          ) : null}
        </section>
      </aside>
    </main>
  );
}
