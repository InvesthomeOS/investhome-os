'use client';

interface ProposalPreviewProps {
  html: string;
  proposalNumber: string;
}

export function ProposalPreview({ html, proposalNumber }: ProposalPreviewProps) {
  return (
    <div className="proposal-preview">
      <div className="proposal-preview-toolbar">
        <span>{proposalNumber}</span>
        <button type="button" onClick={() => window.print()}>
          Print
        </button>
      </div>
      <iframe
        title={`Proposal ${proposalNumber}`}
        srcDoc={html}
        className="proposal-preview-frame"
        sandbox="allow-same-origin"
      />
    </div>
  );
}
