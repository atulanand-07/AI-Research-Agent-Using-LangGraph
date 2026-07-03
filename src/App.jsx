import { useMemo, useState, useEffect, useRef } from 'react';
import {
  Bot,
  FileText,
  Globe2,
  Plus,
  Search,
  Send,
  Trash2,
  Zap,
} from 'lucide-react';
import {
  getSession,
  sendChat,
  uploadPdf,
  addWikipediaSource,
  deleteSource,
  searchArticles,
  selectArticle
} from './api';

const fallbackSuggestions = [
  'Why Multi-head Attention?',
  'Applications',
  'Limitations',
  'Future Work',
  'Encoder vs Decoder',
];

const seedMessages = [
  {
    id: 'seed-1',
    role: 'assistant',
    text: 'Welcome to AI Researcher. Ask a question, add sources, or search for research papers to ground the conversation.',
    followup_questions: fallbackSuggestions,
  },
];

function getKnowledgeMode(sourcesOn, articlesOn) {
  if (sourcesOn && articlesOn) return { key: 'hybrid', label: 'Hybrid' };
  if (sourcesOn) return { key: 'sources', label: 'RAG Mode' };
  if (articlesOn) return { key: 'article', label: 'Article Chat' };
  return { key: 'general', label: 'General Chat' };
}

function Header({ sourcesOn, articlesOn, onToggleSources, onToggleArticles }) {
  const mode = getKnowledgeMode(sourcesOn, articlesOn);

  return (
    <header className="app-header">
      <div className="brand">
        <div className="brand-icon" aria-hidden="true">
          <Bot size={22} />
        </div>
        <h1>AI Researcher</h1>
      </div>

      <div className="header-actions" aria-label="Knowledge controls">
        <ToggleButtons label="Sources" active={sourcesOn} onToggle={onToggleSources} />
        <ToggleButtons label="Articles" active={articlesOn} onToggle={onToggleArticles} />
        <div className="mode-pill">
          <span>Current Mode:</span>
          <strong>{mode.label}</strong>
        </div>
      </div>
    </header>
  );
}

function ToggleButtons({ label, active, onToggle }) {
  return (
    <div className="toggle-group">
      <span>{label}</span>
      <button
        className={`toggle-button ${active ? 'is-on' : ''}`}
        type="button"
        onClick={onToggle}
        aria-pressed={active}
      >
        {active ? 'ON' : 'OFF'}
      </button>
    </div>
  );
}

function SourcesPanel({
  sources,
  onAddPdf,
  onAddWiki,
  onDeleteSource,
  isUploadingPdf,
  isAddingWiki,
}) {
  const fileInputRef = useRef(null);
  const [wikiVal, setWikiVal] = useState('');

  const handleWikiSubmit = (e) => {
    e.preventDefault();
    const val = wikiVal.trim();
    if (!val) return;
    onAddWiki(val);
    setWikiVal('');
  };

  return (
    <section className="panel sources-panel" aria-labelledby="sources-heading">
      <div className="panel-header">
        <h2 id="sources-heading">Sources</h2>
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <button
          className="add-source"
          type="button"
          onClick={() => fileInputRef.current?.click()}
          style={{ margin: 0, width: '100%' }}
          disabled={isUploadingPdf}
        >
          <Plus size={18} />
          {isUploadingPdf ? 'Uploading PDF...' : 'Upload PDF'}
        </button>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          accept=".pdf"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              onAddPdf(e.target.files[0]);
              e.target.value = ''; // Reset file input
            }
          }}
        />

        <form onSubmit={handleWikiSubmit} style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            placeholder="Add Wikipedia URL/topic..."
            value={wikiVal}
            onChange={(e) => setWikiVal(e.target.value)}
            disabled={isAddingWiki}
            style={{
              flex: 1,
              background: '#202226',
              border: '1px solid #34373d',
              borderRadius: '999px',
              padding: '0 14px',
              height: '34px',
              color: '#ffffff',
              fontSize: '13px',
              outline: 'none',
            }}
          />
          <button
            type="submit"
            disabled={isAddingWiki || !wikiVal.trim()}
            style={{
              height: '34px',
              borderRadius: '999px',
              padding: '0 14px',
              background: '#4a90e2',
              color: '#ffffff',
              border: 'none',
              fontSize: '13px',
              fontWeight: '700',
              cursor: 'pointer',
              opacity: isAddingWiki || !wikiVal.trim() ? 0.6 : 1,
            }}
          >
            Add
          </button>
        </form>
      </div>

      <div className="source-support">
        <span>Supported</span>
        <div>
          <span>PDF</span>
          <span>Wikipedia URL</span>
        </div>
      </div>

      <div className="source-list">
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} onDelete={onDeleteSource} />
        ))}
      </div>

      {sources.length === 0 && (
        <div className="empty-state">
          <FileText size={34} />
          <strong>No sources added yet.</strong>
          <p>Add PDFs or Wikipedia links to ground your research chat.</p>
        </div>
      )}
    </section>
  );
}

