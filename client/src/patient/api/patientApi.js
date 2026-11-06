import axios from 'axios';

const API_BASE =
  import.meta.env.VITE_API_URL ||
  'http://localhost:8000';

const PATIENT_API =
  `${API_BASE}/api/patient`;

const patientClient = axios.create({
  baseURL: PATIENT_API,
  timeout: 120000,
  withCredentials: true,
});

export const patientApi = {
   getPatients: async () => {
    const response = await patientClient.get(
      '/patients'
    );

    return response.data;
  },

  getPatientProfile: async (patientId) => {
    const response = await patientClient.get(
      `/patients/${encodeURIComponent(patientId)}`
    );

    return response.data;
  },

  getReports: async (patientId) => {
    const response = await patientClient.get(
      '/reports',
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
      }
    );

    return response.data;
  },

  getReportDetail: async (
    patientId,
    reportId
  ) => {
    if (!reportId) {
      throw new Error('Report ID is required.');
    }

    const response = await patientClient.get(
      `/reports/${encodeURIComponent(reportId)}`,
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
      }
    );

    return response.data;
  },

  getReportResults: async (
    patientId,
    reportId
  ) => {
    if (!reportId) {
      throw new Error('Report ID is required.');
    }

    const response = await patientClient.get(
      `/reports/${encodeURIComponent(reportId)}/results`,
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
      }
    );

    return response.data;
  },

  uploadReport: async (
    patientId,
    file,
    reportCategory = 'Diagnostic Panel'
  ) => {
    if (!file) {
      throw new Error(
        'A report file is required.'
      );
    }
    
    const formData = new FormData();

    if (patientId) {
      formData.append(
        'patient_id',
        patientId
      );
    }

    formData.append(
      'file',
      file,
      file.name
    );

    formData.append(
      'report_category',
      reportCategory
    );
    const response = await patientClient.post(
      '/reports/upload',
      formData,
      {
        timeout: 180000,
      }
    );

    return response.data;
  },

   getTrends: async (patientId) => {
    const response = await patientClient.get(
      '/trends',
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
      }
    );

    return response.data;
  },

  getSummary: async (patientId) => {
    const response = await patientClient.get(
      '/summary',
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
      }
    );

    return response.data;
  },

  generateAIReport: async (
    patientId,
    reportId
  ) => {
    if (!reportId) {
      throw new Error('Report ID is required.');
    }

    const response = await patientClient.post(
      `/reports/${encodeURIComponent(reportId)}/generate`,
      null,
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
        timeout: 180000,
      }
    );

    return response.data;
  },

 
  getEvidence: async (
    patientId,
    reportId
  ) => {
    if (!reportId) {
      throw new Error('Report ID is required.');
    }

    const response = await patientClient.get(
      `/reports/${encodeURIComponent(reportId)}/evidence`,
      {
        params: patientId
          ? { patient_id: patientId }
          : undefined,
      }
    );

    return response.data;
  },
  chat: async (
    patientId,
    query,
    reportId = null
  ) => {
    if (!query || !String(query).trim()) {
      throw new Error(
        'A patient question is required.'
      );
    }

    const response = await patientClient.post(
      '/chat',
      {
      
        ...(patientId
          ? { patient_id: patientId }
          : {}),
        query: String(query).trim(),
        report_id: reportId || null,
      },
      {
        timeout: 120000,
      }
    );
    

    return response.data;
  },
};


export default patientApi;