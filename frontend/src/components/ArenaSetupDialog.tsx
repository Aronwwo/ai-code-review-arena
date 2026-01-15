/**
 * ArenaSetupDialog - Dialog konfiguracji Combat Arena
 *
 * Pozwala użytkownikowi skonfigurować dwa kompletne schematy review (A i B),
 * gdzie każdy schemat zawiera konfigurację dla wszystkich 4 ról:
 * - general (ogólna jakość kodu)
 * - security (bezpieczeństwo)
 * - performance (wydajność)
 * - style (styl i konwencje)
 *
 * Po konfiguracji obu schematów, system uruchamia dwa równoległe review
 * i pozwala użytkownikowi wybrać który schemat działał lepiej.
 */

import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Shield, Zap, Paintbrush, Code, Swords, Loader2, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { getProviders, CustomProvider } from '@/lib/providers';
import { parseApiError } from '@/lib/errorParser';
import type { AgentConfig } from '@/types';

interface SchemaConfig {
  general: AgentConfig;
  security: AgentConfig;
  performance: AgentConfig;
  style: AgentConfig;
}

interface ArenaConfig {
  schema_a: SchemaConfig;
  schema_b: SchemaConfig;
}

interface ArenaSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: number;
  onArenaStarted: (sessionId: number) => void;
  isLoading?: boolean;
  fileCount: number;
}

interface OllamaModelsResponse {
  models: string[];
  cached: boolean;
}

const AGENT_ROLES = [
  { id: 'general', name: 'Ogólny', icon: Code, color: 'text-blue-500', description: 'Ogólna jakość kodu' },
  { id: 'security', name: 'Bezpieczeństwo', icon: Shield, color: 'text-red-500', description: 'Analiza bezpieczeństwa' },
  { id: 'performance', name: 'Wydajność', icon: Zap, color: 'text-yellow-500', description: 'Optymalizacja i wydajność' },
  { id: 'style', name: 'Styl', icon: Paintbrush, color: 'text-purple-500', description: 'Styl i formatowanie' },
] as const;