function SourceCard({ source, onDelete }) {
  const isPdf = source.source_type === 'pdf';
  const displayName = source.filename;

  const isPendingOrProcessing = source.status === 'pending' || source.status === 'processing';

  return (
    <article className={`source-card ${isPendingOrProcessing ? 'processing' : ''}`}>
      <div className="source-icon" aria-hidden="true">
        {isPdf ? <FileText size={18} /> : <Globe2 size={18} />}
      </div>
      <div style={{ minWidth: 0, flex: 1 }}>
        <h3 style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', margin: 0 }} title={displayName}>
          {displayName}
        </h3>
        <p style={{ display: 'flex', gap: '8px', alignItems: 'center', margin: '4px 0 0' }}>
          <span>{isPdf ? 'PDF' : 'Wikipedia'}</span>
          {source.status && (
            <span
              style={{
                fontSize: '11px',
                padding: '2px 6px',
                borderRadius: '4px',
                background:
                  source.status === 'ready'
                    ? 'rgba(74, 144, 226, 0.2)'
                    : source.status === 'error'
                      ? 'rgba(235, 87, 87, 0.2)'
                      : 'rgba(242, 201, 76, 0.2)',
                color:
                  source.status === 'ready'
                    ? '#4a90e2'
                    : source.status === 'error'
                      ? '#eb5757'
                      : '#f2c94c',
              }}
            >
              {source.status}
            </span>
          )}
        </p>
      </div>
      <button
        className="icon-button"
        type="button"
        onClick={() => onDelete(source.id)}
        aria-label={`Delete ${displayName}`}
      >
        <Trash2 size={17} />
      </button>
    </article>
  );
}

function ChatPanel({ messages, onSendMessage, isLoading }) {
  const [draft, setDraft] = useState('');

  function submitMessage(text = draft) {
    const cleanText = text.trim();
    if (!cleanText || isLoading) return;
    onSendMessage(cleanText);
    setDraft('');
  }

  return (
    <section className="panel chat-panel" aria-labelledby="chat-heading">
      <div className="panel-header">
        <h2 id="chat-heading">Chat</h2>
        <Zap size={18} />
      </div>

      <div className="message-list">
        {messages.map((message) => (
          <ChatBubble key={message.id} message={message} onChipClick={submitMessage} />
        ))}
        {isLoading && (
          <article className="chat-row assistant" style={{ opacity: 0.7 }}>
            <div className="chat-bubble">
              <p>Thinking...</p>
            </div>
          </article>
        )}
      </div>

      <form
        className="chat-composer"
        onSubmit={(event) => {
          event.preventDefault();
          submitMessage();
        }}
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask anything..."
          aria-label="Ask anything"
          disabled={isLoading}
        />
        <button type="submit" aria-label="Send message" disabled={isLoading || !draft.trim()}>
          <Send size={20} />
        </button>
      </form>
    </section>
  );
}

