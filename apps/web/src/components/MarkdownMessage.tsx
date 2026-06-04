"use client";

import { Fragment, type ReactNode } from "react";

type Props = {
  content: string;
};

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "blockquote"; lines: string[] }
  | { type: "code"; code: string }
  | { type: "table"; header: string[]; rows: string[][] };

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isTableDivider(line: string): boolean {
  const cells = splitTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderInline(text: string): string {
  let html = escapeHtml(text);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer">$1</a>',
  );
  return html;
}

function parseBlocks(content: string): Block[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) {
        i += 1;
      }
      blocks.push({ type: "code", code: codeLines.join("\n") });
      continue;
    }

    const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      i += 1;
      continue;
    }

    if (
      trimmed.includes("|") &&
      i + 1 < lines.length &&
      lines[i + 1] &&
      isTableDivider(lines[i + 1].trim())
    ) {
      const header = splitTableRow(trimmed);
      const rows: string[][] = [];
      i += 2;
      while (i < lines.length) {
        const current = lines[i].trim();
        if (!current || !current.includes("|")) {
          break;
        }
        rows.push(splitTableRow(current));
        i += 1;
      }
      blocks.push({ type: "table", header, rows });
      continue;
    }

    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ type: "blockquote", lines: quoteLines });
      continue;
    }

    const unordered = trimmed.match(/^[-*]\s+(.+)$/);
    const ordered = trimmed.match(/^\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      const items: string[] = [];
      const isOrdered = Boolean(ordered);
      while (i < lines.length) {
        const current = lines[i].trim();
        const match = isOrdered ? current.match(/^\d+\.\s+(.+)$/) : current.match(/^[-*]\s+(.+)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
        i += 1;
      }
      blocks.push({ type: "list", ordered: isOrdered, items });
      continue;
    }

    const paragraphLines: string[] = [trimmed];
    i += 1;
    while (i < lines.length) {
      const current = lines[i].trim();
      if (
        !current ||
        current.startsWith("```") ||
        current.startsWith(">") ||
        /^#{1,6}\s+/.test(current) ||
        /^[-*]\s+/.test(current) ||
        /^\d+\.\s+/.test(current)
      ) {
        break;
      }
      paragraphLines.push(current);
      i += 1;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
  }

  return blocks;
}

function HtmlSpan({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

export function MarkdownMessage({ content }: Props) {
  const blocks = parseBlocks(content);

  return (
    <div className="workspace-markdown">
      {blocks.map((block, index) => {
        const key = `${block.type}-${index}`;
        if (block.type === "heading") {
          if (block.level <= 2) {
            return (
              <h3 key={key}>
                <HtmlSpan html={renderInline(block.text)} />
              </h3>
            );
          }
          return (
            <h4 key={key}>
              <HtmlSpan html={renderInline(block.text)} />
            </h4>
          );
        }
        if (block.type === "paragraph") {
          return (
            <p key={key}>
              <HtmlSpan html={renderInline(block.text)} />
            </p>
          );
        }
        if (block.type === "blockquote") {
          return (
            <blockquote key={key}>
              {block.lines.map((line, lineIndex) => (
                <Fragment key={`${key}-${lineIndex}`}>
                  <HtmlSpan html={renderInline(line)} />
                  {lineIndex < block.lines.length - 1 ? <br /> : null}
                </Fragment>
              ))}
            </blockquote>
          );
        }
        if (block.type === "code") {
          return (
            <pre key={key}>
              <code>{block.code}</code>
            </pre>
          );
        }
        if (block.type === "table") {
          return (
            <div key={key} className="workspace-markdown__table-wrap">
              <table className="workspace-markdown__table">
                <thead>
                  <tr>
                    {block.header.map((cell, cellIndex) => (
                      <th key={`${key}-head-${cellIndex}`}>
                        <HtmlSpan html={renderInline(cell)} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, rowIndex) => (
                    <tr key={`${key}-row-${rowIndex}`}>
                      {row.map((cell, cellIndex) => (
                        <td key={`${key}-row-${rowIndex}-cell-${cellIndex}`}>
                          <HtmlSpan html={renderInline(cell)} />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        const ListTag = block.ordered ? "ol" : "ul";
        return (
          <ListTag key={key}>
            {block.items.map((item, itemIndex) => (
              <li key={`${key}-${itemIndex}`}>
                <HtmlSpan html={renderInline(item)} />
              </li>
            ))}
          </ListTag>
        );
      })}
    </div>
  );
}