export function ArenaSetupDialog({
  open,
  onOpenChange,
  projectId,
  onArenaStarted,
  isLoading = false,
  fileCount,
}: ArenaSetupDialogProps) {
  const [providers, setProviders] = useState<CustomProvider[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Domyślna konfiguracja - oba schematy z Mock
  const [config, setConfig] = useState<ArenaConfig>({
    schema_a: {
      general: { provider: 'mock', model: 'mock-fast' },
      security: { provider: 'mock', model: 'mock-fast' },
      performance: { provider: 'mock', model: 'mock-fast' },
      style: { provider: 'mock', model: 'mock-fast' },
    },
    schema_b: {
      general: { provider: 'mock', model: 'mock-fast' },
      security: { provider: 'mock', model: 'mock-fast' },
      performance: { provider: 'mock', model: 'mock-fast' },
      style: { provider: 'mock', model: 'mock-fast' },
    },
  });

  // Załaduj providerów
  useEffect(() => {
    if (open) {
      setProviders(getProviders());
    }
  }, [open]);

  // Fetch Ollama models
  const { data: ollamaModelsData } = useQuery<OllamaModelsResponse>({
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
  });

  const ollamaModels = useMemo(() => ollamaModelsData?.models || [], [ollamaModelsData?.models]);

  // Aktualizuj domyślny model gdy załadują się modele Ollama (tylko dla Ollama)
  useEffect(() => {
    if (ollamaModels && ollamaModels.length > 0) {
      const defaultModel = ollamaModels[0];
      const updateAgent = (agent: AgentConfig): AgentConfig => {
        if (agent.provider !== 'ollama') return agent;
        return { ...agent, model: ollamaModels.includes(agent.model) ? agent.model : defaultModel };
      };
      const updateSchema = (schema: SchemaConfig): SchemaConfig => ({
        general: updateAgent(schema.general),
        security: updateAgent(schema.security),
        performance: updateAgent(schema.performance),
        style: updateAgent(schema.style),
      });

      setConfig(prev => ({
        ...prev,
        schema_a: updateSchema(prev.schema_a),
        schema_b: updateSchema(prev.schema_b),
      }));
    }
  }, [ollamaModels]);

  const getModelsForProvider = (providerId: string): string[] => {
    const provider = providers.find(p => p.id === providerId);
    if (!provider) return [];
    if (providerId === 'ollama') {
      return ollamaModels.length > 0 ? ollamaModels : provider.models;
    }
    return provider.models;
  };

  const isProviderActive = (providerId: string) => getModelsForProvider(providerId).length > 0;

  const updateAgent = (schema: 'schema_a' | 'schema_b', roleId: string, updates: Partial<AgentConfig>) => {
    setConfig(prev => ({
      ...prev,
      [schema]: {
        ...prev[schema],
        [roleId]: { ...prev[schema][roleId as keyof SchemaConfig], ...updates },
      },
    }));
  };

  const handleStartArena = async () => {
    // Walidacja - wszystkie role muszą mieć model
    for (const schema of ['schema_a', 'schema_b'] as const) {
      for (const role of AGENT_ROLES) {
        const agent = config[schema][role.id as keyof SchemaConfig];
        if (!isProviderActive(agent.provider)) {
          toast.error(`Schemat ${schema === 'schema_a' ? 'A' : 'B'}: provider ${agent.provider} jest nieaktywny`);
          return;
        }
        if (!agent.model) {
          toast.error(`Schemat ${schema === 'schema_a' ? 'A' : 'B'}: wybierz model dla ${role.name}`);
          return;
        }
        if (!agent.provider || !agent.model) {
          toast.error(`Schemat ${schema === 'schema_a' ? 'A' : 'B'}: wybierz provider i model dla ${role.name}`);
          return;
        }
      }
    }

    setSubmitting(true);

    try {
      // Utwórz sesję Arena
      const response = await api.post('/arena/sessions', {
        project_id: projectId,
        schema_a_config: config.schema_a,
        schema_b_config: config.schema_b,
      });

      const sessionId = response.data.id;
      toast.success('Arena rozpoczęta! Dwa review uruchomione równolegle.');
      onArenaStarted(sessionId);
      onOpenChange(false);
    } catch (error: unknown) {
      console.error('Arena start error:', error);
      toast.error(parseApiError(error, 'Nie udało się rozpocząć Arena'));
    } finally {
      setSubmitting(false);
    }
  };

  const warnings: string[] = [];
  if (fileCount === 0) warnings.push('Brak plików do przeglądu');
  const hasInactiveProviders = (['schema_a', 'schema_b'] as const).some(schema =>
    AGENT_ROLES.some(role => !isProviderActive(config[schema][role.id as keyof SchemaConfig].provider))
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[95vw] max-w-5xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Swords className="h-6 w-6 text-orange-500" />
            Combat Arena - Porównanie Schematów
          </DialogTitle>
          <DialogDescription>
            Skonfiguruj dwa kompletne schematy review (A vs B). Każdy schemat ma 4 agentów.
          </DialogDescription>
        </DialogHeader>

        {warnings.length > 0 && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
              <div>
                <p className="font-medium text-yellow-600">Uwagi:</p>
                <ul className="text-sm text-muted-foreground mt-1">
                  {warnings.map((w, i) => <li key={i}>• {w}</li>)}
                </ul>
              </div>
            </div>
          </div>
        )}

        <Tabs defaultValue="schema_a" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="schema_a">Schemat A</TabsTrigger>
            <TabsTrigger value="schema_b">Schemat B</TabsTrigger>
          </TabsList>

          {(['schema_a', 'schema_b'] as const).map(schema => (
            <TabsContent key={schema} value={schema} className="space-y-4 mt-4">
              <div className="grid gap-4">
                {AGENT_ROLES.map(role => {
                  const agent = config[schema][role.id as keyof SchemaConfig];
                  const RoleIcon = role.icon;
                  const models = getModelsForProvider(agent.provider);
                  const providerActive = models.length > 0;
                  return (
                    <Card key={role.id}>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <RoleIcon className={`h-5 w-5 ${role.color}`} />
                          {role.name}
                        </CardTitle>
                        <CardDescription>{role.description}</CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          {/* Provider */}
                          <div>
                            <Label>Provider</Label>
                            <select
                              className="w-full mt-1.5 px-3 py-2 bg-background border rounded-md"
                              value={agent.provider}
                              onChange={(e) => {
                                const newProvider = e.target.value;
                                const models = getModelsForProvider(newProvider);
                                updateAgent(schema, role.id, {
                                  provider: newProvider,
                                  model: models[0] || '',
                                });
                              }}
                            >
                              {providers.map(p => (
                                <option key={p.id} value={p.id}>{p.id}</option>
                              ))}
                            </select>
                          </div>

                          {/* Model */}
                          <div>
                            <Label>Model</Label>
                            {providerActive ? (
                              <select
                                className="w-full mt-1.5 px-3 py-2 bg-background border rounded-md"
                                value={agent.model}
                                onChange={(e) => updateAgent(schema, role.id, { model: e.target.value })}
                              >
                                {models.map(m => (
                                  <option key={m} value={m}>{m}</option>
                                ))}
                              </select>
                            ) : (
                              <div className="text-sm text-muted-foreground mt-2">
                                {agent.provider === 'ollama'
                                  ? 'Brak modeli Ollama - uruchom Ollama i pobierz model'
                                  : 'Brak modeli - skonfiguruj w ustawieniach'}
                              </div>
                            )}
                          </div>
                        </div>

                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </TabsContent>
          ))}
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Anuluj
          </Button>
          <Button onClick={handleStartArena} disabled={submitting || isLoading || fileCount === 0 || hasInactiveProviders}>
            {submitting || isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uruchamianie...
              </>
            ) : (
              <>
                <Swords className="mr-2 h-4 w-4" />
                Start Arena
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
