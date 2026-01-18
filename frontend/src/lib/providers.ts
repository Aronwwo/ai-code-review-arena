/**
 * Provider management for AI code review.
 * Stores custom provider configurations in localStorage.
 */

export interface CustomProvider {
  id: string;
  name: string;
  description?: string;
  baseUrl?: string;
  apiKey?: string;
  models: string[];
  isBuiltIn?: boolean;
  headerName?: string;
  headerPrefix?: string;
}

const STORAGE_KEY = 'ai-code-review-providers';

// Built-in providers with default configurations
// Models are empty - they require API key to be set first (except Ollama which fetches dynamically)
const BUILT_IN_PROVIDERS: CustomProvider[] = [
  {
    id: 'mock',
    name: 'Mock (bez API)',
    description: 'Szybkie testy bez klucza API',
    models: ['mock-fast', 'mock-smart'],
    isBuiltIn: true,
  },
  {
    id: 'groq',
    name: 'Groq',
    description: 'Szybkie API z modelami Llama i Mixtral',
    baseUrl: 'https://api.groq.com/openai/v1',
    models: [], // Requires API key - models will be shown after key is set
    isBuiltIn: true,
    apiKey: ''
  },
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'Oficjalne API OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    models: [], // Requires API key - models will be shown after key is set
    isBuiltIn: true,
    apiKey: ''
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    description: 'Modele Gemini od Google',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    models: [], // Requires API key - models will be shown after key is set
    isBuiltIn: true,
    apiKey: ''
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: 'Modele DeepSeek (API zgodne z OpenAI)',
    baseUrl: 'https://api.deepseek.com/v1',
    models: [], // Requires API key - models will be shown after key is set
    isBuiltIn: true,
    apiKey: ''
  },
  {
    id: 'perplexity',
    name: 'Perplexity',
    description: 'Perplexity AI (API zgodne z OpenAI)',
    baseUrl: 'https://api.perplexity.ai', // Perplexity uses /chat/completions (no /v1)
    models: [], // Requires API key - models will be shown after key is set
    isBuiltIn: true,
    apiKey: ''
  },
  {
    id: 'ollama',
    name: 'Ollama',
    description: 'Lokalne modele AI (wymaga uruchomionego Ollama)',
    baseUrl: 'http://localhost:11434',
    models: [], // Fetched dynamically from Ollama
    isBuiltIn: true,
    apiKey: ''
  }
];

/**
 * Get all providers (built-in + custom from localStorage)
 */
export function getProviders(): CustomProvider[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const customProviders: CustomProvider[] = JSON.parse(stored);

      // Merge built-in providers with stored data (to get API keys)
      const mergedBuiltIn = BUILT_IN_PROVIDERS.map(builtIn => {
        const storedProvider = customProviders.find(p => p.id === builtIn.id);
        if (storedProvider) {
          // For Ollama - models are fetched dynamically, don't use stored
          // For others - only use stored models if API key is set
          let models: string[] = [];
          if (builtIn.id === 'ollama') {
            // Ollama models are fetched dynamically from /ollama/models
            models = storedProvider.models || [];
          } else if (builtIn.id === 'mock') {
            // Mock models are always available
            models = builtIn.models;
          } else if (storedProvider.apiKey) {
            // Other providers - only show models if API key is set
            models = storedProvider.models || [];
          }

          return {
            ...builtIn,
            apiKey: storedProvider.apiKey || '',
            models
          };
        }
        return builtIn;
      });

      // Add custom providers (non-built-in)
      const custom = customProviders.filter(p => !p.isBuiltIn && !BUILT_IN_PROVIDERS.some(b => b.id === p.id));

      return [...mergedBuiltIn, ...custom];
    }
  } catch (e) {
    console.error('Failed to load providers from localStorage:', e);
  }

  return [...BUILT_IN_PROVIDERS];
}

/**
 * Clear old cached provider data (call this to reset)
 */
export function clearProvidersCache(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Save providers to localStorage
 */
export function saveProviders(providers: CustomProvider[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(providers));
  } catch (e) {
    console.error('Failed to save providers to localStorage:', e);
  }
}

/**
 * Get a specific provider by ID
 */
export function getProvider(id: string): CustomProvider | undefined {
  return getProviders().find(p => p.id === id);
}

/**
 * Update a provider's API key
 */
export function updateProviderApiKey(providerId: string, apiKey: string): void {
  const providers = getProviders();
  const index = providers.findIndex(p => p.id === providerId);
  if (index !== -1) {
    providers[index].apiKey = apiKey;
    saveProviders(providers);
  }
}

/**
 * Add a new custom provider
 */
export function addProvider(provider: CustomProvider): void {
  const providers = getProviders();
  providers.push(provider);
  saveProviders(providers);
}

/**
 * Remove a custom provider
 */
export function removeProvider(providerId: string): void {
  const providers = getProviders().filter(p => p.id !== providerId || p.isBuiltIn);
  saveProviders(providers);
}
