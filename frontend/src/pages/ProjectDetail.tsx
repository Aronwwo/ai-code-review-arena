import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Project, FileWithContent, FileCreate, Review, ReviewCreate, AgentConfig, ArenaSession, ArenaSessionCreate, ArenaTeamConfig } from '@/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/EmptyState';
import { CodeViewer } from '@/components/CodeViewer';
import { CodeEditor } from '@/components/CodeEditor';
import { ReviewConfigDialog, ReviewConfig } from '@/components/ReviewConfigDialog';
import { getProviders } from '@/lib/providers';
import { Plus, FileCode, Play, ArrowLeft, Loader2, Upload, Trash2, Edit, Eye, Settings2 } from 'lucide-react';
import { toast } from 'sonner';
import { parseApiError } from '@/lib/errorParser';

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isAddingFile, setIsAddingFile] = useState(false);
  const [newFileName, setNewFileName] = useState('');
  const [newFileContent, setNewFileContent] = useState('');
  const [newFileLanguage, setNewFileLanguage] = useState('');
  const [uploadMode, setUploadMode] = useState<'paste' | 'file'>('paste');
  const [selectedFile, setSelectedFile] = useState<FileWithContent | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [isReviewConfigOpen, setIsReviewConfigOpen] = useState(false);

  // Fetch project with files
  const { data: project, isLoading } = useQuery({
    queryKey: ['project', id],
    queryFn: async () => {
      const response = await api.get(`/projects/${id}`);
      return response.data as Project & { files: FileWithContent[] };
    },
    enabled: !!id,
  });

  // Fetch reviews
  const { data: reviews } = useQuery<Review[]>({
    queryKey: ['reviews', id],
    queryFn: async () => {
      const response = await api.get(`/projects/${id}/reviews`);
      return response.data;
    },
    enabled: !!id,
  });

  // Add file mutation
  const addFileMutation = useMutation({
    mutationFn: async (data: FileCreate) => {
      const response = await api.post(`/projects/${id}/files`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      setIsAddingFile(false);
      setNewFileName('');
      setNewFileContent('');
      setNewFileLanguage('');
      toast.success('Plik dodany pomyślnie!');
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się dodać pliku'));
    },
  });

  // Start review mutation (council mode)
  const startReviewMutation = useMutation({
    mutationFn: async (data: ReviewCreate) => {
      const response = await api.post(`/projects/${id}/reviews`, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['reviews', id] });
      toast.success('Przegląd uruchomiony pomyślnie!');
      navigate(`/reviews/${data.id}`);
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się uruchomić przeglądu'));
    },
  });

  // Start arena session mutation (arena mode)
  const startArenaMutation = useMutation({
    mutationFn: async (data: ArenaSessionCreate) => {
      const response = await api.post('/arena/sessions', data);
      return response.data as ArenaSession;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['arena-sessions', id] });
      toast.success('Sesja Arena uruchomiona pomyślnie!');
      navigate(`/arena/${data.id}`);
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się uruchomić sesji Arena'));
    },
  });

  // Update file mutation
  const updateFileMutation = useMutation({
    mutationFn: async ({ fileId, content }: { fileId: number; content: string }) => {
      const response = await api.patch(`/projects/${id}/files/${fileId}`, { content });
      return response.data;
    },
    onSuccess: (updatedFile) => {
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      setIsEditing(false);
      if (selectedFile) {
        setSelectedFile({ ...selectedFile, content: updatedFile.content || editedContent });
      }
      toast.success('Plik zapisany pomyślnie!');
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się zapisać pliku'));
    },
  });

  // Delete file mutation
  const deleteFileMutation = useMutation({
    mutationFn: async (fileId: number) => {
      await api.delete(`/projects/${id}/files/${fileId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', id] });
      setSelectedFile(null);
      toast.success('Plik usunięty pomyślnie!');
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się usunąć pliku'));
    },
  });

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (max 10MB)
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB in bytes
    if (file.size > MAX_SIZE) {
      toast.error(`Plik jest za duży. Maksymalnie 10MB (obecny: ${(file.size / 1024 / 1024).toFixed(1)}MB)`);
      e.target.value = ''; // Reset file input
      return;
    }

    const extension = file.name.split('.').pop()?.toLowerCase();
    const languageMap: Record<string, string> = {
      py: 'python', js: 'javascript', ts: 'typescript', tsx: 'typescript',
      jsx: 'javascript', java: 'java', cpp: 'cpp', c: 'c', cs: 'csharp',
      go: 'go', rs: 'rust', rb: 'ruby', php: 'php', swift: 'swift',
      kt: 'kotlin', sql: 'sql', sh: 'bash', html: 'html', css: 'css',
      json: 'json', xml: 'xml', yaml: 'yaml', yml: 'yaml', md: 'markdown',
    };

    setNewFileName(file.name);
    if (extension && languageMap[extension]) {
      setNewFileLanguage(languageMap[extension]);
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setNewFileContent(content);
    };
    reader.onerror = () => {
      toast.error('Nie udało się odczytać pliku');
    };
    reader.readAsText(file);
  };

  const handleAddFile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFileName.trim() || !newFileContent.trim()) {
      toast.error('Nazwa pliku i zawartość są wymagane');
      return;
    }
    addFileMutation.mutate({
      name: newFileName,
      content: newFileContent,
      language: newFileLanguage || undefined,
    });
  };

  const handleStartReview = async (config: ReviewConfig) => {
    // Get all providers (including custom ones)
    const providers = getProviders();

    // Build API keys from provider configs
    const apiKeys: Record<string, string> = {};
    providers.forEach(p => {
      if (p.apiKey) {
        apiKeys[p.id] = p.apiKey;
      }
    });

    // Helper to get custom provider config if applicable
    const getCustomProviderConfig = (providerId: string) => {
      const provider = providers.find(p => p.id === providerId);
      if (!provider) return undefined;

      // Only include custom_provider for non-built-in or custom providers
      if ((providerId.startsWith('custom-') || !provider.isBuiltIn) && provider.baseUrl) {
        return {
          id: provider.id,
          name: provider.name,
          base_url: provider.baseUrl,
          api_key: provider.apiKey,
          header_name: provider.headerName || 'Authorization',
          header_prefix: provider.headerPrefix ?? 'Bearer ',
        };
      }
      return undefined;
    };

    // Helper to build team config for Arena
    const buildTeamConfig = (team: typeof config.teamA): ArenaTeamConfig => {
      if (!team) throw new Error('Team config is required');
      const result: Record<string, AgentConfig> = {};
      for (const [role, agent] of Object.entries(team)) {
        const customProvider = getCustomProviderConfig(agent.provider);
        result[role] = {
          provider: agent.provider,
          model: agent.model,
          temperature: 0.2,
          max_tokens: 2048,
          custom_provider: customProvider,
        };
      }
      return result as unknown as ArenaTeamConfig;
    };

    if (config.mode === 'arena') {
      // Arena mode - send to /arena/sessions with two teams
      if (!config.teamA || !config.teamB) {
        toast.error('Konfiguracja zespołów jest wymagana');
        return;
      }

      startArenaMutation.mutate({
        project_id: Number(id),
        team_a_config: buildTeamConfig(config.teamA),
        team_b_config: buildTeamConfig(config.teamB),
        api_keys: Object.keys(apiKeys).length > 0 ? apiKeys : undefined,
      });
    } else {
      // Council mode - send to /projects/{id}/reviews
      const agentConfigs: Record<string, AgentConfig> = {};
      const enabledRoles: string[] = [];

      for (const [role, agent] of Object.entries(config.agents)) {
        if (agent.enabled) {
          enabledRoles.push(role);
          const customProvider = getCustomProviderConfig(agent.provider);
          agentConfigs[role] = {
            provider: agent.provider,
            model: agent.model,
            temperature: 0.2,
            max_tokens: 2048,
            timeout_seconds: agent.timeout || 180,
            custom_provider: customProvider,
          };
        }
      }

      // Add moderator config
      const moderatorCustomProvider = getCustomProviderConfig(config.moderator.provider);
      const moderatorConfig = {
        provider: config.moderator.provider,
        model: config.moderator.model,
        temperature: 0.0,
        max_tokens: 4096,
        timeout_seconds: config.moderator.timeout || 300,
        custom_provider: moderatorCustomProvider,
      };

      startReviewMutation.mutate({
        review_mode: 'council',
        agent_roles: enabledRoles,
        agent_configs: agentConfigs,
        moderator_config: moderatorConfig,
        api_keys: Object.keys(apiKeys).length > 0 ? apiKeys : undefined,
      });
    }

    setIsReviewConfigOpen(false);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Skeleton className="h-10 w-32 mb-4" />
          <div className="flex items-center justify-between">
            <div>
              <Skeleton className="h-9 w-64 mb-2" />
              <Skeleton className="h-5 w-96" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-10 w-28" />
              <Skeleton className="h-10 w-32" />
            </div>
          </div>
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <h2 className="text-2xl font-bold mb-2">Projekt nie znaleziony</h2>
        <p className="text-muted-foreground mb-4">Projekt, którego szukasz, nie istnieje</p>
        <Link to="/projects">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Powrót do Projektów
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/projects">
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Powrót do Projektów
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{project.name}</h1>
            <p className="text-muted-foreground">{project.description || 'Brak opisu'}</p>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => setIsAddingFile(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Dodaj Plik
            </Button>
            <Button
              onClick={() => setIsReviewConfigOpen(true)}
              disabled={startReviewMutation.isPending || startArenaMutation.isPending || (project.files?.length || 0) === 0}
            >
              {(startReviewMutation.isPending || startArenaMutation.isPending) ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uruchamianie...
                </>
              ) : (
                <>
                  <Settings2 className="mr-2 h-4 w-4" />
                  Konfiguruj Review
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Add File Dialog */}
      <Dialog open={isAddingFile} onOpenChange={setIsAddingFile}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Dodaj Plik</DialogTitle>
            <DialogDescription>
              Prześlij plik lub wklej kod, aby dodać go do projektu
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleAddFile}>
            <div className="space-y-4 py-4">
              {/* Upload Mode Toggle */}
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant={uploadMode === 'file' ? 'default' : 'outline'}
                  onClick={() => setUploadMode('file')}
                  size="sm"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Prześlij Plik
                </Button>
                <Button
                  type="button"
                  variant={uploadMode === 'paste' ? 'default' : 'outline'}
                  onClick={() => setUploadMode('paste')}
                  size="sm"
                >
                  <FileCode className="mr-2 h-4 w-4" />
                  Wklej Kod
                </Button>
              </div>

              {uploadMode === 'file' && (
                <div className="space-y-2">
                  <Label htmlFor="file-upload">Wybierz Plik</Label>
                  <Input
                    id="file-upload"
                    type="file"
                    accept=".py,.js,.ts,.tsx,.jsx,.java,.cpp,.c,.cs,.go,.rs,.rb,.php,.swift,.kt,.sql,.sh,.html,.css,.json,.xml,.yaml,.yml,.md,.txt"
                    onChange={handleFileUpload}
                  />
                  <p className="text-xs text-muted-foreground">
                    Obsługiwane: Python, JavaScript, TypeScript, Java, C/C++, Go, Rust i więcej
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="filename">Nazwa Pliku</Label>
                  <Input
                    id="filename"
                    placeholder="app.py"
                    value={newFileName}
                    onChange={(e) => setNewFileName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="language">Język (opcjonalnie)</Label>
                  <Input
                    id="language"
                    placeholder="python"
                    value={newFileLanguage}
                    onChange={(e) => setNewFileLanguage(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="content">Zawartość Kodu</Label>
                <Textarea
                  id="content"
                  placeholder={uploadMode === 'file' ? 'Zawartość pliku pojawi się tutaj...' : "def hello_world():\n    print('Hello, World!')"}
                  value={newFileContent}
                  onChange={(e) => setNewFileContent(e.target.value)}
                  required
                  rows={12}
                  className="font-mono text-sm"
                  readOnly={uploadMode === 'file'}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setIsAddingFile(false);
                  setNewFileName('');
                  setNewFileContent('');
                  setNewFileLanguage('');
                  setUploadMode('paste');
                }}
              >
                Anuluj
              </Button>
              <Button type="submit" disabled={addFileMutation.isPending}>
                {addFileMutation.isPending ? 'Dodawanie...' : 'Dodaj Plik'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Tabs for Files and Reviews */}
      <Tabs defaultValue="files" className="space-y-4">
        <TabsList>
          <TabsTrigger value="files">
            Pliki ({project.files?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="reviews">
            Przeglądy ({reviews?.length || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="files" className="space-y-4">
          {project.files && project.files.length > 0 ? (
            <>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {project.files.map((file) => (
                  <Card
                    key={file.id}
                    className="cursor-pointer hover:shadow-lg transition-shadow"
                    onClick={() => setSelectedFile(file)}
                  >
                    <CardHeader>
                      <div className="flex items-center gap-2">
                        <FileCode className="h-5 w-5 text-primary" />
                        <CardTitle className="text-lg truncate">{file.name}</CardTitle>
                      </div>
                      <CardDescription className="flex items-center gap-2">
                        {file.language && <Badge variant="secondary">{file.language}</Badge>}
                        <span className="text-xs">
                          {(file.size_bytes / 1024).toFixed(1)} KB
                        </span>
                      </CardDescription>
                    </CardHeader>
                  </Card>
                ))}
              </div>

              {/* File Viewer/Editor Dialog */}
              {selectedFile && (
                <Dialog open={!!selectedFile} onOpenChange={() => {
                  setSelectedFile(null);
                  setIsEditing(false);
                  setEditedContent('');
                }}>
                  <DialogContent className="w-[95vw] max-w-5xl max-h-[90vh] flex flex-col">
                    <DialogHeader>
                      <div className="flex items-center justify-between">
                        <div>
                          <DialogTitle className="flex items-center gap-2">
                            <FileCode className="h-5 w-5" />
                            {selectedFile.name}
                          </DialogTitle>
                          <DialogDescription className="flex items-center gap-2 mt-1">
                            {selectedFile.language && (
                              <Badge variant="secondary">{selectedFile.language}</Badge>
                            )}
                            <span>{(selectedFile.size_bytes / 1024).toFixed(1)} KB</span>
                          </DialogDescription>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant={isEditing ? "default" : "outline"}
                            size="sm"
                            onClick={() => {
                              if (!isEditing) {
                                setEditedContent(selectedFile.content || '');
                              }
                              setIsEditing(!isEditing);
                            }}
                          >
                            {isEditing ? (
                              <>
                                <Eye className="mr-2 h-4 w-4" />
                                Tryb Podglądu
                              </>
                            ) : (
                              <>
                                <Edit className="mr-2 h-4 w-4" />
                                Tryb Edycji
                              </>
                            )}
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => {
                              if (confirm('Czy na pewno chcesz usunąć ten plik?')) {
                                deleteFileMutation.mutate(selectedFile.id);
                              }
                            }}
                            disabled={deleteFileMutation.isPending}
                          >
                            {deleteFileMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </DialogHeader>
                    <div className="flex-1 min-h-[500px] overflow-hidden">
                      {isEditing ? (
                        <CodeEditor
                          code={editedContent || selectedFile.content || ''}
                          language={selectedFile.language || 'text'}
                          filename={selectedFile.name}
                          onChange={(code) => setEditedContent(code)}
                          onSave={(code) => {
                            updateFileMutation.mutate({
                              fileId: selectedFile.id,
                              content: code,
                            });
                          }}
                          height="500px"
                        />
                      ) : (
                        <CodeViewer
                          code={selectedFile.content || ''}
                          language={selectedFile.language || 'text'}
                          filename={selectedFile.name}
                        />
                      )}
                    </div>
                    {isEditing && (
                      <DialogFooter className="mt-4">
                        <Button
                          variant="outline"
                          onClick={() => {
                            setIsEditing(false);
                            setEditedContent('');
                          }}
                        >
                          Anuluj
                        </Button>
                        <Button
                          onClick={() => {
                            updateFileMutation.mutate({
                              fileId: selectedFile.id,
                              content: editedContent,
                            });
                          }}
                          disabled={updateFileMutation.isPending}
                        >
                          {updateFileMutation.isPending ? 'Zapisywanie...' : 'Zapisz Zmiany'}
                        </Button>
                      </DialogFooter>
                    )}
                  </DialogContent>
                </Dialog>
              )}
            </>
          ) : (
            <EmptyState
              icon={FileCode}
              title="Brak plików"
              description="Prześlij pliki z kodem do projektu, aby rozpocząć analizę przez agentów AI"
              action={{
                label: 'Dodaj Pierwszy Plik',
                onClick: () => setIsAddingFile(true),
              }}
            />
          )}
        </TabsContent>

        <TabsContent value="reviews" className="space-y-4">
          {reviews && reviews.length > 0 ? (
            <div className="space-y-4">
              {reviews.map((review) => (
                <Link key={review.id} to={`/reviews/${review.id}`}>
                  <Card className="hover:shadow-lg transition-shadow cursor-pointer">
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle>Review #{review.id}</CardTitle>
                        <Badge
                          variant={
                            review.status === 'completed'
                              ? 'success'
                              : review.status === 'failed'
                              ? 'destructive'
                              : review.status === 'running'
                              ? 'warning'
                              : 'default'
                          }
                        >
                          {review.status === 'running' && (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          )}
                          {review.status}
                        </Badge>
                      </div>
                      <CardDescription>
                        {review.agent_count} agentów • {review.issue_count} problemów
                        <br />
                        Utworzono: {new Date(review.created_at).toLocaleString()}
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Play}
              title="Brak przeglądów"
              description="Uruchom przegląd, aby przeanalizować kod przez wielu agentów AI. Najpierw dodaj pliki!"
              action={
                (project.files?.length || 0) > 0
                  ? {
                      label: 'Konfiguruj Przegląd',
                      onClick: () => setIsReviewConfigOpen(true),
                    }
                  : undefined
              }
            />
          )}
        </TabsContent>
      </Tabs>

      {/* Review Configuration Dialog */}
      <ReviewConfigDialog
        open={isReviewConfigOpen}
        onOpenChange={setIsReviewConfigOpen}
        onStartReview={handleStartReview}
        isLoading={startReviewMutation.isPending || startArenaMutation.isPending}
        fileCount={project.files?.length || 0}
        totalCodeSize={project.files?.reduce((acc, f) => acc + f.size_bytes, 0) || 0}
      />
    </div>
  );
}
