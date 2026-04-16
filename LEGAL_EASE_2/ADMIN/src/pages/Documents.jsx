import { useEffect, useState } from 'react';
import { adminApi } from '../services/api';
import { HiOutlineTrash } from 'react-icons/hi';
import toast from 'react-hot-toast';

export default function Documents() {
  const [docs, setDocs] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(null);
  const limit = 20;

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const data = await adminApi.getDocuments(page * limit, limit, statusFilter || null);
      setDocs(data.documents);
      setTotal(data.total);
    } catch {
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [page, statusFilter]);

  const handleDelete = async (docId, docName) => {
    if (!window.confirm(`Delete "${docName}"? This will remove the file, embeddings, and all analysis data. This cannot be undone.`)) return;
    setDeleting(docId);
    try {
      await adminApi.deleteDocument(docId);
      toast.success('Document deleted');
      fetchDocs();
    } catch {
      toast.error('Failed to delete document');
    } finally {
      setDeleting(null);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#1d1d1f] tracking-tight">Documents</h1>
          <p className="text-sm text-[#86868b] mt-0.5">{total} total documents</p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="input-field w-36 text-sm"
        >
          <option value="">All Status</option>
          <option value="processing">Processing</option>
          <option value="ready">Ready</option>
          <option value="error">Error</option>
        </select>
      </div>

      <div className="card">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-7 h-7 border-[3px] border-[#e8e8ed] border-t-[#0071e3] rounded-full animate-spin" />
          </div>
        ) : docs.length === 0 ? (
          <p className="text-[#86868b] text-sm text-center py-12">No documents found</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#e8e8ed]">
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Document</th>
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Uploaded By</th>
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Status</th>
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Risk</th>
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Pages</th>
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Uploaded</th>
                  <th className="pb-3 text-left text-[11px] font-semibold text-[#86868b] uppercase tracking-widest">Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id} className="border-b border-[#f5f5f7] hover:bg-[#f5f5f7]/50 transition-colors">
                    <td className="py-3 font-medium text-[#1d1d1f]">{doc.original_name}</td>
                    <td className="py-3 text-[#6e6e73] text-sm">{doc.full_name || 'Unknown'}</td>
                    <td className="py-3">
                      <span
                        className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${
                          doc.status === 'ready'
                            ? 'bg-green-500/10 text-green-600'
                            : doc.status === 'processing'
                            ? 'bg-[#0071e3]/10 text-[#0071e3]'
                            : 'bg-red-500/10 text-red-600'
                        }`}
                      >
                        {doc.status}
                      </span>
                    </td>
                    <td className="py-3">
                      {doc.risk_level ? (
                        <span
                          className={`text-[11px] px-2.5 py-0.5 rounded-full font-medium ${
                            doc.risk_level === 'High'
                              ? 'bg-red-500/10 text-red-600'
                              : doc.risk_level === 'Medium'
                              ? 'bg-amber-500/10 text-amber-600'
                              : 'bg-green-500/10 text-green-600'
                          }`}
                        >
                          {doc.risk_level} ({doc.risk_score?.toFixed(1)}%)
                        </span>
                      ) : (
                        <span className="text-[#86868b] text-xs">—</span>
                      )}
                    </td>
                    <td className="py-3 text-[#6e6e73]">{doc.page_count}</td>
                    <td className="py-3 text-[#86868b] text-xs">{new Date(doc.upload_date).toLocaleDateString()}</td>
                    <td className="py-3">
                      <button
                        onClick={() => handleDelete(doc.id, doc.original_name)}
                        disabled={deleting === doc.id}
                        className="w-7 h-7 rounded-full flex items-center justify-center text-[#86868b] hover:text-[#ff3b30] hover:bg-red-500/10 transition-all disabled:opacity-40"
                        title="Delete document"
                      >
                        {deleting === doc.id ? (
                          <div className="w-3.5 h-3.5 border-2 border-[#e8e8ed] border-t-[#ff3b30] rounded-full animate-spin" />
                        ) : (
                          <HiOutlineTrash className="w-4 h-4" />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#e8e8ed]">
            <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="btn-secondary text-sm disabled:opacity-40">
              Previous
            </button>
            <span className="text-xs text-[#86868b]">Page {page + 1} of {totalPages}</span>
            <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="btn-secondary text-sm disabled:opacity-40">
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
