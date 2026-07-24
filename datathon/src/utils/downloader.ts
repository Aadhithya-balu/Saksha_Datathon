import { API_BASE_URL, getStoredTokens } from '../services/api';

export const downloadSecureDossier = async (title: string, data: Record<string, any>, watermark: string, format: 'pdf' | 'docx' | 'txt' | 'csv' = 'pdf') => {
  try {
    const tokens = getStoredTokens();
    const response = await fetch(`${API_BASE_URL}/reports/dossier/export/${format}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(tokens?.accessToken ? { Authorization: `Bearer ${tokens.accessToken}` } : {})
      },
      body: JSON.stringify({
        title,
        data,
        watermark
      })
    });

    if (!response.ok) {
      throw new Error(`Failed to generate ${format.toUpperCase()}`);
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const element = document.createElement('a');
    element.href = url;
    element.download = `ksp_${title.toLowerCase().replace(/\s+/g, '_')}.${format}`;
    document.body.appendChild(element);
    element.click();
    setTimeout(() => {
      document.body.removeChild(element);
      URL.revokeObjectURL(url);
    }, 300);
  } catch (error) {
    console.error('Download error:', error);
    alert(`Failed to download ${format.toUpperCase()} dossier`);
  }
};
