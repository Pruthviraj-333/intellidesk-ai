import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import api from '../../services/api';
import { ChevronLeft, Search, BookOpen, FileText, CheckCircle } from 'lucide-react';

interface SearchResult {
  collection: string;  // 'knowledge_articles' | 'knowledge_documents'
  content: string;
  score: number;
  metadata: {
    article_id?: number;
    document_id?: number;
    chunk_index?: number;
    title?: string;
    slug?: string;
  };
}

export const KBSearch: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') || '';

  const [searchQuery, setSearchQuery] = useState(query);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (query) {
      performSearch(query);
    }
  }, [query]);

  const performSearch = async (q: string) => {
    setIsLoading(true);
    try {
      const response = await api.get(`/knowledge/search?q=${encodeURIComponent(q)}`);
      // API returns: { data: { query, result_count, results: [] } }
      const payload = response.data.data;
      setResults(Array.isArray(payload?.results) ? payload.results : []);
    } catch (e) {
      console.error(e);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearchParams({ q: searchQuery });
  };

  /** Pull the first # heading out of markdown content as the title. */
  const extractTitle = (content: string): string | null => {
    const match = content.match(/^#{1,3}\s+(.+)/m);
    return match ? match[1].trim() : null;
  };

  /** Strip markdown syntax and return a short plain-text preview. */
  const getSnippet = (content: string, maxLen = 220): string => {
    const plain = content
      .replace(/#{1,6}\s+/g, '')   // headings
      .replace(/\*\*(.+?)\*\*/g, '$1') // bold
      .replace(/\*(.+?)\*/g, '$1')     // italic
      .replace(/`(.+?)`/g, '$1')       // inline code
      .replace(/\[(.+?)\]\(.+?\)/g, '$1') // links
      .replace(/\n+/g, ' ')
      .trim();
    return plain.length > maxLen ? plain.slice(0, maxLen) + '…' : plain;
  };

  return (
    <div className="page-container">
      <div>
        <Link to="/knowledge" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--primary)', fontWeight: 600, marginBottom: '1rem' }}>
          <ChevronLeft size={16} />
          <span>Back to Articles</span>
        </Link>
      </div>

      <div>
        <h1 style={{ margin: 0, fontSize: '2rem' }}>AI Semantic Search</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Conceptual RAG search across knowledge articles and files</p>
      </div>

      <div className="card" style={{ padding: '1rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '1rem' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              className="input-field" 
              placeholder="Ask a question..." 
              style={{ paddingLeft: '2.5rem' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={isLoading}>
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </div>

      {query && (
        <div style={{ marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
          <span>Search results for: </span>
          <strong style={{ color: 'var(--text-primary)' }}>"{query}"</strong>
        </div>
      )}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <div className="avatar" style={{ width: '40px', height: '40px', fontSize: '1.2rem', animation: 'pulse 1.5s infinite ease-in-out', margin: '0 auto 1rem' }}>AI</div>
          <span>Analyzing documents and articles...</span>
        </div>
      ) : results.length === 0 ? (
        query ? (
          <div style={{ textAlign: 'center', padding: '3rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
            <Search size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
            <h3>No Concept Matches Found</h3>
            <p style={{ color: 'var(--text-secondary)' }}>We couldn't find matching concepts in the knowledge base.</p>
          </div>
        ) : null
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {results.map((result, idx) => {
            const isArticle = result.collection === 'knowledge_articles';
            // Try metadata title first, then extract from markdown heading, then fallback
            const title = result.metadata?.title
              || extractTitle(result.content)
              || (isArticle ? 'Knowledge Article' : 'Document');
            const slug = result.metadata?.slug || null;
            const snippet = getSnippet(result.content);

            return (
              <div key={idx} className="card" style={{ gap: '0.75rem' }}>
                {/* Header row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    {isArticle ? (
                      <BookOpen size={18} style={{ color: 'var(--primary)' }} />
                    ) : (
                      <FileText size={18} style={{ color: 'var(--info)' }} />
                    )}
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', color: isArticle ? 'var(--primary)' : 'var(--info)' }}>
                      {isArticle ? 'Article' : 'Document'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.85rem', fontWeight: 600, color: 'var(--success)' }}>
                    <CheckCircle size={14} />
                    <span>Match: {Math.round(result.score * 100)}%</span>
                  </div>
                </div>

                {/* Title */}
                {isArticle && slug ? (
                  <Link to={`/knowledge/articles/${slug}`}>
                    <h3 style={{ color: 'var(--primary)', cursor: 'pointer', margin: 0 }}>{title}</h3>
                  </Link>
                ) : (
                  <h3 style={{ margin: 0 }}>{title}</h3>
                )}

                {/* Content snippet — truncated, markdown stripped */}
                <p style={{
                  color: 'var(--text-secondary)',
                  fontSize: '0.95rem',
                  backgroundColor: 'var(--bg-tertiary)',
                  padding: '1rem',
                  borderRadius: 'var(--radius-sm)',
                  borderLeft: '3px solid var(--border-color)',
                  lineHeight: 1.6,
                  margin: 0,
                }}>
                  {snippet}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
