"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createMcpServer, type McpServerConfig, type McpServerEnvVar } from "@/lib/api";

type EnvRow = {
  id: string;
  key: string;
  value: string;
};

type FormState = {
  name: string;
  description: string;
  transport: McpServerConfig["transport"];
  scope: McpServerConfig["scope"];
  enabled: boolean;
  command: string;
  endpoint: string;
  args: string[];
  env: EnvRow[];
};

const transportOptions: Array<{ value: McpServerConfig["transport"]; label: string }> = [
  { value: "stdio", label: "STDIO" },
  { value: "streamable_http", label: "Streamable HTTP" },
  { value: "sse", label: "SSE" }
];

const initialForm: FormState = {
  name: "",
  description: "",
  transport: "stdio",
  scope: "global",
  enabled: true,
  command: "npx",
  endpoint: "",
  args: ["chrome-devtools-mcp@latest"],
  env: [{ id: "env_1", key: "", value: "" }]
};

export function McpServiceCreateForm() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(initialForm);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function updateArg(index: number, value: string) {
    setForm((current) => ({
      ...current,
      args: current.args.map((item, itemIndex) => (itemIndex === index ? value : item))
    }));
  }

  function addArg() {
    setForm((current) => ({ ...current, args: [...current.args, ""] }));
  }

  function removeArg(index: number) {
    setForm((current) => ({
      ...current,
      args: current.args.filter((_, itemIndex) => itemIndex !== index)
    }));
  }

  function updateEnv(id: string, key: "key" | "value", value: string) {
    setForm((current) => ({
      ...current,
      env: current.env.map((item) => (item.id === id ? { ...item, [key]: value } : item))
    }));
  }

  function addEnv() {
    setForm((current) => ({
      ...current,
      env: [...current.env, { id: `env_${current.env.length + 1}`, key: "", value: "" }]
    }));
  }

  function removeEnv(id: string) {
    setForm((current) => ({
      ...current,
      env: current.env.filter((item) => item.id !== id)
    }));
  }

  async function handleSave() {
    setError(null);
    setIsSaving(true);
    try {
      const env: McpServerEnvVar[] = form.env
        .filter((item) => item.key.trim())
        .map((item) => ({ key: item.key.trim(), value: item.value }));
      await createMcpServer({
        name: form.name.trim(),
        description: form.description.trim(),
        transport: form.transport,
        scope: form.scope,
        enabled: form.enabled,
        command: form.transport === "stdio" ? form.command.trim() : null,
        args: form.args.map((item) => item.trim()).filter(Boolean),
        endpoint: form.transport === "stdio" ? null : form.endpoint.trim(),
        env
      });
      router.push("/settings/mcp");
      router.refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "保存 MCP 服务失败。");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="settings-workspace settings-workspace--single">
      <div className="settings-workspace__main">
        <section className="workspace-topbar settings-topbar">
          <div className="workspace-topbar__title">
            <Link href="/settings/mcp" className="mcp-back-link">
              ← 返回服务列表
            </Link>
          </div>
        </section>

        <section className="workspace-panel settings-hero-card">
          <div className="settings-hero-card__body">
            <p className="settings-hero-card__eyebrow">CREATE MCP SERVICE</p>
            <h1>连接自定义 MCP</h1>
            <p>按当前桌面端支持的字段录入一个自定义 MCP 服务。这里先对齐页面结构与交互形态，后续再接真实保存接口。</p>
          </div>
        </section>

        <section className="workspace-panel mcp-form-panel">
          <form className="mcp-form" onSubmit={(event) => event.preventDefault()}>
            <section className="mcp-form-section">
              <div className="settings-form-grid">
                <label className="settings-field">
                  <span>名称 *</span>
                  <input
                    value={form.name}
                    onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                    placeholder="MCP 服务名称"
                  />
                </label>
                <label className="settings-field">
                  <span>范围</span>
                  <select
                    value={form.scope}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, scope: event.target.value as McpServerConfig["scope"] }))
                    }
                  >
                    <option value="global">全局用户</option>
                    <option value="project">项目级</option>
                  </select>
                </label>
                <label className="settings-field settings-field--full">
                  <span>描述</span>
                  <input
                    value={form.description}
                    onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                    placeholder="描述这个 MCP 服务主要提供的能力"
                  />
                </label>
              </div>
            </section>

            <section className="mcp-form-section">
              <div className="workspace-panel__header">
                <div>
                  <strong>配置范围</strong>
                  <span>支持全局用户与项目级服务，后续可直接接入更细颗粒度的作用域控制。</span>
                </div>
              </div>
            </section>

            <section className="mcp-form-section">
              <div className="mcp-transport-tabs" role="tablist" aria-label="传输方式">
                {transportOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`mcp-transport-tabs__item ${form.transport === option.value ? "mcp-transport-tabs__item--active" : ""}`}
                    onClick={() => setForm((current) => ({ ...current, transport: option.value }))}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </section>

            {form.transport === "stdio" ? (
              <section className="mcp-form-section">
                <label className="settings-field">
                  <span>启动命令 *</span>
                  <input
                    value={form.command}
                    onChange={(event) => setForm((current) => ({ ...current, command: event.target.value }))}
                    placeholder="npx"
                  />
                </label>
                <p className="settings-agent-card__description">
                  STDIO MCP 命令会直接在宿主机上运行。像 Node.js、Python、Bun、uv 这类运行时需要用户自己安装，并确保命令在 PATH 里可用。
                </p>
              </section>
            ) : (
              <section className="mcp-form-section">
                <label className="settings-field">
                  <span>{form.transport === "sse" ? "SSE 地址 *" : "HTTP 地址 *"}</span>
                  <input
                    value={form.endpoint}
                    onChange={(event) => setForm((current) => ({ ...current, endpoint: event.target.value }))}
                    placeholder={form.transport === "sse" ? "https://example.com/events" : "https://example.com/mcp"}
                  />
                </label>
              </section>
            )}

            <section className="mcp-form-section">
              <div className="workspace-panel__header">
                <div>
                  <strong>参数</strong>
                  <span>按顺序追加命令参数，后续可映射到真实保存结构。</span>
                </div>
              </div>
              <div className="mcp-dynamic-list">
                {form.args.map((arg, index) => (
                  <div key={`arg_${index}`} className="mcp-dynamic-row">
                    <input
                      value={arg}
                      onChange={(event) => updateArg(index, event.target.value)}
                      placeholder="chrome-devtools-mcp@latest"
                    />
                    <button type="button" className="mcp-remove-button" onClick={() => removeArg(index)} aria-label="删除参数">
                      🗑
                    </button>
                  </div>
                ))}
                <button type="button" className="mcp-add-row-button" onClick={addArg}>
                  ＋ 添加参数
                </button>
              </div>
            </section>

            <section className="mcp-form-section">
              <div className="workspace-panel__header">
                <div>
                  <strong>环境变量</strong>
                  <span>适合配置 API Key、认证方式或服务运行开关。</span>
                </div>
              </div>
              <div className="mcp-dynamic-list">
                {form.env.map((item) => (
                  <div key={item.id} className="mcp-dynamic-row mcp-dynamic-row--pair">
                    <input
                      value={item.key}
                      onChange={(event) => updateEnv(item.id, "key", event.target.value)}
                      placeholder="键"
                    />
                    <input
                      value={item.value}
                      onChange={(event) => updateEnv(item.id, "value", event.target.value)}
                      placeholder="值"
                    />
                    <button type="button" className="mcp-remove-button" onClick={() => removeEnv(item.id)} aria-label="删除环境变量">
                      🗑
                    </button>
                  </div>
                ))}
                <button type="button" className="mcp-add-row-button" onClick={addEnv}>
                  ＋ 添加环境变量
                </button>
              </div>
            </section>

            <div className="settings-form-actions">
              <button type="button" className="settings-cta settings-cta--primary" onClick={() => void handleSave()} disabled={isSaving}>
                {isSaving ? "保存中..." : "保存服务"}
              </button>
              <Link href="/settings/mcp" className="settings-cta settings-cta--secondary">
                取消
              </Link>
            </div>
            {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
          </form>
        </section>
      </div>
    </section>
  );
}
