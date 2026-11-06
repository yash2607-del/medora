import React, { useMemo, useState } from 'react';
import { Search, ChevronDown, FileText } from 'lucide-react';

export default function PatientSelector({
  patients = [],
  selectedPatient,
  onSelectPatient,
  loading
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filteredPatients = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return patients;
    }

    return patients.filter((patient) => {
      const name = String(patient?.name || '').toLowerCase();
      const patientId = String(patient?.patient_id || '').toLowerCase();
      const city = String(patient?.city || '').toLowerCase();

      return (
        name.includes(query) ||
        patientId.includes(query) ||
        city.includes(query)
      );
    });
  }, [patients, search]);

  const handleSelect = (patient) => {
    onSelectPatient(patient);
    setIsOpen(false);
    setSearch('');
  };

  const handleToggle = () => {
    if (loading) {
      return;
    }

    setIsOpen((previous) => !previous);
  };

  return (
    <div className="relative w-full max-w-sm">
      {/* Selected patient */}
      <button
        type="button"
        onClick={handleToggle}
        disabled={loading}
        className="w-full p-3 bg-white border border-slate-200 rounded-2xl shadow-sm hover:border-primary/50 cursor-pointer transition-all flex items-center justify-between text-left disabled:opacity-60 disabled:cursor-not-allowed"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm shrink-0">
            {selectedPatient?.name
              ? selectedPatient.name.charAt(0).toUpperCase()
              : 'P'}
          </div>

          <div className="min-w-0">
            <div className="text-[10px] font-semibold text-primary uppercase tracking-wider">
              Active Patient
            </div>

            <div className="font-bold text-slate-900 text-sm truncate">
              {selectedPatient?.name || 'Select Patient'}
            </div>

            {selectedPatient && (
              <div className="text-xs text-slate-500 truncate">
                {selectedPatient.patient_id || 'No ID'}
                {selectedPatient.gender
                  ? ` • ${selectedPatient.gender}`
                  : ''}
                {selectedPatient.age !== null &&
                selectedPatient.age !== undefined
                  ? `, ${selectedPatient.age} yrs`
                  : ''}
              </div>
            )}
          </div>
        </div>

        <ChevronDown
          size={18}
          className={`text-slate-400 transition-transform shrink-0 ml-2 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-full bg-white border border-slate-200 rounded-2xl shadow-xl z-50 overflow-hidden animate-slide-up">
          {/* Search */}
          <div className="p-3 border-b border-slate-200 flex items-center gap-2">
            <Search
              size={16}
              className="text-slate-400 shrink-0"
            />

            <input
              type="text"
              placeholder="Search by name, ID or city..."
              value={search}
              onChange={(event) =>
                setSearch(event.target.value)
              }
              className="w-full text-xs bg-transparent focus:outline-none text-slate-800 placeholder:text-slate-400"
              autoFocus
            />
          </div>

          {/* Patient list */}
          <div
            className="max-h-64 overflow-y-auto divide-y divide-slate-100"
            role="listbox"
          >
            {filteredPatients.length > 0 ? (
              filteredPatients.map((patient) => {
                const isSelected =
                  selectedPatient?.patient_id ===
                  patient.patient_id;

                const totalReports =
                  Number(patient?.total_reports) || 0;

                return (
                  <button
                    type="button"
                    key={patient.patient_id}
                    onClick={() => handleSelect(patient)}
                    className={`w-full p-3 text-left hover:bg-slate-50 cursor-pointer transition-colors flex items-center justify-between gap-3 ${
                      isSelected
                        ? 'bg-primary/5'
                        : 'bg-white'
                    }`}
                    role="option"
                    aria-selected={isSelected}
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-800 text-xs truncate">
                        {patient.name || 'Unnamed Patient'}
                      </div>

                      <div className="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5 flex-wrap">
                        <span>
                          {patient.patient_id || 'No ID'}
                        </span>

                        {patient.gender && (
                          <>
                            <span>•</span>
                            <span>
                              {patient.gender}
                              {patient.age !== null &&
                              patient.age !== undefined
                                ? `, ${patient.age}y`
                                : ''}
                            </span>
                          </>
                        )}

                        {patient.city && (
                          <>
                            <span>•</span>
                            <span>{patient.city}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <span className="shrink-0 inline-flex items-center gap-1 text-[11px] font-medium text-primary px-2 py-0.5 rounded-full bg-primary/10">
                      <FileText size={11} />
                      {totalReports}{' '}
                      {totalReports === 1
                        ? 'report'
                        : 'reports'}
                    </span>
                  </button>
                );
              })
            ) : (
              <div className="p-6 text-center">
                <Search
                  size={22}
                  className="mx-auto text-slate-300 mb-2"
                />

                <p className="text-xs font-medium text-slate-500">
                  No matching patient found.
                </p>

                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch('')}
                    className="mt-2 text-[11px] font-semibold text-primary hover:underline"
                  >
                    Clear search
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}