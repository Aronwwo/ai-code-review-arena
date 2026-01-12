import { useState, useEffect, useMemo } from 'react';
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
import { getProviders, CustomProvider } from '@/lib/providers';

interface AgentConfig {
  enabled: boolean;
  provider: string;
  model: string;
}

interface TeamConfig {
  general: AgentConfig;
  security: AgentConfig;
  performance: AgentConfig;
  style: AgentConfig;
}

export interface ReviewConfig {
  agents: TeamConfig;
  teamA?: TeamConfig;
  teamB?: TeamConfig;
  moderator: {
    provider: string;
    model: string;
    type: 'debate' | 'consensus' | 'strategic';
  };
  mode: 'council' | 'arena' | null;
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

const DEFAULT_AGENT_CONFIG: AgentConfig = {
  enabled: true,
  provider: 'ollama',
  model: 'qwen2.5-coder:1.5b'
};

const createDefaultTeam = (): TeamConfig => ({
  general: { ...DEFAULT_AGENT_CONFIG },
  security: { ...DEFAULT_AGENT_CONFIG },
  performance: { ...DEFAULT_AGENT_CONFIG },
  style: { ...DEFAULT_AGENT_CONFIG },
});

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
    agents: createDefaultTeam(),
    teamA: createDefaultTeam(),
    teamB: createDefaultTeam(),
    moderator: { provider: 'ollama', model: 'qwen2.5-coder:1.5b', type: 'debate' },
    mode: null,
  });

  // Fetch Ollama models
  const { data: ollamaModelsData, isLoading: modelsLoading } = useQuery<OllamaModelsResponse>({
    queryKey: ['ollama-models'],
    queryFn: async () => {
      try {
        const response = await api.get('/ollama/models');
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

  // Set default model when Ollama models load
  useEffect(() => {
    if (ollamaModels && ollamaModels.length > 0) {
      const defaultModel = ollamaModels[0];
      setConfig(prev => {
        const updateTeam = (team: TeamConfig): TeamConfig => ({
          general: { ...team.general, model: ollamaModels.includes(team.general.model) ? team.general.model : defaultModel },
          security: { ...team.security, model: ollamaModels.includes(team.security.model) ? team.security.model : defaultModel },
          performance: { ...team.performance, model: ollamaModels.includes(team.performance.model) ? team.performance.model : defaultModel },
          style: { ...team.style, model: ollamaModels.includes(team.style.model) ? team.style.model : defaultModel },
        });

        return {
          ...prev,
          agents: updateTeam(prev.agents),
          teamA: prev.teamA ? updateTeam(prev.teamA) : undefined,
          teamB: prev.teamB ? updateTeam(prev.teamB) : undefined,
          moderator: { ...prev.moderator, model: ollamaModels.includes(prev.moderator.model) ? prev.moderator.model : defaultModel },
        };
      });
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

  // Update agent in specific team
  const updateTeamAgent = (team: 'agents' | 'teamA' | 'teamB', agentId: string, updates: Partial<AgentConfig>) => {
    setConfig(prev => {
      const currentTeam = prev[team];
      if (!currentTeam) return prev;
      return {
        ...prev,
        [team]: {
          ...currentTeam,
          [agentId]: { ...currentTeam[agentId as keyof TeamConfig], ...updates },
        },
      };
    });
  };

  const updateModerator = (updates: Partial<{ provider: string; model: string; type: 'debate' | 'consensus' | 'strategic' }>) => {
    setConfig(prev => ({
      ...prev,
      moderator: { ...prev.moderator, ...updates },
    }));
  };

  // Count enabled agents (for council mode - use agents, for arena - both teams always enabled)
  const enabledAgentCount = config.mode === 'arena' ? 4 : Object.values(config.agents).filter(a => a.enabled).length;

  const handleStartReview = () => {
    if (!config.mode) {
      toast.error('Wybierz tryb przed rozpoczęciem');
      return;
    }

    if (config.mode === 'council') {
      if (enabledAgentCount === 0) {
        toast.error('Wybierz przynajmniej jednego agenta');
        return;
      }

      for (const [id, agent] of Object.entries(config.agents)) {
        if (agent.enabled && !agent.model) {
          toast.error(`Wybierz model dla agenta ${id}`);
          return;
        }
      }
    }

    if (config.mode === 'arena') {
      // Validate both teams
      for (const teamName of ['teamA', 'teamB'] as const) {
        const team = config[teamName];
        if (!team) continue;
        for (const [id, agent] of Object.entries(team)) {
          if (!agent.model) {
            toast.error(`Zespół ${teamName === 'teamA' ? 'A' : 'B'}: Wybierz model dla agenta ${id}`);
            return;
          }
        }
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

  // Render agent cards for a team
  const renderTeamAgents = (team: 'agents' | 'teamA' | 'teamB', showSwitch: boolean = true) => {
    const teamConfig = config[team];
    if (!teamConfig) return null;

    return (
      <div className="grid gap-4 md:grid-cols-2">
        {AGENT_ROLES.map((role) => {
          const agent = teamConfig[role.id as keyof TeamConfig];
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
                  {showSwitch && (
                    <Switch
                      checked={agent.enabled}
                      onCheckedChange={(checked) => updateTeamAgent(team, role.id, { enabled: checked })}
                    />
                  )}
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
                        updateTeamAgent(team, role.id, {
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
                        onChange={(e) => updateTeamAgent(team, role.id, { model: e.target.value })}
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
    );
  };


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

        <Tabs defaultValue="mode" className="mt-4">
          <TabsList className={`grid w-full ${!config.mode ? 'grid-cols-1' : config.mode === 'council' ? 'grid-cols-3' : 'grid-cols-4'}`}>
            <TabsTrigger value="mode">Tryb</TabsTrigger>
            {config.mode === 'council' && (
              <>
                <TabsTrigger value="agents">Agenci ({enabledAgentCount}/4)</TabsTrigger>
                <TabsTrigger value="moderator">Moderator</TabsTrigger>
              </>
            )}
            {config.mode === 'arena' && (
              <>
                <TabsTrigger value="teamA">Zespół A</TabsTrigger>
                <TabsTrigger value="teamB">Zespół B</TabsTrigger>
                <TabsTrigger value="moderator">Moderator</TabsTrigger>
              </>
            )}
          </TabsList>

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
                    Jeden zespół 4 agentów analizuje kod. Moderator podsumowuje konsensus.
                    Ten tryb NIE wpływa na rankingi.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>✓ Jeden zespół agentów</li>
                    <li>✓ Współpraca i konsensus</li>
                    <li>✓ Szybsza analiza</li>
                    <li className="text-orange-500">✗ Brak wpływu na rankingi</li>
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
                    Dwa zespoły (A i B) niezależnie analizują kod. Po zakończeniu głosujesz,
                    który zespół dał lepsze wyniki. Głosy budują ranking ELO.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>✓ Dwa konkurujące zespoły</li>
                    <li>✓ Porównanie wyników</li>
                    <li>✓ Głosowanie użytkownika</li>
                    <li className="text-green-500">✓ Buduje rankingi ELO</li>
                  </ul>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Council Mode - Agents Tab */}
          {config.mode === 'council' && (
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
              {renderTeamAgents('agents', true)}
            </TabsContent>
          )}

          {/* Arena Mode - Team A Tab */}
          {config.mode === 'arena' && (
            <TabsContent value="teamA" className="space-y-4 mt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-blue-600 border-blue-600">Zespół A</Badge>
                  <p className="text-sm text-muted-foreground">
                    Skonfiguruj modele AI dla pierwszego zespołu
                  </p>
                </div>
                <Link to="/settings" onClick={() => onOpenChange(false)}>
                  <Button variant="outline" size="sm" className="gap-2">
                    <Settings className="h-4 w-4" />
                    Dodaj Provider
                  </Button>
                </Link>
              </div>
              {renderTeamAgents('teamA', false)}
            </TabsContent>
          )}

          {/* Arena Mode - Team B Tab */}
          {config.mode === 'arena' && (
            <TabsContent value="teamB" className="space-y-4 mt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-red-600 border-red-600">Zespół B</Badge>
                  <p className="text-sm text-muted-foreground">
                    Skonfiguruj modele AI dla drugiego zespołu
                  </p>
                </div>
                <Link to="/settings" onClick={() => onOpenChange(false)}>
                  <Button variant="outline" size="sm" className="gap-2">
                    <Settings className="h-4 w-4" />
                    Dodaj Provider
                  </Button>
                </Link>
              </div>
              {renderTeamAgents('teamB', false)}
            </TabsContent>
          )}

          {/* Moderator Tab */}
          {config.mode && (
            <TabsContent value="moderator" className="space-y-4 mt-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-green-500" />
                    <CardTitle>Moderator</CardTitle>
                  </div>
                  <CardDescription>
                    {config.mode === 'council'
                      ? 'Moderator analizuje dyskusję między agentami i wydaje końcowy werdykt.'
                      : 'Moderator prezentuje wnioski obu zespołów. Po analizie zagłosujesz, który zespół dał lepsze wyniki.'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Moderator Type Selection - only for council mode */}
                  {config.mode === 'council' && (
                    <div className="space-y-2">
                      <Label>Typ Moderatora</Label>
                      <select
                        className="w-full p-2 border rounded-md bg-background"
                        value={config.moderator.type}
                        onChange={(e) => updateModerator({ type: e.target.value as 'debate' | 'consensus' | 'strategic' })}
                      >
                        <option value="debate">Moderator Debaty</option>
                        <option value="consensus">Syntezator Konsensusu</option>
                        <option value="strategic">Strategiczny Koordynator</option>
                      </select>
                      <p className="text-xs text-muted-foreground">
                        {config.moderator.type === 'debate' && '🎭 Aktywnie prowadzi dyskusję, zadaje pytania, rozstrzyga spory'}
                        {config.moderator.type === 'consensus' && '🤝 Łączy różne perspektywy w spójne rekomendacje'}
                        {config.moderator.type === 'strategic' && '🎯 Priorytetyzuje problemy, planuje kolejność działań'}
                      </p>
                    </div>
                  )}

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
          )}

        </Tabs>

        <DialogFooter className="mt-6">
          <div className="flex items-center justify-between w-full">
            <div className="text-sm text-muted-foreground">
              {fileCount} plik(ów) • {Math.round(totalCodeSize / 1024)} KB kodu
              {config.mode === 'council' && ` • ${enabledAgentCount} agentów`}
              {config.mode === 'arena' && ' • 2 zespoły × 4 agentów'}
              {config.mode && ` • Tryb: ${config.mode === 'council' ? 'Rada' : 'Arena'}`}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Anuluj
              </Button>
              <Button
                onClick={handleStartReview}
                disabled={!config.mode || isLoading || (config.mode === 'council' && enabledAgentCount === 0) || fileCount === 0}
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
