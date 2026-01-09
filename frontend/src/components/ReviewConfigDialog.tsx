import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Switch } from '@/components/ui/Switch';
import { Shield, Zap, Paintbrush, Code, Users, Swords, Loader2, AlertTriangle, Bot, Settings } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from 'react-router-dom';
import { getProviders, CustomProvider } from '@/pages/Settings';

interface AgentConfig {
  enabled: boolean;
  provider: string;
  model: string;
}

interface ReviewConfig {
  agents: {
    general: AgentConfig;
    security: AgentConfig;
    performance: AgentConfig;
    style: AgentConfig;
  };
  moderator: {
    provider: string;
    model: string;
  };
  mode: 'council' | 'arena';
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

const AGENT_ROLES = [
  { id: 'general', name: 'Ogólny', icon: Code, color: 'text-blue-500', description: 'Ogólna jakość kodu i dobre praktyki' },
  { id: 'security', name: 'Bezpieczeństwo', icon: Shield, color: 'text-red-500', description: 'Analiza bezpieczeństwa i podatności' },
  { id: 'performance', name: 'Wydajność', icon: Zap, color: 'text-yellow-500', description: 'Optymalizacja i wydajność kodu' },
  { id: 'style', name: 'Styl', icon: Paintbrush, color: 'text-purple-500', description: 'Styl kodu i formatowanie' },
] as const;

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
    agents: {
      general: { enabled: true, provider: 'ollama', model: 'qwen2.5-coder:1.5b' },
      security: { enabled: true, provider: 'ollama', model: 'qwen2.5-coder:1.5b' },
      performance: { enabled: true, provider: 'ollama', model: 'qwen2.5-coder:1.5b' },
      style: { enabled: true, provider: 'ollama', model: 'qwen2.5-coder:1.5b' },
    },
    moderator: { provider: 'ollama', model: 'qwen2.5-coder:1.5b' },
    mode: 'council',
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
    staleTime: 0, // Always fetch fresh data when dialog opens
    refetchOnMount: 'always',
  });

  const ollamaModels = ollamaModelsData?.models || [];

  // Aktualizuj providerów gdy załadują się modele Ollama
  useEffect(() => {
    if (ollamaModels && ollamaModels.length > 0) {
      setProviders(prev => {
        const updated = prev.map(p =>
          p.id === 'ollama' ? { ...p, models: ollamaModels } : p
        );

        // Update localStorage for Ollama provider
        const saved = localStorage.getItem('custom_providers');
        const customProviders = saved ? JSON.parse(saved) : [];

        // Update or add Ollama to localStorage
        const ollamaIndex = customProviders.findIndex((p: any) => p.id === 'ollama');
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

  // Set default model when Ollama models load
  useEffect(() => {
    if (ollamaModels && ollamaModels.length > 0) {
      const defaultModel = ollamaModels[0];
      // Tylko aktualizuj model jeśli obecny model nie istnieje w Ollama
      setConfig(prev => ({
        ...prev,
        agents: {
          general: { ...prev.agents.general, model: ollamaModels.includes(prev.agents.general.model) ? prev.agents.general.model : defaultModel },
          security: { ...prev.agents.security, model: ollamaModels.includes(prev.agents.security.model) ? prev.agents.security.model : defaultModel },
          performance: { ...prev.agents.performance, model: ollamaModels.includes(prev.agents.performance.model) ? prev.agents.performance.model : defaultModel },
          style: { ...prev.agents.style, model: ollamaModels.includes(prev.agents.style.model) ? prev.agents.style.model : defaultModel },
        },
        moderator: { ...prev.moderator, model: ollamaModels.includes(prev.moderator.model) ? prev.moderator.model : defaultModel },
      }));
    }
  }, [ollamaModels]);

  // Pobierz modele dla danego providera
  const getModelsForProvider = (providerId: string): string[] => {
    const provider = providers.find(p => p.id === providerId);
    if (!provider) return [];

    // Dla Ollama - użyj dynamicznie załadowanych modeli
    if (providerId === 'ollama') {
      return ollamaModels.length > 0 ? ollamaModels : provider.models;
    }

    return provider.models;
  };

  const updateAgent = (agentId: string, updates: Partial<AgentConfig>) => {
    setConfig(prev => ({
      ...prev,
      agents: {
        ...prev.agents,
        [agentId]: { ...prev.agents[agentId as keyof typeof prev.agents], ...updates },
      },
    }));
  };

  const updateModerator = (updates: Partial<{ provider: string; model: string }>) => {
    setConfig(prev => ({
      ...prev,
      moderator: { ...prev.moderator, ...updates },
    }));
  };

  const enabledAgentCount = Object.values(config.agents).filter(a => a.enabled).length;

  const handleStartReview = () => {
    if (enabledAgentCount === 0) {
      toast.error('Wybierz przynajmniej jednego agenta');
      return;
    }

    // Validate that all enabled agents have models selected
    for (const [id, agent] of Object.entries(config.agents)) {
      if (agent.enabled && !agent.model) {
        toast.error(`Wybierz model dla agenta ${id}`);
        return;
      }
    }

    if (!config.moderator.model) {
      toast.error('Wybierz model dla moderatora');
      return;
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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Bot className="h-6 w-6" />
            Konfiguracja Code Review
          </DialogTitle>
          <DialogDescription>
            Wybierz agentów AI i modele do analizy Twojego kodu
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

        <Tabs defaultValue="agents" className="mt-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="agents">Agenci ({enabledAgentCount}/4)</TabsTrigger>
            <TabsTrigger value="moderator">Moderator</TabsTrigger>
            <TabsTrigger value="mode">Tryb Dyskusji</TabsTrigger>
          </TabsList>

          {/* Agents Tab */}
          <TabsContent value="agents" className="space-y-4 mt-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Każdy agent analizuje kod z innej perspektywy. Możesz wybrać różne modele AI dla każdego.
              </p>
              <Link to="/settings" onClick={() => onOpenChange(false)}>
                <Button variant="outline" size="sm" className="gap-2">
                  <Settings className="h-4 w-4" />
                  Dodaj Provider
                </Button>
              </Link>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {AGENT_ROLES.map((role) => {
                const agent = config.agents[role.id as keyof typeof config.agents];
                const Icon = role.icon;
                const models = getModelsForProvider(agent.provider);

                return (
                  <Card key={role.id} className={`transition-opacity ${!agent.enabled ? 'opacity-50' : ''}`}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className={`h-5 w-5 ${role.color}`} />
                          <CardTitle className="text-base">{role.name}</CardTitle>
                        </div>
                        <Switch
                          checked={agent.enabled}
                          onCheckedChange={(checked) => updateAgent(role.id, { enabled: checked })}
                        />
                      </div>
                      <CardDescription className="text-xs">{role.description}</CardDescription>
                    </CardHeader>

                    {agent.enabled && (
                      <CardContent className="space-y-3">
                        <div className="space-y-2">
                          <Label className="text-xs">Provider</Label>
                          <select
                            className="w-full p-2 border rounded-md text-sm bg-background"
                            value={agent.provider}
                            onChange={(e) => {
                              const newProvider = e.target.value;
                              const newModels = getModelsForProvider(newProvider);
                              updateAgent(role.id, {
                                provider: newProvider,
                                model: newModels[0] || ''
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
                              onChange={(e) => updateAgent(role.id, { model: e.target.value })}
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
                      </CardContent>
                    )}
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* Moderator Tab */}
          <TabsContent value="moderator" className="space-y-4 mt-4">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-green-500" />
                  <CardTitle>Moderator</CardTitle>
                </div>
                <CardDescription>
                  Moderator analizuje dyskusję między agentami i wydaje końcowy werdykt.
                  W trybie Council - podsumowuje konsensus. W trybie Arena - rozstrzyga debatę.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Provider</Label>
                    <select
                      className="w-full p-2 border rounded-md bg-background"
                      value={config.moderator.provider}
                      onChange={(e) => {
                        const newProvider = e.target.value;
                        const newModels = getModelsForProvider(newProvider);
                        updateModerator({ provider: newProvider, model: newModels[0] || '' });
                      }}
                    >
                      {providers.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label>Model</Label>
                    {modelsLoading && config.moderator.provider === 'ollama' ? (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground p-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Ładowanie modeli...
                      </div>
                    ) : (
                      <select
                        className="w-full p-2 border rounded-md bg-background"
                        value={config.moderator.model}
                        onChange={(e) => updateModerator({ model: e.target.value })}
                      >
                        {getModelsForProvider(config.moderator.provider).map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Mode Tab */}
          <TabsContent value="mode" className="space-y-4 mt-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Card
                className={`cursor-pointer transition-all ${config.mode === 'council' ? 'ring-2 ring-primary' : 'hover:border-primary/50'}`}
                onClick={() => setConfig(prev => ({ ...prev, mode: 'council' }))}
              >
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Users className="h-6 w-6 text-blue-500" />
                    <CardTitle>Tryb Rady (Council)</CardTitle>
                    {config.mode === 'council' && <Badge>Wybrany</Badge>}
                  </div>
                  <CardDescription>
                    Agenci współpracują i dyskutują kooperatywnie. Każdy przedstawia swoją perspektywę,
                    a moderator podsumowuje konsensus i tworzy wspólne rekomendacje.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>✓ Współpraca między agentami</li>
                    <li>✓ Konsensus rekomendacji</li>
                    <li>✓ Szybsza analiza</li>
                    <li>✓ Idealne do ogólnych przeglądów</li>
                  </ul>
                </CardContent>
              </Card>

              <Card
                className={`cursor-pointer transition-all ${config.mode === 'arena' ? 'ring-2 ring-primary' : 'hover:border-primary/50'}`}
                onClick={() => setConfig(prev => ({ ...prev, mode: 'arena' }))}
              >
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Swords className="h-6 w-6 text-red-500" />
                    <CardTitle>Tryb Areny (Arena)</CardTitle>
                    {config.mode === 'arena' && <Badge>Wybrany</Badge>}
                  </div>
                  <CardDescription>
                    Agenci debatują przeciwstawne stanowiska. Prokurator argumentuje za powagą problemów,
                    Obrońca broni kodu. Moderator wydaje końcowy werdykt.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>✓ Głębsza analiza problemów</li>
                    <li>✓ Debata za i przeciw</li>
                    <li>✓ Werdykt moderatora</li>
                    <li>✓ Idealne do kontrowersyjnych problemów</li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-6">
          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {fileCount} plik(ów) • {Math.round(totalCodeSize / 1024)} KB kodu • {enabledAgentCount} agentów
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Anuluj
              </Button>
              <Button
                onClick={handleStartReview}
                disabled={isLoading || enabledAgentCount === 0 || fileCount === 0}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uruchamianie...
                  </>
                ) : (
                  <>Rozpocznij Review</>
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
