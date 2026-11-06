import React, { useState } from 'react';
import {
  Sparkles,
  FileText,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  AlertCircle,
  CheckCircle,
  Info
} from 'lucide-react';

export default function LatestReportView({
  reportDetail,
  onInspectEvidence,
  onGenerateAI,
  generatingAI
}) {
  const [filter, setFilter] = useState('ALL');

  if (!reportDetail) {
    return (
      <div className="p-12 text-center text-slate-400 bg-white rounded-3xl border border-slate-200">
        No report selected. Please select a report from the list or history timeline.
      </div>
    );
  }

  const results = Array.isArray(reportDetail.results)
    ? reportDetail.results
    : [];

  const abnormalCount = results.filter(
    (result) =>
      result?.status === 'HIGH' ||
      result?.status === 'LOW'
  ).length;

  const normalCount = results.filter(
    (result) => result?.status === 'NORMAL'
  ).length;

  const unknownCount = results.filter(
    (result) =>
      !['HIGH', 'LOW', 'NORMAL'].includes(
        result?.status
      )
  ).length;

  const filteredResults = results.filter((result) => {
    if (filter === 'ABNORMAL') {
      return (
        result?.status === 'HIGH' ||
        result?.status === 'LOW'
      );
    }

    if (filter === 'NORMAL') {
      return result?.status === 'NORMAL';
    }

    return true;
  });

  const reportDate = reportDetail.report_date || 'Date unavailable';

  const laboratory =
    reportDetail.laboratory || "Lord's Pathology";

  const category =
    reportDetail.report_category || 'Diagnostic Panel';

  const handleGenerateAI = () => {
    if (
      typeof onGenerateAI === 'function' &&
      reportDetail.report_id
    ) {
      onGenerateAI(reportDetail.report_id);
    }
  };

  const renderStatus = (status) => {
    const normalizedStatus = String(
      status || 'UNKNOWN'
    ).toUpperCase();

    if (normalizedStatus === 'HIGH') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-red-100 text-red-700 border border-red-300/40">
          <ArrowUpRight size={13} />
          HIGH
        </span>
      );
    }

    if (normalizedStatus === 'LOW') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-700 border border-amber-300/40">
          <ArrowDownRight size={13} />
          LOW
        </span>
      );
    }

    if (normalizedStatus === 'NORMAL') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-300/40">
          <CheckCircle size={13} />
          NORMAL
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
        <Info size={13} />
        UNKNOWN
      </span>
    );
  };

  const getReferenceDisplay = (result) => {
    if (result?.reference_text) {
      return result.reference_text;
    }

    const low = result?.reference_low;
    const high = result?.reference_high;

    if (low !== null && low !== undefined &&
        high !== null && high !== undefined) {
      return `${low} - ${high}`;
    }

    if (low !== null && low !== undefined) {
      return `≥ ${low}`;
    }

    if (high !== null && high !== undefined) {
      return `≤ ${high}`;
    }

    return 'Not available';
  };

  const getResultValue = (result) => {
    const value =
      result?.normalized_value ??
      result?.original_value;

    if (
      value === null ||
      value === undefined ||
      value === ''
    ) {
      return 'N/A';
    }

    return value;
  };

  const getResultUnit = (result) => {
    return (
      result?.normalized_unit ||
      result?.original_unit ||
      ''
    );
  };

  return (
    <div className="space-y-6">

      {/* Report Summary */}
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary px-2.5 py-0.5 rounded-full bg-primary/10">
              {category}
            </span>

            <span className="text-xs text-slate-400">
              •
            </span>

            <span className="text-xs font-mono font-bold text-slate-700">
              {reportDetail.report_id || 'Unknown Report'}
            </span>
          </div>

          <h3 className="text-xl font-extrabold text-slate-900 mt-1">
            Diagnostic Test Results
          </h3>

          <p className="text-xs text-slate-500 mt-0.5">
            Report Date:{' '}
            <strong className="text-slate-700">
              {reportDate}
            </strong>{' '}
            • Laboratory:{' '}
            <strong className="text-slate-700">
              {laboratory}
            </strong>
          </p>
        </div>

        {/* AI Explanation */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={handleGenerateAI}
            disabled={
              generatingAI ||
              !reportDetail.report_id
            }
            className="px-5 py-2.5 rounded-2xl bg-gradient-to-r from-primary to-blue-600 hover:from-primary-hover hover:to-blue-700 text-white font-bold text-xs shadow-lg shadow-primary/25 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Sparkles
              size={16}
              className={
                generatingAI
                  ? 'animate-spin'
                  : ''
              }
            />

            <span>
              {generatingAI
                ? 'Analyzing...'
                : 'Generate AI Report'}
            </span>
          </button>
        </div>
      </div>

      {/* Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">

        {/* Total */}
        <button
          type="button"
          onClick={() => setFilter('ALL')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filter === 'ALL'
              ? 'bg-primary/5 border-primary ring-2 ring-primary/20'
              : 'bg-white border-slate-200 hover:border-primary/30'
          }`}
        >
          <span className="text-xs font-semibold text-slate-500">
            Total Evaluated
          </span>

          <div className="text-2xl font-black text-slate-900 mt-1">
            {results.length}
          </div>

          <span className="text-[11px] text-slate-400">
            Extracted parameters
          </span>
        </button>

        {/* Abnormal */}
        <button
          type="button"
          onClick={() => setFilter('ABNORMAL')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filter === 'ABNORMAL'
              ? 'bg-red-50 border-red-500 ring-2 ring-red-500/20'
              : 'bg-white border-slate-200 hover:border-red-300'
          }`}
        >
          <span className="text-xs font-semibold text-red-600">
            Abnormal
          </span>

          <div className="text-2xl font-black text-red-600 mt-1">
            {abnormalCount}
          </div>

          <span className="text-[11px] text-slate-400">
            High or low
          </span>
        </button>

        {/* Normal */}
        <button
          type="button"
          onClick={() => setFilter('NORMAL')}
          className={`p-4 rounded-2xl border text-left transition-all ${
            filter === 'NORMAL'
              ? 'bg-emerald-50 border-emerald-500 ring-2 ring-emerald-500/20'
              : 'bg-white border-slate-200 hover:border-emerald-300'
          }`}
        >
          <span className="text-xs font-semibold text-emerald-600">
            Normal
          </span>

          <div className="text-2xl font-black text-emerald-600 mt-1">
            {normalCount}
          </div>

          <span className="text-[11px] text-slate-400">
            Within reference range
          </span>
        </button>

        {/* Unknown */}
        <div className="p-4 rounded-2xl border border-slate-200 bg-white text-left">
          <span className="text-xs font-semibold text-slate-500">
            Unclassified
          </span>

          <div className="text-2xl font-black text-slate-600 mt-1">
            {unknownCount}
          </div>

          <span className="text-[11px] text-slate-400">
            No deterministic status
          </span>
        </div>
      </div>

      {/* No results */}
      {results.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-3xl border border-slate-200">
          <FileText
            size={32}
            className="mx-auto text-slate-300 mb-3"
          />

          <h4 className="text-sm font-bold text-slate-700">
            No extracted test results
          </h4>

          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            No structured test results are currently
            available for this report. Please verify the
            report processing status and source document.
          </p>
        </div>
      ) : (
        <>
          {/* Results Table */}
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3.5 px-5">
                      Test Parameter
                    </th>

                    <th className="py-3.5 px-4">
                      Result
                    </th>

                    <th className="py-3.5 px-4">
                      Reference Interval
                    </th>

                    <th className="py-3.5 px-4">
                      Status
                    </th>

                    <th className="py-3.5 px-4">
                      Previous Value
                    </th>

                    <th className="py-3.5 px-4 text-right">
                      Provenance
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-slate-100 font-medium">
                  {filteredResults.map((result, index) => {
                    const resultId =
                      result?.result_id ||
                      `${result?.test_name_normalized || 'result'}-${index}`;

                    const testName =
                      result?.test_name_normalized ||
                      result?.test_name_original ||
                      'Unnamed Test';

                    const originalName =
                      result?.test_name_original;

                    const normalizedName =
                      result?.test_name_normalized;

                    const value =
                      getResultValue(result);

                    const unit =
                      getResultUnit(result);

                    const previousValue =
                      result?.previous_value;

                    return (
                      <tr
                        key={resultId}
                        className="hover:bg-slate-50/80 transition-colors"
                      >
                        {/* Test Name */}
                        <td className="py-3.5 px-5">
                          <div className="font-bold text-slate-900 text-sm">
                            {testName}
                          </div>

                          {originalName &&
                            normalizedName &&
                            originalName !== normalizedName && (
                              <div className="text-[11px] text-slate-400 font-normal mt-0.5">
                                Raw: {originalName}
                              </div>
                            )}
                        </td>

                        {/* Result */}
                        <td className="py-3.5 px-4">
                          <span className="font-bold text-sm text-slate-900">
                            {value}
                          </span>

                          {unit && (
                            <span className="text-slate-500 text-[11px] ml-1">
                              {unit}
                            </span>
                          )}
                        </td>

                        {/* Reference */}
                        <td className="py-3.5 px-4 text-slate-600 font-normal">
                          {getReferenceDisplay(result)}
                        </td>

                        {/* Status */}
                        <td className="py-3.5 px-4">
                          {renderStatus(result?.status)}
                        </td>

                        {/* Previous */}
                        <td className="py-3.5 px-4 text-slate-500">
                          {previousValue !==
                            undefined &&
                          previousValue !== null ? (
                            <div className="flex flex-col gap-0.5">
                              <span>
                                {previousValue}{' '}
                                {unit}
                              </span>

                              {result?.previous_status && (
                                <span className="text-[10px] font-semibold text-slate-400">
                                  Previous:{' '}
                                  {
                                    result.previous_status
                                  }
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 text-xs italic">
                              Baseline
                            </span>
                          )}
                        </td>

                        {/* Provenance */}
                        <td className="py-3.5 px-4 text-right">
                          <button
                            type="button"
                            onClick={() =>
                              onInspectEvidence?.(
                                result
                              )
                            }
                            disabled={
                              !onInspectEvidence
                            }
                            className="px-2.5 py-1 rounded-lg text-primary hover:bg-primary/10 text-xs font-semibold inline-flex items-center gap-1 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                            title="View OCR page and source text provenance"
                          >
                            <FileText size={14} />
                            <span>Source</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Empty filter state */}
            {filteredResults.length === 0 && (
              <div className="p-10 text-center">
                <AlertCircle
                  size={28}
                  className="mx-auto text-slate-300 mb-2"
                />

                <p className="text-xs font-semibold text-slate-500">
                  No results match this filter.
                </p>

                <button
                  type="button"
                  onClick={() => setFilter('ALL')}
                  className="mt-2 text-xs font-semibold text-primary hover:underline"
                >
                  Show all results
                </button>
              </div>
            )}
          </div>

          {/* Evidence note */}
          <div className="flex items-start gap-2 px-1 text-[10px] text-slate-400">
            <Info
              size={13}
              className="shrink-0 mt-0.5"
            />

            <span>
              Status, values, and reference intervals shown
              here are derived from the structured report
              processing pipeline. Use the Source action to
              inspect the underlying report provenance.
            </span>
          </div>
        </>
      )}
    </div>
  );
}