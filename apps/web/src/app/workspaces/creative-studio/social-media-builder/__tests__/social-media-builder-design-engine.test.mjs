/**
 * Social Media Builder AI Design Engine (Phase 1) client helpers.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-design-engine.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const apiClientPath = join(here, '../../../../../lib/api/creative-studio.ts');

const TEMPLE_UUID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const COVER_UUID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

describe('source modules', () => {
  it('ships design engine module + API client endpoint', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-design-engine.ts')), true);
    const client = readFileSync(apiClientPath, 'utf8');
    assert.match(client, /export async function generateSocialDesign/);
    assert.match(client, /\/ai\/creative-studio\/social\/design/);
    assert.match(client, /SocialDesignRequest/);
    assert.match(client, /SocialDesignResponse/);
    assert.doesNotMatch(client, /unsplash/i);
  });
});

describe('workspace wires design engine (same canvas)', () => {
  it('calls generateSocialDesign and applies posts to canvas', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /generateSocialDesign/);
    assert.match(workspace, /buildSocialDesignRequest/);
    assert.match(workspace, /applyDesignResponseToPosts/);
    assert.match(workspace, /toDesignGenerationMeta/);
    assert.match(workspace, /serializeGenerationMetaForDraft/);
    assert.match(workspace, /setPosts\(applied\.posts\)/);
    assert.doesNotMatch(workspace, /runAiDemo/);
    assert.doesNotMatch(workspace, /images\.unsplash/);
    assert.match(workspace, /never Unsplash/);
  });

  it('keeps single AI command input + manual editor', () => {
    const drawers = readSmb('social-media-builder-rail-drawers.tsx');
    assert.match(drawers, /data-testid="smb-ai-prompt"/);
    assert.match(drawers, /data-testid="smb-ai-generate"/);
    assert.match(drawers, /onGenerate\(instruction\)/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /P0_BOTTOM_ACTIONS/);
    assert.match(workspace, /SmbArtboardElements/);
  });
});

describe('design request builder logic (inlined mirror)', () => {
  const EDIT_HINTS = [
    'değiştir',
    'güncelle',
    'edit',
    'update',
    'move',
    'color',
    'renk',
    'cta',
    'taşı',
    'yukarı',
    'beyaz',
  ];

  function inferDesignMode(instruction, posts, preferred) {
    if (preferred === 'create' || preferred === 'edit') {
      if (preferred === 'edit' && posts.length === 0) return 'create';
      return preferred;
    }
    const instr = (instruction || '').toLowerCase();
    if (posts.length > 0 && EDIT_HINTS.some((h) => instr.includes(h))) return 'edit';
    if (posts.length === 0) return 'create';
    return 'create';
  }

  function buildSocialDesignRequest(input) {
    const linked = typeof input.linkedProjectId === 'string' ? input.linkedProjectId.trim() : '';
    if (!linked || !UUID_RE.test(linked)) return { ok: false, reason: 'missing_project' };
    const instruction = (input.instruction || '').trim();
    if (!instruction) return { ok: false, reason: 'missing_instruction' };
    const mode = inferDesignMode(instruction, input.posts ?? [], input.mode);
    return {
      ok: true,
      request: {
        linked_project_id: linked,
        instruction,
        mode,
        draft: {
          posts: (input.posts ?? []).map((p) => ({ id: p.id, elements: p.elements ?? [] })),
          selected_post_id: input.selectedPostId ?? null,
        },
        selected_asset_ids: [COVER_UUID].filter((id) => UUID_RE.test(id)),
        builder_context: { builder: 'social', design_engine: 'phase1' },
      },
    };
  }

  it('builds create request for Temple with Asset UUIDs only', () => {
    const built = buildSocialDesignRequest({
      linkedProjectId: TEMPLE_UUID,
      instruction: 'THE TEMPLE için Instagram kare post oluştur',
      posts: [],
      selectedPostId: null,
    });
    assert.equal(built.ok, true);
    assert.equal(built.request.mode, 'create');
    assert.equal(built.request.linked_project_id, TEMPLE_UUID);
    assert.equal(built.request.builder_context.design_engine, 'phase1');
    for (const id of built.request.selected_asset_ids) {
      assert.match(id, UUID_RE);
      assert.doesNotMatch(id, /^https?:/i);
    }
  });

  it('infers edit mode from Turkish edit instruction on existing posts', () => {
    const built = buildSocialDesignRequest({
      linkedProjectId: TEMPLE_UUID,
      instruction: 'Başlık rengini beyaz yap ve biraz yukarı taşı',
      posts: [{ id: 'p1', elements: [{ id: 'h1', type: 'TEXT' }] }],
      selectedPostId: 'p1',
    });
    assert.equal(built.ok, true);
    assert.equal(built.request.mode, 'edit');
  });

  it('rejects missing project / instruction', () => {
    assert.equal(
      buildSocialDesignRequest({
        linkedProjectId: null,
        instruction: 'x',
        posts: [],
      }).ok,
      false,
    );
    assert.equal(
      buildSocialDesignRequest({
        linkedProjectId: TEMPLE_UUID,
        instruction: '  ',
        posts: [],
      }).reason,
      'missing_instruction',
    );
  });
});

describe('persistence includes generation metadata', () => {
  it('builder-media-persistence serializes generationMeta', () => {
    const persistence = readFileSync(
      join(here, '../../_components/builder-media-persistence.ts'),
      'utf8',
    );
    assert.match(persistence, /generationMeta/);
    assert.match(persistence, /draft\.generationMeta/);
  });

  it('design engine exports meta serializers', () => {
    const eng = readSmb('social-media-builder-design-engine.ts');
    assert.match(eng, /export function serializeGenerationMetaForDraft/);
    assert.match(eng, /export function toDesignGenerationMeta/);
    assert.match(eng, /brand_context_status/);
    assert.doesNotMatch(eng, /unsplash/i);
  });
});
