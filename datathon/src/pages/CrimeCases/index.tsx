import React, { useEffect, useState } from 'react';
import CrimeCasesList from './CrimeCasesList';
import CrimeCaseDetails from './CrimeCaseDetails';
import CreateCrimeCase from './CreateCrimeCase';
import EditCrimeCase from './EditCrimeCase';

type ViewMode = 'list' | 'create' | 'details' | 'edit';

const CrimeCases: React.FC = () => {
  const [view, setView] = useState<ViewMode>('list');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);

  useEffect(() => {
    // Honor cross-module navigation (e.g. anomaly feed -> linked case file)
    const redirectId = sessionStorage.getItem('selected_entity_id');
    if (redirectId) {
      sessionStorage.removeItem('selected_entity_id');
      setSelectedCaseId(redirectId);
      setView('details');
    }
  }, []);

  const handleSelectCase = (id: string) => {
    setSelectedCaseId(id);
    setView('details');
  };

  const handleEditCase = (id: string) => {
    setSelectedCaseId(id);
    setView('edit');
  };

  return (
    <div className="w-full h-full min-h-[80vh] flex flex-col font-mono text-[var(--text-primary)]">
      {view === 'list' && (
        <CrimeCasesList
          onSelectCase={handleSelectCase}
          onCreateCase={() => setView('create')}
          onEditCase={handleEditCase}
        />
      )}

      {view === 'create' && (
        <CreateCrimeCase
          onCancel={() => setView('list')}
          onSuccess={() => setView('list')}
        />
      )}

      {view === 'details' && selectedCaseId && (
        <CrimeCaseDetails
          caseId={selectedCaseId}
          onBack={() => setView('list')}
          onEdit={() => setView('edit')}
        />
      )}

      {view === 'edit' && selectedCaseId && (
        <EditCrimeCase
          caseId={selectedCaseId}
          onCancel={() => setView('list')}
          onSuccess={() => setView('list')}
        />
      )}
    </div>
  );
};

export default CrimeCases;
