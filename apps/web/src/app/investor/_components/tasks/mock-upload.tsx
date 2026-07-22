'use client';

import { useCallback, useState } from 'react';

const ACCEPTED_TYPES = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'image/png', 'image/jpeg'];
const ACCEPTED_LABELS = 'PDF, DOCX, PNG, JPEG';

interface MockUploadProps {
  label?: string;
  onMockUpload?: (fileName: string, fileType: string) => void;
}

export function MockUpload({ label = 'Upload document', onMockUpload }: MockUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [uploaded, setUploaded] = useState<string[]>([]);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      const names: string[] = [];
      for (const file of Array.from(files)) {
        if (ACCEPTED_TYPES.includes(file.type) || file.name.match(/\.(pdf|docx|png|jpe?g)$/i)) {
          names.push(file.name);
          onMockUpload?.(file.name, file.type);
        }
      }
      if (names.length > 0) {
        setUploaded((prev) => [...prev, ...names]);
      }
    },
    [onMockUpload],
  );

  return (
    <div className="inv-mock-upload">
      <p className="inv-mock-upload__label">{label}</p>
      <div
        className={`inv-mock-upload__dropzone${dragOver ? ' inv-mock-upload__dropzone--active' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        role="button"
        tabIndex={0}
        aria-label={`Upload area. Accepted formats: ${ACCEPTED_LABELS}`}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            document.getElementById('mock-upload-input')?.click();
          }
        }}
      >
        <span className="inv-mock-upload__icon" aria-hidden="true">
          ↑
        </span>
        <p>Drag & drop or click to browse</p>
        <p className="inv-mock-upload__hint">{ACCEPTED_LABELS} — UI only, no storage</p>
        <input
          id="mock-upload-input"
          type="file"
          className="inv-mock-upload__input"
          accept=".pdf,.docx,.png,.jpg,.jpeg"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          aria-hidden="true"
          tabIndex={-1}
        />
      </div>
      {uploaded.length > 0 ? (
        <ul className="inv-mock-upload__files" aria-label="Uploaded files (mock)">
          {uploaded.map((name) => (
            <li key={name}>📎 {name} (mock)</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
