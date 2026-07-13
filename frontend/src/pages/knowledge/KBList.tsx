import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { useAuthStore } from '../../store/authStore';
import { Search, Plus, BookOpen, ChevronRight, ThumbsUp, Eye } from 'lucide-react';

interface Article {
  id: number;
  title: string;
  slug: string;
  short_summary: string;
  category: { id: number; name: string } | null;
  author: { first_name: string; last_name: string } | null;
  upvotes: number;
  views: number;
  status: string;
  created_at: string;
}

interface Category {
  id: number;
  name: string;
  slug: string;
}

export const KBList: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  
  const [articles, setArticles] = useState<Article[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isSemantic, setIsSemantic] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchCategories();
  }, []);

  useEffect(() => {
    fetchArticles();
  }, [selectedCategory]);

  const fetchCategories = async () => {
    try {
      const response = await api.get('/knowledge/categories');
      setCategories(response.data.data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchArticles = async () => {
    setIsLoading(true);
    try {
      let url = '/knowledge/articles';
      const params: any = {};
      if (selectedCategory !== 'all') {
        params.category_id = selectedCategory;
      }
      const response = await api.get(url, { params });
      setArticles(response.data.data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    if (isSemantic) {
      navigate(`/knowledge/search?q=${encodeURIComponent(searchQuery)}`);
    } else {
      // Direct local filter/search
      setIsLoading(true);
      api.get(`/knowledge/articles?search=${encodeURIComponent(searchQuery)}`)
        .then(response => {
          setArticles(response.data.data);
          setIsLoading(false);
        })
        .catch(e => {
          console.error(e);
          setIsLoading(false);
        });
    }
  };

  const isStaff = user && ['agent', 'manager', 'admin', 'super_admin'].includes(user.role);

  return (
    <div className="page-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '2rem' }}>Knowledge Base</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Find guides, resolution steps, and self-help articles</p>
        </div>
        {isStaff && (
          <Link to="/knowledge/new" className="btn btn-primary">
            <Plus size={18} />
            <span>Create Article</span>
          </Link>
        )}
      </div>

      <div className="card" style={{ padding: '1rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              className="input-field" 
              placeholder="Search knowledge base..." 
              style={{ paddingLeft: '2.5rem' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem', whiteSpace: 'nowrap' }}>
            <input 
              type="checkbox" 
              checked={isSemantic} 
              onChange={(e) => setIsSemantic(e.target.checked)} 
            />
            <span>AI Semantic Search (RAG)</span>
          </label>
          <button type="submit" className="btn btn-primary">Search</button>
        </form>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: '2rem' }}>
        {/* Categories Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <h3 style={{ marginBottom: '0.5rem', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-muted)' }}>Categories</h3>
          <button 
            className={`btn ${selectedCategory === 'all' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ justifyContent: 'space-between', textAlign: 'left' }}
            onClick={() => setSelectedCategory('all')}
          >
            <span>All Articles</span>
            <ChevronRight size={16} />
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              className={`btn ${selectedCategory === String(cat.id) ? 'btn-primary' : 'btn-secondary'}`}
              style={{ justifyContent: 'space-between', textAlign: 'left' }}
              onClick={() => setSelectedCategory(String(cat.id))}
            >
              <span>{cat.name}</span>
              <ChevronRight size={16} />
            </button>
          ))}
        </div>

        {/* Articles List */}
        <div>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '3rem' }}>Loading articles...</div>
          ) : articles.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)' }}>
              <BookOpen size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
              <h3>No Articles Found</h3>
              <p style={{ color: 'var(--text-secondary)' }}>There are no articles available in this category.</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {articles.map(art => (
                <div key={art.id} className="card" style={{ gap: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Link to={`/knowledge/articles/${art.slug}`}>
                      <h3 style={{ color: 'var(--primary)', cursor: 'pointer' }}>{art.title}</h3>
                    </Link>
                    <span className="badge badge-info">{art.category?.name || 'Uncategorized'}</span>
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
                    {art.short_summary || 'No summary available.'}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    <span>By {art.author ? `${art.author.first_name} ${art.author.last_name}` : 'System'} • {new Date(art.created_at).toLocaleDateString()}</span>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Eye size={14} /> {art.views}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <ThumbsUp size={14} /> {art.upvotes}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
