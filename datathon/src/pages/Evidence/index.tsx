import React, { useState, useEffect } from 'react';
import { useRBAC } from '../../hooks/useRBAC';
import { Search, Plus, Filter, HardDrive, FileText, UploadCloud, Cpu, Download, Sparkles } from 'lucide-react';
import { apiRequest } from '../../services/api';

interface Evidence {
  id: string;
  case_id: string;
  title: string;
  description: string;
  evidence_type: string;
  status: string;
  storage_path: string | null;
  created_at: string;
}

const EvidencePage: React.FC = () => {
  const { isSCRB, isInspector, isIO, isForensic } = useRBAC();
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<any[]>([]);
  
  // Modals
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [currentEvidence, setCurrentEvidence] = useState<Partial<Evidence>>({
    title: '', description: '', evidence_type: 'Digital', case_id: ''
  });
  const [evidenceDetail, setEvidenceDetail] = useState<any>(null);
  const [assigneeId, setAssigneeId] = useState('');

  const fetchEvidence = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (statusFilter) params.set('status', statusFilter);
      const data = await apiRequest<{ results: Evidence[] }>(`/evidence?${params.toString()}`);
      setEvidenceList(data.results || []);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch evidence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchEvidence();
  }, [search, statusFilter]);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await apiRequest<{ results: any[] }>(`/crime-cases?page_size=100`);
        setCases(data.results || []);
      } catch (e) {
        console.error(e);
      }
    };
    void fetchCases();
  }, []);

  const handleCreate = async () => {
    if (!currentEvidence.case_id?.trim() || !currentEvidence.title?.trim() || !currentEvidence.evidence_type?.trim()) {
      setError('Case ID, title, and evidence type are required.');
      return;
    }

    try {
      // Normalize optional fields
      const payload = { ...currentEvidence };
      Object.keys(payload).forEach(key => {
        if (payload[key as keyof typeof payload] === '') {
          payload[key as keyof typeof payload] = null;
        }
      });
      
      await apiRequest(`/evidence`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      
      setIsFormOpen(false);
      setError(null);
      void fetchEvidence();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create evidence');
    }
  };

  const handleUpload = async (id: string, file: File) => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      
      await apiRequest(`/evidence/${id}/upload`, {
        method: 'POST',
        body: formData
      });
      
      setError(null);
      void openDetail(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to upload file');
    }
  };

  const downloadFile = async (id: string) => {
    try {
      // apiRequest assumes JSON response, so we still use fetch for blob download
      const { accessToken, API_BASE_URL } = await import('../../services/api').then(m => ({ 
        accessToken: m.getStoredTokens().accessToken, 
        API_BASE_URL: m.API_BASE_URL 
      }));
      const res = await fetch(`${API_BASE_URL}/evidence/${id}/download`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
      });
      if (!res.ok) {
        let msg = res.statusText;
        try { const d = await res.json(); msg = d.detail || d.message || msg; } catch {}
        throw new Error(msg || 'Failed to download file');
      }
      const blob = await res.blob();
      const disposition = res.headers.get('Content-Disposition') ?? '';
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match?.[1] ?? `evidence-${id}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to download file');
    }
  };

  const generateAISummary = async (id: string) => {
    try {
      await apiRequest(`/evidence/${id}/summary`, { method: 'POST' });
      setError(null);
      void openDetail(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to generate AI summary');
    }
  };

  const assignEvidence = async (evidenceId: string) => {
    if (!assigneeId.trim()) {
      setError('Enter the assignee user UUID.');
      return;
    }

    try {
      await apiRequest(`/evidence/${evidenceId}/assign?assigned_to=${encodeURIComponent(assigneeId.trim())}`, {
        method: 'POST'
      });
      setAssigneeId('');
      setError(null);
      void openDetail(evidenceId);
      void fetchEvidence();
    } catch(e) {
      setError(e instanceof Error ? e.message : 'Failed to assign evidence');
    }
  };

  const handleAssignmentAction = async (evidenceId: string, assignmentId: string, action: 'accept' | 'complete' | 'return' | 'reject') => {
    try {
      await apiRequest(`/evidence/${evidenceId}/assignments/${assignmentId}/${action}`, {
        method: 'POST'
      });
      setError(null);
      void openDetail(evidenceId);
      void fetchEvidence();
    } catch(e) {
      setError(e instanceof Error ? e.message : 'Failed to update assignment');
    }
  };

  const openDetail = async (id: string) => {
    try {
      const data = await apiRequest(`/evidence/${id}`);
      setEvidenceDetail(data);
      setIsDetailOpen(true);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to open evidence');
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      {/* Header Panel */}
      <div className="flex items-center justify-between p-6 bg-[var(--bg-surface)]/80 border border-border-color rounded-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-[#C94A2A]/10 rounded-full blur-[80px]" />
        <div className="z-10">
          <h1 className="text-2xl font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-3">
            <HardDrive className="w-7 h-7 text-[#C94A2A]" />
            Digital Evidence Handling
          </h1>
          <p className="text-[var(--text-secondary)] text-sm mt-2 font-mono">Secure repository for case evidence, chain of custody, and AI analysis.</p>
        </div>
        <div className="z-10 flex gap-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search evidence..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-56 bg-secondary-bg border border-border-color rounded-btn px-4 py-2 pl-10 text-sm font-mono text-[var(--text-primary)] focus:border-[#C94A2A] outline-none"
            />
            <Search className="w-4 h-4 text-[var(--text-muted)] absolute left-3 top-2.5" />
          </div>
          <div className="relative">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="appearance-none w-44 bg-secondary-bg border border-border-color rounded-btn px-4 py-2 pr-9 text-sm font-mono text-[var(--text-primary)] focus:border-[#C94A2A] outline-none">
              <option value="">All Statuses</option>
              <option value="Pending">Pending</option>
              <option value="Assigned">Assigned</option>
              <option value="Under Analysis">Under Analysis</option>
              <option value="Analyzed">Analyzed</option>
              <option value="Returned">Returned</option>
              <option value="Assignment Rejected">Rejected</option>
            </select>
            <Filter className="w-4 h-4 text-[var(--text-muted)] absolute right-3 top-2.5 pointer-events-none" />
          </div>
          {(isSCRB || isIO || isInspector) && (
            <button 
              onClick={() => {
                setCurrentEvidence({ title: '', description: '', evidence_type: 'Digital', case_id: '' });
                setIsFormOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-[#C94A2A] hover:bg-[#A83D22] border border-transparent rounded-btn text-sm font-mono text-[var(--text-primary)] font-bold transition-all shadow-glow-orange"
            >
              <Plus className="w-4 h-4" /> Log Evidence
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 bg-[#C94A2A]/10 border border-[#C94A2A]/30 rounded text-[var(--accent-coral)] text-xs font-mono">
          {error}
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 overflow-auto custom-scrollbar">
        {loading ? (
          <div className="w-full h-full flex justify-center items-center">
            <div className="w-8 h-8 rounded-full border-2 border-[#C94A2A] border-t-transparent animate-spin" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {evidenceList.map((item) => (
              <div 
                key={item.id} 
                onClick={() => openDetail(item.id)}
                className="bg-secondary-bg border border-border-color rounded-lg p-5 flex flex-col gap-4 hover:border-[#C94A2A]/50 transition-colors cursor-pointer group"
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded bg-[#C94A2A]/20 flex items-center justify-center text-[#C94A2A] border border-[#C94A2A]/40 shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="overflow-hidden">
                      <h3 className="text-[var(--text-primary)] font-bold text-sm truncate">{item.title}</h3>
                      <p className="text-[var(--text-muted)] font-mono text-[10px] uppercase font-bold tracking-wider">{item.evidence_type}</p>
                    </div>
                  </div>
                </div>
                
                <p className="text-xs text-[var(--text-secondary)] line-clamp-2">{item.description}</p>
                
                <div className="mt-auto pt-4 border-t border-border-color flex justify-between items-center">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${item.status === 'Analyzed' ? 'bg-[#0E9E78]/20 text-[#0E9E78]' : 'bg-[#D4820A]/20 text-[#D4820A]'}`}>
                    {item.status}
                  </span>
                  {item.storage_path && <HardDrive className="w-4 h-4 text-[#1E6FD9]" title="File Attached" />}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Form Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 bg-[var(--bg-surface)]/80 flex items-center justify-center p-4">
          <div className="bg-secondary-bg border border-[#C94A2A]/40 rounded-lg shadow-glow-orange max-w-md w-full p-6 animate-[fadeIn_0.2s_ease-out]">
            <h2 className="text-lg font-bold text-[var(--text-primary)] mb-4 uppercase font-mono">Log New Evidence</h2>
            
            <div className="flex flex-col gap-4 mb-6">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Case</label>
                {cases.length > 0 ? (
                  <select 
                    value={currentEvidence.case_id} 
                    onChange={e => setCurrentEvidence({...currentEvidence, case_id: e.target.value})} 
                    className="bg-[var(--bg-surface)] border border-border-color rounded px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[#C94A2A] outline-none"
                  >
                    <option value="">Select a Case...</option>
                    {cases.map((c: any) => (
                      <option key={c.id} value={c.id}>
                        {c.case_number} - {c.description ? (c.description.length > 40 ? `${c.description.slice(0, 40)}...` : c.description) : 'No description'}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input type="text" value={currentEvidence.case_id} onChange={e => setCurrentEvidence({...currentEvidence, case_id: e.target.value})} className="bg-[var(--bg-surface)] border border-border-color rounded px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[#C94A2A] outline-none" placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000" />
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Title</label>
                <input type="text" value={currentEvidence.title} onChange={e => setCurrentEvidence({...currentEvidence, title: e.target.value})} className="bg-[var(--bg-surface)] border border-border-color rounded px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[#C94A2A] outline-none" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Description</label>
                <textarea value={currentEvidence.description} onChange={e => setCurrentEvidence({...currentEvidence, description: e.target.value})} className="bg-[var(--bg-surface)] border border-border-color rounded px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[#C94A2A] outline-none min-h-[80px]" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[var(--text-muted)] uppercase">Evidence Type</label>
                <select value={currentEvidence.evidence_type} onChange={e => setCurrentEvidence({...currentEvidence, evidence_type: e.target.value})} className="bg-[var(--bg-surface)] border border-border-color rounded px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[#C94A2A] outline-none">
                  <option value="Digital">Digital (CCTV, Mobile, PC)</option>
                  <option value="Physical">Physical</option>
                  <option value="Biological">Biological</option>
                  <option value="Document">Documentary</option>
                </select>
              </div>
            </div>
            
            <div className="flex justify-end gap-3">
              <button onClick={() => setIsFormOpen(false)} className="px-4 py-2 border border-border-color rounded text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/10 transition-colors font-mono">Cancel</button>
              <button onClick={handleCreate} className="px-4 py-2 bg-[#C94A2A] hover:bg-[#A83D22] rounded text-sm text-[var(--text-primary)] font-bold transition-colors font-mono">Save Evidence</button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {isDetailOpen && evidenceDetail && (
        <div className="fixed inset-0 z-50 bg-[var(--bg-surface)]/90 flex items-center justify-center p-4">
          <div className="bg-secondary-bg border border-[#1E6FD9]/40 rounded-lg max-w-4xl w-full h-[90vh] flex flex-col animate-[fadeIn_0.2s_ease-out]">
            <div className="p-4 border-b border-border-color flex justify-between items-center bg-[var(--bg-surface)]">
              <h2 className="text-lg font-bold text-[var(--text-primary)] uppercase font-mono flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#1E6FD9]" />
                Evidence Dossier: {evidenceDetail.title}
              </h2>
              <button onClick={() => setIsDetailOpen(false)} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] font-mono text-sm px-3 py-1 bg-[var(--bg-tertiary)]/60 rounded">Close [X]</button>
            </div>
            
            <div className="flex-1 overflow-auto p-6 grid grid-cols-3 gap-6 custom-scrollbar">
              <div className="col-span-2 space-y-6">
                <div className="bg-[var(--bg-surface)] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#1E6FD9] font-mono text-xs uppercase font-bold mb-3 border-b border-border-color pb-2">Overview</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Case UUID</span>
                      <span className="text-[var(--text-primary)] font-mono break-all">{evidenceDetail.case_id}</span>
                    </div>
                    <div>
                      <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Type & Status</span>
                      <span className="text-[var(--text-primary)]">{evidenceDetail.evidence_type} • {evidenceDetail.status}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Description</span>
                      <span className="text-[var(--text-primary)]">{evidenceDetail.description}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-[var(--bg-surface)] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#1E6FD9] font-mono text-xs uppercase font-bold mb-3 border-b border-border-color pb-2 flex justify-between items-center">
                    Digital Asset & Metadata
                    <div className="flex gap-2">
                      {evidenceDetail.metadata && (
                        <button onClick={() => void downloadFile(evidenceDetail.id)} className="flex items-center gap-1 text-[10px] bg-[#1E6FD9]/20 text-[#1E6FD9] px-2 py-1 rounded hover:bg-[#1E6FD9]/40 transition-colors">
                          <Download className="w-3 h-3" /> Download
                        </button>
                      )}
                      {(isForensic || isSCRB) && (
                        <label className="cursor-pointer flex items-center gap-1 text-[10px] bg-[#C94A2A]/20 text-[#C94A2A] px-2 py-1 rounded hover:bg-[#C94A2A]/40 transition-colors">
                          <UploadCloud className="w-3 h-3" /> Upload File
                          <input type="file" className="hidden" onChange={(e) => {
                            if (e.target.files && e.target.files[0]) {
                              void handleUpload(evidenceDetail.id, e.target.files[0]);
                            }
                          }} />
                        </label>
                      )}
                    </div>
                  </h3>
                  
                  {evidenceDetail.metadata ? (
                    <div className="grid grid-cols-2 gap-4 text-sm mt-3">
                      <div>
                        <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Filename</span>
                        <span className="text-[var(--text-primary)]">{evidenceDetail.metadata.filename}</span>
                      </div>
                      <div>
                        <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono">Size & Type</span>
                        <span className="text-[var(--text-primary)]">{(evidenceDetail.metadata.filesize / 1024 / 1024).toFixed(2)} MB • {evidenceDetail.metadata.mime_type}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-[var(--text-muted)] block text-[10px] uppercase font-mono mb-1">Extracted Metadata</span>
                        <pre className="bg-black/50 p-2 rounded text-[#0E9E78] font-mono text-[10px] overflow-auto">
                          {JSON.stringify(evidenceDetail.metadata.extracted_data, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-[var(--text-secondary)] text-sm">
                      <HardDrive className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      No digital file attached to this evidence record.
                    </div>
                  )}
                </div>

                <div className="bg-[var(--bg-surface)] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#6C43CC] font-mono text-xs uppercase font-bold mb-3 border-b border-border-color pb-2 flex justify-between items-center">
                    AI Summary & Analysis
                    <div className="flex items-center gap-2">
                      {(isSCRB || isInspector || isIO || isForensic) && (
                        <button onClick={() => void generateAISummary(evidenceDetail.id)} className="flex items-center gap-1 text-[10px] bg-[#6C43CC]/20 text-[#6C43CC] px-2 py-1 rounded hover:bg-[#6C43CC]/40 transition-colors">
                          <Cpu className="w-3 h-3" /> Generate Analysis
                        </button>
                      )}
                      <button
                        onClick={() => {
                          window.dispatchEvent(new CustomEvent('open-ai-assistant', {
                            detail: { query: `Tell me about evidence ${evidenceDetail.title} (ID: ${evidenceDetail.id}). What is the type, status, and associated case details?` }
                          }));
                        }}
                        className="flex items-center gap-1 text-[10px] bg-[#1E6FD9]/15 text-[#1E6FD9] px-2 py-1 rounded hover:bg-[#1E6FD9]/30 transition-colors"
                      >
                        <Sparkles className="w-3 h-3" /> Ask AI
                      </button>
                    </div>
                  </h3>
                  
                  {evidenceDetail.ai_summaries && evidenceDetail.ai_summaries.length > 0 ? (
                    <div className="space-y-4 mt-3">
                      {evidenceDetail.ai_summaries.map((s: any) => (
                        <div key={s.id} className="bg-black/30 p-3 rounded border border-[#6C43CC]/20">
                          <span className="text-[10px] text-[var(--text-muted)] block mb-1 font-mono">{new Date(s.created_at).toLocaleString()}</span>
                          <p className="text-sm text-[var(--text-primary)]">{s.summary}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-[var(--text-secondary)] text-sm">
                      No AI analysis generated yet.
                    </div>
                  )}
                </div>

              </div>
              
              <div className="col-span-1 space-y-6">
                
                {/* Assignments */}
                <div className="bg-[var(--bg-surface)] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#C94A2A] font-mono text-xs uppercase font-bold mb-4 border-b border-border-color pb-2">Assignments</h3>
                  {(isSCRB || isInspector) && (
                    <div className="mb-4 flex gap-2">
                      <input
                        type="text"
                        value={assigneeId}
                        onChange={(e) => setAssigneeId(e.target.value)}
                        placeholder="Assignee user UUID"
                        className="min-w-0 flex-1 bg-black/30 border border-border-color rounded px-2 py-1.5 text-[10px] text-[var(--text-primary)] font-mono outline-none focus:border-[#C94A2A]"
                      />
                      <button onClick={() => void assignEvidence(evidenceDetail.id)} className="px-2 py-1.5 bg-[#C94A2A]/20 text-[#C94A2A] text-[10px] rounded hover:bg-[#C94A2A]/40 transition-colors uppercase font-bold">Assign</button>
                    </div>
                  )}
                  <div className="space-y-4">
                    {evidenceDetail.assignments && evidenceDetail.assignments.length > 0 ? (
                      evidenceDetail.assignments.map((a: any) => (
                        <div key={a.id} className="bg-black/30 p-3 rounded border border-[#C94A2A]/20">
                          <span className="text-[10px] text-[var(--text-muted)] block mb-1 font-mono">To: {a.assigned_to}</span>
                          <span className="text-[var(--text-primary)] text-xs block mb-2 font-bold">{a.status}</span>
                          
                          {/* Assignment Actions */}
                          {(isForensic || isIO || isSCRB) && (
                            <div className="flex gap-2 mt-2">
                              {a.status === 'Assigned' && (
                                <>
                                  <button onClick={() => void handleAssignmentAction(evidenceDetail.id, a.id, 'accept')} className="px-2 py-1 bg-[#0E9E78]/20 text-[#0E9E78] text-[10px] rounded hover:bg-[#0E9E78]/40 transition-colors uppercase font-bold">Accept</button>
                                  <button onClick={() => void handleAssignmentAction(evidenceDetail.id, a.id, 'reject')} className="px-2 py-1 bg-[#D4820A]/20 text-[#D4820A] text-[10px] rounded hover:bg-[#D4820A]/40 transition-colors uppercase font-bold">Reject</button>
                                </>
                              )}
                              {a.status === 'In Progress' && (
                                <button onClick={() => void handleAssignmentAction(evidenceDetail.id, a.id, 'complete')} className="px-2 py-1 bg-[#1E6FD9]/20 text-[#1E6FD9] text-[10px] rounded hover:bg-[#1E6FD9]/40 transition-colors uppercase font-bold">Complete</button>
                              )}
                              {(a.status === 'In Progress' || a.status === 'Completed') && (
                                <button onClick={() => void handleAssignmentAction(evidenceDetail.id, a.id, 'return')} className="px-2 py-1 bg-[#C94A2A]/20 text-[#C94A2A] text-[10px] rounded hover:bg-[#C94A2A]/40 transition-colors uppercase font-bold">Return</button>
                              )}
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <span className="text-[var(--text-secondary)] text-xs">No assignments.</span>
                    )}
                  </div>
                </div>

                {/* Chain of Custody */}
                <div className="bg-[var(--bg-surface)] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#D4820A] font-mono text-xs uppercase font-bold mb-4 border-b border-border-color pb-2">Chain of Custody</h3>
                  <div className="relative pl-3 space-y-4">
                    <div className="absolute left-[3px] top-2 bottom-2 w-px bg-border-color" />
                    {evidenceDetail.chain_of_custody && evidenceDetail.chain_of_custody.map((custody: any) => (
                      <div key={custody.id} className="relative pl-4">
                        <div className="absolute left-[-4px] top-1 w-2 h-2 rounded-full bg-[#D4820A]" />
                        <span className="text-[10px] text-[var(--text-muted)] font-mono block">{new Date(custody.timestamp).toLocaleString()}</span>
                        <strong className="text-[var(--text-primary)] text-[11px] block">{custody.action}</strong>
                        <span className="text-[var(--text-secondary)] text-[10px] block">To: {custody.to_user}</span>
                      </div>
                    ))}
                  </div>
                  {(!evidenceDetail.chain_of_custody || evidenceDetail.chain_of_custody.length === 0) && (
                    <span className="text-[var(--text-secondary)] text-xs">No custody transfers recorded.</span>
                  )}
                </div>

                {/* Timeline */}
                <div className="bg-[var(--bg-surface)] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#0E9E78] font-mono text-xs uppercase font-bold mb-4 border-b border-border-color pb-2">Event Timeline</h3>
                  <div className="relative pl-3 space-y-4">
                    <div className="absolute left-[3px] top-2 bottom-2 w-px bg-border-color" />
                    {evidenceDetail.timeline && evidenceDetail.timeline.map((event: any) => (
                      <div key={event.id} className="relative pl-4">
                        <div className="absolute left-[-4px] top-1 w-2 h-2 rounded-full bg-[#0E9E78]" />
                        <span className="text-[10px] text-[var(--text-muted)] font-mono block">{new Date(event.created_at).toLocaleString()}</span>
                        <strong className="text-[var(--text-primary)] text-[11px] block">{event.action}</strong>
                        <span className="text-[var(--text-secondary)] text-[10px] block">by {event.performed_by} ({event.role})</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EvidencePage;
