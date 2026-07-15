import React, { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { ChevronLeft, ThumbsUp, ThumbsDown, Eye, Edit, Calendar, User, Trash2 } from 'lucide-react';

interface ArticleDetail {
  id: number;
  title: string;
  slug: string;
  body: string;
  summary: string | null;          // API returns 'summary'
  categories: { id: number; name: string }[];  // API returns array
  author: { id: number; full_name: string } | null;  // API returns 'full_name'
  helpful_count: number;           // API returns 'helpful_count'
  not_helpful_count: number;       // API returns 'not_helpful_count'
  view_count: number;              // API returns 'view_count'
  created_at: string;
  tags: { id: number; name: string; slug: string }[];  // tags are objects
}

export const KBDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [userVote, setUserVote] = useState<number | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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

  const handleVote = async (isHelpful: boolean) => {
    if (!article) return;
    try {
      await api.post(`/knowledge/articles/${article.id}/vote`, { is_helpful: isHelpful });
      fetchArticle();
      setUserVote(isHelpful ? 1 : -1);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDelete = async () => {
    if (!article) return;
    const confirmed = window.confirm(
      `Are you sure you want to delete "${article.title}"?\n\nThis action cannot be undone.`
    );
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      await api.delete(`/knowledge/articles/${article.id}`);
      navigate('/knowledge');
    } catch (e: any) {
      const msg = e.response?.data?.error?.message || 'Failed to delete article.';
      alert(msg);
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Loading article...</div>;
  }

  if (!article) {
    return <div style={{ textAlign: 'center', padding: '3rem' }}>Article not found</div>;
  }

  const isAuthorOrAdmin = user && (user.id === article.author?.id || ['admin', 'super_admin'].includes(user.role));
  const canDelete = user && ['admin', 'super_admin'].includes(user.role);

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
                <span>
                  By {article.author?.full_name || 'System'}
                </span>
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <Calendar size={16} />
                <span>{new Date(article.created_at).toLocaleDateString()}</span>
              </span>
              <span className="badge badge-info">{article.categories?.[0]?.name || 'Uncategorized'}</span>
            </div>
          </div>
          {isAuthorOrAdmin && (
            <Link to={`/knowledge/edit/${article.slug}`} className="btn btn-secondary">
              <Edit size={16} />
              <span>Edit Article</span>
            </Link>
          )}
          {canDelete && (
            <button
              className="btn btn-danger"
              onClick={handleDelete}
              disabled={isDeleting}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Trash2 size={16} />
              <span>{isDeleting ? 'Deleting...' : 'Delete'}</span>
            </button>
          )}
        </div>

        {article.summary && (
          <div style={{ padding: '1rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: 'var(--radius-sm)', borderLeft: '4px solid var(--info)', fontStyle: 'italic', color: 'var(--text-secondary)' }}>
            {article.summary}
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
              <span key={tag.id} style={{ padding: '0.25rem 0.75rem', backgroundColor: 'var(--bg-tertiary)', borderRadius: '50px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                #{tag.name}
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
            <span>{article.view_count} views</span>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', alignSelf: 'center' }}>Was this article helpful?</span>
            <button 
              className={`btn ${userVote === 1 ? 'btn-primary' : 'btn-secondary'}`} 
              style={{ padding: '0.5rem 1rem' }}
              onClick={() => handleVote(true)}
            >
              <ThumbsUp size={16} />
              <span>Yes ({article.helpful_count})</span>
            </button>
            <button 
              className={`btn ${userVote === -1 ? 'btn-danger' : 'btn-secondary'}`} 
              style={{ padding: '0.5rem 1rem' }}
              onClick={() => handleVote(false)}
            >
              <ThumbsDown size={16} />
              <span>No ({article.not_helpful_count})</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
