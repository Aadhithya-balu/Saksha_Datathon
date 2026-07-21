import React, { useState, useEffect } from 'react';
import { useRBAC } from '../../hooks/useRBAC';
import { Search, Plus, Filter, HardDrive, FileText, UploadCloud, Cpu, Trash2 } from 'lucide-react';
import { API_BASE_URL, getStoredTokens } from '../../services/api';

interface Evidence {
  id: string;
  case_id: string;
  title: string;
  description: string;
  evidence_type: string;
  status: string;
  storage_path: string;
  created_at: string;
}

const EvidencePage: React.FC = () => {
  const { isSCRB, isInspector, isIO, isForensic } = useRBAC();
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Modals
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [currentEvidence, setCurrentEvidence] = useState<Partial<Evidence>>({
    title: '', description: '', evidence_type: 'Digital', case_id: ''
  });
  const [evidenceDetail, setEvidenceDetail] = useState<any>(null);

  const fetchEvidence = async () => {
    try {
      setLoading(true);
      const { accessToken } = getStoredTokens();
      const res = await fetch(`${API_BASE_URL}/evidence`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEvidenceList(data.items || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, []);

  const handleCreate = async () => {
    try {
      const { accessToken } = getStoredTokens();
      const payload = {
        ...currentEvidence,
        case_id: currentEvidence.case_id || "00000000-0000-0000-0000-000000000000" // Need a real case ID ideally, but using placeholder for demo if empty
      };
      const res = await fetch(`${API_BASE_URL}/evidence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        setIsFormOpen(false);
        fetchEvidence();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleUpload = async (id: string, file: File) => {
    try {
      const { accessToken } = getStoredTokens();
      const formData = new FormData();
      formData.append("file", file);
      
      const res = await fetch(`${API_BASE_URL}/evidence/${id}/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        body: formData
      });
      
      if (res.ok) {
        alert("File uploaded and metadata extracted.");
        openDetail(id); // refresh detail
      }
    } catch (e) {
      console.error(e);
    }
  };

  const generateAISummary = async (id: string) => {
    try {
      const { accessToken } = getStoredTokens();
      const res = await fetch(`${API_BASE_URL}/evidence/${id}/summary`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        alert("AI Summary Generated!");
        openDetail(id); // refresh
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleAssignmentAction = async (evidenceId: string, assignmentId: string, action: 'accept' | 'complete' | 'return') => {
    try {
      const { accessToken } = getStoredTokens();
      const res = await fetch(`${API_BASE_URL}/evidence/${evidenceId}/assignments/${assignmentId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        openDetail(evidenceId); // refresh
      } else {
        const err = await res.json();
        alert(`Error: ${err.detail || 'Failed to update assignment'}`);
      }
    } catch(e) {
      console.error(e);
    }
  };

  const openDetail = async (id: string) => {
    try {
      const { accessToken } = getStoredTokens();
      const res = await fetch(`${API_BASE_URL}/evidence/${id}`, {
        headers: { Authorization: `Bearer ${accessToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setEvidenceDetail(data);
        setIsDetailOpen(true);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      {/* Header Panel */}
      <div className="flex items-center justify-between p-6 bg-[#080E1B]/80 border border-border-color rounded-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-[#C94A2A]/10 rounded-full blur-[80px]" />
        <div className="z-10">
          <h1 className="text-2xl font-mono font-bold text-white uppercase tracking-wider flex items-center gap-3">
            <HardDrive className="w-7 h-7 text-[#C94A2A]" />
            Digital Evidence Handling
          </h1>
          <p className="text-[#A8B4CC] text-sm mt-2 font-mono">Secure repository for case evidence, chain of custody, and AI analysis.</p>
        </div>
        <div className="z-10 flex gap-4">
          <button className="flex items-center gap-2 px-4 py-2 bg-secondary-bg hover:bg-white/5 border border-border-color rounded-btn text-sm font-mono text-white transition-all">
            <Filter className="w-4 h-4" /> Filter
          </button>
          {(isSCRB || isIO || isInspector) && (
            <button 
              onClick={() => {
                setCurrentEvidence({ title: '', description: '', evidence_type: 'Digital', case_id: '' });
                setIsFormOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2 bg-[#C94A2A] hover:bg-[#A83D22] border border-transparent rounded-btn text-sm font-mono text-white font-bold transition-all shadow-glow-orange"
            >
              <Plus className="w-4 h-4" /> Log Evidence
            </button>
          )}
        </div>
      </div>

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
                      <h3 className="text-white font-bold text-sm truncate">{item.title}</h3>
                      <p className="text-[#6A7A96] font-mono text-[10px] uppercase font-bold tracking-wider">{item.evidence_type}</p>
                    </div>
                  </div>
                </div>
                
                <p className="text-xs text-[#A8B4CC] line-clamp-2">{item.description}</p>
                
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
        <div className="fixed inset-0 z-50 bg-[#080E1B]/80 flex items-center justify-center p-4">
          <div className="bg-secondary-bg border border-[#C94A2A]/40 rounded-lg shadow-glow-orange max-w-md w-full p-6 animate-[fadeIn_0.2s_ease-out]">
            <h2 className="text-lg font-bold text-white mb-4 uppercase font-mono">Log New Evidence</h2>
            
            <div className="flex flex-col gap-4 mb-6">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[#6A7A96] uppercase">Case ID (UUID)</label>
                <input type="text" value={currentEvidence.case_id} onChange={e => setCurrentEvidence({...currentEvidence, case_id: e.target.value})} className="bg-[#080E1B] border border-border-color rounded px-3 py-2 text-sm text-white focus:border-[#C94A2A] outline-none" placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[#6A7A96] uppercase">Title</label>
                <input type="text" value={currentEvidence.title} onChange={e => setCurrentEvidence({...currentEvidence, title: e.target.value})} className="bg-[#080E1B] border border-border-color rounded px-3 py-2 text-sm text-white focus:border-[#C94A2A] outline-none" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[#6A7A96] uppercase">Description</label>
                <textarea value={currentEvidence.description} onChange={e => setCurrentEvidence({...currentEvidence, description: e.target.value})} className="bg-[#080E1B] border border-border-color rounded px-3 py-2 text-sm text-white focus:border-[#C94A2A] outline-none min-h-[80px]" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] font-mono text-[#6A7A96] uppercase">Evidence Type</label>
                <select value={currentEvidence.evidence_type} onChange={e => setCurrentEvidence({...currentEvidence, evidence_type: e.target.value})} className="bg-[#080E1B] border border-border-color rounded px-3 py-2 text-sm text-white focus:border-[#C94A2A] outline-none">
                  <option value="Digital">Digital (CCTV, Mobile, PC)</option>
                  <option value="Physical">Physical</option>
                  <option value="Biological">Biological</option>
                  <option value="Document">Documentary</option>
                </select>
              </div>
            </div>
            
            <div className="flex justify-end gap-3">
              <button onClick={() => setIsFormOpen(false)} className="px-4 py-2 border border-border-color rounded text-sm text-[#A8B4CC] hover:bg-white/5 transition-colors font-mono">Cancel</button>
              <button onClick={handleCreate} className="px-4 py-2 bg-[#C94A2A] hover:bg-[#A83D22] rounded text-sm text-white font-bold transition-colors font-mono">Save Evidence</button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {isDetailOpen && evidenceDetail && (
        <div className="fixed inset-0 z-50 bg-[#080E1B]/90 flex items-center justify-center p-4">
          <div className="bg-secondary-bg border border-[#1E6FD9]/40 rounded-lg max-w-4xl w-full h-[90vh] flex flex-col animate-[fadeIn_0.2s_ease-out]">
            <div className="p-4 border-b border-border-color flex justify-between items-center bg-[#080E1B]">
              <h2 className="text-lg font-bold text-white uppercase font-mono flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#1E6FD9]" />
                Evidence Dossier: {evidenceDetail.title}
              </h2>
              <button onClick={() => setIsDetailOpen(false)} className="text-[#A8B4CC] hover:text-white font-mono text-sm px-3 py-1 bg-white/5 rounded">Close [X]</button>
            </div>
            
            <div className="flex-1 overflow-auto p-6 grid grid-cols-3 gap-6 custom-scrollbar">
              <div className="col-span-2 space-y-6">
                <div className="bg-[#080E1B] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#1E6FD9] font-mono text-xs uppercase font-bold mb-3 border-b border-border-color pb-2">Overview</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-[#6A7A96] block text-[10px] uppercase font-mono">Case UUID</span>
                      <span className="text-white font-mono break-all">{evidenceDetail.case_id}</span>
                    </div>
                    <div>
                      <span className="text-[#6A7A96] block text-[10px] uppercase font-mono">Type & Status</span>
                      <span className="text-white">{evidenceDetail.evidence_type} • {evidenceDetail.status}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-[#6A7A96] block text-[10px] uppercase font-mono">Description</span>
                      <span className="text-white">{evidenceDetail.description}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-[#080E1B] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#1E6FD9] font-mono text-xs uppercase font-bold mb-3 border-b border-border-color pb-2 flex justify-between items-center">
                    Digital Asset & Metadata
                    {(isForensic || isSCRB) && (
                      <label className="cursor-pointer flex items-center gap-1 text-[10px] bg-[#C94A2A]/20 text-[#C94A2A] px-2 py-1 rounded hover:bg-[#C94A2A]/40 transition-colors">
                        <UploadCloud className="w-3 h-3" /> Upload File
                        <input type="file" className="hidden" onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            handleUpload(evidenceDetail.id, e.target.files[0]);
                          }
                        }} />
                      </label>
                    )}
                  </h3>
                  
                  {evidenceDetail.metadata ? (
                    <div className="grid grid-cols-2 gap-4 text-sm mt-3">
                      <div>
                        <span className="text-[#6A7A96] block text-[10px] uppercase font-mono">Filename</span>
                        <span className="text-white">{evidenceDetail.metadata.filename}</span>
                      </div>
                      <div>
                        <span className="text-[#6A7A96] block text-[10px] uppercase font-mono">Size & Type</span>
                        <span className="text-white">{(evidenceDetail.metadata.filesize / 1024 / 1024).toFixed(2)} MB • {evidenceDetail.metadata.mime_type}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-[#6A7A96] block text-[10px] uppercase font-mono mb-1">Extracted Metadata</span>
                        <pre className="bg-black/50 p-2 rounded text-[#0E9E78] font-mono text-[10px] overflow-auto">
                          {JSON.stringify(evidenceDetail.metadata.extracted_data, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-[#A8B4CC] text-sm">
                      <HardDrive className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      No digital file attached to this evidence record.
                    </div>
                  )}
                </div>

                <div className="bg-[#080E1B] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#6C43CC] font-mono text-xs uppercase font-bold mb-3 border-b border-border-color pb-2 flex justify-between items-center">
                    AI Summary & Analysis
                    <button onClick={() => generateAISummary(evidenceDetail.id)} className="flex items-center gap-1 text-[10px] bg-[#6C43CC]/20 text-[#6C43CC] px-2 py-1 rounded hover:bg-[#6C43CC]/40 transition-colors">
                      <Cpu className="w-3 h-3" /> Generate Analysis
                    </button>
                  </h3>
                  
                  {evidenceDetail.ai_summaries && evidenceDetail.ai_summaries.length > 0 ? (
                    <div className="space-y-4 mt-3">
                      {evidenceDetail.ai_summaries.map((s: any) => (
                        <div key={s.id} className="bg-black/30 p-3 rounded border border-[#6C43CC]/20">
                          <span className="text-[10px] text-[#6A7A96] block mb-1 font-mono">{new Date(s.created_at).toLocaleString()}</span>
                          <p className="text-sm text-white">{s.summary}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-[#A8B4CC] text-sm">
                      No AI analysis generated yet.
                    </div>
                  )}
                </div>

              </div>
              
              <div className="col-span-1 space-y-6">
                
                {/* Assignments */}
                <div className="bg-[#080E1B] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#C94A2A] font-mono text-xs uppercase font-bold mb-4 border-b border-border-color pb-2">Assignments</h3>
                  <div className="space-y-4">
                    {evidenceDetail.assignments && evidenceDetail.assignments.length > 0 ? (
                      evidenceDetail.assignments.map((a: any) => (
                        <div key={a.id} className="bg-black/30 p-3 rounded border border-[#C94A2A]/20">
                          <span className="text-[10px] text-[#6A7A96] block mb-1 font-mono">To: {a.assigned_to}</span>
                          <span className="text-white text-xs block mb-2 font-bold">{a.status}</span>
                          
                          {/* Assignment Actions */}
                          {(isForensic || isInspector || isIO || isSCRB) && (
                            <div className="flex gap-2 mt-2">
                              {a.status === 'Assigned' && (
                                <button onClick={() => handleAssignmentAction(evidenceDetail.id, a.id, 'accept')} className="px-2 py-1 bg-[#0E9E78]/20 text-[#0E9E78] text-[10px] rounded hover:bg-[#0E9E78]/40 transition-colors uppercase font-bold">Accept</button>
                              )}
                              {a.status === 'In Progress' && (
                                <button onClick={() => handleAssignmentAction(evidenceDetail.id, a.id, 'complete')} className="px-2 py-1 bg-[#1E6FD9]/20 text-[#1E6FD9] text-[10px] rounded hover:bg-[#1E6FD9]/40 transition-colors uppercase font-bold">Complete</button>
                              )}
                              {(a.status === 'In Progress' || a.status === 'Completed') && (
                                <button onClick={() => handleAssignmentAction(evidenceDetail.id, a.id, 'return')} className="px-2 py-1 bg-[#C94A2A]/20 text-[#C94A2A] text-[10px] rounded hover:bg-[#C94A2A]/40 transition-colors uppercase font-bold">Return</button>
                              )}
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <span className="text-[#A8B4CC] text-xs">No assignments.</span>
                    )}
                  </div>
                </div>

                {/* Chain of Custody */}
                <div className="bg-[#080E1B] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#D4820A] font-mono text-xs uppercase font-bold mb-4 border-b border-border-color pb-2">Chain of Custody</h3>
                  <div className="relative pl-3 space-y-4">
                    <div className="absolute left-[3px] top-2 bottom-2 w-px bg-border-color" />
                    {evidenceDetail.chain_of_custody && evidenceDetail.chain_of_custody.map((custody: any) => (
                      <div key={custody.id} className="relative pl-4">
                        <div className="absolute left-[-4px] top-1 w-2 h-2 rounded-full bg-[#D4820A]" />
                        <span className="text-[10px] text-[#6A7A96] font-mono block">{new Date(custody.timestamp).toLocaleString()}</span>
                        <strong className="text-white text-[11px] block">{custody.action}</strong>
                        <span className="text-[#A8B4CC] text-[10px] block">To: {custody.to_user}</span>
                      </div>
                    ))}
                  </div>
                  {(!evidenceDetail.chain_of_custody || evidenceDetail.chain_of_custody.length === 0) && (
                    <span className="text-[#A8B4CC] text-xs">No custody transfers recorded.</span>
                  )}
                </div>

                {/* Timeline */}
                <div className="bg-[#080E1B] p-4 rounded-lg border border-border-color">
                  <h3 className="text-[#0E9E78] font-mono text-xs uppercase font-bold mb-4 border-b border-border-color pb-2">Event Timeline</h3>
                  <div className="relative pl-3 space-y-4">
                    <div className="absolute left-[3px] top-2 bottom-2 w-px bg-border-color" />
                    {evidenceDetail.timeline && evidenceDetail.timeline.map((event: any) => (
                      <div key={event.id} className="relative pl-4">
                        <div className="absolute left-[-4px] top-1 w-2 h-2 rounded-full bg-[#0E9E78]" />
                        <span className="text-[10px] text-[#6A7A96] font-mono block">{new Date(event.created_at).toLocaleString()}</span>
                        <strong className="text-white text-[11px] block">{event.action}</strong>
                        <span className="text-[#A8B4CC] text-[10px] block">by {event.performed_by} ({event.role})</span>
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
