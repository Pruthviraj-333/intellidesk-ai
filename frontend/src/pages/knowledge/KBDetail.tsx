import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { ChevronLeft, ThumbsUp, ThumbsDown, Eye, Edit, Calendar, User } from 'lucide-react';

interface ArticleDetail {
  id: number;
  title: string;
  slug: string;
  body: string;
  short_summary: string;
  category: { id: number; name: string } | null;
  author: { id: number; first_name: string; last_name: string } | null;
  upvotes: number;
  downvotes: number;
  views: number;
  created_at: string;
  tags: string[];
}

export const KBDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [userVote, setUserVote] = useState<number | null>(null);

  useEffect(() => {
    fetchArticle();
  }, [slug]);

  const fetchArticle = async () => {
    setIsLoading(true);
    try {
      const response = await api.get(`/knowledge/articles/${slug}`);
      setArticle(response.data.data);
    } catch (e) {
      console.error(e);
      navigate('/knowledge');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVote = async (voteType: number) => {
    if (!article) return;
    try {
      await api.post(`/knowledge/articles/${article.id}/vote`, { vote_type: voteType });
      // Reload article to get updated vote counts
      fetchArticle();
      setUserVote(voteType);
    } catch (e) {
      console.error(e);
    }
  };

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading article...</div>;
  }

  if (!article) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Article not found</div>;
  }

  const isAuthorOrAdmin = user && (user.id === article.author?.id || ['admin', 'super_admin'].includes(user.role));

  return (
    <div className="page-container">
      <div>
        <Link to="/knowledge" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--primary)', fontWeight: 600, marginBottom: '1rem' }}>
          <ChevronLeft size={16} />
          <span>Back to Articles</span>
        </Link>
      </div>

      <div className="card" style={{ gap: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '2.25rem' }}>{article.title}</h1>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', marginTop: '0.75rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <User size={16} />
                <span>By {article.author ? `${article.author.first_name} ${article.author.last_name}` : 'System'}</span>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <Calendar size={16} />
                <span>{new Date(article.created_at).toLocaleDateString()}</span>
              </span>
              <span className="badge badge-info">{article.category?.name || 'Uncategorized'}</span>
            </div>
          </div>
          {isAuthorOrAdmin && (
            <Link to={`/knowledge/edit/${article.slug}`} className="btn btn-secondary">
              <Edit size={16} />
              <span>Edit Article</span>
            </Link>
          )}
        </div>

        {article.short_summary && (
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', borderLeft: '4px solid var(--info)', fontStyle: 'italic', color: 'var(--text-secondary)' }}>
            {article.short_summary}
          </div>
        )}

        <div style={{
          lineHeight: '1.75',
          fontSize: '1.05rem',
          color: 'var(--text-primary)',
          whiteSpace: 'pre-wrap'
        }}>
          {article.body}
        </div>

        {article.tags && article.tags.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '1rem' }}>
            {article.tags.map(tag => (
              <span key={tag} style={{ padding: '0.25rem 0.75rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: '50px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                #{tag}
              </span>
            ))}
          </div>
        )}

        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderTop: '1px solid var(--border-color)',
          paddingTop: '1.5rem',
          marginTop: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)' }}>
            <Eye size={18} />
            <span>{article.views} views</span>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', alignSelf: 'center' }}>Was this article helpful?</span>
            <button 
              className={`btn ${userVote === 1 ? 'btn-primary' : 'btn-secondary'}`} 
              style={{ padding: '0.5rem 1rem' }}
              onClick={() => handleVote(1)}
            >
              <ThumbsUp size={16} />
              <span>Yes ({article.upvotes})</span>
            </button>
            <button 
              className={`btn ${userVote === -1 ? 'btn-danger' : 'btn-secondary'}`} 
              style={{ padding: '0.5rem 1rem' }}
              onClick={() => handleVote(-1)}
            >
              <ThumbsDown size={16} />
              <span>No ({article.downvotes})</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