function ChatBubble({ message, onChipClick }) {
  const isAssistant = message.role === 'assistant';

  const sourcesText =
    isAssistant && message.grounded_in && message.grounded_in.length > 0
      ? `Answer generated using: ${message.grounded_in.join(', ')}`
      : '';

  const modeText = isAssistant && message.knowledge_mode ? `Mode: ${message.knowledge_mode}` : '';

  return (
    <article className={`chat-row ${isAssistant ? 'assistant' : 'user'}`}>
      <div className="chat-bubble">
        <p>{message.text}</p>
        {isAssistant && (sourcesText || modeText) && (
          <div
            style={{
              marginTop: '8px',
              fontSize: '11px',
              color: '#aeb4be',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            {sourcesText && <span style={{ fontStyle: 'italic' }}>{sourcesText}</span>}
            {modeText && <span style={{ opacity: 0.8 }}>{modeText}</span>}
          </div>
        )}
      </div>
      {isAssistant && message.followup_questions && message.followup_questions.length > 0 && (
        <SuggestionChips suggestions={message.followup_questions} onSelect={onChipClick} />
      )}
    </article>
  );
}

function SuggestionChips({ suggestions, onSelect }) {
  return (
    <div className="suggestion-chips" aria-label="Follow-up suggestions">
      {suggestions.map((suggestion) => (
        <button key={suggestion} type="button" onClick={() => onSelect(suggestion)}>
          {suggestion}
        </button>
      ))}
    </div>
  );
}

function ArticlesPanel({
  searchText,
  onSearchText,
  onSearchSubmit,
  filteredPapers,
  selectedArticle,
  onSelectPaper,
  isSearchingArticles,
}) {
  return (
    <section className="panel articles-panel" aria-labelledby="articles-heading">
      <div className="panel-header">
        <h2 id="articles-heading">Get Articles</h2>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSearchSubmit();
        }}
      >
        <SearchBar value={searchText} onChange={onSearchText} />
      </form>

      <div className="paper-list">
        {isSearchingArticles && (
          <div style={{ textAlign: 'center', padding: '20px', color: '#aeb4be' }}>
            Searching articles...
          </div>
        )}
        {!isSearchingArticles &&
          filteredPapers.map((paper) => (
            <PaperCard
              key={paper.id || paper.title}
              paper={paper}
              selected={selectedArticle?.title === paper.title || selectedArticle?.id === paper.id}
              selectedArticleStatus={selectedArticle?.status}
              onSelect={onSelectPaper}
            />
          ))}
        {!isSearchingArticles && filteredPapers.length === 0 && (
          <div className="empty-state" style={{ marginTop: '20px' }}>
            <Search size={34} />
            <strong>No articles found.</strong>
            <p>Type a topic above and press Enter to search.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function SearchBar({ value, onChange }) {
  return (
    <label className="search-bar">
      <Search size={18} />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search research papers..."
      />
    </label>
  );
}

function PaperCard({ paper, selected, onSelect, selectedArticleStatus }) {
  const authorsStr = Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors;
  const citationCountStr =
    paper.citation_count !== undefined && paper.citation_count !== null
      ? `${paper.citation_count.toLocaleString()} citations`
      : '';

  return (
    <button
      type="button"
      className={`paper-card ${selected ? 'is-selected' : ''}`}
      onClick={() => onSelect(paper)}
    >
      <span
        className="paper-meta"
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
      >
        <span>
          {paper.source} · {paper.publication_year || paper.year}
        </span>
        {selected && selectedArticleStatus && (
          <span
            style={{
              fontSize: '11px',
              padding: '2px 6px',
              borderRadius: '4px',
              background:
                selectedArticleStatus === 'ready'
                  ? 'rgba(74, 144, 226, 0.2)'
                  : selectedArticleStatus === 'error'
                    ? 'rgba(235, 87, 87, 0.2)'
                    : 'rgba(242, 201, 76, 0.2)',
              color:
                selectedArticleStatus === 'ready'
                  ? '#4a90e2'
                  : selectedArticleStatus === 'error'
                    ? '#eb5757'
                    : '#f2c94c',
            }}
          >
            {selectedArticleStatus}
          </span>
        )}
      </span>
      <h3>{paper.title}</h3>
      <p className="authors">{authorsStr}</p>
      <p>{paper.abstract}</p>
      {citationCountStr && <strong>{citationCountStr}</strong>}
    </button>
  );
}

export default function App() {
  const [sources, setSources] = useState([]);
  const [messages, setMessages] = useState(seedMessages);
  const [searchText, setSearchText] = useState('');
  const [filteredPapers, setFilteredPapers] = useState([]);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [sourcesOn, setSourcesOn] = useState(false);
  const [articlesOn, setArticlesOn] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSearchingArticles, setIsSearchingArticles] = useState(false);
  const [isUploadingPdf, setIsUploadingPdf] = useState(false);
  const [isAddingWiki, setIsAddingWiki] = useState(false);

  // Polling effect for pending/processing sources or articles.
  // Chat history is page-local for the session; only sync status of
  // in-flight sources and the selected article.
  useEffect(() => {
    const hasPendingSources = sources.some(
      (s) => s.status === 'pending' || s.status === 'processing'
    );
    const hasPendingArticle =
      selectedArticle &&
      (selectedArticle.status === 'pending' || selectedArticle.status === 'processing');

    if (hasPendingSources || hasPendingArticle) {
      const timer = setTimeout(async () => {
        try {
          const data = await getSession();
          setSources(data.uploaded_sources || []);
          setSelectedArticle(data.selected_article || null);
          setFilteredPapers(data.article_results || []);
        } catch (err) {
          console.error('Error polling session status:', err);
        }
      }, 1500);

      return () => clearTimeout(timer);
    }
  }, [sources, selectedArticle]);

  const handleAddPdf = async (file) => {
    setIsUploadingPdf(true);
    try {
      await uploadPdf(file);
      const data = await getSession();
      setSources(data.uploaded_sources || []);
    } catch (err) {
      console.error('Error uploading PDF:', err);
      alert(`Failed to upload PDF: ${err.message}`);
    } finally {
      setIsUploadingPdf(false);
    }
  };

  const handleAddWiki = async (urlOrTopic) => {
    setIsAddingWiki(true);
    try {
      await addWikipediaSource(urlOrTopic);
      const data = await getSession();
      setSources(data.uploaded_sources || []);
    } catch (err) {
      console.error('Error adding Wikipedia source:', err);
      alert(`Failed to add Wikipedia source: ${err.message}`);
    } finally {
      setIsAddingWiki(false);
    }
  };

  const handleDeleteSource = async (id) => {
    try {
      await deleteSource(id);
      const data = await getSession();
      setSources(data.uploaded_sources || []);
    } catch (err) {
      console.error('Error deleting source:', err);
      alert(`Failed to delete source: ${err.message}`);
    }
  };

  const handleSearchSubmit = async () => {
    const query = searchText.trim();
    if (!query) return;
    setIsSearchingArticles(true);
    try {
      const data = await searchArticles(query);
      setFilteredPapers(data.articles || []);
    } catch (err) {
      console.error('Error searching articles:', err);
      alert(`Failed to search articles: ${err.message}`);
    } finally {
      setIsSearchingArticles(false);
    }
  };

  const handleSelectPaper = async (paper) => {
    try {
      await selectArticle(paper);
      const data = await getSession();
      setSelectedArticle(data.selected_article || null);
    } catch (err) {
      console.error('Error selecting article:', err);
      alert(`Failed to select article: ${err.message}`);
    }
  };

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      text: text.trim(),
    };

    setMessages((current) => [...current, userMsg]);
    setIsLoading(true);

    try {
      const mode = getKnowledgeMode(sourcesOn, articlesOn).key;
      const response = await sendChat(text.trim(), mode);

      const assistantMsg = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        text: response.answer,
        grounded_in: response.active_sources_used || [],
        knowledge_mode: response.knowledge_mode,
        followup_questions: response.followup_questions || [],
      };

      setMessages((current) => [...current, assistantMsg]);
    } catch (err) {
      console.error('Error sending chat:', err);
      setMessages((current) => [
        ...current,
        {
          id: `error-${Date.now()}`,
          role: 'assistant',
          text: `Error sending message: ${err.message}. Please verify the backend is running.`,
          followup_questions: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <Header
        sourcesOn={sourcesOn}
        articlesOn={articlesOn}
        onToggleSources={() => setSourcesOn((value) => !value)}
        onToggleArticles={() => setArticlesOn((value) => !value)}
      />

      <main className="workspace">
        <SourcesPanel
          sources={sources}
          onAddPdf={handleAddPdf}
          onAddWiki={handleAddWiki}
          onDeleteSource={handleDeleteSource}
          isUploadingPdf={isUploadingPdf}
          isAddingWiki={isAddingWiki}
        />
        <ChatPanel messages={messages} onSendMessage={handleSendMessage} isLoading={isLoading} />
        <ArticlesPanel
          searchText={searchText}
          onSearchText={setSearchText}
          onSearchSubmit={handleSearchSubmit}
          filteredPapers={filteredPapers}
          selectedArticle={selectedArticle}
          onSelectPaper={handleSelectPaper}
          isSearchingArticles={isSearchingArticles}
        />
      </main>
    </div>
  );
}
