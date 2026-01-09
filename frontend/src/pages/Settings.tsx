/**
 * Settings Page - User configuration and provider management
 *
 * Refactored into smaller, focused components:
 * - UserSettingsSection: User account info and password change
 * - ProviderCard: Individual provider display and inline editing
 * - ProviderDialog: Add/edit provider form dialog
 * - OllamaSection: Ollama-specific configuration section
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Separator } from '@/components/ui/Separator';
import { toast } from 'sonner';
import { RefreshCw, Key, Plus, Globe } from 'lucide-react';
import api from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { UserSettingsSection } from '@/components/settings/UserSettingsSection';
import { ProviderCard } from '@/components/settings/ProviderCard';
import { ProviderDialog } from '@/components/settings/ProviderDialog';
import { OllamaSection } from '@/components/settings/OllamaSection';

// Interfejs dla custom providera
export interface CustomProvider {
  id: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  models: string[];
  isBuiltIn: boolean;
  description?: string;
  headerName?: string; // Nazwa nagłówka dla API key (domyślnie "Authorization")
  headerPrefix?: string; // Prefix dla klucza (domyślnie "Bearer ")
}

// Wbudowani providerzy (można ich edytować ale nie usuwać)
const BUILT_IN_PROVIDERS: CustomProvider[] = [
  {
    id: 'ollama',
    name: 'Ollama (Lokalny)',
    baseUrl: 'http://localhost:11434',
    apiKey: '',
    models: [], // Ładowane dynamicznie
    isBuiltIn: true,
    description: 'Darmowy, działa lokalnie na Twoim komputerze',
  },
  {
    id: 'mock',
    name: 'Mock (Demo)',
    baseUrl: '',
    apiKey: '',
    models: ['mock-model'],
    isBuiltIn: true,
    description: 'Symulacja do testów bez prawdziwego AI',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    baseUrl: 'https://api.openai.com/v1',
    apiKey: '',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
    isBuiltIn: true,
    description: 'GPT-4, GPT-3.5 - wymaga klucza API',
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    baseUrl: 'https://api.anthropic.com/v1',
    apiKey: '',
    models: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229'],
    isBuiltIn: true,
    description: 'Claude 3.5 Sonnet/Haiku - wymaga klucza API',
    headerName: 'x-api-key',
    headerPrefix: '',
  },
  {
    id: 'groq',
    name: 'Groq',
    baseUrl: 'https://api.groq.com/openai/v1',
    apiKey: '',
    models: [
      'llama-3.3-70b-versatile',
      'llama-3.1-70b-versatile',
      'llama-3.1-8b-instant',
      'mixtral-8x7b-32768',
      'gemma2-9b-it',
      'llama-3.2-90b-vision-preview'
    ],
    isBuiltIn: true,
    description: 'Bardzo szybkie, darmowy tier',
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
    apiKey: '',
    models: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro'],
    isBuiltIn: true,
    description: 'Gemini Pro/Flash - wymaga klucza API',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    baseUrl: 'https://openrouter.ai/api/v1',
    apiKey: '',
    models: ['openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'google/gemini-pro-1.5', 'meta-llama/llama-3.1-70b-instruct'],
    isBuiltIn: true,
    description: 'Agregator wielu modeli AI - jeden klucz do wszystkiego',
  },
];

// Funkcja do pobierania providerów z localStorage
export function getProviders(): CustomProvider[] {
  const saved = localStorage.getItem('custom_providers');
  const customProviders: CustomProvider[] = saved ? JSON.parse(saved) : [];

  // Połącz wbudowanych z własnymi (własne mogą nadpisywać wbudowanych)
  const builtInWithUpdates = BUILT_IN_PROVIDERS.map(builtIn => {
    const updated = customProviders.find(p => p.id === builtIn.id);
    if (updated) {
      // Merge carefully - keep built-in models for non-Ollama providers
      const merged = { ...builtIn, ...updated, isBuiltIn: true };

      // For non-Ollama providers, always use built-in models (don't let them get overwritten)
      if (builtIn.id !== 'ollama' && builtIn.models.length > 0) {
        merged.models = builtIn.models;
      }

      return merged;
    }
    return builtIn;
  });

  // Dodaj całkowicie nowych providerów
  const newCustom = customProviders.filter(p => !BUILT_IN_PROVIDERS.find(b => b.id === p.id));

  return [...builtInWithUpdates, ...newCustom];
}

// Funkcja do zapisywania providerów
function saveProviders(providers: CustomProvider[]) {
  // Zapisujemy tylko zmiany względem wbudowanych + nowi
  const toSave = providers.filter(p => {
    if (!p.isBuiltIn) return true; // Nowi zawsze zapisywani
    // Dla wbudowanych - zapisuj tylko jeśli zmienione
    const original = BUILT_IN_PROVIDERS.find(b => b.id === p.id);
    if (!original) return true;

    // Dla Ollama - zawsze zapisuj modele (ładowane dynamicznie)
    if (p.id === 'ollama') {
      return p.apiKey !== original.apiKey ||
             p.baseUrl !== original.baseUrl ||
             p.models.length > 0; // Zapisz jeśli ma modele
    }

    return p.apiKey !== original.apiKey ||
           JSON.stringify(p.models) !== JSON.stringify(original.models) ||
           p.baseUrl !== original.baseUrl;
  });
  localStorage.setItem('custom_providers', JSON.stringify(toSave));
}

interface OllamaModel {
  models: string[];
  cached: boolean;
}

export function Settings() {
  const { user } = useAuth();
  const [providers, setProviders] = useState<CustomProvider[]>(getProviders);
  const [isAddingProvider, setIsAddingProvider] = useState(false);
  const [editingProvider, setEditingProvider] = useState<CustomProvider | null>(null);

  // Pobierz modele Ollama
  const {
    data: ollamaData,
    isLoading: ollamaLoading,
    error: ollamaError,
    refetch: refetchOllama,
  } = useQuery<OllamaModel>({
    queryKey: ['ollama-models'],
    queryFn: async () => {
      const response = await api.get('/api/ollama/models');
      return response.data;
    },
    retry: 1,
  });

  // Aktualizuj modele Ollama gdy się załadują
  useEffect(() => {
    if (ollamaData?.models) {
      setProviders(prev => prev.map(p =>
        p.id === 'ollama' ? { ...p, models: ollamaData.models } : p
      ));
    }
  }, [ollamaData]);

  // Zapisz przy każdej zmianie
  useEffect(() => {
    saveProviders(providers);
  }, [providers]);

  const handleAddProvider = () => {
    setEditingProvider(null);
    setIsAddingProvider(true);
  };

  const handleEditProvider = (provider: CustomProvider) => {
    setEditingProvider(provider);
    setIsAddingProvider(true);
  };

  const handleDeleteProvider = (providerId: string) => {
    setProviders(prev => prev.filter(p => p.id !== providerId));
    toast.success('Provider usunięty');
  };

  const handleSaveProvider = (provider: CustomProvider) => {
    if (editingProvider) {
      setProviders(prev => prev.map(p => p.id === provider.id ? provider : p));
      toast.success('Provider zaktualizowany');
    } else {
      setProviders(prev => [...prev, provider]);
      toast.success('Provider dodany');
    }
  };

  const handleUpdateApiKey = (providerId: string, apiKey: string) => {
    setProviders(prev => prev.map(p =>
      p.id === providerId ? { ...p, apiKey } : p
    ));
  };

  const handleSaveAll = () => {
    saveProviders(providers);
    toast.success('Wszystkie ustawienia zapisane!');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Ustawienia</h1>
          <p className="text-muted-foreground">Zarządzaj providerami AI i kluczami API</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetchOllama()} disabled={ollamaLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${ollamaLoading ? 'animate-spin' : ''}`} />
            Odśwież
          </Button>
          <Button onClick={handleSaveAll}>
            Zapisz Wszystko
          </Button>
        </div>
      </div>

      {/* User Settings - Account info and password change */}
      <UserSettingsSection
        userEmail={user?.email || ''}
        userName={user?.username || ''}
      />

      {/* Ollama Section */}
      <OllamaSection
        models={ollamaData?.models || []}
        isLoading={ollamaLoading}
        error={ollamaError}
        onRefresh={() => refetchOllama()}
        isCached={ollamaData?.cached}
      />

      {/* Lista Providerów */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Globe className="h-5 w-5" />
                Providerzy API
              </CardTitle>
              <CardDescription>
                Dodaj dowolne API kompatybilne z OpenAI lub własne endpointy
              </CardDescription>
            </div>
            <Button onClick={handleAddProvider}>
              <Plus className="h-4 w-4 mr-2" />
              Dodaj Provider
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {providers.map((provider, index) => (
            <div key={provider.id}>
              {index > 0 && <Separator className="my-4" />}
              <ProviderCard
                provider={provider}
                onEdit={handleEditProvider}
                onDelete={handleDeleteProvider}
                onUpdateApiKey={handleUpdateApiKey}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Provider Dialog */}
      <ProviderDialog
        open={isAddingProvider}
        onOpenChange={setIsAddingProvider}
        provider={editingProvider}
        onSave={handleSaveProvider}
      />

      {/* Info Card */}
      <Card className="border-primary/50 bg-primary/5">
        <CardContent className="pt-6">
          <div className="flex gap-3">
            <Key className="h-5 w-5 text-primary mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium">O Ustawieniach</p>
              <p className="text-sm text-muted-foreground">
                Wszystkie klucze API i ustawienia są przechowywane lokalnie w Twojej przeglądarce.
                Nigdy nie są wysyłane na serwer. Możesz dodać dowolne API kompatybilne z formatem OpenAI.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
