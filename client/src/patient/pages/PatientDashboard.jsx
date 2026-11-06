import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  FileText,
  TrendingUp,
  History,
  Sparkles,
  UploadCloud,
  MessageSquare,
  ArrowLeft,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
} from 'lucide-react';

import { patientApi } from '../api/patientApi';
import PatientSelector from '../components/PatientSelector';
import ReportUploadModal from '../components/ReportUploadModal';
import ReportCard from '../components/ReportCard';
import LatestReportView from '../components/LatestReportView';
import TrendsChart from '../components/TrendsChart';
import AIReportView from '../components/AIReportView';
import PatientChatBox from '../components/PatientChatBox';
import EvidenceDrawer from '../components/EvidenceDrawer';

export default function PatientDashboard({
  onBackToHome,
  onLogout,
  currentUser,
}) {
  const [patients, setPatients] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [activeTab, setActiveTab] = useState('latest');
  const [reports, setReports] = useState([]);
  const [selectedReportDetail, setSelectedReportDetail] = useState(null);
  const [trends, setTrends] = useState([]);
  const [aiReport, setAiReport] = useState(null);

  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [generatingAI, setGeneratingAI] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [activeEvidenceItem, setActiveEvidenceItem] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  const getPatientId = useCallback(() => {
    return selectedPatient?.patient_id || null;
  }, [selectedPatient]);

  const getReportDate = useCallback((report) => {
    const date =
      report?.report_date ||
      report?.collection_date ||
      report?.created_at;

    if (!date) return 0;

    const timestamp = new Date(date).getTime();

    return Number.isNaN(timestamp) ? 0 : timestamp;
  }, []);

  const getReportCreatedAt = useCallback((report) => {
    if (!report?.created_at) return 0;

    const timestamp = new Date(report.created_at).getTime();

    return Number.isNaN(timestamp) ? 0 : timestamp;
  }, []);

  const sortedReports = useMemo(() => {
    return [...reports].sort((a, b) => {
      const dateDifference =
        getReportDate(b) - getReportDate(a);

      if (dateDifference !== 0) {
        return dateDifference;
      }

      return (
        getReportCreatedAt(b) -
        getReportCreatedAt(a)
      );
    });
  }, [reports, getReportDate, getReportCreatedAt]);

  const loadPatients = useCallback(async () => {
    try {
      setLoading(true);
      setInitialLoading(true);
      setErrorMessage('');

      const data = await patientApi.getPatients();

      const patientList = Array.isArray(data) ? data : [];

      setPatients(patientList);

      if (patientList.length === 0) {
        setSelectedPatient(null);
        return;
      }

      setSelectedPatient((current) => {
        if (!current) {
          return patientList[0];
        }

        const stillExists = patientList.find(
          (patient) =>
            patient.patient_id === current.patient_id
        );

        return stillExists || patientList[0];
      });
    } catch (error) {
      console.error('Failed to load patients:', error);

      setPatients([]);
      setSelectedPatient(null);

      setErrorMessage(
        error?.response?.data?.detail ||
          'Unable to load patient records. Please make sure the backend server is running.'
      );
    } finally {
      setLoading(false);
      setInitialLoading(false);
    }
  }, []);

  const loadReportDetail = useCallback(
    async (patientId, reportId) => {
      if (!patientId || !reportId) {
        setSelectedReportDetail(null);
        return;
      }

      try {
        setLoadingDetail(true);
        setErrorMessage('');

        const detail = await patientApi.getReportDetail(
          patientId,
          reportId
        );

        setSelectedReportDetail(detail);

        setAiReport(null);
        setActiveEvidenceItem(null);
        setEvidenceDrawerOpen(false);
      } catch (error) {
        console.error('Failed to load report detail:', error);

        setSelectedReportDetail(null);
        setAiReport(null);
        setActiveEvidenceItem(null);
        setEvidenceDrawerOpen(false);

        setErrorMessage(
          error?.response?.data?.detail ||
            'Unable to load the selected report.'
        );
      } finally {
        setLoadingDetail(false);
      }
    },
    []
  );

  const loadPatientData = useCallback(
    async (patientId) => {
      if (!patientId) {
        setReports([]);
        setTrends([]);
        setSelectedReportDetail(null);
        setAiReport(null);
        setActiveEvidenceItem(null);
        setEvidenceDrawerOpen(false);
        return;
      }

      try {
        setLoading(true);
        setErrorMessage('');

        const [reportsResponse, trendsResponse] =
          await Promise.all([
            patientApi.getReports(patientId),
            patientApi.getTrends(patientId),
          ]);

        const reportList = Array.isArray(reportsResponse)
          ? reportsResponse
          : [];

        const trendList = Array.isArray(trendsResponse)
          ? trendsResponse
          : [];

        setReports(reportList);
        setTrends(trendList);

        const orderedReports = [...reportList].sort(
          (a, b) => {
            const dateDifference =
              getReportDate(b) - getReportDate(a);

            if (dateDifference !== 0) {
              return dateDifference;
            }

            return (
              getReportCreatedAt(b) -
              getReportCreatedAt(a)
            );
          }
        );

        if (orderedReports.length > 0) {
          const latest = orderedReports[0];

          await loadReportDetail(
            patientId,
            latest.report_id
          );
        } else {
          setSelectedReportDetail(null);
          setAiReport(null);
          setActiveEvidenceItem(null);
          setEvidenceDrawerOpen(false);
        }
      } catch (error) {
        console.error(
          'Failed to load patient data:',
          error
        );

        setReports([]);
        setTrends([]);
        setSelectedReportDetail(null);
        setAiReport(null);
        setActiveEvidenceItem(null);
        setEvidenceDrawerOpen(false);

        setErrorMessage(
          error?.response?.data?.detail ||
            'Unable to load patient data from the backend.'
        );
      } finally {
        setLoading(false);
      }
    },
    [
      getReportDate,
      getReportCreatedAt,
      loadReportDetail,
    ]
  );

  useEffect(() => {
    loadPatients();
  }, [loadPatients]);

  useEffect(() => {
    if (!selectedPatient?.patient_id) {
      return;
    }

    loadPatientData(selectedPatient.patient_id);
  }, [selectedPatient, loadPatientData]);

  const handlePatientChange = (patient) => {
    if (!patient?.patient_id) {
      return;
    }

    setSelectedPatient(patient);
    setSelectedReportDetail(null);
    setAiReport(null);
    setActiveEvidenceItem(null);
    setEvidenceDrawerOpen(false);
    setActiveTab('latest');
    setErrorMessage('');
  };

  const handleRefresh = async () => {
    if (!selectedPatient?.patient_id) {
      await loadPatients();
      return;
    }

    await loadPatientData(
      selectedPatient.patient_id
    );
  };

  const handleUploadSuccess = async () => {
    if (!selectedPatient?.patient_id) {
      return;
    }

    setUploadModalOpen(false);
    setErrorMessage('');
    setAiReport(null);
    setActiveEvidenceItem(null);
    setEvidenceDrawerOpen(false);

    await loadPatientData(
      selectedPatient.patient_id
    );

    setActiveTab('latest');
  };

  const handleGenerateAI = async (reportId) => {
    const patientId = selectedPatient?.patient_id;

    if (!patientId || !reportId) {
      return;
    }

    try {
      setGeneratingAI(true);
      setErrorMessage('');

      const result =
        await patientApi.generateAIReport(
          patientId,
          reportId
        );

      setAiReport(result);
      setActiveTab('ai_report');
    } catch (error) {
      console.error(
        'AI report generation failed:',
        error
      );

      setErrorMessage(
        error?.response?.data?.detail ||
          'Unable to generate the AI patient report.'
      );
    } finally {
      setGeneratingAI(false);
    }
  };

  const handleInspectEvidence = (item) => {
    if (!item) {
      return;
    }

    setActiveEvidenceItem(item);
    setEvidenceDrawerOpen(true);
  };

  const handleSelectReport = async (report) => {
    if (
      !selectedPatient?.patient_id ||
      !report?.report_id
    ) {
      return;
    }

    setActiveTab('latest');
    setAiReport(null);
    setActiveEvidenceItem(null);
    setEvidenceDrawerOpen(false);

    await loadReportDetail(
      selectedPatient.patient_id,
      report.report_id
    );
  };

  if (initialLoading) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
        <header className="sticky top-0 z-40 bg-white border-b border-slate-200 px-4 sm:px-8 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <button
              onClick={onBackToHome}
              className="px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors flex items-center gap-2 text-xs font-semibold"
            >
              <ArrowLeft size={16} />
              Healthcare Home
            </button>

            <div className="flex items-center gap-3">
              <img
                src="/lords-path-logo.png"
                alt="Lord's Pathology"
                className="w-9 h-9 object-contain"
              />

              <div>
                <h1 className="font-extrabold text-base text-slate-900">
                  Lord's Pathology
                </h1>

                <p className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                  Patient Intelligence Portal
                </p>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-20">
          <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-10 text-center">
            <RefreshCw
              size={30}
              className="mx-auto text-primary animate-spin"
            />

            <h2 className="mt-5 text-lg font-extrabold text-slate-900">
              Loading patient records
            </h2>

            <p className="text-sm text-slate-500 mt-2">
              Preparing your patient intelligence dashboard...
            </p>
          </div>
        </main>
      </div>
    );
  }

  if (patients.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
        <header className="sticky top-0 z-40 bg-white border-b border-slate-200 px-4 sm:px-8 py-4">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <button
              onClick={onBackToHome}
              className="px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors flex items-center gap-2 text-xs font-semibold"
            >
              <ArrowLeft size={16} />
              Healthcare Home
            </button>

            <div className="flex items-center gap-3">
              <img
                src="/lords-path-logo.png"
                alt="Lord's Pathology"
                className="w-9 h-9 object-contain"
              />

              <div>
                <h1 className="font-extrabold text-base text-slate-900">
                  Lord's Pathology
                </h1>

                <p className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                  Patient Intelligence Portal
                </p>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-16">
          <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-8 text-center">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 text-primary flex items-center justify-center mx-auto mb-4">
              <AlertTriangle size={26} />
            </div>

            <h2 className="text-xl font-extrabold text-slate-900">
              Patient records unavailable
            </h2>

            <p className="text-sm text-slate-500 mt-2">
              {errorMessage ||
                'No patient records were returned by the backend.'}
            </p>

            <button
              onClick={loadPatients}
              className="mt-6 px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-hover text-white text-xs font-bold flex items-center gap-2 mx-auto"
            >
              <RefreshCw size={15} />
              Retry
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans">
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200 px-4 sm:px-8 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={onBackToHome}
              className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 transition-colors flex items-center gap-1.5 text-xs font-semibold"
            >
              <ArrowLeft size={16} />
              <span>Healthcare Home</span>
            </button>

            <div className="flex items-center gap-3">
              <img
                src="/lords-path-logo.png"
                alt="Lord's Pathology Logo"
                className="w-9 h-9 object-contain"
              />

              <div>
                <h1 className="font-extrabold text-base text-slate-900 leading-tight">
                  Lord's Pathology
                </h1>

                <span className="text-[11px] font-semibold text-primary uppercase tracking-wider">
                  Patient Intelligence Portal
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 w-full md:w-auto">
            <div className="flex-1 md:flex-none md:w-80">
              <PatientSelector
                patients={patients}
                selectedPatient={selectedPatient}
                onSelectPatient={handlePatientChange}
                loading={loading}
              />
            </div>

            <button
              onClick={handleRefresh}
              disabled={loading}
              title="Refresh patient data"
              className="p-3 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 disabled:opacity-50 transition-colors"
            >
              <RefreshCw
                size={16}
                className={
                  loading ? 'animate-spin' : ''
                }
              />
            </button>

            <button
              onClick={() => setUploadModalOpen(true)}
              disabled={!selectedPatient}
              className="px-4 py-2.5 rounded-2xl bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-md shadow-primary/20 transition-all flex items-center gap-2 cursor-pointer shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <UploadCloud size={16} />

              <span className="hidden sm:inline">
                Upload Report
              </span>
            </button>

            {onLogout && (
              <button
                onClick={onLogout}
                title="Logout"
                className="px-4 py-2.5 rounded-2xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-bold transition-colors shrink-0"
              >
                Logout
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-8 py-8 space-y-6">
        {errorMessage && (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3">
            <AlertTriangle
              size={18}
              className="text-red-600 shrink-0 mt-0.5"
            />

            <div className="flex-1">
              <p className="text-sm font-semibold text-red-800">
                Unable to complete request
              </p>

              <p className="text-xs text-red-600 mt-1">
                {errorMessage}
              </p>
            </div>

            <button
              onClick={() => setErrorMessage('')}
              className="text-xs font-semibold text-red-600 hover:text-red-800"
            >
              Dismiss
            </button>
          </div>
        )}

        {selectedPatient && (
          <div className="bg-white border border-slate-200 rounded-3xl shadow-sm p-5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center font-extrabold text-lg">
                  {selectedPatient.name
                    ?.charAt(0)
                    ?.toUpperCase() || 'P'}
                </div>

                <div>
                  <p className="text-[11px] uppercase tracking-wider font-bold text-primary">
                    Active Patient
                  </p>

                  <h2 className="text-lg font-extrabold text-slate-900">
                    {selectedPatient.name}
                  </h2>

                  <p className="text-xs text-slate-500">
                    {selectedPatient.patient_id}

                    {selectedPatient.gender && (
                      <> • {selectedPatient.gender}</>
                    )}

                    {selectedPatient.age && (
                      <> • {selectedPatient.age} years</>
                    )}

                    {selectedPatient.city && (
                      <> • {selectedPatient.city}</>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-500">
                <ShieldCheck
                  size={16}
                  className="text-emerald-600"
                />

                <span>
                  Patient data isolated from company knowledge base
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none border-b border-slate-200 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('latest')}
            className={`px-4 py-2.5 rounded-2xl transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
              activeTab === 'latest'
                ? 'bg-primary text-white shadow-md shadow-primary/20'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <FileText size={16} />
            <span>Latest Report</span>
          </button>

          <button
            onClick={() => setActiveTab('reports')}
            className={`px-4 py-2.5 rounded-2xl transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
              activeTab === 'reports'
                ? 'bg-primary text-white shadow-md shadow-primary/20'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <FileText size={16} />
            <span>
              My Reports ({reports.length})
            </span>
          </button>

          <button
            onClick={() => setActiveTab('trends')}
            className={`px-4 py-2.5 rounded-2xl transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
              activeTab === 'trends'
                ? 'bg-primary text-white shadow-md shadow-primary/20'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <TrendingUp size={16} />
            <span>Longitudinal Trends</span>
          </button>

           <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2.5 rounded-2xl transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
              activeTab === 'chat'
                ? 'bg-primary text-white shadow-md shadow-primary/20'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            <MessageSquare size={16} />
            <span>Patient Assistant</span>
          </button>
        </div>

        {loadingDetail && (
          <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center gap-3 text-sm text-slate-600">
            <RefreshCw
              size={16}
              className="animate-spin text-primary"
            />
            Loading report details...
          </div>
        )}

        {activeTab === 'latest' && (
          <LatestReportView
            reportDetail={selectedReportDetail}
            onInspectEvidence={handleInspectEvidence}
            onGenerateAI={handleGenerateAI}
            generatingAI={generatingAI}
          />
        )}

        {activeTab === 'reports' && (
          <div className="space-y-4">
            <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2.5 py-0.5 rounded-full bg-primary/10">
                Patient Records
              </span>

              <h3 className="text-xl font-extrabold text-slate-900 mt-2">
                All Diagnostic Reports
              </h3>

              <p className="text-xs text-slate-500 mt-1">
                Select any report to view laboratory parameters,
                deterministic status and provenance.
              </p>
            </div>

            {sortedReports.length === 0 ? (
              <div className="bg-white border border-slate-200 rounded-3xl p-10 text-center">
                <FileText
                  size={32}
                  className="mx-auto text-slate-300"
                />

                <h3 className="mt-3 font-bold text-slate-800">
                  No reports yet
                </h3>

                <p className="text-xs text-slate-500 mt-1">
                  Upload a diagnostic report to begin analysis.
                </p>

                <button
                  onClick={() => setUploadModalOpen(true)}
                  className="mt-5 px-4 py-2.5 rounded-xl bg-primary text-white text-xs font-bold inline-flex items-center gap-2"
                >
                  <UploadCloud size={15} />
                  Upload Report
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sortedReports.map((report) => (
                  <ReportCard
                    key={report.report_id}
                    report={report}
                    isSelected={
                      selectedReportDetail?.report_id ===
                      report.report_id
                    }
                    onSelect={handleSelectReport}
                    onGenerateAI={(selectedReport) =>
                      handleGenerateAI(
                        selectedReport.report_id
                      )
                    }
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'trends' && (
          <TrendsChart trends={trends} />
        )}

         {activeTab === 'ai_report' && (
          <AIReportView
            aiReport={aiReport}
            onRefresh={() => {
              if (selectedReportDetail?.report_id) {
                handleGenerateAI(
                  selectedReportDetail.report_id
                );
              }
            }}
            loading={generatingAI}
            onOpenEvidence={() => {
              if (
                selectedReportDetail?.results &&
                selectedReportDetail.results.length > 0
              ) {
                handleInspectEvidence(
                  selectedReportDetail.results[0]
                );
              }
            }}
          />
        )}

        {activeTab === 'chat' && (
          <PatientChatBox
            patientId={getPatientId()}
            reportId={selectedReportDetail?.report_id}
            onOpenEvidence={handleInspectEvidence}
          />
        )}
      </main>

      <ReportUploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        patientId={selectedPatient?.patient_id}
        onUploadSuccess={handleUploadSuccess}
      />

      <EvidenceDrawer
        isOpen={evidenceDrawerOpen}
        onClose={() => setEvidenceDrawerOpen(false)}
        evidenceItem={activeEvidenceItem}
        reportMeta={selectedReportDetail}
      />
    </div>
  );
}