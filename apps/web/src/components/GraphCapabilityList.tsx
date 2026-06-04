import type { GraphCapabilityDefinition } from "@/lib/api";

import { GraphStatusBadge } from "@/components/GraphStatusBadge";

type GraphCapabilityListProps = {
  capabilities: GraphCapabilityDefinition[];
};

export function GraphCapabilityList({ capabilities }: GraphCapabilityListProps) {
  if (!capabilities.length) {
    return (
      <section className="workspace-panel">
        <div className="workspace-panel__header">
          <div>
            <strong>能力注册</strong>
            <span>Capability Registry</span>
          </div>
        </div>
        <p className="workspace-empty">还没有注册 capability。</p>
      </section>
    );
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-panel__header">
        <div>
          <p className="eyebrow">任务驾驶舱</p>
          <h1>能力注册</h1>
        </div>
        <p className="muted">基础动作单元，供组合链路和任务剧本复用。</p>
      </div>
      <div className="list-table">
        {capabilities.map((capability) => (
          <article key={capability.id} className="list-table__row">
            <div>
              <strong>{capability.name}</strong>
              <p>{capability.description || capability.id}</p>
            </div>
            <div>
              <span>类型</span>
              <strong>{capability.kind}</strong>
            </div>
            <div>
              <span>动作</span>
              <strong>{capability.action}</strong>
            </div>
            <div>
              <span>状态</span>
              <GraphStatusBadge status={capability.enabled ? "succeeded" : "failed"} />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
