import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import { Project } from '@/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Sword, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { parseApiError } from '@/lib/errorParser';

const PROVIDERS = ['groq', 'gemini', 'openai', 'anthropic', 'ollama'];
const ROLES = ['general', 'security', 'performance', 'style'];

const MODELS_BY_PROVIDER: Record<string, string[]> = {
  groq: ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768'],
  gemini: ['gemini-1.5-flash', 'gemini-1.5-pro'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022'],
  ollama: ['qwen2.5-coder:7b', 'llama3.2:3b', 'deepseek-coder-v2:16b'],
};

interface EvaluationSessionCreate {
  project_id: number;
  num_rounds: number;
  candidate_a_provider: string;
  candidate_a_model: string;
  candidate_a_role: string;
  candidate_b_provider: string;
  candidate_b_model: string;
  candidate_b_role: string;
}

export function ModelDuelSetup() {
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState<number | null>(null);
  const [numRounds, setNumRounds] = useState(5);

  // Candidate A
  const [providerA, setProviderA] = useState('groq');
  const [modelA, setModelA] = useState('llama-3.3-70b-versatile');
  const [roleA, setRoleA] = useState('general');

  // Candidate B
  const [providerB, setProviderB] = useState('gemini');
  const [modelB, setModelB] = useState('gemini-1.5-flash');
  const [roleB, setRoleB] = useState('general');

  // Fetch projects
  const { data: projects, isLoading: loadingProjects } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get('/projects?page=1&page_size=100');
      return response.data.items || [];
    },
  });

  // Create evaluation session mutation
  const createMutation = useMutation({
    mutationFn: async (data: EvaluationSessionCreate) => {
      const response = await api.post('/evaluations', data);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Model Duel rozpoczęty!');
      navigate(`/model-duel/${data.id}`);
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się rozpocząć Model Duel'));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!projectId) {
      toast.error('Wybierz projekt');
      return;
    }

    if (providerA === providerB && modelA === modelB && roleA === roleB) {
      toast.error('Kandydaci nie mogą być identyczni');
      return;
    }

    createMutation.mutate({
      project_id: projectId,
      num_rounds: numRounds,
      candidate_a_provider: providerA,
      candidate_a_model: modelA,
      candidate_a_role: roleA,
      candidate_b_provider: providerB,
      candidate_b_model: modelB,
      candidate_b_role: roleB,
    });
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Sword className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Model Duel</h1>
          <p className="text-muted-foreground">Porównaj dwie konfiguracje modeli AI</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Project & Rounds Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Ustawienia sesji</CardTitle>
            <CardDescription>Wybierz projekt i liczbę rund</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="project">Projekt</Label>
              <Select
                value={projectId?.toString() || ''}
                onValueChange={(value) => setProjectId(parseInt(value))}
              >
                <SelectTrigger id="project">
                  <SelectValue placeholder="Wybierz projekt" />
                </SelectTrigger>
                <SelectContent>
                  {loadingProjects ? (
                    <SelectItem value="loading" disabled>
                      Ładowanie...
                    </SelectItem>
                  ) : projects?.length === 0 ? (
                    <SelectItem value="none" disabled>
                      Brak projektów
                    </SelectItem>
                  ) : (
                    projects?.map((project) => (
                      <SelectItem key={project.id} value={project.id.toString()}>
                        {project.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="rounds">Liczba rund (1-20)</Label>
              <Input
                id="rounds"
                type="number"
                min={1}
                max={20}
                value={numRounds}
                onChange={(e) => setNumRounds(parseInt(e.target.value) || 5)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Candidate A */}
        <Card>
          <CardHeader>
            <CardTitle className="text-blue-600">Kandydat A</CardTitle>
            <CardDescription>Pierwsza konfiguracja do porównania</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="provider-a">Provider</Label>
              <Select value={providerA} onValueChange={setProviderA}>
                <SelectTrigger id="provider-a">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((provider) => (
                    <SelectItem key={provider} value={provider}>
                      {provider}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="model-a">Model</Label>
              <Select value={modelA} onValueChange={setModelA}>
                <SelectTrigger id="model-a">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODELS_BY_PROVIDER[providerA]?.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="role-a">Rola agenta</Label>
              <Select value={roleA} onValueChange={setRoleA}>
                <SelectTrigger id="role-a">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Candidate B */}
        <Card>
          <CardHeader>
            <CardTitle className="text-green-600">Kandydat B</CardTitle>
            <CardDescription>Druga konfiguracja do porównania</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="provider-b">Provider</Label>
              <Select value={providerB} onValueChange={setProviderB}>
                <SelectTrigger id="provider-b">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROVIDERS.map((provider) => (
                    <SelectItem key={provider} value={provider}>
                      {provider}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="model-b">Model</Label>
              <Select value={modelB} onValueChange={setModelB}>
                <SelectTrigger id="model-b">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {MODELS_BY_PROVIDER[providerB]?.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="role-b">Rola agenta</Label>
              <Select value={roleB} onValueChange={setRoleB}>
                <SelectTrigger id="role-b">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role} value={role}>
                      {role}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/projects')}
          >
            Anuluj
          </Button>
          <Button
            type="submit"
            disabled={createMutation.isPending || !projectId}
          >
            {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Rozpocznij Duel
          </Button>
        </div>
      </form>
    </div>
  );
}
