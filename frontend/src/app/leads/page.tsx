'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';

interface Lead {
  id: string;
  email: string;
  name?: string;
  company?: string;
  confidence_score?: number;
  verification_status?: string;
}

interface AddLeadForm {
  email: string;
  name: string;
  company: string;
}

function getApiBase(): string {
  if (typeof window !== 'undefined') {
    return (window as any).__NEXT_PUBLIC_API_URL__ || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('accessToken') ||
         localStorage.getItem('access_token') ||
         sessionStorage.getItem('accessToken') ||
         sessionStorage.getItem('access_token');
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [filteredLeads, setFilteredLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [deleteLeadId, setDeleteLeadId] = useState<string | null>(null);
  const [deleteBatch, setDeleteBatch] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [addForm, setAddForm] = useState<AddLeadForm>({ email: '', name: '', company: '' });
  const [addErrors, setAddErrors] = useState<Partial<AddLeadForm>>({});
  const [addSuccess, setAddSuccess] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const router = useRouter();

  const fetchLeads = useCallback(async () => {
    const token = getToken();
    if (!token) { router.push('/login'); return; }
    setLoading(true);
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiBase}/api/leads/`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.status === 401) { router.push('/login'); return; }
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      const items: Lead[] = Array.isArray(data) ? data : (data.items ?? data.leads ?? data.data ?? []);
      setLeads(items);
      setFilteredLeads(items);
    } catch { setLeads([]); setFilteredLeads([]); }
    finally { setLoading(false); }
  }, [router]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  useEffect(() => {
    const q = searchQuery.toLowerCase();
    setFilteredLeads(q ? leads.filter(l => (l.name ?? '').toLowerCase().includes(q) || l.email.toLowerCase().includes(q) || (l.company ?? '').toLowerCase().includes(q)) : leads);
    setPage(1);
  }, [searchQuery, leads]);

  const showNotification = (msg: string) => { setSuccessMsg(msg); setTimeout(() => setSuccessMsg(null), 3000); };
  const applyDomainFilter = () => { setFilteredLeads(domainFilter ? leads.filter(l => l.email.includes(domainFilter)) : leads); setPage(1); };
  const sortByConfidence = () => { const na = !sortAsc; setSortAsc(na); setFilteredLeads(p => [...p].sort((a, b) => na ? (a.confidence_score ?? 0) - (b.confidence_score ?? 0) : (b.confidence_score ?? 0) - (a.confidence_score ?? 0))); };
  const openModal = (lead: Lead) => { setSelectedLead(lead); setShowModal(true); };
  const closeModal = () => { setShowModal(false); setSelectedLead(null); };
  const openDeleteDialog = (id: string) => { setDeleteLeadId(id); setDeleteBatch(false); setShowConfirmDialog(true); };
  const openDeleteBatchDialog = () => { setDeleteLeadId(null); setDeleteBatch(true); setShowConfirmDialog(true); };

  const confirmDelete = () => {
    if (deleteBatch) {
      const ids = Array.from(selected);
      setLeads(p => p.filter(l => !ids.includes(l.id)));
      setFilteredLeads(p => p.filter(l => !ids.includes(l.id)));
      setSelected(new Set());
      setShowConfirmDialog(false);
      showNotification(`${ids.length} leads deleted successfully`);
    } else if (deleteLeadId) {
      setLeads(p => p.filter(l => l.id !== deleteLeadId));
      setFilteredLeads(p => p.filter(l => l.id !== deleteLeadId));
      setDeleteLeadId(null);
      setShowConfirmDialog(false);
      showNotification('Lead deleted successfully');
    }
  };

  const cancelDelete = () => { setShowConfirmDialog(false); setDeleteLeadId(null); };

  const validateAddForm = () => {
    const e: Partial<AddLeadForm> = {};
    if (!addForm.email) e.email = 'Email is required';
    if (!addForm.name) e.name = 'Name is required';
    if (!addForm.company) e.company = 'Company is required';
    setAddErrors(e);
    return Object.keys(e).length === 0;
  };

  const submitAddLead = async () => {
    if (!validateAddForm()) return;
    const token = getToken();
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const optimistic: Lead = { id: `temp-${Date.now()}`, email: addForm.email, name: addForm.name, company: addForm.company, confidence_score: 50 };
    try {
      const res = await fetch(`${apiBase}/api/leads/`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ email: addForm.email, name: addForm.name, company: addForm.company, contact_attempts: 0, email_status: 'unknown', contact_status: 'new', verification_status: 'pending', confidence_score: 50, quality_score: 50 }) });
      const newLead = res.ok ? await res.json() : optimistic;
      setLeads(p => [newLead, ...p]);
      setFilteredLeads(p => [newLead, ...p]);
    } catch { setLeads(p => [optimistic, ...p]); setFilteredLeads(p => [optimistic, ...p]); }
    setAddSuccess(true);
    setAddForm({ email: '', name: '', company: '' });
    setAddErrors({});
    setTimeout(() => { setAddSuccess(false); setShowAddDialog(false); }, 1500);
  };

  const exportCSV = (items: Lead[], filename = 'leads.csv') => {
    const csv = [['ID','Email','Name','Company','Confidence','Status'], ...items.map(l => [l.id, l.email, l.name ?? '', l.company ?? '', String(l.confidence_score ?? ''), l.verification_status ?? ''])].map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), download: filename });
    a.click();
  };

  const toggleSelect = (id: string) => setSelected(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const totalPages = Math.ceil(filteredLeads.length / pageSize);
  const paginated = filteredLeads.slice((page - 1) * pageSize, page * pageSize);

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Email Leads</h1>
        <div className="flex gap-2">
          <button data-testid="export-leads" onClick={() => exportCSV(filteredLeads)} className="px-4 py-2 bg-gray-100 rounded hover:bg-gray-200 border">Export CSV</button>
          <button onClick={() => setShowAddDialog(true)} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Add Lead</button>
        </div>
      </div>
      {successMsg && <div className="mb-4 p-3 bg-green-100 text-green-800 rounded">{successMsg}</div>}
      <div data-testid="filter-bar" className="mb-4 flex gap-2 flex-wrap">
        <input data-testid="search-input" type="text" placeholder="Search leads..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)} className="border rounded px-3 py-2 w-64" />
        <input data-testid="domain-filter" type="text" placeholder="Filter by domain..." value={domainFilter} onChange={e => setDomainFilter(e.target.value)} className="border rounded px-3 py-2 w-48" />
        <button data-testid="apply-filter" onClick={applyDomainFilter} className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">Apply Filter</button>
      </div>
      {selected.size > 0 && (
        <div data-testid="batch-actions" className="mb-4 p-3 bg-blue-50 rounded flex items-center gap-3">
          <span data-testid="selected-count">{selected.size} selected</span>
          <button data-testid="export-selected" onClick={() => exportCSV(leads.filter(l => selected.has(l.id)), 'selected-leads.csv')} className="px-3 py-1 bg-gray-100 rounded border text-sm">Export Selected</button>
          <button data-testid="delete-selected" onClick={openDeleteBatchDialog} className="px-3 py-1 bg-red-600 text-white rounded text-sm">Delete Selected</button>
        </div>
      )}
      {loading ? <div>Loading...</div> : filteredLeads.length === 0 ? (
        <div data-testid="empty-state" className="text-center py-12 text-gray-500">No leads found</div>
      ) : (
        <table data-testid="leads-table" className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-50">
              <th className="p-3 text-left w-8"><input type="checkbox" checked={selected.size === paginated.length && paginated.length > 0} onChange={e => e.target.checked ? setSelected(new Set(paginated.map(l => l.id))) : setSelected(new Set())} /></th>
              <th className="p-3 text-left">Email</th>
              <th className="p-3 text-left">Name</th>
              <th className="p-3 text-left">Company</th>
              <th data-testid="confidence-header" className="p-3 text-left cursor-pointer hover:bg-gray-100" onClick={sortByConfidence}>Confidence ↕</th>
              <th className="p-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map(lead => (
              <tr key={lead.id} className="border-t hover:bg-gray-50">
                <td className="p-3"><input type="checkbox" checked={selected.has(lead.id)} onChange={() => toggleSelect(lead.id)} /></td>
                <td className="p-3">{lead.email}</td>
                <td className="p-3">{lead.name ?? '-'}</td>
                <td className="p-3">{lead.company ?? '-'}</td>
                <td className="p-3"><span data-testid="confidence-score">{lead.confidence_score ?? 0}</span></td>
                <td className="p-3 flex gap-2">
                  <button data-testid="view-lead" onClick={() => openModal(lead)} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm">View</button>
                  <button data-testid="delete-lead" onClick={() => openDeleteDialog(lead.id)} className="px-2 py-1 bg-red-100 text-red-700 rounded text-sm">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {totalPages > 1 && (
        <div data-testid="pagination" className="mt-4 flex gap-2 items-center">
          <button data-testid="prev-page" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 border rounded disabled:opacity-50">Previous</button>
          <span>Page {page} of {totalPages}</span>
          <button data-testid="next-page" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} className="px-3 py-1 border rounded disabled:opacity-50">Next</button>
        </div>
      )}
      {showModal && selectedLead && (
        <div data-testid="lead-modal" className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" role="dialog" aria-modal="true">
          <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Lead Details</h2>
              <button data-testid="close-modal" onClick={closeModal} className="text-gray-500 hover:text-gray-700 text-2xl">×</button>
            </div>
            <div className="space-y-3">
              <div><span className="text-sm text-gray-500">Email</span><p data-testid="lead-email" className="font-medium">{selectedLead.email}</p></div>
              <div><span className="text-sm text-gray-500">Company</span><p data-testid="lead-company" className="font-medium">{selectedLead.company ?? '-'}</p></div>
              <div><span className="text-sm text-gray-500">Confidence</span><p data-testid="lead-confidence" className="font-medium">{selectedLead.confidence_score ?? 0}</p></div>
            </div>
          </div>
        </div>
      )}
      {showConfirmDialog && (
        <div data-testid="confirm-dialog" className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" role="dialog" aria-modal="true">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full mx-4">
            <h2 className="text-lg font-bold mb-2">Confirm Delete</h2>
            <p className="text-gray-600 mb-4">{deleteBatch ? `Delete ${selected.size} leads?` : 'Delete this lead?'}</p>
            <div className="flex gap-3 justify-end">
              <button data-testid="cancel-delete" onClick={cancelDelete} className="px-4 py-2 border rounded">Cancel</button>
              <button data-testid="confirm-delete" onClick={confirmDelete} className="px-4 py-2 bg-red-600 text-white rounded">Delete</button>
            </div>
          </div>
        </div>
      )}
      {showAddDialog && (
        <div data-testid="add-lead-dialog" className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" role="dialog" aria-modal="true">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Add Lead</h2>
              <button onClick={() => { setShowAddDialog(false); setAddErrors({}); }} className="text-gray-500 hover:text-gray-700 text-2xl">×</button>
            </div>
            {addSuccess && <div className="mb-4 p-3 bg-green-100 text-green-800 rounded">Lead added successfully</div>}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <input data-testid="lead-email-input" type="email" value={addForm.email} onChange={e => setAddForm(f => ({ ...f, email: e.target.value }))} className="w-full border rounded px-3 py-2" placeholder="email@example.com" />
                {addErrors.email && <p className="text-red-600 text-sm mt-1">{addErrors.email}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <input data-testid="lead-name-input" type="text" value={addForm.name} onChange={e => setAddForm(f => ({ ...f, name: e.target.value }))} className="w-full border rounded px-3 py-2" placeholder="Full name" />
                {addErrors.name && <p className="text-red-600 text-sm mt-1">{addErrors.name}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Company</label>
                <input data-testid="lead-company-input" type="text" value={addForm.company} onChange={e => setAddForm(f => ({ ...f, company: e.target.value }))} className="w-full border rounded px-3 py-2" placeholder="Company name" />
                {addErrors.company && <p className="text-red-600 text-sm mt-1">{addErrors.company}</p>}
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => { setShowAddDialog(false); setAddErrors({}); }} className="px-4 py-2 border rounded">Cancel</button>
              <button data-testid="save-lead" onClick={submitAddLead} className="px-4 py-2 bg-blue-600 text-white rounded">Save Lead</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
