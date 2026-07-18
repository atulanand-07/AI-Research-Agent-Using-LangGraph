import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

/**
 * Markdown
 * -----------------------------------------------------------------------------
 * Renders a string of Markdown as fully-styled HTML.
 *
 * Why this component exists:
 *   The previous chat bubble rendered `{message.text}` inside a `<p>` tag, which
 *   collapsed every AI response into a single paragraph — newlines, lists,
 *   tables, headings, and code blocks all vanished. This component delegates
 *   parsing to `react-markdown` and applies our own `remark-gfm` (GitHub-flavoured
 *   Markdown: tables, task lists, strikethrough, autolinks) and `rehype-highlight`
 *   (syntax highlighting for fenced code blocks) plugins.
 *
 * Streaming-friendly:
 *   `react-markdown` re-parses on every render. The parent updates the message
 *   text on each token it receives, and this component re-renders incrementally.
 *   There is no batching or debouncing inside the component — keep it dumb so
 *   that the streaming pipeline stays simple.
 *
 * Whitespace / line breaks:
 *   `remark-gfm` enables GFM line breaks, so a single trailing space + newline
 *   (`  \n`) becomes a real `<br>`. We also override the default `p` renderer
 *   to flatten the top/bottom margin and use the chat-bubble container's gap
 *   instead — this keeps consecutive paragraphs readable without doubling the
 *   spacing between them.
 */
export default function Markdown({ children }) {
  // Guard against non-string input (numbers, undefined, etc.) that can sneak in
  // from streaming payloads or older chat history.
  const source = typeof children === 'string' ? children : children == null ? '' : String(children);

  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        // Allow raw HTML inside Markdown but skip dangerous script tags.
        // The backend only feeds us model output, but be defensive anyway.
        skipHtml={false}
        // Force a paragraph break before every block-level element so that
        // lists / tables / code blocks inside a chat bubble always start on
        // their own line, even if the source text doesn't include a blank
        // line between them. This is the single most common streaming bug.
        components={{
          p: ({ children: pChildren, ...props }) => <p {...props}>{pChildren}</p>,
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
