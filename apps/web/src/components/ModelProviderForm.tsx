"use client";

import { useMemo, useState, useTransition } from "react";

import type { ModelProviderConfig, ModelProviderTestResult } from "@/lib/api";
import { createModelProvider, testProvider } from "@/lib/api";

type ModelProviderFormProps = {
  initialProviders: ModelProviderConfig[];
};

type FormState = {
  id: string;
  name: string;
  provider_type: "openai" | "openai_compatible";
  model: string;
  api_key: string;
  base_url: string;
  api_shape: "responses" | "chat_completions";
  tracing_enabled: boolean;
};

const initialForm: FormState = {
  id: "",
  name: "",
  provider_type: "openai",
  model: "gpt-5.4",
  api_key: "",
  base_url: "",
  api_shape: "responses",
  tracing_enabled: true
};

const featureChips = [
  { label: "真实报文测试", tone: "blue" },
  { label: "Provider Registry", tone: "orange" },
  { label: "统一模型接入", tone: "green" }
] as const;

function buildFormFromProvider(provider: ModelProviderConfig): FormState {
  return {
    id: provider.id,
    name: provider.name,
    provider_type: provider.provider_type,
    model: provider.model,
    api_key: "",
    base_url: provider.base_url ?? "",
    api_shape: provider.api_shape,
    tracing_enabled: provider.tracing_enabled ?? true
  };
}

