import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Code, Loader2, AlertTriangle, Bot, Settings } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import { getProviders, CustomProvider } from '@/lib/providers';

interface AgentConfig {
  provider: string;
  model: string;
  timeout: number; // timeout w sekundach (domyślnie 180 = 3 minuty)
  max_tokens?: number; // max tokens do wygenerowania (domyślnie 4096)
}

export interface ReviewConfig {
  mode: 'single' | 'arena';
  agent: AgentConfig;
  arenaA: AgentConfig;
  arenaB: AgentConfig;
}

interface OllamaModelsResponse {
  models: string[];
  cached: boolean;
}

interface ReviewConfigDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onStartReview: (config: ReviewConfig) => void;
  isLoading?: boolean;
  fileCount: number;
  totalCodeSize: number;
}

const GENERAL_ROLE = {
  id: 'general',
  name: 'Poprawność Kodu',
  icon: Code,
  color: 'text-blue-500',
  description: 'Wykrywa błędy składniowe, logiczne i krytyczne bugi.',
} as const;

const DEFAULT_AGENT_CONFIG: AgentConfig = {
  provider: 'mock',
  model: 'mock-fast',
  timeout: 180, // 3 minuty
  max_tokens: 4096 // domyślnie 4096
};

export function ReviewConfigDialog({
  open,
  onOpenChange,
  onStartReview,
  isLoading = false,
  fileCount,
  totalCodeSize,
}: ReviewConfigDialogProps) {
  // Dynamicznie ładuj providerów z localStorage
  const [providers, setProviders] = useState<CustomProvider[]>([]);

  // Odświeżaj listę providerów gdy dialog się otwiera
  useEffect(() => {
    if (open) {
      setProviders(getProviders());
    }
  }, [open]);

  const [config, setConfig] = useState<ReviewConfig>({
    mode: 'single',
    agent: { ...DEFAULT_AGENT_CONFIG },
    arenaA: { ...DEFAULT_AGENT_CONFIG },
    arenaB: { ...DEFAULT_AGENT_CONFIG },
  });

  // Fetch Ollama models
  const { data: ollamaModelsData, isLoading: modelsLoading } = useQuery<OllamaModelsResponse>({
    queryKey: ['ollama-models'],
    queryFn: async () => {
      try {
        const response = await api.get('/api/ollama/models');
        return response.data;
      } catch {
        return { models: [], cached: false };
      }
    },
    enabled: open,
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const ollamaModels = useMemo(() => ollamaModelsData?.models || [], [ollamaModelsData?.models]);

  // Aktualizuj providerów gdy załadują się modele Ollama
  useEffect(() => {
    if (ollamaModels && ollamaModels.length > 0) {
      setProviders(prev => {
        const updated = prev.map(p =>
          p.id === 'ollama' ? { ...p, models: ollamaModels } : p
        );

        const saved = localStorage.getItem('custom_providers');
        const customProviders: Array<Partial<CustomProvider>> = saved ? JSON.parse(saved) : [];

        const ollamaIndex = customProviders.findIndex((p) => p.id === 'ollama');
        const ollamaProvider = updated.find(p => p.id === 'ollama');

        if (ollamaProvider) {
          const ollamaToSave = {
            id: ollamaProvider.id,
            models: ollamaProvider.models,
            apiKey: ollamaProvider.apiKey,
            baseUrl: ollamaProvider.baseUrl,
          };

          if (ollamaIndex >= 0) {
            customProviders[ollamaIndex] = ollamaToSave;
          } else {
            customProviders.push(ollamaToSave);
          }

          localStorage.setItem('custom_providers', JSON.stringify(customProviders));
        }

        return updated;
      });
    }
  }, [ollamaModels]);

  // Set default model when Ollama models load (only for Ollama-selected agents)
  useEffect(() => {
    if (ollamaModels && ollamaModels.length > 0) {
      const defaultModel = ollamaModels[0];
      const updateAgent = (agent: AgentConfig): AgentConfig => {
        if (agent.provider !== 'ollama') return agent;
        return {
          ...agent,
          model: ollamaModels.includes(agent.model) ? agent.model : defaultModel,
        };
      };
      setConfig(prev => ({
        ...prev,
        agent: updateAgent(prev.agent),
        arenaA: updateAgent(prev.arenaA),
        arenaB: updateAgent(prev.arenaB),
      }));
    }
  }, [ollamaModels]);

  // Pobierz modele dla danego providera
  const getModelsForProvider = (providerId: string): string[] => {
    const provider = providers.find(p => p.id === providerId);
    if (!provider) return [];

    if (providerId === 'ollama') {
      return ollamaModels.length > 0 ? ollamaModels : provider.models;
    }

    return provider.models;
  };

  const isProviderActive = (providerId: string) => getModelsForProvider(providerId).length > 0;

  const handleStartReview = () => {
    if (config.mode === 'arena') {
      const arenaAgents = [config.arenaA, config.arenaB];
      for (const [idx, agent] of arenaAgents.entries()) {
        const label = idx === 0 ? 'Model A' : 'Model B';
        if (!isProviderActive(agent.provider)) {
          toast.error(`${label}: wybrany provider jest nieaktywny`);
          return;
        }
        if (!agent.model) {
          toast.error(`${label}: wybierz model`);
          return;
        }
      }
    } else {
      const agent = config.agent;
      if (!isProviderActive(agent.provider)) {
        toast.error('Wybrany provider jest nieaktywny');
        return;
      }
      if (!agent.model) {
        toast.error('Wybierz model dla agenta');
        return;
      }
    }

    onStartReview(config);
  };

  const warnings: string[] = [];
  if (fileCount === 0) {
    warnings.push('Brak plików do przeglądu');
  }
  if (totalCodeSize < 50) {
    warnings.push('Bardzo mało kodu - wyniki mogą być ograniczone');
  }
  if (totalCodeSize > 100000) {
    warnings.push('Duży projekt - review może potrwać dłużej');
  }

  const buildAgentModels = (agent: AgentConfig) => getModelsForProvider(agent.provider);

  const renderAgentConfig = (agent: AgentConfig, onChange: (next: AgentConfig) => void) => {
    const models = buildAgentModels(agent);
    return (
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <GENERAL_ROLE.icon className={`h-5 w-5 ${GENERAL_ROLE.color}`} />
            <CardTitle className="text-base">{GENERAL_ROLE.name}</CardTitle>
          </div>
          <CardDescription className="text-xs">{GENERAL_ROLE.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-2">
            <Label className="text-xs">Provider</Label>
            <select
              className="w-full p-2 border rounded-md text-sm bg-background"
              value={agent.provider}
              onChange={(e) => {
                const newProvider = e.target.value;
                const newModels = getModelsForProvider(newProvider);
                onChange({
                  ...agent,
                  provider: newProvider,
                  model: newModels[0] || '',
                });
              }}
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Model</Label>
            {modelsLoading && agent.provider === 'ollama' ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Ładowanie modeli...
              </div>
            ) : models.length > 0 ? (
              <select
                className="w-full p-2 border rounded-md text-sm bg-background"
                value={agent.model}
                onChange={(e) => onChange({ ...agent, model: e.target.value })}
              >
                {models.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            ) : (
              <div className="text-sm text-muted-foreground">
                {agent.provider === 'ollama' ? (
                  <span>Brak modeli Ollama - uruchom Ollama i pobierz model</span>
                ) : (
                  <span>
                    Brak modeli -
                    <Link
                      to="/settings"
                      onClick={() => onOpenChange(false)}
                      className="text-primary hover:underline ml-1"
                    >
                      skonfiguruj w ustawieniach
                    </Link>
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label className="text-xs">Timeout (sekundy)</Label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={30}
                max={3600}
                className="w-20 p-2 border rounded-md text-sm bg-background"
                value={agent.timeout}
                onChange={(e) => onChange({ ...agent, timeout: parseInt(e.target.value) || 180 })}
              />
              <span className="text-xs text-muted-foreground">
                ({Math.floor(agent.timeout / 60)}:{String(agent.timeout % 60).padStart(2, '0')} min)
              </span>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Max Tokens</Label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={256}
                max={8192}
                step={256}
                className="w-20 p-2 border rounded-md text-sm bg-background"
                value={agent.max_tokens || 4096}
                onChange={(e) => onChange({ ...agent, max_tokens: parseInt(e.target.value) || 4096 })}
              />
              <span className="text-xs text-muted-foreground">(domyślnie: 4096)</span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-6 w-6" />
            Konfiguracja przeglądu
          </DialogTitle>
        <DialogDescription>
          Wybierz tryb: pojedynczy przegląd albo Arena (model A vs model B)
        </DialogDescription>
        </DialogHeader>

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
              <div>
                <p className="font-medium text-yellow-600">Uwagi:</p>
                <ul className="text-sm text-muted-foreground mt-1">
                  {warnings.map((w, i) => (
                    <li key={i}>• {w}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <div className="mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <Button
                variant={config.mode === 'single' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfig(prev => ({ ...prev, mode: 'single' }))}
              >
                Pojedynczy przegląd
              </Button>
              <Button
                variant={config.mode === 'arena' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setConfig(prev => ({ ...prev, mode: 'arena' }))}
              >
                Arena (A vs B)
              </Button>
            </div>
            <Link to="/settings" onClick={() => onOpenChange(false)}>
              <Button variant="outline" size="sm" className="gap-2">
                <Settings className="h-4 w-4" />
                Dodaj Provider
              </Button>
            </Link>
          </div>

          {config.mode === 'single' ? (
            <>
              <p className="text-sm text-muted-foreground">
                Jeden agent analizuje kod i zwraca problemy krytyczne.
              </p>
              {renderAgentConfig(config.agent, (next) => setConfig(prev => ({ ...prev, agent: next })))}
            </>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Dwa modele analizują ten sam kod. Po zakończeniu wybierasz lepszy wynik.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-sm font-medium">Model A</div>
                  {renderAgentConfig(config.arenaA, (next) => setConfig(prev => ({ ...prev, arenaA: next })))}
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-medium">Model B</div>
                  {renderAgentConfig(config.arenaB, (next) => setConfig(prev => ({ ...prev, arenaB: next })))}
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="mt-6">
          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {fileCount} plik(ów) • {Math.round(totalCodeSize / 1024)} KB kodu
              {config.mode === 'single' ? ' • 1 agent' : ' • 2 modele (A vs B)'}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Anuluj
              </Button>
              <Button
                onClick={handleStartReview}
                disabled={
                  isLoading ||
                  (config.mode === 'single' && (!isProviderActive(config.agent.provider) || !config.agent.model)) ||
                  (config.mode === 'arena' && (
                    !isProviderActive(config.arenaA.provider) ||
                    !config.arenaA.model ||
                    !isProviderActive(config.arenaB.provider) ||
                    !config.arenaB.model
                  )) ||
                  fileCount === 0
                }
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uruchamianie...
                  </>
                ) : (
                  'Rozpocznij Review'
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
