import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { Project, ProjectCreate } from '@/types';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Textarea } from '@/components/ui/Textarea';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/EmptyState';
import { Plus, FolderGit2, FileCode, ClipboardList, ChevronLeft, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { parseApiError } from '@/lib/errorParser';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export function Projects() {
  const [isCreating, setIsCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;
  const queryClient = useQueryClient();

  // Fetch projects with pagination
  const { data: projectsData, isLoading } = useQuery<PaginatedResponse<Project>>({
    queryKey: ['projects', currentPage, pageSize],
    queryFn: async () => {
      const response = await api.get(`/projects?page=${currentPage}&page_size=${pageSize}`);
      return response.data;
    },
  });

  const projects = projectsData?.items || [];

  // Create project mutation
  const createMutation = useMutation({
    mutationFn: async (data: ProjectCreate) => {
      const response = await api.post('/projects', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setIsCreating(false);
      setNewProjectName('');
      setNewProjectDescription('');
      toast.success('Projekt utworzony pomyślnie!');
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się utworzyć projektu'));
    },
  });

  const handleCreateProject = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      toast.error('Nazwa projektu jest wymagana');
      return;
    }
    createMutation.mutate({
      name: newProjectName,
      description: newProjectDescription || undefined,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-9 w-32 mb-2" />
            <Skeleton className="h-5 w-64" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-8 w-8 mb-4" />
                <Skeleton className="h-6 w-3/4 mb-2" />
                <Skeleton className="h-4 w-full" />
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Projekty</h1>
          <p className="text-muted-foreground">Zarządzaj projektami i uruchamiaj przeglądy kodu</p>
        </div>
        <Button onClick={() => setIsCreating(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nowy Projekt
        </Button>
      </div>

      <Dialog open={isCreating} onOpenChange={setIsCreating}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nowy projekt</DialogTitle>
            <DialogDescription>
              Utwórz projekt, aby dodać pliki i uruchomić przegląd
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreateProject}>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nazwa projektu</Label>
                <Input
                  id="name"
                  placeholder="Moja Aplikacja Web"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Opis (opcjonalnie)</Label>
                <Textarea
                  id="description"
                  placeholder="Aplikacja React z backendem FastAPI"
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreating(false)}
              >
                Anuluj
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Tworzenie...' : 'Utwórz projekt'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {projects.length === 0 && projectsData?.total === 0 ? (
        <EmptyState
          icon={FolderGit2}
          title="Brak projektów"
          description="Utwórz pierwszy projekt, aby dodać pliki i rozpocząć analizę"
          action={{
            label: 'Utwórz pierwszy projekt',
            onClick: () => setIsCreating(true),
          }}
        />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link key={project.id} to={`/projects/${project.id}`}>
                <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <FolderGit2 className="h-8 w-8 text-primary" />
                    </div>
                    <CardTitle className="mt-4">{project.name}</CardTitle>
                    <CardDescription className="line-clamp-2">
                      {project.description || 'Brak opisu'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                      <div className="flex items-center">
                        <FileCode className="mr-1 h-4 w-4" />
                        {project.file_count} plików
                      </div>
                      <div className="flex items-center">
                        <ClipboardList className="mr-1 h-4 w-4" />
                        {project.review_count} przeglądów
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {/* Pagination Controls */}
          {projectsData && projectsData.total_pages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-6">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={!projectsData.has_prev}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Poprzednia
              </Button>
              <span className="text-sm text-muted-foreground">
                Strona {projectsData.page} z {projectsData.total_pages} ({projectsData.total} projektów)
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(projectsData.total_pages, p + 1))}
                disabled={!projectsData.has_next}
              >
                Następna
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
