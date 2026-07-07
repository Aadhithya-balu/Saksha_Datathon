export const downloadSecureDossier = (title: string, data: Record<string, any>, watermark: string) => {
  const line = '='.repeat(60);
  const border = '-'.repeat(60);
  
  const content = `${line}
KARNATAKA STATE POLICE - CRYPTOGRAPHIC INTEL DOSSIER
${line}
CLASSIFICATION : CONFIDENTIAL / STATE RECORDS
STAMP STATUS   : DIGITAL SIGNATURE VERIFIED
WATERMARK BLOCK: [ ${watermark.toUpperCase()} ]
EXPORT DATE    : ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}
DEVICE SOURCE  : BNG-INTEL-NODE-08
AUDIT HASH     : SEC-SHA256:${Math.random().toString(36).substring(2, 15).toUpperCase()}
${border}

DOSSIER TARGET: ${title.toUpperCase()}

${Object.entries(data)
  .map(([key, val]) => {
    const formattedKey = key.replace(/([A-Z])/g, ' $1').toUpperCase();
    if (typeof val === 'object' && val !== null) {
      return `${formattedKey}:\n${Object.entries(val)
        .map(([k, v]) => `  - ${k.toUpperCase()}: ${v}`)
        .join('\n')}`;
    }
    return `${formattedKey}: ${val}`;
  })
  .join('\n\n')}

${border}
SECURITY COMPLIANCE ACT NOTICE:
THIS INFORMATION IS REGULATED UNDER SECTION 4 OF THE SECURE SYSTEMS
ACT OF KARNATAKA. UNAUTHORIZED SHARING REPLICATING AND VIEWING
IS STRICTLY PUNISHABLE BY CIVIL PENALTIES AND REMOVAL.
${line}`;

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  
  const element = document.createElement('a');
  element.href = url;
  element.download = `ksp_${title.toLowerCase().replace(/\s+/g, '_')}_dossier.txt`;
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
  URL.revokeObjectURL(url);
};
