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
import { useAuth } from '@/contexts/useAuth';
import { UserSettingsSection } from '@/components/settings/UserSettingsSection';
import { ProviderCard } from '@/components/settings/ProviderCard';
import { ProviderDialog } from '@/components/settings/ProviderDialog';
import { OllamaSection } from '@/components/settings/OllamaSection';
import { CustomProvider, getProviders, saveProviders } from '@/lib/providers';

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
