import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { ChevronLeft, Save, Send, AlertTriangle } from 'lucide-react';

interface Category {
  id: number;
  name: string;
}

export const KBEditor: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const isEditMode = !!slug;
  
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [categories, setCategories] = useState<Category[]>([]);
  const [articleId, setArticleId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [shortSummary, setShortSummary] = useState('');
  const [body, setBody] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [articleStatus, setArticleStatus] = useState<string>('draft');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchCategories();
    if (isEditMode) {
      fetchArticleForEdit();
    }
  }, [slug]);

  const fetchCategories = async () => {
    try {
      const response = await api.get('/knowledge/categories');
      setCategories(response.data.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchArticleForEdit = async () => {
    try {
      const response = await api.get(`/knowledge/articles/${slug}`);
      const art = response.data.data;
      setArticleId(art.id);
      setTitle(art.title);
      setCategoryId(String(art.categories?.[0]?.id || ''));
      setShortSummary(art.summary || '');
      setBody(art.body || '');
      setTagsInput((art.tags || []).map((t: any) => t.name).join(', '));
      setArticleStatus(art.status || 'draft');
    } catch (e) {
      console.error(e);
      navigate('/knowledge');
    }
  };

  const handleSave = async (publish: boolean) => {
    setError(null);
    setIsLoading(true);

    const tags = tagsInput
      .split(',')
      .map(t => t.trim())
      .filter(t => t.length > 0);

    const payload = {
      title,
      category_ids: categoryId ? [Number(categoryId)] : [],
      summary: shortSummary,
      body,
      tag_names: tags,
    };

    try {
      let savedArticleId = articleId;
      if (isEditMode && savedArticleId) {
        await api.put(`/knowledge/articles/${savedArticleId}`, payload);
      } else {
        const response = await api.post('/knowledge/articles', payload);
        savedArticleId = response.data.data.id;
      }

      if (publish && savedArticleId && articleStatus !== 'published') {
        // Trigger publish endpoint (only if not already published)
        await api.put(`/knowledge/articles/${savedArticleId}/publish`);
      }

      navigate('/knowledge');
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || 'Failed to save article.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const canPublish = user && ['manager', 'admin', 'super_admin'].includes(user.role);

  return (
    <div className="page-container">
      <div>
        <Link to="/knowledge" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--primary)', fontWeight: 600, marginBottom: '1rem' }}>
          <ChevronLeft size={16} />
          <span>Back to Articles</span>
        </Link>
      </div>

      <div>
        <h1 style={{ margin: 0, fontSize: '2rem' }}>{isEditMode ? 'Edit Article' : 'Create New Article'}</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Draft or publish guidance documentation</p>
      </div>

      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.75rem 1rem',
          backgroundColor: 'var(--danger-light)',
          color: 'var(--danger)',
          borderRadius: 'var(--radius-sm)',
          marginBottom: '1rem',
          fontSize: '0.9rem'
        }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ gap: '1.25rem' }}>
        <div className="form-group">
          <label className="form-label" htmlFor="title">Article Title</label>
          <input 
            id="title"
            type="text" 
            className="input-field" 
            placeholder="e.g. Setting up VPN access" 
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>

        <div style={{ display: 'flex', gap: '1.5rem' }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label" htmlFor="category">Category</label>
            <select 
              id="category"
              className="input-field"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">Select category...</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label" htmlFor="tags">Tags (comma-separated)</label>
            <input 
              id="tags"
              type="text" 
              className="input-field" 
              placeholder="e.g. vpn, network, access" 
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="shortSummary">Short Summary</label>
          <input 
            id="shortSummary"
            type="text" 
            className="input-field" 
            placeholder="Brief description of what this article covers" 
            value={shortSummary}
            onChange={(e) => setShortSummary(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="body">Article Content (Body)</label>
          <textarea 
            id="body"
            className="input-field" 
            placeholder="Write the detailed resolution or guidance steps..." 
            style={{ minHeight: '300px', resize: 'vertical', fontFamily: 'monospace' }}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
          <button 
            type="button" 
            className="btn btn-secondary" 
            onClick={() => handleSave(false)} 
            disabled={isLoading}
          >
            <Save size={18} />
            <span>Save Draft</span>
          </button>
          
          {canPublish && (
            <button 
              type="button" 
              className="btn btn-primary" 
              onClick={() => handleSave(true)} 
              disabled={isLoading}
            >
              <Send size={18} />
              <span>Publish Article</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
