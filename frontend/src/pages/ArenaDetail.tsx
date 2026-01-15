import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { ArenaSession, ArenaVote, ArenaIssue } from '@/types';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { ArrowLeft, Loader2, Trophy, Users, AlertTriangle, CheckCircle, Info, Swords, ThumbsUp, ThumbsDown, Scale } from 'lucide-react';
import { toast } from 'sonner';
import { parseApiError } from '@/lib/errorParser';

export function ArenaDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [voteComment, setVoteComment] = useState('');

  // Fetch arena session
  const { data: session, isLoading, error } = useQuery<ArenaSession>({
    queryKey: ['arena-session', id],
    queryFn: async () => {
      const response = await api.get(`/arena/sessions/${id}`);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      // Poll while running
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 3000;
      }
      return false;
    },
  });

  // Vote mutation
  const voteMutation = useMutation({
    mutationFn: async (vote: ArenaVote) => {
      const response = await api.post(`/arena/sessions/${id}/vote`, vote);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['arena-session', id] });
      toast.success('Głos zapisany pomyślnie!');
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się zagłosować'));
    },
  });

  const handleVote = (winner: 'A' | 'B' | 'tie') => {
    voteMutation.mutate({
      winner,
      comment: voteComment || undefined,
    });
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <Info className="h-4 w-4 text-yellow-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'error':
        return <Badge variant="destructive">error</Badge>;
      case 'warning':
        return <Badge variant="warning">warning</Badge>;
      default:
        return <Badge variant="secondary">info</Badge>;
    }
  };

  const renderIssues = (issues: ArenaIssue[], teamName: string) => {
    if (issues.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
          <p>Zespół {teamName} nie znalazł żadnych problemów</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {issues.map((issue, index) => (
          <div key={index} className="border rounded-lg p-4">
            <div className="flex items-start gap-3">
              {getSeverityIcon(issue.severity)}
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">{issue.title}</span>
                  {getSeverityBadge(issue.severity)}
                  <Badge variant="outline">{issue.category}</Badge>
                </div>
                <p className="text-sm text-muted-foreground">{issue.description}</p>
                {issue.file_name && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Plik: {issue.file_name}
                    {issue.line_start && ` (linia ${issue.line_start}${issue.line_end && issue.line_end !== issue.line_start ? `-${issue.line_end}` : ''})`}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-32" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex flex-col items-center justify-center h-96">
        <AlertTriangle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-2xl font-bold mb-2">Nie znaleziono sesji</h2>
        <p className="text-muted-foreground mb-4">Sesja Areny, której szukasz, nie istnieje</p>
        <Link to="/projects">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Powrót do projektów
          </Button>
        </Link>
      </div>
    );
  }

  const getStatusBadge = () => {
    switch (session.status) {
      case 'completed':
        return <Badge variant="success">Zakończona</Badge>;
      case 'voting':
        return <Badge variant="warning">Oczekuje na głos</Badge>;
      case 'running':
        return (
          <Badge variant="default">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            W trakcie
          </Badge>
        );
      case 'failed':
        return <Badge variant="destructive">Błąd</Badge>;
      default:
        return <Badge variant="secondary">Oczekuje</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to={`/projects/${session.project_id}`}>
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Powrót do projektu
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Swords className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Arena #{session.id}</h1>
              <p className="text-muted-foreground">
                Data utworzenia: {new Date(session.created_at).toLocaleString()}
              </p>
            </div>
          </div>
          {getStatusBadge()}
        </div>
      </div>

      {/* Status messages */}
      {session.status === 'pending' && (
        <Card className="bg-blue-500/10 border-blue-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              <p>Sesja oczekuje na uruchomienie...</p>
            </div>
          </CardContent>
        </Card>
      )}

      {session.status === 'running' && (
        <Card className="bg-yellow-500/10 border-yellow-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-yellow-500" />
              <p>Zespoły analizują kod... To może potrwać kilka minut.</p>
            </div>
          </CardContent>
        </Card>
      )}

      {session.status === 'failed' && (
        <Card className="bg-red-500/10 border-red-500/20">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
              <div>
                <p className="font-medium text-red-600">Wystapil blad podczas analizy</p>
                {session.error_message && (
                  <p className="text-sm text-muted-foreground mt-1">{session.error_message}</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Winner announcement (after voting) */}
      {session.status === 'completed' && session.winner && (
        <Card className="bg-green-500/10 border-green-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Trophy className="h-6 w-6 text-yellow-500" />
              <div>
                <p className="font-medium text-green-600">
                  {session.winner === 'tie'
                    ? 'Wynik: Remis!'
                    : `Zwycięzca: Zespół ${session.winner}!`}
                </p>
                {session.vote_comment && (
                  <p className="text-sm text-muted-foreground mt-1">
                    Komentarz: {session.vote_comment}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results grid */}
      {(session.status === 'voting' || session.status === 'completed') && (
        <>
          <div className="grid gap-6 md:grid-cols-2">
            {/* Team A */}
            <Card className={`${session.winner === 'A' ? 'ring-2 ring-green-500' : ''}`}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-blue-500" />
                    <CardTitle>Zespół A</CardTitle>
                    {session.winner === 'A' && (
                      <Trophy className="h-5 w-5 text-yellow-500" />
                    )}
                  </div>
                  <Badge variant="outline">
                    {session.team_a_issues?.length || 0} problemow
                  </Badge>
                </div>
                <CardDescription>
                  {Object.entries(session.team_a_config || {}).map(([role, config]) => (
                    <span key={role} className="mr-2">
                      {role}: {(config as { model?: string })?.model || 'N/A'}
                    </span>
                  ))}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {session.team_a_summary && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <p className="text-sm font-medium mb-2">Podsumowanie</p>
                    <p className="text-sm whitespace-pre-wrap">{session.team_a_summary}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium mb-3">Znalezione problemy</p>
                  {renderIssues(session.team_a_issues || [], 'A')}
                </div>
              </CardContent>
            </Card>

            {/* Team B */}
            <Card className={`${session.winner === 'B' ? 'ring-2 ring-green-500' : ''}`}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="h-5 w-5 text-red-500" />
                    <CardTitle>Zespół B</CardTitle>
                    {session.winner === 'B' && (
                      <Trophy className="h-5 w-5 text-yellow-500" />
                    )}
                  </div>
                  <Badge variant="outline">
                    {session.team_b_issues?.length || 0} problemow
                  </Badge>
                </div>
                <CardDescription>
                  {Object.entries(session.team_b_config || {}).map(([role, config]) => (
                    <span key={role} className="mr-2">
                      {role}: {(config as { model?: string })?.model || 'N/A'}
                    </span>
                  ))}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {session.team_b_summary && (
                  <div className="bg-muted/50 p-4 rounded-lg">
                    <p className="text-sm font-medium mb-2">Podsumowanie</p>
                    <p className="text-sm whitespace-pre-wrap">{session.team_b_summary}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium mb-3">Znalezione problemy</p>
                  {renderIssues(session.team_b_issues || [], 'B')}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Voting section */}
          {session.status === 'voting' && !session.winner && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Scale className="h-5 w-5" />
                  Zagłosuj na zwycięzcę
                </CardTitle>
                <CardDescription>
                  Który zespół dał lepsze wyniki analizy kodu? Twój głos wpływa na ranking ELO zespołów.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Komentarz (opcjonalnie)</Label>
                  <Textarea
                    placeholder="Dlaczego wybrałeś ten zespół?"
                    value={voteComment}
                    onChange={(e) => setVoteComment(e.target.value)}
                    rows={3}
                  />
                </div>
                <div className="flex gap-4 justify-center">
                  <Button
                    size="lg"
                    variant="outline"
                    className="flex-1 max-w-xs border-blue-500 hover:bg-blue-500/10"
                    onClick={() => handleVote('A')}
                    disabled={voteMutation.isPending}
                  >
                    <ThumbsUp className="mr-2 h-5 w-5 text-blue-500" />
                    Zespół A wygrywa
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    className="flex-1 max-w-xs"
                    onClick={() => handleVote('tie')}
                    disabled={voteMutation.isPending}
                  >
                    <Scale className="mr-2 h-5 w-5" />
                    Remis
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    className="flex-1 max-w-xs border-red-500 hover:bg-red-500/10"
                    onClick={() => handleVote('B')}
                    disabled={voteMutation.isPending}
                  >
                    <ThumbsDown className="mr-2 h-5 w-5 text-red-500" />
                    Zespół B wygrywa
                  </Button>
                </div>
                {voteMutation.isPending && (
                  <div className="flex items-center justify-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Zapisywanie głosu...</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
