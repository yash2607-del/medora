import React, { useEffect, useMemo, useState } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  CheckCircle2,
  AlertCircle,
  Calendar
} from 'lucide-react';

export default function TrendsChart({ trends = [] }) {
  /*
   * Only use trends that actually contain numeric historical readings.
   * This prevents metadata such as "Age / Gender" or malformed extraction
   * rows from appearing as medical longitudinal trends.
   */
  const usableTrends = useMemo(() => {
    return (trends || [])
      .map((trend) => {
        const historyPoints = (trend.history_points || []).filter(
          (point) =>
            point &&
            point.value !== null &&
            point.value !== undefined &&
            point.value !== '' &&
            Number.isFinite(Number(point.value))
        );

        return {
          ...trend,
          history_points: historyPoints
        };
      })
      .filter((trend) => trend.history_points.length > 0);
  }, [trends]);

  const multiReadingTrends = useMemo(
    () => usableTrends.filter((trend) => trend.history_points.length > 1),
    [usableTrends]
  );

  const [selectedTestName, setSelectedTestName] = useState(null);

  /*
   * Select the first real multi-reading trend when data changes.
   */
  useEffect(() => {
    if (multiReadingTrends.length === 0) {
      setSelectedTestName(null);
      return;
    }

    const stillExists = multiReadingTrends.some(
      (trend) => trend.test_name === selectedTestName
    );

    if (!stillExists) {
      setSelectedTestName(multiReadingTrends[0].test_name);
    }
  }, [multiReadingTrends, selectedTestName]);

  /*
   * Nothing usable at all.
   */
  if (usableTrends.length === 0) {
    return (
      <div className="p-10 bg-white rounded-3xl border border-slate-200 shadow-sm text-center">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400">
          <Activity size={26} />
        </div>

        <h3 className="mt-4 text-base font-bold text-slate-900">
          No trend data available
        </h3>

        <p className="mt-2 text-xs leading-relaxed text-slate-500 max-w-md mx-auto">
          Upload a report containing measurable laboratory results. Uploading
          multiple reports for the same patient enables longitudinal comparison.
        </p>
      </div>
    );
  }

  /*
   * There are results, but no test has multiple readings yet.
   */
  if (multiReadingTrends.length === 0) {
    return (
      <div className="space-y-5">
        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Calendar size={19} />
            </div>

            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-primary">
                Longitudinal Intelligence
              </span>

              <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                Longitudinal Trends
              </h3>

              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Trend comparison becomes available when the same laboratory
                test appears in more than one report.
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle size={17} className="text-amber-500" />
            <h4 className="text-sm font-bold text-slate-900">
              Current measurable results
            </h4>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {usableTrends.map((trend) => {
              const latest =
                trend.history_points[trend.history_points.length - 1];

              return (
                <div
                  key={trend.test_name}
                  className="p-4 rounded-2xl border border-slate-200 bg-slate-50"
                >
                  <div className="text-xs font-bold text-slate-800">
                    {trend.test_name}
                  </div>

                  <div className="mt-2 text-lg font-black text-slate-900">
                    {latest?.value}
                    {trend.unit && (
                      <span className="ml-1 text-xs font-normal text-slate-500">
                        {trend.unit}
                      </span>
                    )}
                  </div>

                  <div className="mt-1 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      {latest?.date || 'Current report'}
                    </span>

                    <StatusBadge status={latest?.status} />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-5 p-4 rounded-2xl bg-blue-50 border border-blue-100 text-xs text-blue-800 leading-relaxed">
            <strong>Next step:</strong> Upload another report for this patient
            with the same tests to activate deterministic longitudinal trend
            analysis.
          </div>
        </div>
      </div>
    );
  }

  const activeTrend =
    multiReadingTrends.find(
      (trend) => trend.test_name === selectedTestName
    ) || multiReadingTrends[0];

  const historyPoints = activeTrend.history_points || [];

  const numericValues = historyPoints
    .map((point) => Number(point.value))
    .filter((value) => Number.isFinite(value));

  const referenceLow = Number(activeTrend.reference_low);
  const referenceHigh = Number(activeTrend.reference_high);

  const hasReferenceLow = Number.isFinite(referenceLow);
  const hasReferenceHigh = Number.isFinite(referenceHigh);

  const rawMin = Math.min(
    ...numericValues,
    hasReferenceLow ? referenceLow : numericValues[0]
  );

  const rawMax = Math.max(
    ...numericValues,
    hasReferenceHigh ? referenceHigh : numericValues[0]
  );

  const padding =
    rawMax === rawMin
      ? Math.max(Math.abs(rawMax) * 0.1, 1)
      : (rawMax - rawMin) * 0.1;

  const minVal = rawMin - padding;
  const maxVal = rawMax + padding;

  const getTrendBadge = (trend) => {
    switch (trend) {
      case 'improving':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <TrendingDown size={14} />
            Improving
          </span>
        );

      case 'worsening':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-red-50 text-red-700 border border-red-200">
            <TrendingUp size={14} />
            Worsening
          </span>
        );

      case 'stable':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
            <Minus size={14} />
            Stable
          </span>
        );

      case 'fluctuating':
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">
            <Activity size={14} />
            Fluctuating
          </span>
        );

      default:
        return (
          <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
            <Activity size={14} />
            {trend || 'Not classified'}
          </span>
        );
    }
  };

  const getPersistenceBadge = (persistence) => {
    switch (persistence) {
      case 'persistently_abnormal':
        return (
          <span className="text-xs font-semibold text-red-700 bg-red-50 px-2.5 py-1.5 rounded-lg border border-red-200">
            Persistently Abnormal
          </span>
        );

      case 'newly_abnormal':
        return (
          <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2.5 py-1.5 rounded-lg border border-amber-200">
            Newly Abnormal
          </span>
        );

      case 'previously_abnormal_now_normal':
      case 'resolved':
        return (
          <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1.5 rounded-lg border border-emerald-200">
            Resolved / Normalized
          </span>
        );

      default:
        return (
          <span className="text-xs font-semibold text-slate-600 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
            {persistence || 'No persistence classification'}
          </span>
        );
    }
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return 'N/A';

    const number = Number(value);

    if (!Number.isFinite(number)) return String(value);

    return Number.isInteger(number)
      ? String(number)
      : number.toFixed(2).replace(/\.?0+$/, '');
  };

  const getBarHeight = (value) => {
    const number = Number(value);

    if (!Number.isFinite(number)) return 0;

    const denominator = maxVal - minVal || 1;

    return Math.min(
      Math.max(((number - minVal) / denominator) * 100, 8),
      100
    );
  };

  const getStatusClass = (status) => {
    switch (status) {
      case 'HIGH':
        return 'text-red-600';

      case 'LOW':
        return 'text-amber-600';

      case 'NORMAL':
        return 'text-emerald-600';

      default:
        return 'text-slate-500';
    }
  };

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">

          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-primary px-2.5 py-1 rounded-full bg-primary/10">
              Longitudinal Intelligence
            </span>

            <h3 className="text-xl font-extrabold text-slate-900 mt-2">
              Comparative Test Trends Over Time
            </h3>

            <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
              Values and status classifications are derived from stored
              laboratory results. Trend direction is calculated
              deterministically by the backend.
            </p>
          </div>

          {/* Test Selector */}
          <div className="flex flex-wrap gap-2 max-w-xl">
            {multiReadingTrends.map((trend) => (
              <button
                key={trend.test_name}
                onClick={() => setSelectedTestName(trend.test_name)}
                className={`px-3 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer border ${
                  activeTrend.test_name === trend.test_name
                    ? 'bg-primary text-white border-primary shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-primary/40 hover:bg-slate-50'
                }`}
              >
                {trend.test_name}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Trend Card */}
      <div className="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm space-y-6">

        {/* Test Heading */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-5 border-b border-slate-100">

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-2xl font-black text-slate-900">
                {activeTrend.test_name}
              </h4>

              {activeTrend.unit && (
                <span className="text-sm font-normal text-slate-500">
                  ({activeTrend.unit})
                </span>
              )}
            </div>

            <div className="text-xs text-slate-500 mt-2">
              Reference Interval:{' '}
              <span className="font-semibold text-slate-700">
                {activeTrend.reference_text ||
                  (hasReferenceLow && hasReferenceHigh
                    ? `${activeTrend.reference_low} - ${activeTrend.reference_high}`
                    : 'Not available')}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {getTrendBadge(activeTrend.trend)}
            {getPersistenceBadge(activeTrend.persistence)}
          </div>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

          <MetricCard
            label="Baseline"
            value={activeTrend.earliest_value}
            unit={activeTrend.unit}
            footer={activeTrend.earliest_date}
          />

          <MetricCard
            label="Previous Reading"
            value={activeTrend.previous_value}
            unit={activeTrend.unit}
            footer={activeTrend.previous_date || 'No prior reading'}
          />

          <MetricCard
            label="Current Reading"
            value={activeTrend.latest_value}
            unit={activeTrend.unit}
            footer={
              <span className={getStatusClass(activeTrend.current_status)}>
                Status: {activeTrend.current_status || 'UNKNOWN'}
              </span>
            }
          />

          <MetricCard
            label="Delta Change"
            value={
              activeTrend.absolute_change !== null &&
              activeTrend.absolute_change !== undefined
                ? `${Number(activeTrend.absolute_change) > 0 ? '+' : ''}${formatNumber(activeTrend.absolute_change)}`
                : 'N/A'
            }
            unit={activeTrend.unit}
            footer={
              activeTrend.percentage_change !== null &&
              activeTrend.percentage_change !== undefined
                ? `${formatNumber(activeTrend.percentage_change)}% change`
                : 'Percentage change unavailable'
            }
          />

        </div>

        {/* Timeline Chart */}
        <div className="p-6 bg-slate-50 rounded-2xl border border-slate-200">

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-6">
            <div>
              <div className="text-xs font-bold text-slate-700">
                Historical Progression
              </div>

              <div className="text-[11px] text-slate-400 mt-0.5">
                {historyPoints.length} chronological readings
              </div>
            </div>

            <div className="text-[11px] text-slate-500">
              Reference:{' '}
              {hasReferenceLow && hasReferenceHigh
                ? `${activeTrend.reference_low} - ${activeTrend.reference_high}`
                : 'Not available'}{' '}
              {activeTrend.unit || ''}
            </div>
          </div>

          <div className="overflow-x-auto">
            <div
              className="flex items-end gap-6 h-64 min-w-[520px] px-3"
              role="img"
              aria-label={`Longitudinal trend for ${activeTrend.test_name}`}
            >
              {historyPoints.map((point, index) => {
                const numericValue = Number(point.value);

                if (!Number.isFinite(numericValue)) {
                  return null;
                }

                const heightPct = getBarHeight(numericValue);

                const isHigh = point.status === 'HIGH';
                const isLow = point.status === 'LOW';

                const barClass = isHigh
                  ? 'bg-red-500'
                  : isLow
                    ? 'bg-amber-500'
                    : 'bg-emerald-500';

                return (
                  <div
                    key={`${point.date || 'point'}-${index}`}
                    className="flex-1 min-w-[72px] flex flex-col items-center h-full justify-end"
                  >
                    <div className="text-xs font-bold text-slate-800 mb-2">
                      {formatNumber(numericValue)}
                    </div>

                    <div className="w-full max-w-[52px] h-full bg-slate-200 rounded-t-xl overflow-hidden flex items-end">
                      <div
                        style={{ height: `${heightPct}%` }}
                        className={`w-full ${barClass} rounded-t-xl transition-all duration-500`}
                      />
                    </div>

                    <div className="mt-2 text-[10px] font-semibold text-slate-500 text-center whitespace-nowrap">
                      {point.date || 'Unknown date'}
                    </div>

                    <div
                      className={`mt-0.5 text-[10px] font-bold ${getStatusClass(
                        point.status
                      )}`}
                    >
                      {point.status || 'UNKNOWN'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Deterministic Finding */}
        <div className="p-4 bg-blue-50 border border-blue-100 rounded-2xl flex items-start gap-3">
          <CheckCircle2
            size={18}
            className="text-primary shrink-0 mt-0.5"
          />

          <div className="text-xs text-slate-700 leading-relaxed">
            <strong className="text-primary font-bold">
              Deterministic Finding:
            </strong>{' '}
            {activeTrend.deterministic_statement ||
              'No deterministic finding is available for this trend.'}
          </div>
        </div>

        {/* Data provenance */}
        <div className="pt-2 flex items-start gap-2 text-[11px] text-slate-400">
          <AlertCircle size={14} className="shrink-0 mt-0.5" />

          <span>
            Trend calculations are based on the laboratory values and dates
            returned by the patient intelligence backend. This visualization
            does not independently modify or infer medical values.
          </span>
        </div>
      </div>
    </div>
  );
}


/* ------------------------------------------------------------------ */
/* Metric Card                                                         */
/* ------------------------------------------------------------------ */

function MetricCard({ label, value, unit, footer }) {
  return (
    <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200">

      <span className="text-xs text-slate-500">
        {label}
      </span>

      <div className="text-lg font-bold text-slate-900 mt-1">
        {value !== null && value !== undefined ? value : 'N/A'}

        {unit && (
          <span className="ml-1 text-xs font-normal text-slate-500">
            {unit}
          </span>
        )}
      </div>

      <div className="text-[11px] text-slate-400 mt-1">
        {footer || '—'}
      </div>
    </div>
  );
}


/* ------------------------------------------------------------------ */
/* Status Badge                                                        */
/* ------------------------------------------------------------------ */

function StatusBadge({ status }) {
  if (status === 'HIGH') {
    return (
      <span className="text-[10px] font-bold text-red-700 bg-red-50 border border-red-200 px-2 py-1 rounded-lg">
        HIGH
      </span>
    );
  }

  if (status === 'LOW') {
    return (
      <span className="text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-1 rounded-lg">
        LOW
      </span>
    );
  }

  if (status === 'NORMAL') {
    return (
      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-lg">
        NORMAL
      </span>
    );
  }

  return (
    <span className="text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-2 py-1 rounded-lg">
      UNKNOWN
    </span>
  );
}