export function ModelProviderForm({ initialProviders }: ModelProviderFormProps) {
  const [providers, setProviders] = useState(initialProviders);
  const [form, setForm] = useState<FormState>(() =>
    initialProviders[0] ? buildFormFromProvider(initialProviders[0]) : initialForm
  );
  const [activeProviderId, setActiveProviderId] = useState(initialProviders[0]?.id ?? "");
  const [lastTest, setLastTest] = useState<ModelProviderTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testingProviderId, setTestingProviderId] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const activeProvider = useMemo(
    () => providers.find((provider) => provider.id === activeProviderId) ?? null,
    [providers, activeProviderId]
  );

  const providerStats = useMemo(
    () => ({
      total: providers.length,
      openai: providers.filter((provider) => provider.provider_type === "openai").length,
      compatible: providers.filter((provider) => provider.provider_type === "openai_compatible").length
    }),
    [providers]
  );

  function updateField<Key extends keyof FormState>(key: Key, value: FormState[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function runProviderTest(providerId: string) {
    setError(null);
    setTestingProviderId(providerId);
    startTransition(async () => {
      try {
        const result = await testProvider(providerId);
        setActiveProviderId(providerId);
        setLastTest(result);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Failed to test provider.");
      } finally {
        setTestingProviderId(null);
      }
    });
  }

  function handleLoadProvider(provider: ModelProviderConfig) {
    setActiveProviderId(provider.id);
    setForm(buildFormFromProvider(provider));
    setError(null);
  }

  return (
    <section className="settings-workspace">
      <aside className="settings-workspace__sidebar">
        <section className="workspace-panel settings-hero-card">
          <div className="workspace-brand">
            <div className="workspace-brand__mark">⚙</div>
            <div>
              <strong>模型设置</strong>
              <span>Model Control Deck</span>
            </div>
          </div>
          <div className="settings-hero-card__body">
            <p className="settings-hero-card__eyebrow">SYSTEM CONFIG</p>
            <h1>以首页同款工作台方式管理大模型接入</h1>
            <p>
              在这里维护 Provider 配置、切换接口形态，并对已保存的大模型直接发送测试报文，确认 API 是否真实可用。
            </p>
          </div>
          <div className="settings-chip-row">
            {featureChips.map((chip) => (
              <span key={chip.label} className={`settings-chip settings-chip--${chip.tone}`}>
                {chip.label}
              </span>
            ))}
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>模型概况</strong>
              <span>当前已接入 {providerStats.total} 个 Provider</span>
            </div>
          </div>
          <div className="settings-stat-grid">
            <article className="settings-stat-card">
              <span>总数</span>
              <strong>{providerStats.total}</strong>
            </article>
            <article className="settings-stat-card">
              <span>OpenAI</span>
              <strong>{providerStats.openai}</strong>
            </article>
            <article className="settings-stat-card">
              <span>兼容接口</span>
              <strong>{providerStats.compatible}</strong>
            </article>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>已配置模型</strong>
              <span>支持载入和立即测试</span>
            </div>
          </div>
          <div className="settings-provider-list">
            {providers.length ? (
              providers.map((provider) => {
                const isActive = provider.id === activeProviderId;
                const isTesting = testingProviderId === provider.id;
                return (
                  <article
                    key={provider.id}
                    className={`settings-provider-card ${isActive ? "settings-provider-card--active" : ""}`}
                  >
                    <div className="settings-provider-card__head">
                      <div>
                        <strong>{provider.name}</strong>
                        <span>{provider.id}</span>
                      </div>
                      <em>{provider.provider_type === "openai" ? "OpenAI" : "Compatible"}</em>
                    </div>
                    <div className="settings-provider-card__meta">
                      <span>{provider.model}</span>
                      <span>{provider.api_shape}</span>
                    </div>
                    <div className="settings-provider-card__actions">
                      <button type="button" onClick={() => handleLoadProvider(provider)}>
                        载入配置
                      </button>
                      <button type="button" onClick={() => runProviderTest(provider.id)} disabled={isPending || isTesting}>
                        {isTesting ? "测试中..." : "发送测试"}
                      </button>
                    </div>
                  </article>
                );
              })
            ) : (
              <p className="workspace-empty">还没有已保存的大模型配置，先在右侧创建一个 Provider。</p>
            )}
          </div>
        </section>
      </aside>

      <div className="settings-workspace__main">
        <section className="workspace-topbar settings-topbar">
          <div className="workspace-topbar__title">
            <span className="workspace-topbar__logo">◉</span>
            <strong>大模型配置工作台</strong>
          </div>
          <div className="settings-topbar__note">
            <span>测试会向目标模型发送真实请求</span>
          </div>
        </section>

        <section className="workspace-panel settings-form-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>配置编辑区</strong>
              <span>保存后加入 Provider Registry</span>
            </div>
          </div>

          <form className="settings-form-grid">
            <label className="settings-field">
              <span>Provider ID</span>
              <input value={form.id} onChange={(event) => updateField("id", event.target.value)} placeholder="router-api" />
            </label>

            <label className="settings-field">
              <span>Provider Name</span>
              <input value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="Router API" />
            </label>

            <label className="settings-field">
              <span>Provider Type</span>
              <select
                value={form.provider_type}
                onChange={(event) => updateField("provider_type", event.target.value as FormState["provider_type"])}
              >
                <option value="openai">openai</option>
                <option value="openai_compatible">openai_compatible</option>
              </select>
            </label>

            <label className="settings-field">
              <span>API Shape</span>
              <select
                value={form.api_shape}
                onChange={(event) => updateField("api_shape", event.target.value as FormState["api_shape"])}
              >
                <option value="responses">responses</option>
                <option value="chat_completions">chat_completions</option>
              </select>
            </label>

            <label className="settings-field">
              <span>Model</span>
              <input value={form.model} onChange={(event) => updateField("model", event.target.value)} placeholder="gpt-5.4" />
            </label>

            <label className="settings-field">
              <span>Base URL</span>
              <input
                value={form.base_url}
                onChange={(event) => updateField("base_url", event.target.value)}
                placeholder="https://example.com/v1"
              />
            </label>

            <label className="settings-field settings-field--full">
              <span>API Key</span>
              <input
                type="password"
                value={form.api_key}
                onChange={(event) => updateField("api_key", event.target.value)}
                placeholder="sk-..."
              />
            </label>

            <label className="settings-toggle settings-field--full">
              <input
                type="checkbox"
                checked={form.tracing_enabled}
                onChange={(event) => updateField("tracing_enabled", event.target.checked)}
              />
              <div>
                <strong>Enable Tracing</strong>
                <span>保留模型调用链路调试能力</span>
              </div>
            </label>

            <div className="settings-form-actions settings-field--full">
              <button
                type="button"
                className="settings-cta settings-cta--primary"
                disabled={isPending || !form.id.trim() || !form.name.trim() || !form.model.trim()}
                onClick={() => {
                  setError(null);
                  setLastTest(null);
                  startTransition(async () => {
                    try {
                      const payload: ModelProviderConfig = {
                        id: form.id.trim(),
                        name: form.name.trim(),
                        provider_type: form.provider_type,
                        model: form.model.trim(),
                        api_shape: form.api_shape,
                        tracing_enabled: form.tracing_enabled,
                        ...(form.api_key.trim() ? { api_key: form.api_key.trim() } : {}),
                        ...(form.base_url.trim() ? { base_url: form.base_url.trim() } : {})
                      };
                      const created = await createModelProvider(payload);
                      setProviders((current) => {
                        const next = current.filter((item) => item.id !== created.id);
                        return [created, ...next];
                      });
                      setActiveProviderId(created.id);
                    } catch (caughtError) {
                      setError(caughtError instanceof Error ? caughtError.message : "Failed to save provider.");
                    }
                  });
                }}
              >
                {isPending ? "保存中..." : "保存配置"}
              </button>

              <button
                type="button"
                className="settings-cta settings-cta--secondary"
                disabled={isPending || !form.id.trim()}
                onClick={() => runProviderTest(form.id.trim())}
              >
                {testingProviderId === form.id.trim() ? "测试中..." : "发送测试报文"}
              </button>
            </div>
          </form>
        </section>
      </div>

      <aside className="settings-workspace__right">
        <section className="workspace-panel workspace-panel--summary">
          <div className="workspace-panel__header">
            <div>
              <strong>当前焦点</strong>
              <span>{activeProvider?.name ?? "未选择 Provider"}</span>
            </div>
          </div>
          <div className="settings-focus">
            <h3>{activeProvider?.model ?? "等待选择模型"}</h3>
            <p>{activeProvider ? `${activeProvider.provider_type} · ${activeProvider.api_shape}` : "从左侧载入已配置模型，或在中间新建配置。"}</p>
            <div className="settings-focus__tags">
              <span>{activeProvider?.id ?? "provider-id"}</span>
              <span>{activeProvider?.base_url ?? "default base url"}</span>
            </div>
          </div>
        </section>

        <section className="workspace-panel">
          <div className="workspace-panel__header">
            <div>
              <strong>测试结果</strong>
              <span>最近一次真实 API 响应</span>
            </div>
          </div>

          {lastTest ? (
            <div className={`settings-test-result ${lastTest.ok ? "settings-test-result--success" : "settings-test-result--error"}`}>
              <strong>{lastTest.ok ? "连接正常" : "连接失败"}</strong>
              <p>{lastTest.message}</p>
              {lastTest.response_text ? (
                <div className="settings-response-block">
                  <span>模型返回</span>
                  <code>{lastTest.response_text}</code>
                </div>
              ) : null}
              <div className="settings-capability-list">
                {Object.entries(lastTest.capabilities).map(([key, value]) => (
                  <span key={key}>{`${key}: ${value ? "on" : "off"}`}</span>
                ))}
              </div>
            </div>
          ) : (
            <p className="workspace-empty">发送一次测试报文后，这里会展示模型回包和能力摘要。</p>
          )}
        </section>

        {error ? <p className="workspace-status workspace-status--error">{error}</p> : null}
      </aside>
    </section>
  );
}
