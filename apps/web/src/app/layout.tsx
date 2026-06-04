import type { ReactNode } from "react";

import { AppNav } from "@/components/AppNav";

export const metadata = {
  title: "三眼技术评审 Agent",
  description: "通用 agent 多轮对话评审工作台。"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="app-frame">
          <AppNav />
          <main className="app-content">{children}</main>
        </div>
      </body>
      <style>{`
        :root {
          color-scheme: light;
          --bg: #f3efe7;
          --panel: rgba(255, 255, 255, 0.82);
          --panel-strong: #ffffff;
          --panel-soft: #f8f5ef;
          --line: rgba(33, 53, 88, 0.1);
          --line-strong: rgba(33, 53, 88, 0.18);
          --text: #22304a;
          --muted: #7c869b;
          --navy: #213558;
          --blue: #4f7cff;
          --blue-soft: #ebf1ff;
          --orange: #ff9b52;
          --orange-soft: #fff1e6;
          --green: #42b59a;
          --green-soft: #e8f8f3;
          --shadow-lg: 0 26px 80px rgba(54, 72, 98, 0.16);
          --shadow-md: 0 16px 40px rgba(54, 72, 98, 0.1);
          --shadow-sm: 0 10px 22px rgba(54, 72, 98, 0.08);
        }

        * {
          box-sizing: border-box;
        }

        html,
        body {
          margin: 0;
          min-height: 100%;
          background:
            radial-gradient(circle at top center, rgba(90, 130, 255, 0.08), transparent 22%),
            radial-gradient(circle at left 20%, rgba(255, 208, 120, 0.1), transparent 24%),
            linear-gradient(180deg, #f8f5ef 0%, #f2ede4 100%);
          color: var(--text);
          font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif;
        }

        a {
          color: inherit;
          text-decoration: none;
        }

        button,
        input,
        select,
        textarea {
          font: inherit;
        }

        button {
          border: none;
          background: none;
          color: inherit;
        }

        .app-frame {
          width: min(1600px, calc(100vw - 32px));
          margin: 12px auto 28px;
        }

        .app-nav {
          display: flex;
          justify-content: center;
          gap: 10px;
          padding: 10px 0 14px;
        }

        .app-nav__link {
          padding: 10px 14px;
          border-radius: 999px;
          color: var(--muted);
          border: 1px solid transparent;
          transition: 160ms ease;
        }

        .app-nav__link:hover {
          color: var(--navy);
          border-color: var(--line);
          background: rgba(255, 255, 255, 0.62);
        }

        .app-content {
          min-height: calc(100vh - 80px);
        }

        .settings-fab {
          position: fixed;
          left: 24px;
          bottom: 24px;
          z-index: 40;
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          border-radius: 999px;
          border: 1px solid rgba(33, 53, 88, 0.12);
          background: rgba(255, 255, 255, 0.9);
          box-shadow: var(--shadow-md);
          backdrop-filter: blur(18px);
          color: var(--navy);
          transition: transform 160ms ease, box-shadow 160ms ease;
        }

        .settings-fab:hover {
          transform: translateY(-2px);
          box-shadow: var(--shadow-lg);
        }

        .settings-fab__icon {
          display: grid;
          place-items: center;
          width: 30px;
          height: 30px;
          border-radius: 999px;
          background: var(--blue-soft);
          color: var(--blue);
          font-size: 0.95rem;
        }

        .settings-fab__label {
          font-weight: 600;
          letter-spacing: 0.02em;
        }

        .workspace-shell {
          display: grid;
          grid-template-columns: 248px minmax(0, 1fr) 348px;
          gap: 18px;
          min-height: calc(100vh - 110px);
          padding: 12px;
          border-radius: 28px;
          background: rgba(255, 255, 255, 0.56);
          border: 1px solid rgba(255, 255, 255, 0.7);
          box-shadow: var(--shadow-lg);
          backdrop-filter: blur(18px);
        }

        .workspace-sidebar,
        .workspace-rightbar {
          display: grid;
          gap: 16px;
          align-content: start;
          align-self: start;
        }

        .workspace-main {
          display: grid;
          grid-template-rows: auto auto auto auto minmax(0, 1fr) auto;
          gap: 18px;
          min-width: 0;
          min-height: 0;
        }

        .workspace-brand,
        .workspace-panel,
        .workspace-knowledge-card,
        .workspace-composer,
        .workspace-toolbar,
        .workspace-topbar,
        .workspace-message,
        .workspace-capability,
        .workspace-project-item,
        .workspace-primary-action,
        .workspace-search,
        .workspace-menu__item {
          border: 1px solid var(--line);
          background: var(--panel);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(12px);
        }

        .workspace-brand {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 18px;
          border-radius: 22px;
        }

        .workspace-brand__mark {
          display: grid;
          place-items: center;
          width: 44px;
          height: 44px;
          border-radius: 16px;
          background: linear-gradient(145deg, #f8fbff, #e8edfb);
          color: var(--navy);
          font-size: 1.5rem;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
        }

        .workspace-brand__mark--image {
          overflow: hidden;
          background: rgba(255, 255, 255, 0.9);
          box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.9),
            0 8px 18px rgba(54, 72, 98, 0.12);
        }

        .workspace-brand__logo {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .workspace-brand strong,
        .workspace-panel__header strong,
        .workspace-topbar__title strong {
          display: block;
          font-weight: 700;
        }

        .workspace-brand span,
        .workspace-panel__header span,
        .workspace-sidebar__header,
        .workspace-message__meta span,
        .workspace-empty,
        .workspace-knowledge-card p,
        .workspace-knowledge-card small,
        .workspace-project-item small,
        .workspace-menu__item small,
        .workspace-session-item small {
          color: var(--muted);
        }

        .workspace-primary-action {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          width: 100%;
          padding: 14px 16px;
          border-radius: 16px;
          background: linear-gradient(135deg, #213558, #314a78);
          color: white;
          cursor: pointer;
        }

        .workspace-primary-action small {
          padding: 2px 8px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.16);
          color: rgba(255, 255, 255, 0.86);
        }

        .workspace-search {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
          padding: 10px;
          border-radius: 16px;
        }

        .workspace-search input,
        .workspace-doc-search input,
        .workspace-toolbar select,
        .workspace-toolbar input,
        .workspace-composer textarea {
          width: 100%;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.74);
          color: var(--text);
        }

        .workspace-search input,
        .workspace-doc-search input {
          padding: 10px 12px;
          border-radius: 12px;
        }

        .workspace-search button,
        .workspace-doc-search button {
          width: 40px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          cursor: pointer;
        }

        .workspace-menu,
        .workspace-project-list,
        .workspace-chat,
        .workspace-session-list {
          display: grid;
          gap: 10px;
        }

        .workspace-menu__item,
        .workspace-project-item,
        .workspace-session-item {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
          padding: 14px;
          border-radius: 18px;
          text-align: left;
          cursor: pointer;
        }

        .workspace-menu__item div,
        .workspace-project-item strong,
        .workspace-project-item__body {
          min-width: 0;
        }

        .workspace-project-item {
          grid-template-columns: auto minmax(0, 1fr) auto;
        }

        .workspace-project-item__body {
          display: grid;
          gap: 2px;
        }

        .workspace-project-item__delete {
          display: grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 999px;
          border: 1px solid rgba(255, 93, 84, 0.12);
          background: rgba(255, 93, 84, 0.08);
          color: #c4544d;
          cursor: pointer;
        }

        .workspace-project-item__delete:hover {
          background: rgba(255, 93, 84, 0.14);
        }

        .workspace-menu__item strong,
        .workspace-project-item strong,
        .workspace-session-item strong,
        .workspace-summary h3,
        .workspace-capability strong,
        .workspace-message__body strong,
        .workspace-doc-item__body strong,
        .workspace-finding__header strong {
          font-weight: 600;
        }

        .workspace-menu__item--active,
        .workspace-project-item--active,
        .workspace-session-item--active {
          border-color: rgba(79, 124, 255, 0.25);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(235, 241, 255, 0.9));
        }

        .workspace-sidebar__section {
          display: grid;
          gap: 12px;
        }

        .workspace-sidebar__header,
        .workspace-panel__header,
        .workspace-topbar,
        .workspace-composer__footer,
        .workspace-summary__footer,
        .workspace-doc-group__title,
        .workspace-message__meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
        }

        .workspace-knowledge-card {
          padding: 18px;
          border-radius: 22px;
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(240, 246, 255, 0.84)),
            radial-gradient(circle at right bottom, rgba(79, 124, 255, 0.18), transparent 35%);
        }

        .workspace-knowledge-card__header {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: center;
          margin-bottom: 10px;
        }

        .workspace-knowledge-card__header span {
          color: #37a96b;
          font-size: 0.88rem;
        }

        .workspace-knowledge-card button,
        .workspace-upload,
        .workspace-summary__footer button,
        .workspace-finding button {
          padding: 10px 14px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.85);
          cursor: pointer;
        }

        .workspace-topbar {
          padding: 16px 20px;
          border-radius: 22px;
        }

        .workspace-topbar__title,
        .workspace-topbar__actions {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .workspace-topbar__logo {
          display: grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: var(--blue-soft);
          color: var(--blue);
        }

        .workspace-topbar__actions button {
          padding: 8px 12px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.75);
          border: 1px solid var(--line);
          cursor: pointer;
        }

        .workspace-hero {
          display: grid;
          justify-items: center;
          gap: 10px;
          padding: 18px 12px 2px;
          text-align: center;
        }

        .workspace-hero h1 {
          margin: 0;
          font-size: clamp(2rem, 3.2vw, 3.2rem);
          letter-spacing: -0.04em;
        }

        .workspace-hero p {
          margin: 0;
          color: var(--muted);
        }

        .workspace-orbit {
          position: relative;
          width: 220px;
          height: 140px;
        }

        .workspace-orbit__ring,
        .workspace-orbit__core,
        .workspace-orbit__node {
          position: absolute;
          border-radius: 999px;
        }

        .workspace-orbit__ring {
          inset: 14px;
          border: 1px solid rgba(79, 124, 255, 0.16);
        }

        .workspace-orbit__ring--outer {
          transform: rotate(16deg);
        }

        .workspace-orbit__ring--inner {
          inset: 30px 18px;
          transform: rotate(-18deg);
        }

        .workspace-orbit__core,
        .workspace-orbit__node {
          display: grid;
          place-items: center;
          background:
            radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(176, 200, 255, 0.75)),
            linear-gradient(180deg, #24406a, #1c2c4a);
          color: white;
          box-shadow:
            0 10px 24px rgba(62, 95, 160, 0.28),
            inset 0 2px 10px rgba(255, 255, 255, 0.18);
        }

        .workspace-orbit__core {
          inset: 34px 76px;
          font-size: 2rem;
        }

        .workspace-orbit__node {
          width: 52px;
          height: 52px;
          top: 60px;
          font-size: 1.15rem;
        }

        .workspace-orbit__node--left {
          left: 28px;
        }

        .workspace-orbit__node--right {
          right: 28px;
        }

        .workspace-capabilities {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
        }

        .workspace-capability {
          padding: 18px;
          border-radius: 22px;
        }

        .workspace-capability__badge {
          display: inline-grid;
          place-items: center;
          width: 30px;
          height: 30px;
          border-radius: 50%;
          margin-bottom: 14px;
        }

        .workspace-capability--blue .workspace-capability__badge {
          color: var(--blue);
          background: var(--blue-soft);
        }

        .workspace-capability--orange .workspace-capability__badge {
          color: var(--orange);
          background: var(--orange-soft);
        }

        .workspace-capability--green .workspace-capability__badge {
          color: var(--green);
          background: var(--green-soft);
        }

        .workspace-capability p,
        .workspace-summary p,
        .workspace-summary li,
        .workspace-message__body p,
        .workspace-finding p {
          color: var(--muted);
          line-height: 1.7;
        }

        .workspace-toolbar {
          display: grid;
          grid-template-columns: minmax(0, 1fr);
          gap: 12px;
          padding: 14px;
          border-radius: 18px;
        }

        .workspace-project-creator {
          display: grid;
          gap: 10px;
          padding: 12px;
          border-radius: 16px;
          border: 1px dashed var(--line-strong);
          background: rgba(255, 255, 255, 0.56);
        }

        .workspace-project-creator input {
          width: 100%;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.78);
          color: var(--text);
        }

        .workspace-project-creator button,
        .workspace-sidebar__header button {
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.84);
          cursor: pointer;
        }

        .workspace-toolbar label {
          display: grid;
          gap: 8px;
          min-width: 0;
        }

        .workspace-toolbar__summary {
          display: grid;
          gap: 6px;
        }

        .workspace-toolbar__summary strong {
          font-size: 1rem;
          font-weight: 600;
          color: var(--text);
        }

        .workspace-toolbar span {
          font-size: 0.85rem;
          color: var(--muted);
        }

        .workspace-toolbar select {
          padding: 10px 12px;
          border-radius: 12px;
        }

        .workspace-chat {
          align-content: start;
          min-height: 0;
          max-height: min(52vh, 760px);
          padding-right: 4px;
          overflow: auto;
        }

        .workspace-message {
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          gap: 14px;
          padding: 16px;
          border-radius: 24px;
        }

        .workspace-message--user {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(247, 245, 240, 0.9));
        }

        .workspace-message--assistant {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.94));
        }

        .workspace-message--welcome {
          border-style: dashed;
        }

        .workspace-avatar {
          display: grid;
          place-items: center;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: linear-gradient(180deg, #eef3ff, #dde8fb);
          color: var(--navy);
          font-size: 0.95rem;
          font-weight: 700;
        }

        .workspace-message__body p {
          margin: 8px 0 0;
        }

        .workspace-message__meta-actions {
          display: inline-flex;
          align-items: center;
          gap: 10px;
        }

        .workspace-copy-button {
          padding: 6px 10px;
          border-radius: 999px;
          border: 1px solid rgba(148, 163, 184, 0.28);
          background: rgba(255, 255, 255, 0.82);
          color: var(--muted);
          font-size: 0.75rem;
          line-height: 1;
          cursor: pointer;
          transition: all 160ms ease;
        }

        .workspace-copy-button:hover {
          border-color: rgba(79, 124, 255, 0.28);
          color: var(--navy);
          background: rgba(238, 244, 255, 0.95);
        }

        .workspace-copy-button--copied {
          border-color: rgba(55, 169, 107, 0.26);
          color: #1f7a4f;
          background: rgba(235, 248, 240, 0.96);
        }

        .workspace-markdown {
          display: grid;
          gap: 10px;
          margin-top: 8px;
          min-width: 0;
        }

        .workspace-markdown h3,
        .workspace-markdown h4 {
          margin: 0;
          color: var(--text);
          line-height: 1.35;
        }

        .workspace-markdown h3 {
          font-size: 1.02rem;
        }

        .workspace-markdown h4 {
          font-size: 0.94rem;
        }

        .workspace-markdown p,
        .workspace-markdown ul,
        .workspace-markdown ol,
        .workspace-markdown blockquote,
        .workspace-markdown pre,
        .workspace-markdown table {
          margin: 0;
        }

        .workspace-markdown p,
        .workspace-markdown li,
        .workspace-markdown blockquote {
          color: var(--muted);
          line-height: 1.7;
          word-break: break-word;
        }

        .workspace-markdown ul,
        .workspace-markdown ol {
          padding-left: 20px;
          display: grid;
          gap: 6px;
        }

        .workspace-markdown blockquote {
          padding: 10px 14px;
          border-left: 3px solid rgba(79, 124, 255, 0.45);
          border-radius: 0 12px 12px 0;
          background: rgba(79, 124, 255, 0.06);
        }

        .workspace-markdown pre {
          padding: 14px;
          border-radius: 14px;
          overflow: auto;
          background: rgba(18, 28, 45, 0.96);
          color: #edf3ff;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.84rem;
          line-height: 1.65;
        }

        .workspace-markdown code {
          padding: 0.1em 0.35em;
          border-radius: 6px;
          background: rgba(20, 29, 43, 0.08);
          color: var(--navy);
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.88em;
        }

        .workspace-markdown pre code {
          padding: 0;
          background: transparent;
          color: inherit;
        }

        .workspace-markdown__table-wrap {
          overflow-x: auto;
          border: 1px solid rgba(148, 163, 184, 0.18);
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.86);
        }

        .workspace-markdown__table {
          width: 100%;
          border-collapse: collapse;
          min-width: 480px;
        }

        .workspace-markdown__table th,
        .workspace-markdown__table td {
          padding: 12px 14px;
          text-align: left;
          vertical-align: top;
          border-bottom: 1px solid rgba(226, 232, 240, 0.9);
          color: var(--muted);
          line-height: 1.65;
        }

        .workspace-markdown__table th {
          color: var(--text);
          font-weight: 600;
          background: rgba(241, 245, 249, 0.72);
        }

        .workspace-markdown__table tr:last-child td {
          border-bottom: none;
        }

        .workspace-markdown a {
          color: var(--blue);
          text-decoration: none;
        }

        .workspace-markdown strong {
          color: var(--text);
          font-weight: 600;
        }

        .workspace-starters,
        .workspace-finding-cards,
        .workspace-doc-tabs,
        .workspace-composer__actions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .workspace-starters button,
        .workspace-doc-tabs button,
        .workspace-composer__actions button {
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .workspace-finding-cards {
          margin-top: 14px;
        }

        .workspace-finding {
          flex: 1 1 180px;
          min-width: 0;
          padding: 14px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.92);
        }

        .workspace-finding--blue {
          background: linear-gradient(180deg, rgba(239, 245, 255, 0.9), rgba(255, 255, 255, 0.95));
        }

        .workspace-finding--orange {
          background: linear-gradient(180deg, rgba(255, 244, 233, 0.92), rgba(255, 255, 255, 0.95));
        }

        .workspace-finding--green {
          background: linear-gradient(180deg, rgba(236, 251, 246, 0.92), rgba(255, 255, 255, 0.95));
        }

        .workspace-composer {
          padding: 16px;
          border-radius: 24px;
        }

        .workspace-composer textarea {
          min-height: 116px;
          padding: 14px 16px;
          border-radius: 16px;
          resize: vertical;
        }

        .workspace-composer__submit {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }

        .workspace-composer__submit span {
          color: var(--muted);
          font-size: 0.92rem;
        }

        .workspace-composer__control {
          display: grid;
          gap: 6px;
        }

        .workspace-context-meter {
          position: relative;
          display: grid;
          place-items: center;
          width: 44px;
          height: 44px;
          border: 1px solid rgba(68, 119, 248, 0.24);
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.9);
          cursor: default;
          outline: none;
          box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.6);
        }

        .workspace-context-meter--idle {
          border-color: var(--line);
        }

        .workspace-context-meter__ring {
          display: grid;
          place-items: center;
          width: 34px;
          height: 34px;
          border-radius: 999px;
          padding: 3px;
        }

        .workspace-context-meter__core {
          display: grid;
          place-items: center;
          width: 100%;
          height: 100%;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.96);
          color: var(--text);
          font-size: 0.62rem;
          font-weight: 700;
        }

        .workspace-context-meter__popover {
          position: absolute;
          left: 50%;
          bottom: calc(100% + 12px);
          z-index: 20;
          display: grid;
          gap: 12px;
          min-width: 260px;
          padding: 14px;
          border: 1px solid rgba(210, 222, 243, 0.9);
          border-radius: 18px;
          background: rgba(255, 252, 248, 0.98);
          box-shadow: 0 20px 48px rgba(15, 23, 42, 0.14);
          opacity: 0;
          pointer-events: none;
          transform: translate(-50%, 8px);
          transition: opacity 140ms ease, transform 140ms ease;
        }

        .workspace-context-meter:hover .workspace-context-meter__popover,
        .workspace-context-meter:focus-visible .workspace-context-meter__popover {
          opacity: 1;
          transform: translate(-50%, 0);
        }

        .workspace-context-meter__popover-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }

        .workspace-context-meter__popover-head div {
          display: grid;
          gap: 4px;
        }

        .workspace-context-meter__popover-head strong:last-child {
          font-size: 1.45rem;
          line-height: 1;
        }

        .workspace-context-meter__popover-head span,
        .workspace-context-meter__stats span,
        .workspace-context-meter__breakdown span,
        .workspace-context-meter__hint {
          color: var(--muted);
          font-size: 0.78rem;
        }

        .workspace-context-meter__stats,
        .workspace-context-meter__breakdown {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
        }

        .workspace-context-meter__stats div,
        .workspace-context-meter__breakdown div {
          display: grid;
          gap: 4px;
        }

        .workspace-context-meter__stats strong,
        .workspace-context-meter__breakdown strong {
          font-size: 0.92rem;
        }

        .workspace-context-meter__breakdown {
          padding-top: 12px;
          border-top: 1px solid rgba(226, 232, 240, 0.92);
        }

        .workspace-context-meter__hint {
          margin: 0;
        }

        .workspace-composer__control span {
          font-size: 0.78rem;
          color: var(--muted);
        }

        .workspace-composer__control select {
          min-width: 148px;
          padding: 10px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          color: var(--text);
        }

        .workspace-composer__submit button {
          display: grid;
          place-items: center;
          width: 44px;
          height: 44px;
          border-radius: 14px;
          background: linear-gradient(135deg, #4477f8, #1f56dd);
          color: white;
          cursor: pointer;
          box-shadow: 0 12px 24px rgba(68, 119, 248, 0.3);
        }

        .workspace-composer__submit button:disabled {
          cursor: wait;
          opacity: 0.6;
        }

        .workspace-panel {
          display: grid;
          gap: 14px;
          padding: 18px;
          border-radius: 24px;
          align-content: start;
        }

        .workspace-panel--summary {
          background:
            linear-gradient(180deg, rgba(255, 252, 243, 0.95), rgba(255, 249, 232, 0.9)),
            radial-gradient(circle at top right, rgba(255, 196, 82, 0.12), transparent 32%);
        }

        .workspace-doc-tabs {
          gap: 12px;
        }

        .workspace-doc-tabs__active {
          color: var(--blue);
          border-color: rgba(79, 124, 255, 0.2);
          background: rgba(235, 241, 255, 0.9);
        }

        .workspace-doc-search {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 10px;
        }

        .workspace-knowledge-actions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .workspace-knowledge-actions button {
          padding: 8px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .workspace-knowledge-actions button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .workspace-doc-tree,
        .workspace-doc-group {
          display: grid;
          gap: 10px;
        }

        .workspace-doc-node,
        .workspace-doc-node__children {
          display: grid;
          gap: 8px;
        }

        .workspace-doc-node__dir {
          display: flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
          padding: 8px 10px;
          border-radius: 12px;
          border: 1px solid rgba(33, 53, 88, 0.06);
          background: rgba(255, 255, 255, 0.62);
          cursor: pointer;
          text-align: left;
        }

        .workspace-doc-node__dir strong {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .workspace-doc-item {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
        }

        .workspace-doc-item__icon {
          display: grid;
          place-items: center;
          min-width: 38px;
          height: 38px;
          padding: 0 10px;
          border-radius: 12px;
          font-size: 0.7rem;
          font-weight: 700;
        }

        .workspace-doc-item__icon--pdf {
          background: #fff0ef;
          color: #ff5e57;
        }

        .workspace-doc-item__icon--doc {
          background: #ecf3ff;
          color: #4f7cff;
        }

        .workspace-doc-item__icon--uml {
          background: #f5f2ff;
          color: #7a67f8;
        }

        .workspace-doc-item__icon--sheet {
          background: #e8f8f3;
          color: #22a16f;
        }

        .workspace-doc-item__body small,
        .workspace-doc-item time {
          color: var(--muted);
        }

        .workspace-upload {
          width: 100%;
          display: inline-flex;
          justify-content: center;
          align-items: center;
        }

        .workspace-summary h3 {
          margin: 0 0 8px;
          font-size: 1rem;
        }

        .workspace-summary p,
        .workspace-summary ul {
          margin: 0 0 16px;
          padding-left: 18px;
        }

        .workspace-summary p {
          padding-left: 0;
        }

        .workspace-summary__footer {
          padding-top: 8px;
          border-top: 1px solid rgba(33, 53, 88, 0.08);
        }

        .workspace-summary__links {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .workspace-summary__footer button {
          background: rgba(255, 184, 77, 0.14);
          color: #d48a18;
          border-color: rgba(255, 184, 77, 0.18);
        }

        .workspace-summary__link {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 10px 14px;
          border-radius: 12px;
          border: 1px solid rgba(255, 184, 77, 0.18);
          background: rgba(255, 184, 77, 0.14);
          color: #d48a18;
        }

        .workspace-session-item {
          display: grid;
          gap: 4px;
          min-width: 0;
        }

        .workspace-session-item strong,
        .workspace-session-item small {
          display: block;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .workspace-status {
          margin: 0;
          padding: 12px 14px;
          border-radius: 14px;
        }

        .workspace-status button {
          margin-left: 10px;
          padding: 6px 10px;
          border-radius: 10px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .workspace-status--error {
          color: #b34b46;
          background: rgba(255, 93, 84, 0.09);
          border: 1px solid rgba(255, 93, 84, 0.14);
        }

        .workspace-message--tool .workspace-message__body {
          gap: 10px;
        }

        .workspace-tool-call {
          display: grid;
          gap: 10px;
        }

        .workspace-tool-call > p {
          margin: 0;
        }

        .workspace-tool-call__details {
          border: 1px solid var(--line);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.78);
          overflow: hidden;
        }

        .workspace-tool-call__details summary {
          cursor: pointer;
          list-style: none;
          padding: 12px 14px;
          font-size: 0.92rem;
          font-weight: 600;
          color: var(--navy);
          background: rgba(247, 249, 252, 0.95);
        }

        .workspace-tool-call__details summary::-webkit-details-marker {
          display: none;
        }

        .workspace-tool-call__details pre {
          margin: 0;
          padding: 14px;
          max-height: 260px;
          overflow: auto;
          white-space: pre-wrap;
          word-break: break-word;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.84rem;
          line-height: 1.6;
          color: var(--navy);
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-workspace {
          display: grid;
          grid-template-columns: 300px minmax(0, 1fr) 340px;
          gap: 18px;
          min-height: calc(100vh - 110px);
          padding: 12px;
          border-radius: 28px;
          background: rgba(255, 255, 255, 0.56);
          border: 1px solid rgba(255, 255, 255, 0.7);
          box-shadow: var(--shadow-lg);
          backdrop-filter: blur(18px);
        }

        .settings-section-tabs {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          padding: 10px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.72);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(12px);
        }

        .settings-section-tabs__item {
          padding: 10px 14px;
          border-radius: 12px;
          color: var(--muted);
          transition: 160ms ease;
        }

        .settings-section-tabs__item:hover {
          color: var(--navy);
          background: rgba(255, 255, 255, 0.84);
        }

        .settings-section-tabs__item--active {
          color: white;
          background: linear-gradient(135deg, #213558, #314a78);
          box-shadow: 0 12px 24px rgba(33, 53, 88, 0.18);
        }

        .settings-workspace__sidebar,
        .settings-workspace__right,
        .settings-workspace__main {
          display: grid;
          gap: 16px;
          align-content: start;
          min-width: 0;
        }

        .settings-hero-card {
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(240, 246, 255, 0.84)),
            radial-gradient(circle at right bottom, rgba(79, 124, 255, 0.14), transparent 38%);
        }

        .settings-hero-card__body {
          display: grid;
          gap: 10px;
        }

        .settings-hero-card__eyebrow {
          margin: 0;
          font-size: 0.78rem;
          letter-spacing: 0.24em;
          color: var(--blue);
        }

        .settings-hero-card__body h1,
        .settings-focus h3 {
          margin: 0;
          line-height: 1.15;
          letter-spacing: -0.04em;
        }

        .settings-hero-card__body h1 {
          font-size: clamp(1.8rem, 2.2vw, 2.6rem);
        }

        .settings-hero-card__body p,
        .settings-focus p,
        .settings-test-result p {
          margin: 0;
          color: var(--muted);
          line-height: 1.75;
        }

        .settings-chip-row,
        .settings-focus__tags,
        .settings-capability-list {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .settings-chip,
        .settings-focus__tags span,
        .settings-capability-list span {
          display: inline-flex;
          align-items: center;
          padding: 8px 12px;
          border-radius: 999px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.84);
          font-size: 0.85rem;
        }

        .settings-chip--blue {
          color: var(--blue);
          background: rgba(235, 241, 255, 0.92);
        }

        .settings-chip--orange {
          color: #da7f2d;
          background: rgba(255, 241, 230, 0.9);
        }

        .settings-chip--green {
          color: #2f9a7e;
          background: rgba(232, 248, 243, 0.92);
        }

        .settings-stat-grid,
        .settings-provider-list {
          display: grid;
          gap: 12px;
        }

        .settings-stat-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }

        .settings-stat-card,
        .settings-provider-card,
        .settings-response-block {
          border: 1px solid var(--line);
          background: var(--panel);
          box-shadow: var(--shadow-sm);
          backdrop-filter: blur(12px);
        }

        .settings-stat-card {
          display: grid;
          gap: 6px;
          padding: 14px 16px;
          border-radius: 18px;
        }

        .settings-stat-card span,
        .settings-provider-card__head span,
        .settings-provider-card__meta span,
        .settings-response-block span,
        .settings-toggle span,
        .settings-topbar__note span {
          color: var(--muted);
        }

        .settings-stat-card strong {
          font-size: 1.6rem;
        }

        .settings-provider-card {
          display: grid;
          gap: 12px;
          padding: 16px;
          border-radius: 22px;
        }

        .settings-provider-card--active {
          border-color: rgba(79, 124, 255, 0.22);
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(235, 241, 255, 0.9));
        }

        .settings-provider-card__head,
        .settings-provider-card__actions,
        .settings-form-actions,
        .settings-topbar__note {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .settings-provider-card__head em {
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.8);
          color: var(--navy);
          font-style: normal;
          font-size: 0.82rem;
        }

        .settings-provider-card__meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .settings-agent-card__description {
          margin: 0;
          color: var(--muted);
          line-height: 1.7;
        }

        .settings-provider-card__meta span {
          padding: 6px 10px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.72);
        }

        .settings-provider-card__actions button,
        .settings-provider-card__link,
        .settings-cta {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 10px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          cursor: pointer;
        }

        .settings-provider-card__actions button,
        .settings-provider-card__link {
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-topbar {
          padding: 16px 20px;
          border-radius: 22px;
        }

        .settings-form-panel {
          gap: 18px;
        }

        .settings-form-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
        }

        .settings-field {
          display: grid;
          gap: 8px;
          min-width: 0;
        }

        .settings-field span {
          font-size: 0.9rem;
          color: var(--muted);
        }

        .settings-field input,
        .settings-field select,
        .settings-field textarea {
          width: 100%;
          padding: 12px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          color: var(--text);
        }

        .settings-field textarea {
          resize: vertical;
          min-height: 320px;
          line-height: 1.7;
        }

        .settings-upload {
          display: grid;
          gap: 10px;
          padding: 16px;
          border-radius: 18px;
          border: 1px dashed var(--line-strong);
          background: rgba(255, 255, 255, 0.8);
          cursor: pointer;
        }

        .settings-upload input {
          width: 100%;
        }

        .settings-upload span {
          color: var(--muted);
        }

        .settings-field--full {
          grid-column: 1 / -1;
        }

        .settings-toggle {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 16px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.78);
        }

        .settings-toggle input {
          width: 18px;
          height: 18px;
          margin: 0;
        }

        .settings-toggle div {
          display: grid;
          gap: 4px;
        }

        .settings-cta--primary {
          background: linear-gradient(135deg, #213558, #314a78);
          color: white;
          box-shadow: 0 14px 30px rgba(33, 53, 88, 0.2);
        }

        .settings-cta--secondary {
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-cta:disabled,
        .settings-provider-card__actions button:disabled {
          opacity: 0.6;
          cursor: wait;
        }

        .settings-workspace--single {
          grid-template-columns: minmax(0, 1fr);
        }

        .mcp-service-list,
        .mcp-form,
        .mcp-dynamic-list {
          display: grid;
          gap: 12px;
        }

        .mcp-service-row,
        .mcp-form-section {
          display: grid;
          gap: 14px;
          padding: 20px 22px;
          border-radius: 24px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          box-shadow: var(--shadow-sm);
        }

        .mcp-service-row {
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: center;
        }

        .mcp-service-row__main {
          display: grid;
          gap: 10px;
          min-width: 0;
        }

        .mcp-service-row__title,
        .mcp-service-row__actions {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .mcp-service-row__actions {
          justify-content: flex-end;
        }

        .mcp-status-badge {
          display: inline-flex;
          align-items: center;
          padding: 6px 12px;
          border-radius: 999px;
          font-size: 0.82rem;
          border: 1px solid transparent;
        }

        .mcp-status-badge--connected {
          color: #1d8f73;
          background: rgba(227, 249, 241, 0.95);
          border-color: rgba(29, 143, 115, 0.16);
        }

        .mcp-status-badge--idle {
          color: #7d6d5c;
          background: rgba(245, 240, 232, 0.95);
          border-color: rgba(125, 109, 92, 0.12);
        }

        .mcp-status-badge--attention {
          color: #cc7a2e;
          background: rgba(255, 242, 228, 0.95);
          border-color: rgba(204, 122, 46, 0.14);
        }

        .mcp-icon-button {
          width: 42px;
          height: 42px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .mcp-switch {
          display: inline-flex;
          align-items: center;
          cursor: pointer;
        }

        .mcp-switch input {
          position: absolute;
          opacity: 0;
          pointer-events: none;
        }

        .mcp-switch__track {
          position: relative;
          width: 58px;
          height: 34px;
          border-radius: 999px;
          background: rgba(184, 205, 235, 0.9);
          transition: 160ms ease;
        }

        .mcp-switch__thumb {
          position: absolute;
          top: 4px;
          left: 4px;
          width: 26px;
          height: 26px;
          border-radius: 50%;
          background: #ffffff;
          box-shadow: 0 6px 14px rgba(33, 53, 88, 0.18);
          transition: 160ms ease;
        }

        .mcp-switch input:checked + .mcp-switch__track {
          background: linear-gradient(135deg, #73a8f2, #90bbf3);
        }

        .mcp-switch input:checked + .mcp-switch__track .mcp-switch__thumb {
          transform: translateX(24px);
        }

        .mcp-back-link {
          color: var(--navy);
          text-decoration: none;
        }

        .mcp-form-panel {
          gap: 18px;
        }

        .mcp-transport-tabs {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          border-radius: 20px;
          overflow: hidden;
          border: 1px solid var(--line);
          background: rgba(243, 240, 234, 0.75);
        }

        .mcp-transport-tabs__item {
          padding: 18px 16px;
          border: 0;
          background: transparent;
          color: var(--navy);
          cursor: pointer;
          font-size: 1rem;
        }

        .mcp-transport-tabs__item--active {
          background: rgba(255, 255, 255, 0.9);
          box-shadow: inset 0 0 0 1px rgba(33, 53, 88, 0.06);
        }

        .mcp-dynamic-row {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 12px;
          align-items: center;
        }

        .mcp-dynamic-row--pair {
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
        }

        .mcp-dynamic-row input {
          width: 100%;
          padding: 12px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          color: var(--text);
        }

        .mcp-remove-button,
        .mcp-add-row-button {
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .mcp-remove-button {
          width: 42px;
          height: 42px;
        }

        .mcp-add-row-button {
          padding: 14px 18px;
        }

        .settings-focus {
          display: grid;
          gap: 12px;
        }

        .settings-test-result {
          display: grid;
          gap: 12px;
          padding: 16px;
          border-radius: 20px;
        }

        .settings-test-result--success {
          background: linear-gradient(180deg, rgba(236, 251, 246, 0.92), rgba(255, 255, 255, 0.95));
          border: 1px solid rgba(66, 181, 154, 0.18);
        }

        .settings-test-result--error {
          background: linear-gradient(180deg, rgba(255, 239, 238, 0.95), rgba(255, 255, 255, 0.95));
          border: 1px solid rgba(255, 93, 84, 0.18);
        }

        .settings-response-block {
          display: grid;
          gap: 8px;
          padding: 14px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.86);
        }

        .settings-response-block code {
          white-space: pre-wrap;
          word-break: break-word;
          color: var(--navy);
        }

        .settings-response-block--prompt code {
          max-height: 420px;
          overflow: auto;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.84rem;
          line-height: 1.7;
        }

        .report-shell {
          display: grid;
          grid-template-columns: 280px minmax(0, 1fr) 330px;
          gap: 18px;
          min-height: calc(100vh - 110px);
          padding: 12px;
          border-radius: 28px;
          background: rgba(255, 255, 255, 0.56);
          border: 1px solid rgba(255, 255, 255, 0.7);
          box-shadow: var(--shadow-lg);
          backdrop-filter: blur(18px);
        }

        .report-sidebar,
        .report-rightbar,
        .report-main {
          display: grid;
          gap: 16px;
          align-content: start;
          min-width: 0;
        }

        .report-panel {
          padding: 18px;
          border-radius: 24px;
        }

        .report-panel--sticky {
          position: sticky;
          top: 12px;
        }

        .report-panel__block {
          display: grid;
          gap: 14px;
        }

        .report-panel__dots {
          color: var(--muted);
          letter-spacing: 0.18em;
        }

        .report-topbar {
          padding: 14px 18px;
          border-radius: 24px;
        }

        .report-topbar .workspace-topbar__title div {
          display: grid;
          gap: 4px;
        }

        .report-topbar .workspace-topbar__title span:last-child {
          color: var(--muted);
          font-size: 0.82rem;
        }

        .report-editor-panel {
          display: grid;
          gap: 16px;
          min-height: calc(100vh - 176px);
          padding: 20px;
          border-radius: 24px;
        }

        .report-editor-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr);
          gap: 16px;
          min-height: 620px;
          min-width: 0;
        }

        .report-markdown-editor {
          width: 100%;
          min-width: 0;
          max-width: 100%;
          min-height: 620px;
          padding: 18px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.88);
          color: var(--text);
          resize: vertical;
          line-height: 1.7;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.92rem;
        }

        .report-preview-panel {
          display: grid;
          gap: 12px;
          padding: 16px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.8);
          overflow: auto;
        }

        .report-preview-panel__header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }

        .report-mode-toggle {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 6px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
        }

        .report-mode-toggle__button {
          padding: 8px 12px;
          border-radius: 10px;
          color: var(--muted);
          cursor: pointer;
        }

        .report-mode-toggle__button--active {
          color: white;
          background: linear-gradient(135deg, #213558, #314a78);
        }

        .report-diff-panel {
          display: grid;
          gap: 12px;
          padding: 16px;
          border-radius: 18px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
        }

        .report-diff-panel__actions {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
        }

        .report-diff-panel__actions button {
          padding: 8px 12px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          cursor: pointer;
        }

        .report-diff-list {
          display: grid;
          gap: 6px;
          max-height: 320px;
          overflow: auto;
        }

        .report-diff-row {
          margin: 0;
          padding: 10px 12px;
          border-radius: 10px;
          white-space: pre-wrap;
          word-break: break-word;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.84rem;
        }

        .report-diff-row--added {
          background: rgba(232, 248, 243, 0.92);
          color: #1f7c5e;
        }

        .report-diff-row--removed {
          background: rgba(255, 239, 238, 0.92);
          color: #b34b46;
        }

        .report-diff-row--same {
          background: rgba(247, 249, 252, 0.88);
          color: var(--muted);
        }

        .report-upload-button {
          width: 100%;
          padding: 14px 16px;
          border-radius: 14px;
          background: linear-gradient(135deg, #2668f6, #2255d3);
          color: white;
          cursor: pointer;
          box-shadow: 0 16px 28px rgba(38, 104, 246, 0.2);
        }

        .report-searchbar input {
          width: 100%;
          padding: 12px 14px;
          border-radius: 14px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.88);
          color: var(--text);
        }

        .report-filter-tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .report-filter-tab {
          padding: 8px 10px;
          border-radius: 999px;
          border: 1px solid transparent;
          color: var(--muted);
          background: rgba(247, 248, 252, 0.84);
          cursor: pointer;
        }

        .report-filter-tab--active {
          color: var(--blue);
          border-color: rgba(79, 124, 255, 0.2);
          background: rgba(235, 241, 255, 0.96);
        }

        .report-file-tree {
          display: grid;
          gap: 4px;
          max-height: calc(100vh - 320px);
          padding-top: 8px;
          overflow: auto;
        }

        .report-file-row {
          display: grid;
          grid-template-columns: auto auto minmax(0, 1fr);
          align-items: center;
          width: 100%;
          min-width: 0;
          padding: 10px 12px;
          border-radius: 14px;
          color: var(--text);
          text-align: left;
          cursor: pointer;
        }

        .report-file-row:disabled {
          opacity: 0.72;
          cursor: default;
        }

        .report-file-row:hover:not(:disabled),
        .report-file-row--active {
          background: linear-gradient(135deg, rgba(236, 242, 255, 0.95), rgba(244, 247, 255, 0.95));
        }

        .report-file-row__indent {
          display: inline-block;
          height: 1px;
        }

        .report-file-row__icon {
          display: inline-grid;
          place-items: center;
          width: 18px;
          margin-right: 10px;
          color: #8fa1bf;
          font-size: 0.82rem;
        }

        .report-file-row__label {
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .report-storage-note {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding-top: 10px;
          color: var(--muted);
          font-size: 0.82rem;
          border-top: 1px solid rgba(33, 53, 88, 0.08);
        }

        .report-preview-card {
          padding: 16px;
          border-radius: 22px;
        }

        .report-preview-card__body {
          max-height: 280px;
          overflow: auto;
          padding: 14px;
          border-radius: 16px;
          border: 1px solid rgba(33, 53, 88, 0.08);
          background: rgba(247, 248, 252, 0.72);
        }

        .report-preview-card__body pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-word;
          color: var(--muted);
          line-height: 1.65;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 0.84rem;
        }

        .document-review-panel {
          display: grid;
          grid-template-rows: auto minmax(0, 1fr);
          gap: 12px;
          min-height: calc(100vh - 176px);
          padding: 0;
          overflow: hidden;
          border-radius: 12px;
          background: #eef1f6;
        }

        .document-review-toolbar {
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 10px;
          padding: 10px 12px;
          border-bottom: 1px solid rgba(33, 53, 88, 0.1);
          background: rgba(255, 255, 255, 0.96);
        }

        .document-review-toolbar__group {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding-right: 10px;
          border-right: 1px solid rgba(33, 53, 88, 0.1);
        }

        .document-review-toolbar__group--wide {
          gap: 8px;
        }

        .document-review-toolbar__group button,
        .document-review-toolbar__group select {
          height: 32px;
          border-radius: 6px;
          border: 1px solid rgba(33, 53, 88, 0.12);
          background: #ffffff;
          color: var(--text);
        }

        .document-review-toolbar__group button {
          width: 32px;
          cursor: pointer;
          font-weight: 700;
        }

        .document-review-toolbar__group select {
          min-width: 82px;
          padding: 0 8px;
        }

        .document-review-toolbar__status {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          margin-left: auto;
          color: var(--muted);
          font-size: 0.82rem;
        }

        .word-editor-stage {
          display: grid;
          grid-template-rows: auto minmax(0, 1fr);
          min-height: 0;
          overflow: hidden;
        }

        .word-editor-ruler {
          display: grid;
          grid-template-columns: repeat(12, 1fr);
          gap: 1px;
          height: 26px;
          padding: 0 28px;
          border-bottom: 1px solid rgba(33, 53, 88, 0.08);
          background: #f7f8fb;
          color: #8d96aa;
          font-size: 0.72rem;
        }

        .word-editor-ruler span {
          display: flex;
          align-items: center;
          justify-content: center;
          border-left: 1px solid rgba(33, 53, 88, 0.08);
        }

        .word-editor-workbench {
          display: grid;
          grid-template-columns: minmax(520px, 760px) 280px;
          gap: 18px;
          align-items: start;
          min-height: 0;
          padding: 24px;
          overflow: auto;
        }

        .word-page {
          display: grid;
          grid-template-rows: auto minmax(720px, 1fr) auto;
          width: min(100%, 760px);
          min-height: 960px;
          margin: 0 auto;
          padding: 38px 46px 32px;
          border: 1px solid rgba(33, 53, 88, 0.14);
          border-radius: 4px;
          background: #ffffff;
          box-shadow: 0 18px 44px rgba(54, 72, 98, 0.14);
        }

        .word-page__header,
        .word-page__footer {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          color: #8d96aa;
          font-size: 0.78rem;
        }

        .word-page__header {
          padding-bottom: 12px;
          border-bottom: 1px solid rgba(33, 53, 88, 0.08);
        }

        .word-page__footer {
          padding-top: 12px;
          border-top: 1px solid rgba(33, 53, 88, 0.08);
        }

        .word-page__editor {
          width: 100%;
          min-height: 720px;
          padding: 26px 0;
          border: 0;
          outline: none;
          resize: none;
          color: #1f2937;
          background: transparent;
          line-height: 1.9;
          font-family: "Times New Roman", "SimSun", serif;
          font-size: 1rem;
          white-space: pre-wrap;
        }

        .word-review-margin {
          display: grid;
          gap: 12px;
          align-content: start;
          position: sticky;
          top: 0;
        }

        .word-review-margin__summary,
        .word-comment {
          border: 1px solid rgba(33, 53, 88, 0.1);
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.94);
          box-shadow: 0 12px 26px rgba(54, 72, 98, 0.08);
        }

        .word-review-margin__summary {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          padding: 12px 14px;
        }

        .word-review-margin__summary span {
          color: var(--muted);
        }

        .word-comment {
          display: grid;
          gap: 10px;
          padding: 12px;
        }

        .word-comment__header {
          display: grid;
          gap: 8px;
        }

        .word-comment__header strong {
          font-size: 0.9rem;
          line-height: 1.45;
        }

        .word-comment__field {
          display: grid;
          gap: 6px;
        }

        .word-comment__field span {
          color: var(--muted);
          font-size: 0.78rem;
        }

        .word-comment__field textarea {
          width: 100%;
          padding: 10px 11px;
          border-radius: 6px;
          border: 1px solid rgba(103, 132, 181, 0.22);
          background: rgba(248, 250, 252, 0.9);
          color: var(--navy);
          resize: vertical;
          line-height: 1.6;
          font-size: 0.86rem;
        }

        .word-comment__field textarea:focus {
          outline: none;
          border-color: rgba(79, 124, 255, 0.45);
          box-shadow: 0 0 0 3px rgba(79, 124, 255, 0.08);
        }

        .document-review-severity {
          padding: 6px 12px;
          border-radius: 999px;
          font-size: 0.82rem;
          white-space: nowrap;
        }

        .document-review-severity--blocker {
          color: #d74d46;
          background: rgba(255, 238, 236, 0.95);
        }

        .document-review-severity--major {
          color: #da7e27;
          background: rgba(255, 244, 230, 0.95);
        }

        .document-review-severity--minor {
          color: #2a8d70;
          background: rgba(234, 248, 241, 0.95);
        }

        .document-review-severity--nit {
          color: #68758f;
          background: rgba(240, 243, 249, 0.95);
        }

        .document-review-field {
          display: grid;
          gap: 8px;
        }

        .document-review-field span {
          font-size: 0.88rem;
          color: var(--muted);
        }

        .document-review-field textarea {
          width: 100%;
          padding: 14px 16px;
          border-radius: 14px;
          border: 1px solid rgba(103, 132, 181, 0.22);
          background: rgba(255, 255, 255, 0.9);
          color: var(--navy);
          resize: vertical;
          line-height: 1.7;
          box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.8);
        }

        .document-review-field textarea:focus {
          outline: none;
          border-color: rgba(79, 124, 255, 0.45);
          box-shadow: 0 0 0 4px rgba(79, 124, 255, 0.08);
        }

        .document-review-item__footnote {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          padding-top: 2px;
          color: var(--muted);
          font-size: 0.84rem;
        }

        .report-assistant-badge {
          display: inline-grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 999px;
          background: rgba(235, 241, 255, 0.92);
          color: var(--blue);
        }

        .report-assistant-hero {
          display: grid;
          justify-items: center;
          gap: 10px;
          padding: 12px 10px 4px;
          text-align: left;
        }

        .report-assistant-hero__icon {
          display: grid;
          place-items: center;
          width: 78px;
          height: 78px;
          border-radius: 24px;
          background:
            radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.96), rgba(160, 193, 255, 0.78)),
            linear-gradient(180deg, #2e67f5, #1f53ce);
          box-shadow: 0 18px 30px rgba(47, 102, 243, 0.18);
          color: white;
          font-size: 2rem;
        }

        .report-assistant-hero p {
          margin: 0;
          color: var(--text);
          line-height: 1.7;
        }

        .report-assistant-shortcuts,
        .report-assistant-thread {
          display: grid;
          gap: 10px;
        }

        .report-assistant-shortcuts button,
        .report-assistant-message {
          display: grid;
          gap: 6px;
          min-width: 0;
          padding: 14px;
          border-radius: 16px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.84);
        }

        .report-assistant-shortcuts button {
          grid-template-columns: minmax(0, 1fr) auto;
          align-items: center;
          text-align: left;
          cursor: pointer;
        }

        .report-assistant-shortcuts button:hover {
          border-color: rgba(79, 124, 255, 0.18);
          background: rgba(247, 249, 255, 0.96);
        }

        .report-assistant-shortcuts button span:last-child {
          color: var(--muted);
        }

        .report-assistant-message--assistant {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.94));
        }

        .report-assistant-message--user {
          background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(247, 245, 240, 0.9));
        }

        .report-assistant-composer {
          display: grid;
          gap: 10px;
        }

        .report-assistant-composer textarea {
          width: 100%;
          padding: 14px 16px;
          border-radius: 16px;
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          color: var(--text);
          resize: vertical;
          line-height: 1.7;
        }

        .report-assistant-composer__footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          color: var(--muted);
          font-size: 0.82rem;
        }

        .report-assistant-composer__footer button {
          padding: 10px 16px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: linear-gradient(135deg, #2668f6, #2255d3);
          color: white;
          cursor: pointer;
        }

        .panel,
        .subpanel,
        .page-stack,
        .hero,
        .main-content,
        .review-grid,
        .chat-thread,
        .chat-bubble,
        .info-grid,
        .status,
        .button,
        .field,
        .form-grid,
        .action-row,
        .rule-list,
        .plain-list,
        .evidence-list,
        .list-table,
        .list-table__row,
        .stats-grid,
        .stat-card,
        .debug-details,
        .debug-grid,
        .token-list,
        .tab-row,
        .code-block,
        .eyebrow,
        .muted {
          font-family: inherit;
        }

        .observability-shell {
          display: grid;
          grid-template-columns: 280px minmax(0, 1fr) 360px;
          gap: 18px;
          min-height: calc(100vh - 110px);
          padding: 12px;
          border-radius: 30px;
          background:
            linear-gradient(180deg, rgba(255, 252, 246, 0.9), rgba(250, 245, 237, 0.84)),
            radial-gradient(circle at top right, rgba(192, 107, 66, 0.12), transparent 30%);
          border: 1px solid rgba(255, 255, 255, 0.72);
          box-shadow: 0 26px 80px rgba(94, 70, 48, 0.14);
          backdrop-filter: blur(18px);
        }

        .observability-shell--landing {
          grid-template-columns: minmax(0, 1fr) 360px;
        }

        .observability-sidebar,
        .observability-main,
        .observability-inspector {
          min-width: 0;
        }

        .observability-sidebar,
        .observability-inspector {
          display: grid;
          align-content: start;
        }

        .observability-sidebar__panel,
        .observability-inspector__panel,
        .observability-stage,
        .observability-panel,
        .observability-metric-card,
        .observability-header {
          border: 1px solid rgba(93, 67, 42, 0.1);
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(250, 246, 240, 0.9)),
            radial-gradient(circle at top left, rgba(255, 240, 224, 0.28), transparent 36%);
          box-shadow: 0 18px 36px rgba(94, 70, 48, 0.08);
        }

        .observability-sidebar__panel,
        .observability-inspector__panel,
        .observability-stage,
        .observability-panel {
          padding: 18px;
          border-radius: 26px;
        }

        .observability-main {
          display: grid;
          grid-template-rows: auto auto minmax(0, 1fr) auto;
          gap: 18px;
          align-content: start;
          min-height: 0;
        }

        .observability-stage {
          display: grid;
          grid-template-rows: auto minmax(0, 1fr);
          min-height: 0;
        }

        .observability-header {
          display: flex;
          justify-content: space-between;
          gap: 18px;
          align-items: flex-start;
          padding: 22px 24px;
          border-radius: 28px;
        }

        .observability-header h1 {
          margin: 4px 0 8px;
          font-size: clamp(1.8rem, 2.6vw, 2.8rem);
          letter-spacing: -0.05em;
          color: #2c2118;
        }

        .observability-header p,
        .observability-inspector__block p {
          margin: 0;
          color: #8b7766;
          line-height: 1.7;
        }

        .observability-header__badges {
          display: inline-flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 8px;
        }

        .observability-kicker {
          display: inline-block;
          color: #a06b49;
          font-size: 0.75rem;
          font-weight: 700;
          letter-spacing: 0.14em;
          text-transform: uppercase;
        }

        .observability-metrics {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 14px;
        }

        .observability-metric-card {
          display: grid;
          gap: 10px;
          padding: 18px;
          border-radius: 22px;
        }

        .observability-metric-card span,
        .observability-metric-card small,
        .observability-sidebar__header > span,
        .observability-stage__header > span,
        .observability-panel__header > span,
        .observability-trace-row small,
        .observability-session-card p,
        .observability-session-card__stats,
        .observability-session-card__time,
        .observability-task-row small,
        .observability-signal-card small,
        .observability-inspector__field span {
          color: #8b7766;
        }

        .observability-metric-card strong {
          font-size: 1.7rem;
          letter-spacing: -0.05em;
          color: #2c2118;
        }

        .observability-sidebar__header,
        .observability-stage__header,
        .observability-panel__header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 14px;
        }

        .observability-panel__actions {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .observability-sidebar__header strong,
        .observability-stage__header strong,
        .observability-panel__header strong,
        .observability-inspector__field strong {
          color: #2c2118;
        }

        .observability-session-list {
          display: grid;
          gap: 10px;
          max-height: calc(100vh - 210px);
          overflow: auto;
          padding-right: 4px;
        }

        .observability-session-card {
          display: grid;
          gap: 10px;
          padding: 14px;
          border-radius: 20px;
          border: 1px solid rgba(93, 67, 42, 0.08);
          background: rgba(255, 252, 248, 0.9);
          transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease;
        }

        .observability-session-card:hover,
        .observability-session-card--active {
          transform: translateY(-1px);
          border-color: rgba(160, 107, 73, 0.26);
          box-shadow: 0 16px 28px rgba(94, 70, 48, 0.08);
        }

        .observability-session-card strong,
        .observability-trace-row strong,
        .observability-task-row strong,
        .observability-signal-card strong {
          color: #2c2118;
        }

        .observability-session-card__meta,
        .observability-session-card__footer,
        .observability-session-card__stats {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          align-items: center;
          flex-wrap: wrap;
        }

        .observability-session-card__stats,
        .observability-session-card__footer {
          font-size: 0.8rem;
        }

        .observability-session-card p {
          margin: 0;
          line-height: 1.55;
        }

        .observability-session-card__anomaly {
          color: #a06b49;
        }

        .observability-pill {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          padding: 6px 10px;
          border-radius: 999px;
          background: #2f5548;
          color: #fdf8f1;
          font-size: 0.75rem;
          line-height: 1;
          white-space: nowrap;
        }

        .observability-pill--ghost {
          background: rgba(162, 115, 82, 0.12);
          color: #8f5d3e;
        }

        .observability-trace-table {
          display: grid;
          gap: 10px;
          min-height: 0;
          max-height: 58vh;
          overflow: auto;
          padding-right: 4px;
          padding-bottom: 4px;
        }

        .observability-trace-table__head {
          display: grid;
          grid-template-columns: 130px minmax(220px, 320px) minmax(0, 1fr);
          gap: 12px;
          padding: 0 12px;
          min-width: 920px;
          position: sticky;
          top: 0;
          z-index: 2;
          background: linear-gradient(180deg, rgba(255, 251, 246, 0.98), rgba(255, 248, 241, 0.98));
          color: #8b7766;
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.12em;
        }

        .observability-trace-table__body {
          display: grid;
          gap: 8px;
          min-height: 0;
        }

        .observability-trace-row {
          display: grid;
          grid-template-columns: 130px minmax(220px, 320px) minmax(0, 1fr);
          gap: 12px;
          width: 100%;
          min-width: 920px;
          padding: 12px;
          border-radius: 20px;
          border: 1px solid rgba(93, 67, 42, 0.08);
          background: rgba(255, 253, 250, 0.84);
          text-align: left;
          cursor: pointer;
          transition: border-color 160ms ease, background 160ms ease, transform 160ms ease;
        }

        .observability-trace-row:hover,
        .observability-trace-row--selected {
          transform: translateY(-1px);
          border-color: rgba(160, 107, 73, 0.24);
          background: rgba(255, 251, 246, 0.98);
        }

        .observability-trace-row__step,
        .observability-trace-row__lane {
          display: grid;
          gap: 6px;
          min-width: 0;
        }

        .observability-trace-row__lane strong,
        .observability-trace-row__lane small {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .observability-trace-row__bar {
          position: relative;
          display: flex;
          align-items: center;
          min-height: 58px;
          padding: 0 12px;
          overflow: hidden;
        }

        .observability-trace-row__track,
        .observability-trace-row__fill {
          position: absolute;
          height: 18px;
          border-radius: 999px;
        }

        .observability-trace-row__track {
          inset: 50% 0 auto 0;
          transform: translateY(-50%);
          background: linear-gradient(90deg, rgba(210, 189, 170, 0.26), rgba(210, 189, 170, 0.08));
        }

        .observability-trace-row__fill {
          top: 50%;
          transform: translateY(-50%);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.42);
        }

        .observability-trace-row__label {
          position: relative;
          z-index: 1;
          margin-left: auto;
          padding-left: 10px;
          color: #8b7766;
          font-size: 0.78rem;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .observability-trace-row--success .observability-trace-row__fill {
          background: linear-gradient(90deg, #3f6f60, #6fab90);
        }

        .observability-trace-row--error .observability-trace-row__fill {
          background: linear-gradient(90deg, #8f493f, #c3745e);
        }

        .observability-trace-row--running .observability-trace-row__fill {
          background: linear-gradient(90deg, #a06b49, #d79a63);
        }

        .observability-trace-row--info .observability-trace-row__fill {
          background: linear-gradient(90deg, #74645a, #a9998d);
        }

        .observability-lower-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.85fr);
          gap: 18px;
        }

        .observability-task-list,
        .observability-signal-list {
          display: grid;
          gap: 10px;
        }

        .observability-task-row,
        .observability-signal-card {
          display: grid;
          gap: 6px;
          padding: 12px 14px;
          border-radius: 16px;
          border: 1px solid rgba(93, 67, 42, 0.08);
          background: rgba(255, 252, 248, 0.76);
        }

        .observability-task-row {
          position: relative;
        }

        .observability-task-row::before {
          content: "";
          position: absolute;
          left: 14px;
          top: 18px;
          width: 7px;
          height: 7px;
          border-radius: 999px;
          background: #a06b49;
        }

        .observability-task-row--selected {
          border-color: rgba(160, 107, 73, 0.24);
          background: rgba(255, 248, 241, 0.96);
        }

        .observability-task-row__kind,
        .observability-signal-card span,
        .observability-open-link {
          color: #a06b49;
        }

        .observability-signal-card--alert {
          background: linear-gradient(180deg, rgba(255, 243, 238, 0.94), rgba(255, 248, 243, 0.94));
        }

        .observability-inspector__panel {
          display: grid;
          gap: 14px;
          align-content: start;
          min-height: calc(100vh - 134px);
          position: sticky;
          top: 12px;
        }

        .observability-inspector__block {
          display: grid;
          gap: 12px;
          padding: 14px;
          border-radius: 18px;
          background: rgba(255, 252, 248, 0.72);
          border: 1px solid rgba(93, 67, 42, 0.08);
        }

        .observability-inspector__grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }

        .observability-inspector__field {
          display: grid;
          gap: 6px;
          padding: 10px 12px;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.72);
          min-width: 0;
        }

        .observability-inspector__field strong,
        .observability-panel__header span,
        .observability-sidebar__header > span {
          white-space: normal;
          overflow-wrap: anywhere;
          word-break: break-word;
        }

        .observability-inspector__block pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 260px;
          overflow: auto;
          color: #5d4f45;
          font-size: 0.83rem;
          line-height: 1.7;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }

        .observability-open-link {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          padding: 12px 16px;
          border-radius: 14px;
          border: 1px solid rgba(160, 107, 73, 0.16);
          background: rgba(255, 248, 241, 0.82);
          font-weight: 600;
        }

        .observability-toggle-button {
          padding: 7px 12px;
          border-radius: 999px;
          border: 1px solid rgba(160, 107, 73, 0.18);
          background: rgba(255, 248, 241, 0.86);
          color: #8f5d3e;
          cursor: pointer;
          transition: background 160ms ease, border-color 160ms ease;
        }

        .observability-toggle-button:hover {
          background: rgba(255, 243, 233, 0.96);
          border-color: rgba(160, 107, 73, 0.28);
        }

        @media (max-width: 1280px) {
          .workspace-shell {
            grid-template-columns: 220px minmax(0, 1fr) 320px;
          }

          .settings-workspace {
            grid-template-columns: 260px minmax(0, 1fr) 300px;
          }

          .observability-shell {
            grid-template-columns: 240px minmax(0, 1fr) 320px;
          }

          .observability-shell--landing {
            grid-template-columns: minmax(0, 1fr) 320px;
          }

          .observability-metrics,
          .observability-lower-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 1100px) {
          .workspace-shell {
            grid-template-columns: 1fr;
          }

          .settings-workspace {
            grid-template-columns: 1fr;
          }

          .report-shell {
            grid-template-columns: 1fr;
          }

          .observability-shell,
          .observability-shell--landing {
            grid-template-columns: 1fr;
          }

          .workspace-sidebar,
          .workspace-rightbar,
          .settings-workspace__sidebar,
          .settings-workspace__right,
          .report-sidebar,
          .report-rightbar {
            grid-template-columns: 1fr;
            align-self: stretch;
          }

          .observability-inspector__panel {
            position: static;
            min-height: 0;
          }

          .workspace-main,
          .settings-workspace__main,
          .report-main {
            order: -1;
          }

          .workspace-chat {
            max-height: none;
          }

          .mcp-service-row,
          .mcp-dynamic-row,
          .mcp-dynamic-row--pair {
            grid-template-columns: 1fr;
          }

          .mcp-service-row__actions {
            justify-content: flex-start;
          }
        }

        @media (max-width: 760px) {
          .app-frame {
            width: min(100vw - 12px, 1600px);
            margin-top: 6px;
          }

          .app-nav {
            justify-content: flex-start;
            overflow: auto;
            padding-bottom: 10px;
          }

          .settings-fab {
            left: 12px;
            bottom: 12px;
            padding: 10px 14px;
          }

          .workspace-shell,
          .settings-workspace,
          .report-shell {
            padding: 10px;
            border-radius: 22px;
          }

          .observability-shell {
            padding: 10px;
            border-radius: 24px;
          }

          .workspace-capabilities,
          .workspace-toolbar,
          .settings-stat-grid,
          .settings-form-grid,
          .report-editor-grid {
            grid-template-columns: 1fr;
          }

          .observability-metrics,
          .observability-lower-grid,
          .observability-inspector__grid,
          .observability-trace-row {
            grid-template-columns: 1fr;
          }

          .observability-header {
            flex-direction: column;
          }

          .workspace-composer__footer,
          .workspace-topbar,
          .workspace-panel__header,
          .settings-provider-card__head,
          .settings-provider-card__actions,
          .settings-form-actions,
          .settings-topbar__note {
            align-items: flex-start;
            flex-direction: column;
          }

          .workspace-message {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </html>
  );
}
