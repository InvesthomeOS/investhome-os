import { getCspNonce } from '@/lib/security/csp-nonce';

export async function JsonLdScript({ data }: { data: unknown }) {
  const nonce = await getCspNonce();
  return (
    <script
      type="application/ld+json"
      nonce={nonce}
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
