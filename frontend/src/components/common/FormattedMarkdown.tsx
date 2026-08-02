import React from 'react';

interface FormattedMarkdownProps {
  content: string;
  className?: string;
}

export const FormattedMarkdown: React.FC<FormattedMarkdownProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Pre-process text: Fix squeezed list items like "1. **Title**: text 2. **Title**" -> put newlines before numberings
  let processed = content
    .replace(/([^\n])\s*(\d+\.\s+\*\*)/g, '$1\n\n$2')
    .replace(/([^\n])\s*(-\s+\*\*)/g, '$1\n\n$2');

  // Split into lines/blocks
  const paragraphs = processed.split('\n');

  const renderInline = (text: string) => {
    // Split by code blocks first `code`
    const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);

    return parts.map((part, index) => {
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={index} className="inline-code">
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className={`formatted-markdown ${className}`}>
      {paragraphs.map((para, i) => {
        const trimmed = para.trim();
        if (!trimmed) return <div key={i} style={{ height: '0.5rem' }} />;

        // Header ###
        if (trimmed.startsWith('### ')) {
          return (
            <h4 key={i} className="markdown-h4">
              {renderInline(trimmed.slice(4))}
            </h4>
          );
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h3 key={i} className="markdown-h3">
              {renderInline(trimmed.slice(3))}
            </h3>
          );
        }
        if (trimmed.startsWith('# ')) {
          return (
            <h2 key={i} className="markdown-h2">
              {renderInline(trimmed.slice(2))}
            </h2>
          );
        }

        // List item (1. or - or *)
        const listMatch = trimmed.match(/^(\d+\.|\*|-)\s+(.*)/);
        if (listMatch) {
          const prefix = listMatch[1];
          const text = listMatch[2];
          return (
            <div key={i} className="markdown-list-item">
              <span className="markdown-list-prefix">{prefix}</span>
              <div className="markdown-list-text">{renderInline(text)}</div>
            </div>
          );
        }

        // Blockquote
        if (trimmed.startsWith('> ')) {
          return (
            <blockquote key={i} className="markdown-blockquote">
              {renderInline(trimmed.slice(2))}
            </blockquote>
          );
        }

        // Regular paragraph
        return (
          <p key={i} className="markdown-paragraph">
            {renderInline(trimmed)}
          </p>
        );
      })}
    </div>
  );
};
