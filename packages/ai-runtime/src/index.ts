export type AiModelProvider = 'openai' | 'anthropic' | 'azure' | 'local';

export interface AiRuntimeConfig {
  provider: AiModelProvider;
  model: string;
  temperature: number;
  maxTokens: number;
}

export interface AiPromptRequest {
  promptId: string;
  input: Record<string, unknown>;
  metadata?: Record<string, string>;
}

export interface AiPromptResponse {
  output: string;
  tokensUsed: number;
  latencyMs: number;
}
