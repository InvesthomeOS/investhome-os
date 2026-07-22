'use client';

import { useEffect, useState } from 'react';

import { SignatureDetailView } from '../../_components/signatures/signing-flow';

export default function SignatureDetailPage({
  params,
}: {
  params: Promise<{ signatureRequestId: string }>;
}) {
  const [id, setId] = useState<string | null>(null);

  useEffect(() => {
    void params.then((p) => setId(p.signatureRequestId));
  }, [params]);

  if (!id) return null;
  return <SignatureDetailView signatureRequestId={id} />;
}
