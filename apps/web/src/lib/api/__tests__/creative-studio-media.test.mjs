/**
 * Creative Studio Media Library API client tests.
 * Run: node --test src/lib/api/__tests__/creative-studio-media.test.mjs
 *
 * Mirrors query/upload/content helpers from creative-studio.ts
 * (Node cannot resolve TS path aliases without a bundler).
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, beforeEach, afterEach } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, '../creative-studio.ts'), 'utf8');

const API_BASE = 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status, code, requestId, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

function parseApiErrorBody(body, status) {
  const requestId = body.meta?.request_id ?? null;
  const code = body.error?.code;
  let message = `Request failed with status ${status}`;
  if (typeof body.detail === 'string') message = body.detail;
  else if (body.error?.message) message = body.error.message;
  else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
  return new ApiError(message, status, code, requestId, body.details);
}

function buildMediaQuery(params) {
  const search = new URLSearchParams();
  if (params?.q) search.set('q', params.q);
  if (params?.folder_id) search.set('folder_id', params.folder_id);
  if (params?.tag) search.set('tag', params.tag);
  if (params?.include_archived) search.set('include_archived', 'true');
  if (params?.page != null) search.set('page', String(params.page));
  if (params?.page_size != null) search.set('page_size', String(params.page_size));
  if (params?.parent_id) search.set('parent_id', params.parent_id);
  const query = search.toString();
  return query ? `?${query}` : '';
}

async function throwMediaApiError(response) {
  const requestId = response.headers.get('X-Request-Id');
  let message = `Request failed with status ${response.status}`;
  let code;
  let details;
  try {
    const body = await response.json();
    const parsed = parseApiErrorBody(body, response.status);
    message = parsed.message;
    code = parsed.code;
    details = parsed.details;
  } catch {
    // keep default
  }
  throw new ApiError(message, response.status, code, requestId, details);
}

function createClient(fetchImpl) {
  async function apiFetch(path, init) {
    const response = await fetchImpl(`${API_BASE}${path}`, {
      ...init,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) await throwMediaApiError(response);
    if (response.status === 204) return undefined;
    return response.json();
  }

  return {
    listCreativeStudioMediaAssets(params) {
      return apiFetch(`/creative-studio/media/assets${buildMediaQuery(params)}`);
    },
    searchCreativeStudioMediaAssets(params) {
      return apiFetch(`/creative-studio/media/search${buildMediaQuery(params)}`);
    },
    getCreativeStudioMediaAsset(assetId) {
      return apiFetch(`/creative-studio/media/assets/${assetId}`);
    },
    async uploadCreativeStudioMediaAsset(input) {
      const form = new FormData();
      form.append('file', input.file);
      if (input.folder_id) form.append('folder_id', input.folder_id);
      if (input.tags != null) {
        form.append(
          'tags',
          Array.isArray(input.tags) ? JSON.stringify(input.tags) : input.tags,
        );
      }
      if (input.company_id) form.append('company_id', input.company_id);
      if (input.linked_project_id) form.append('linked_project_id', input.linked_project_id);

      const response = await fetchImpl(`${API_BASE}/creative-studio/media/upload`, {
        method: 'POST',
        credentials: 'include',
        body: form,
      });
      if (!response.ok) await throwMediaApiError(response);
      return response.json();
    },
    getCreativeStudioMediaContentUrl(assetId) {
      return `${API_BASE}/creative-studio/media/assets/${assetId}/content`;
    },
    async fetchCreativeStudioMediaBlob(assetId) {
      const response = await fetchImpl(
        `${API_BASE}/creative-studio/media/assets/${assetId}/content`,
        { credentials: 'include' },
      );
      if (!response.ok) await throwMediaApiError(response);
      return response.blob();
    },
    deleteCreativeStudioMediaAsset(assetId) {
      return apiFetch(`/creative-studio/media/assets/${assetId}`, { method: 'DELETE' });
    },
  };
}

function jsonResponse(status, body, headers = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get(name) {
        return headers[name.toLowerCase()] ?? null;
      },
    },
    async json() {
      return body;
    },
    async blob() {
      return new Blob([typeof body === 'string' ? body : JSON.stringify(body)], {
        type: headers['content-type'] ?? 'application/octet-stream',
      });
    },
  };
}

describe('source exports', () => {
  const methods = [
    'listCreativeStudioMediaAssets',
    'searchCreativeStudioMediaAssets',
    'getCreativeStudioMediaAsset',
    'uploadCreativeStudioMediaAsset',
    'getCreativeStudioMediaContentUrl',
    'fetchCreativeStudioMediaBlob',
    'listCreativeStudioMediaFolders',
    'createCreativeStudioMediaFolder',
    'updateCreativeStudioMediaTags',
    'deleteCreativeStudioMediaAsset',
  ];

  for (const name of methods) {
    it(`exports ${name}`, () => {
      assert.match(source, new RegExp(`export (async )?function ${name}`));
    });
  }

  it('declares media types', () => {
    for (const typeName of [
      'CreativeStudioMediaAsset',
      'CreativeStudioMediaAssetListResponse',
      'CreativeStudioMediaFolder',
      'CreativeStudioMediaUploadInput',
      'CreativeStudioMediaSearchParams',
    ]) {
      assert.match(source, new RegExp(`export type ${typeName}`));
    }
  });

  it('upload uses FormData without JSON Content-Type', () => {
    assert.match(source, /new FormData\(\)/);
    assert.match(source, /\/creative-studio\/media\/upload/);
    assert.doesNotMatch(
      source.slice(source.indexOf('uploadCreativeStudioMediaAsset')),
      /Content-Type': 'application\/json'/,
    );
  });
});

describe('buildMediaQuery / search params', () => {
  it('builds empty query when no params', () => {
    assert.equal(buildMediaQuery(), '');
    assert.equal(buildMediaQuery({}), '');
  });

  it('serializes list and search params', () => {
    const q = buildMediaQuery({
      q: 'hero',
      folder_id: 'fold-1',
      tag: 'landing',
      include_archived: true,
      page: 2,
      page_size: 25,
    });
    const params = new URLSearchParams(q.slice(1));
    assert.equal(params.get('q'), 'hero');
    assert.equal(params.get('folder_id'), 'fold-1');
    assert.equal(params.get('tag'), 'landing');
    assert.equal(params.get('include_archived'), 'true');
    assert.equal(params.get('page'), '2');
    assert.equal(params.get('page_size'), '25');
  });
});

describe('media client with mocked fetch', () => {
  let calls;
  let client;

  beforeEach(() => {
    calls = [];
  });

  afterEach(() => {
    calls = [];
  });

  it('listCreativeStudioMediaAssets parses items/total/page', async () => {
    client = createClient(async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, {
        items: [{ id: 'a1', filename: 'hero.png' }],
        total: 1,
        page: 1,
        page_size: 50,
      });
    });

    const result = await client.listCreativeStudioMediaAssets({ tag: 'hero', page: 1 });
    assert.equal(result.total, 1);
    assert.equal(result.items[0].id, 'a1');
    assert.equal(result.page, 1);
    assert.equal(result.page_size, 50);
    assert.match(calls[0].url, /\/creative-studio\/media\/assets\?tag=hero&page=1$/);
    assert.equal(calls[0].init.credentials, 'include');
  });

  it('searchCreativeStudioMediaAssets sends q', async () => {
    client = createClient(async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(200, { items: [], total: 0, page: 1, page_size: 50 });
    });

    await client.searchCreativeStudioMediaAssets({ q: 'banner', folder_id: 'f1' });
    assert.match(calls[0].url, /\/creative-studio\/media\/search\?/);
    const params = new URL(calls[0].url).searchParams;
    assert.equal(params.get('q'), 'banner');
    assert.equal(params.get('folder_id'), 'f1');
  });

  it('getCreativeStudioMediaAsset returns asset', async () => {
    client = createClient(async (url) => {
      calls.push({ url });
      return jsonResponse(200, { id: 'asset-9', filename: 'x.png', content_type: 'image/png' });
    });

    const asset = await client.getCreativeStudioMediaAsset('asset-9');
    assert.equal(asset.id, 'asset-9');
    assert.match(calls[0].url, /\/creative-studio\/media\/assets\/asset-9$/);
  });

  it('uploadCreativeStudioMediaAsset sends multipart FormData', async () => {
    client = createClient(async (url, init) => {
      calls.push({ url, init });
      return jsonResponse(201, {
        id: 'up-1',
        filename: 'smoke.png',
        content_type: 'image/png',
        file_size: 12,
      });
    });

    const file = new Blob([Uint8Array.from([1, 2, 3])], { type: 'image/png' });
    const asset = await client.uploadCreativeStudioMediaAsset({
      file,
      folder_id: 'fold-2',
      tags: ['hero', 'landing'],
      company_id: 'co-1',
      linked_project_id: 'proj-1',
    });

    assert.equal(asset.id, 'up-1');
    assert.equal(calls[0].url, `${API_BASE}/creative-studio/media/upload`);
    assert.equal(calls[0].init.method, 'POST');
    assert.equal(calls[0].init.credentials, 'include');
    assert.ok(calls[0].init.body instanceof FormData);
    assert.equal(calls[0].init.headers?.['Content-Type'], undefined);
    assert.equal(calls[0].init.body.get('folder_id'), 'fold-2');
    assert.equal(calls[0].init.body.get('tags'), JSON.stringify(['hero', 'landing']));
    assert.equal(calls[0].init.body.get('company_id'), 'co-1');
    assert.equal(calls[0].init.body.get('linked_project_id'), 'proj-1');
    assert.ok(calls[0].init.body.get('file'));
  });

  it('getCreativeStudioMediaContentUrl is stable absolute URL', () => {
    client = createClient(async () => jsonResponse(200, {}));
    assert.equal(
      client.getCreativeStudioMediaContentUrl('abc'),
      `${API_BASE}/creative-studio/media/assets/abc/content`,
    );
  });

  it('fetchCreativeStudioMediaBlob returns Blob without object URL', async () => {
    const bytes = Uint8Array.from([137, 80, 78, 71]);
    client = createClient(async (url, init) => {
      calls.push({ url, init });
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'image/png' },
        async json() {
          return {};
        },
        async blob() {
          return new Blob([bytes], { type: 'image/png' });
        },
      };
    });

    const blob = await client.fetchCreativeStudioMediaBlob('blob-1');
    assert.equal(blob.type, 'image/png');
    assert.equal(blob.size, 4);
    assert.match(calls[0].url, /\/assets\/blob-1\/content$/);
    assert.equal(calls[0].init.credentials, 'include');
    assert.doesNotMatch(source, /createObjectURL/);
  });

  it('propagates ApiError from failed responses', async () => {
    client = createClient(async () =>
      jsonResponse(
        403,
        { detail: 'Forbidden media access', error: { code: 'forbidden', message: 'Forbidden media access' } },
        { 'x-request-id': 'req-42' },
      ),
    );

    await assert.rejects(
      () => client.getCreativeStudioMediaAsset('missing'),
      (err) => {
        assert.equal(err.name, 'ApiError');
        assert.equal(err.status, 403);
        assert.equal(err.message, 'Forbidden media access');
        assert.equal(err.code, 'forbidden');
        assert.equal(err.requestId, 'req-42');
        return true;
      },
    );
  });

  it('upload propagates ApiError', async () => {
    client = createClient(async () =>
      jsonResponse(413, { detail: 'creative_studio.media.errors.file_too_large' }),
    );

    await assert.rejects(
      () =>
        client.uploadCreativeStudioMediaAsset({
          file: new Blob([Uint8Array.from([1])], { type: 'image/png' }),
        }),
      (err) => {
        assert.equal(err.status, 413);
        assert.equal(err.message, 'creative_studio.media.errors.file_too_large');
        return true;
      },
    );
  });
});
