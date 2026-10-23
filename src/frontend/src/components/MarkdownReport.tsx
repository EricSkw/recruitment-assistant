import type { ReactNode } from "react";

type Block =
  | { kind: "h2"; text: string }
  | { kind: "h3"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "p"; text: string };

export function parseMarkdown(markdown: string): Block[] {
  const lines = markdown.replaceAll("\r\n", "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index] ?? "";
    if (line.trim() === "") {
      index += 1;
      continue;
    }
    if (line.startsWith("### ")) {
      blocks.push({ kind: "h3", text: line.slice(4) });
      index += 1;
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push({ kind: "h2", text: line.slice(3) });
      index += 1;
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push({ kind: "h2", text: line.slice(2) });
      index += 1;
      continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      const items: string[] = [];
      while (index < lines.length) {
        const item = lines[index] ?? "";
        if (!item.startsWith("- ") && !item.startsWith("* ")) break;
        items.push(item.slice(2));
        index += 1;
      }
      blocks.push({ kind: "list", items });
      continue;
    }
    const paragraph: string[] = [];
    while (index < lines.length) {
      const part = lines[index] ?? "";
      if (part.trim() === "" || part.startsWith("#") || part.startsWith("- ") || part.startsWith("* ")) {
        break;
      }
      paragraph.push(part);
      index += 1;
    }
    blocks.push({ kind: "p", text: paragraph.join(" ") });
  }
  return blocks;
}

function inline(text: string, key: string): ReactNode[] {
  const pattern =
    /(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/[^\s)]+))/g;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let match = pattern.exec(text);
  let part = 0;
  while (match) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }
    if (match[2]) {
      nodes.push(<strong key={`${key}-${part}`}>{match[2]}</strong>);
    } else if (match[3]) {
      nodes.push(<code key={`${key}-${part}`}>{match[3]}</code>);
    } else if (match[4] && match[5]) {
      nodes.push(
        <a key={`${key}-${part}`} href={match[5]} rel="noopener noreferrer" target="_blank">
          {match[4]}
        </a>,
      );
    } else if (match[6]) {
      nodes.push(
        <a key={`${key}-${part}`} href={match[6]} rel="noopener noreferrer" target="_blank">
          {match[6]}
        </a>,
      );
    }
    cursor = match.index + match[0].length;
    part += 1;
    match = pattern.exec(text);
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

export function MarkdownReport({ markdown }: { markdown: string }) {
  const blocks = parseMarkdown(markdown);
  return (
    <div className="markdown">
      {blocks.map((block, index) => {
        const key = `b${index}`;
        if (block.kind === "h2") return <h2 key={key}>{inline(block.text, key)}</h2>;
        if (block.kind === "h3") return <h3 key={key}>{inline(block.text, key)}</h3>;
        if (block.kind === "list") {
          return (
            <ul key={key}>
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{inline(item, `${key}-${itemIndex}`)}</li>
              ))}
            </ul>
          );
        }
        return <p key={key}>{inline(block.text, key)}</p>;
      })}
    </div>
  );
}
