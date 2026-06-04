import type { GraphCompileResult, GraphCompositeDefinition } from "@/lib/api";

type GraphCompositeListProps = {
  composites: GraphCompositeDefinition[];
  compileResults?: Record<string, GraphCompileResult>;
};

export function GraphCompositeList({ composites, compileResults = {} }: GraphCompositeListProps) {
  if (!composites.length) {
    return (
      <section className="workspace-panel">
        <div className="workspace-panel__header">
          <div>
            <strong>组合链路</strong>
            <span>Composite Registry</span>
          </div>
        </div>
        <p className="workspace-empty">还没有注册 composite。</p>
      </section>
    );
  }

  return (
    <section className="workspace-panel">
      <div className="workspace-panel__header">
        <div>
          <p className="eyebrow">任务驾驶舱</p>
          <h1>组合链路</h1>
        </div>
        <p className="muted">P0 只支持 chain mode，按依赖顺序串起多个 capability。</p>
      </div>
      <div className="list-table">
        {composites.map((composite) => {
          const compile = compileResults[composite.id];
          return (
            <article key={composite.id} className="list-table__row">
              <div>
                <strong>{composite.name}</strong>
                <p>{composite.description || composite.id}</p>
              </div>
              <div>
                <span>模式</span>
                <strong>{composite.mode}</strong>
              </div>
              <div>
                <span>节点数</span>
                <strong>{composite.nodes.length}</strong>
              </div>
              <div>
                <span>告警</span>
                <strong>{compile?.warnings.length ?? 0}</strong>
                {compile?.warnings[0] ? <p>{compile.warnings[0]}</p> : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
