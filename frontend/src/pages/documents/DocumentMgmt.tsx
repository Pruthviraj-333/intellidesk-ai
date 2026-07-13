import React, { useEffect, useState, useRef } from 'react';
import api from '../../services/api';
import { 
  UploadCloud, 
  FileText, 
  RefreshCw, 
  CheckCircle2, 
  Loader2, 
  AlertCircle, 
  Clock
} from 'lucide-react';

interface DocumentInfo {
  id: number;
  file_name: string;        // backend field name
  title: string;
  file_size: number;
  status: 'pending' | 'processing' | 'processed' | 'failed';
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

export const DocumentMgmt: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDocuments();
    // Poll for status updates every 5 seconds
    const interval = setInterval(fetchDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDocuments = async () => {
    try {
      const response = await api.get('/documents/');
      setDocuments(response.data.data);
    } catch (e) {
      console.error('Error fetching documents:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      await uploadFile(file);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      await uploadFile(file);
    }
  };

  const uploadFile = async (file: File) => {
    setUploadError(null);
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/documents/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      fetchDocuments();
    } catch (err: any) {
      const msg = err.response?.data?.error?.message || 'File upload failed.';
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleReprocess = async (id: number) => {
    try {
      await api.post(`/documents/${id}/reprocess`);
      // Update locally
      setDocuments(prev => prev.map(doc => doc.id === id ? { ...doc, status: 'pending' as const } : doc));
    } catch (e) {
      console.error('Error reprocessing document:', e);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'processed':
        return <CheckCircle2 size={18} style={{ color: 'var(--success)' }} />;
      case 'processing':
        return <Loader2 size={18} className="spin" style={{ color: 'var(--info)' }} />;
      case 'failed':
        return <AlertCircle size={18} style={{ color: 'var(--danger)' }} />;
      default:
        return <Clock size={18} style={{ color: 'var(--warning)' }} />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'processed':
        return <span className="badge badge-success">Completed</span>;
      case 'processing':
        return <span className="badge badge-info">Processing</span>;
      case 'failed':
        return <span className="badge badge-danger">Failed</span>;
      default:
        return <span className="badge badge-warning">Pending</span>;
    }
  };

  return (
    <div className="page-container">
      <div>
        <h1 style={{ margin: 0, fontSize: '2rem' }}>Document Ingestion</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Upload and process knowledge articles, handbooks, or files into RAG embeddings</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', alignItems: 'flex-start' }}>
        {/* Upload Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div 
            className="dropzone"
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <UploadCloud size={48} style={{ color: 'var(--primary)', opacity: 0.8 }} />
            <div>
              <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>Drag & Drop file here</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>or click to browse from device</p>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Supported formats: PDF, DOCX, TXT, MD (Max 25MB)</p>
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileSelect} 
              accept=".pdf,.docx,.txt,.md"
            />
          </div>

          {isUploading && (
            <div className="card" style={{ padding: '1rem', flexDirection: 'row', alignItems: 'center', gap: '1rem' }}>
              <Loader2 className="spin" style={{ color: 'var(--primary)' }} />
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>Uploading document...</span>
                <div style={{ width: '100%', height: '4px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '2px', marginTop: '0.5rem', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: '45%', backgroundColor: 'var(--primary)', animation: 'pulse 1.5s infinite ease-in-out' }} />
                </div>
              </div>
            </div>
          )}

          {uploadError && (
            <div className="card" style={{ padding: '1rem', borderLeft: '4px solid var(--danger)', color: 'var(--danger)', fontSize: '0.9rem', flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
              <AlertCircle size={18} />
              <span>{uploadError}</span>
            </div>
          )}
        </div>

        {/* Documents Registry Table */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Processed Documents</h3>
            <button className="btn btn-secondary" style={{ padding: '0.5rem' }} onClick={fetchDocuments}>
              <RefreshCw size={16} />
            </button>
          </div>

          {isLoading ? (
            <div style={{ textAlign: 'center', padding: '3rem' }}>Loading documents...</div>
          ) : documents.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem' }}>
              <FileText size={48} style={{ color: 'var(--text-muted)', marginBottom: '1rem' }} />
              <h3>No Documents Ingested</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Upload files to start search querying with AI.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Size</th>
                    <th>Status</th>
                    <th>Embeddings</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map(doc => (
                    <tr key={doc.id}>
                      <td style={{ fontWeight: 600, maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={doc.file_name}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          {getStatusIcon(doc.status)}
                          <span>{doc.title || doc.file_name}</span>
                        </div>
                      </td>
                      <td>{formatBytes(doc.file_size)}</td>
                      <td>{getStatusBadge(doc.status)}</td>
                      <td>
                        {doc.status === 'processed' ? (
                          <div style={{ display: 'flex', flexDirection: 'column', fontSize: '0.8rem' }}>
                            <span>{doc.chunk_count} chunks</span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>—</span>
                        )}
                      </td>
                      <td>
                        {doc.status === 'failed' ? (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.8rem' }}
                            onClick={() => handleReprocess(doc.id)}
                            title={doc.error_message || 'Unknown error'}
                          >
                            Reprocess
                          </button>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
