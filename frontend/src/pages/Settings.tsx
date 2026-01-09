/**
 * Settings Page - User configuration and provider management
 *
 * TODO (Clean Code): This file is 696 lines - too large!
 * Should be refactored into smaller components:
 * - ProviderList.tsx
 * - ProviderForm.tsx
 * - APIKeyManager.tsx
 * - UserSettings.tsx
 *
 * Current structure works but violates Single Responsibility Principle.
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Label } from '@/components/ui/Label';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Separator } from '@/components/ui/Separator';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { toast } from 'sonner';
import {
  RefreshCw, AlertCircle, Key, Lock, User,
  Plus, Trash2, Edit, Check, Globe, Cpu, Loader2
} from 'lucide-react';
import api from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

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
      return { ...builtIn, ...updated, isBuiltIn: true };
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

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // Formularz nowego/edytowanego providera
  const [formData, setFormData] = useState<Partial<CustomProvider>>({
    name: '',
    baseUrl: '',
    apiKey: '',
    models: [],
    description: '',
    headerName: 'Authorization',
    headerPrefix: 'Bearer ',
  });
  const [modelsInput, setModelsInput] = useState('');

  // Password validation
  const validatePassword = (pwd: string): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];
    if (pwd.length < 8) errors.push('minimum 8 znaków');
    if (!/[A-Z]/.test(pwd)) errors.push('wielka litera');
    if (!/[a-z]/.test(pwd)) errors.push('mała litera');
    if (!/\d/.test(pwd)) errors.push('cyfra');
    return { valid: errors.length === 0, errors };
  };

  const handleChangePassword = async () => {
    // Validation
    if (!currentPassword) {
      toast.error('Wprowadź obecne hasło');
      return;
    }

    const { valid, errors } = validatePassword(newPassword);
    if (!valid) {
      toast.error(`Nowe hasło musi zawierać: ${errors.join(', ')}`);
      return;
    }

    if (newPassword !== confirmNewPassword) {
      toast.error('Nowe hasła nie są identyczne');
      return;
    }

    setIsChangingPassword(true);
    try {
      await api.patch('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success('Hasło zostało zmienione');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (error: any) {
      // Don't show error toast for 401 - interceptor handles redirect to login
      if (error.response?.status !== 401) {
        toast.error(error.response?.data?.detail || 'Nie udało się zmienić hasła');
      }
    } finally {
      setIsChangingPassword(false);
    }
  };

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
    setFormData({
      name: '',
      baseUrl: '',
      apiKey: '',
      models: [],
      description: '',
      headerName: 'Authorization',
      headerPrefix: 'Bearer ',
    });
    setModelsInput('');
    setEditingProvider(null);
    setIsAddingProvider(true);
  };

  const handleEditProvider = (provider: CustomProvider) => {
    setFormData({ ...provider });
    setModelsInput(provider.models.join(', '));
    setEditingProvider(provider);
    setIsAddingProvider(true);
  };

  const handleDeleteProvider = (providerId: string) => {
    const provider = providers.find(p => p.id === providerId);
    if (provider?.isBuiltIn) {
      toast.error('Nie można usunąć wbudowanego providera');
      return;
    }
    setProviders(prev => prev.filter(p => p.id !== providerId));
    toast.success('Provider usunięty');
  };

  const handleSaveProvider = () => {
    if (!formData.name?.trim()) {
      toast.error('Nazwa jest wymagana');
      return;
    }

    const models = modelsInput
      .split(',')
      .map(m => m.trim())
      .filter(m => m.length > 0);

    const newProvider: CustomProvider = {
      id: editingProvider?.id || `custom-${Date.now()}`,
      name: formData.name!.trim(),
      baseUrl: formData.baseUrl?.trim() || '',
      apiKey: formData.apiKey || '',
      models: models,
      isBuiltIn: editingProvider?.isBuiltIn || false,
      description: formData.description?.trim(),
      headerName: formData.headerName || 'Authorization',
      headerPrefix: formData.headerPrefix ?? 'Bearer ',
    };

    if (editingProvider) {
      setProviders(prev => prev.map(p => p.id === editingProvider.id ? newProvider : p));
      toast.success('Provider zaktualizowany');
    } else {
      setProviders(prev => [...prev, newProvider]);
      toast.success('Provider dodany');
    }

    setIsAddingProvider(false);
    setEditingProvider(null);
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

      {/* Informacje o koncie */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Konto
          </CardTitle>
          <CardDescription>
            Informacje o Twoim koncie
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label className="text-muted-foreground">Email</Label>
              <p className="font-medium">{user?.email || '-'}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Nazwa użytkownika</Label>
              <p className="font-medium">{user?.username || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Zmiana hasła */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Zmiana hasła
          </CardTitle>
          <CardDescription>
            Zmień swoje hasło. Wymagane: min. 8 znaków, wielka litera, mała litera, cyfra.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-password">Obecne hasło</Label>
            <Input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-password">Nowe hasło</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Potwierdź nowe hasło</Label>
            <Input
              id="confirm-password"
              type="password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button onClick={handleChangePassword} disabled={isChangingPassword}>
            {isChangingPassword ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Zmieniam...
              </>
            ) : (
              'Zmień hasło'
            )}
          </Button>
        </CardFooter>
      </Card>

      {/* Status Ollama */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5" />
            Ollama (Lokalny AI)
          </CardTitle>
          <CardDescription>
            Darmowe modele AI działające lokalnie na Twoim komputerze
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ollamaLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : ollamaError ? (
            <div className="flex items-start gap-3 p-4 border border-destructive/50 rounded-lg bg-destructive/10">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Ollama niedostępna</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Upewnij się że Ollama działa na http://localhost:11434
                </p>
                <p className="text-sm text-muted-foreground">
                  Pobierz z{' '}
                  <a href="https://ollama.ai" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                    ollama.ai
                  </a>
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Dostępne Modele</Label>
                {ollamaData?.cached && (
                  <span className="text-xs text-muted-foreground">Z cache</span>
                )}
              </div>
              {ollamaData?.models.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Brak zainstalowanych modeli. Uruchom: <code className="bg-muted px-1 rounded">ollama pull qwen2.5-coder</code>
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {ollamaData?.models.map((model) => (
                    <Badge key={model} variant="secondary">
                      {model}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

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
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{provider.name}</h4>
                    {provider.isBuiltIn && (
                      <Badge variant="outline" className="text-xs">Wbudowany</Badge>
                    )}
                    {provider.apiKey && (
                      <Badge variant="success" className="text-xs">
                        <Check className="h-3 w-3 mr-1" />
                        Klucz ustawiony
                      </Badge>
                    )}
                  </div>

                  {provider.description && (
                    <p className="text-sm text-muted-foreground">{provider.description}</p>
                  )}

                  {provider.id !== 'mock' && provider.id !== 'ollama' && (
                    <div className="flex items-center gap-2">
                      <Input
                        type="password"
                        placeholder="Klucz API..."
                        value={provider.apiKey}
                        onChange={(e) => handleUpdateApiKey(provider.id, e.target.value)}
                        className="max-w-md"
                      />
                    </div>
                  )}

                  {provider.models.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {provider.models.slice(0, 5).map((model) => (
                        <Badge key={model} variant="secondary" className="text-xs">
                          {model}
                        </Badge>
                      ))}
                      {provider.models.length > 5 && (
                        <Badge variant="outline" className="text-xs">
                          +{provider.models.length - 5} więcej
                        </Badge>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => handleEditProvider(provider)}>
                    <Edit className="h-4 w-4" />
                  </Button>
                  {!provider.isBuiltIn && (
                    <Button variant="ghost" size="sm" onClick={() => handleDeleteProvider(provider.id)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Dialog dodawania/edycji providera */}
      <Dialog open={isAddingProvider} onOpenChange={setIsAddingProvider}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingProvider ? 'Edytuj Provider' : 'Dodaj Nowy Provider'}
            </DialogTitle>
            <DialogDescription>
              Dodaj dowolne API kompatybilne z formatem OpenAI lub własny endpoint
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="provider-name">Nazwa *</Label>
              <Input
                id="provider-name"
                placeholder="np. Mój Custom API"
                value={formData.name || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider-url">URL Bazowy</Label>
              <Input
                id="provider-url"
                placeholder="https://api.example.com/v1"
                value={formData.baseUrl || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, baseUrl: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Endpoint API (np. https://api.openai.com/v1)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider-key">Klucz API</Label>
              <Input
                id="provider-key"
                type="password"
                placeholder="sk-..."
                value={formData.apiKey || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, apiKey: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider-models">Modele (oddzielone przecinkami)</Label>
              <Textarea
                id="provider-models"
                placeholder="gpt-4, gpt-3.5-turbo, custom-model"
                value={modelsInput}
                onChange={(e) => setModelsInput(e.target.value)}
                rows={3}
              />
              <p className="text-xs text-muted-foreground">
                Lista dostępnych modeli, np: gpt-4, claude-3-sonnet, llama-70b
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider-desc">Opis (opcjonalnie)</Label>
              <Input
                id="provider-desc"
                placeholder="Krótki opis providera"
                value={formData.description || ''}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              />
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="header-name">Nagłówek Auth</Label>
                <Input
                  id="header-name"
                  placeholder="Authorization"
                  value={formData.headerName || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, headerName: e.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="header-prefix">Prefix</Label>
                <Input
                  id="header-prefix"
                  placeholder="Bearer "
                  value={formData.headerPrefix || ''}
                  onChange={(e) => setFormData(prev => ({ ...prev, headerPrefix: e.target.value }))}
                />
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Większość API używa "Authorization: Bearer TOKEN". Anthropic używa "x-api-key: TOKEN"
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddingProvider(false)}>
              Anuluj
            </Button>
            <Button onClick={handleSaveProvider}>
              {editingProvider ? 'Zapisz Zmiany' : 'Dodaj Provider'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
