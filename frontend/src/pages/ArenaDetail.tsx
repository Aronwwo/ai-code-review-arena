/**
 * ArenaDetail - Strona szczegółów sesji Combat Arena
 *
 * Pokazuje:
 * - Status sesji Arena (pending/running/completed/failed)
 * - Konfiguracje schematów A i B
 * - Szczegóły dwóch review (A i B)
 * - Porównanie wyników (liczba issues)
 * - Formularz głosowania (jeśli completed i nie zagłosowano)
 * - Wynik głosowania i ELO (jeśli zagłosowano)
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { ArenaSession, Review, ArenaWinner } from '@/types';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import {
  ArrowLeft, Swords, Trophy, Clock, CheckCircle2, XCircle,
  AlertCircle, Loader2, TrendingUp, FileCode
} from 'lucide-react';
import { toast } from 'sonner';
import { parseApiError } from '@/lib/errorParser';
import type { AgentConfig } from '@/types';
import type { LucideIcon } from 'lucide-react';

export function ArenaDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedWinner, setSelectedWinner] = useState<ArenaWinner | null>(null);
  const [comment, setComment] = useState('');

  // Fetch Arena Session
  const { data: session, isLoading: sessionLoading } = useQuery<ArenaSession>({
    queryKey: ['arena-session', id],
    queryFn: async () => {
      const response = await api.get(`/arena/sessions/${id}`);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === 'running' || data?.status === 'pending' ? 3000 : false;
    },
  });

  // Fetch Review A
  const { data: reviewA, isLoading: loadingA } = useQuery<Review>({
    queryKey: ['review', session?.review_a_id],
    queryFn: async () => {
      const response = await api.get(`/reviews/${session?.review_a_id}`);
      return response.data;
    },
    enabled: !!session?.review_a_id,
  });

  // Fetch Review B
  const { data: reviewB, isLoading: loadingB } = useQuery<Review>({
    queryKey: ['review', session?.review_b_id],
    queryFn: async () => {
      const response = await api.get(`/reviews/${session?.review_b_id}`);
      return response.data;
    },
    enabled: !!session?.review_b_id,
  });

  // Submit Vote Mutation
  const voteMutation = useMutation({
    mutationFn: async () => {
      if (!selectedWinner) throw new Error('Wybierz zwycięzcę');

      const response = await api.post(`/arena/sessions/${id}/vote`, {
        winner: selectedWinner,
        comment: comment || undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success('Głos zapisany! Rankingi ELO zaktualizowane.');
      queryClient.invalidateQueries({ queryKey: ['arena-session', id] });
      queryClient.invalidateQueries({ queryKey: ['arena-rankings'] });
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się zapisać głosu'));
    },
  });

  if (sessionLoading) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <Skeleton className="h-8 w-64 mb-6" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!session) {
    return (
      <div className="container mx-auto p-6 max-w-7xl">
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col items-center gap-4">
              <AlertCircle className="h-12 w-12 text-muted-foreground" />
              <p className="text-muted-foreground">Sesja Arena nie znaleziona</p>
              <Button onClick={() => navigate('/projects')} variant="outline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Powrót do projektów
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { variant: 'default' | 'secondary' | 'destructive' | 'success'; icon: LucideIcon; label: string }> = {
      pending: { variant: 'secondary', icon: Clock, label: 'Oczekuje' },
      running: { variant: 'default', icon: Loader2, label: 'Uruchomione' },
      completed: { variant: 'success', icon: CheckCircle2, label: 'Zakończone' },
      failed: { variant: 'destructive', icon: XCircle, label: 'Błąd' },
    };

    const config = variants[status] || variants.pending;
    const Icon = config.icon;

    return (
      <Badge variant={config.variant} className="gap-1">
        <Icon className={`h-3 w-3 ${status === 'running' ? 'animate-spin' : ''}`} />
        {config.label}
      </Badge>
    );
  };

  const canVote = session.status === 'completed' && !session.winner;
  const hasVoted = !!session.winner;
  const schemaAConfig = session.schema_a_config as Record<string, AgentConfig>;
  const schemaBConfig = session.schema_b_config as Record<string, AgentConfig>;

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <Swords className="h-6 w-6 text-orange-500" />
              <h1 className="text-3xl font-bold">Combat Arena #{id}</h1>
              {getStatusBadge(session.status)}
            </div>
            <p className="text-muted-foreground mt-1">
              Porównanie dwóch schematów review - Schema A vs Schema B
            </p>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {session.error_message && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Błąd podczas wykonywania Arena</p>
                <p className="text-sm text-muted-foreground mt-1">{session.error_message}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Vote Result (if voted) */}
      {hasVoted && (
        <Card className="border-green-500/50 bg-green-500/5">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Trophy className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="font-semibold text-lg">Zwycięzca: Schema {session.winner}</p>
                  {session.vote_comment && (
                    <p className="text-sm text-muted-foreground mt-1">{session.vote_comment}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">
                    Głosowano: {new Date(session.voted_at!).toLocaleString('pl-PL')}
                  </p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={() => navigate('/arena/rankings')}>
                <TrendingUp className="mr-2 h-4 w-4" />
                Zobacz Rankingi
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comparison Grid */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Schema A */}
        <Card className={hasVoted && session.winner === 'A' ? 'border-green-500' : ''}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                Schema A
                {hasVoted && session.winner === 'A' && (
                  <Trophy className="h-5 w-5 text-yellow-500" />
                )}
              </CardTitle>
              {reviewA && (
                <Badge variant={reviewA.status === 'completed' ? 'success' : 'default'}>
                  {reviewA.issue_count} issues
                </Badge>
              )}
            </div>
            <CardDescription>
              {loadingA ? 'Ładowanie...' : `Review #${session.review_a_id}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(schemaAConfig).map(([role, config]) => (
              <div key={role} className="flex items-center justify-between text-sm">
                <span className="font-medium capitalize">{role}:</span>
                <span className="text-muted-foreground">
                  {config.provider} / {config.model}
                </span>
              </div>
            ))}
            {reviewA && (
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-4"
                onClick={() => navigate(`/reviews/${session.review_a_id}`)}
              >
                <FileCode className="mr-2 h-4 w-4" />
                Zobacz Review A
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Schema B */}
        <Card className={hasVoted && session.winner === 'B' ? 'border-green-500' : ''}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                Schema B
                {hasVoted && session.winner === 'B' && (
                  <Trophy className="h-5 w-5 text-yellow-500" />
                )}
              </CardTitle>
              {reviewB && (
                <Badge variant={reviewB.status === 'completed' ? 'success' : 'default'}>
                  {reviewB.issue_count} issues
                </Badge>
              )}
            </div>
            <CardDescription>
              {loadingB ? 'Ładowanie...' : `Review #${session.review_b_id}`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(schemaBConfig).map(([role, config]) => (
              <div key={role} className="flex items-center justify-between text-sm">
                <span className="font-medium capitalize">{role}:</span>
                <span className="text-muted-foreground">
                  {config.provider} / {config.model}
                </span>
              </div>
            ))}
            {reviewB && (
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-4"
                onClick={() => navigate(`/reviews/${session.review_b_id}`)}
              >
                <FileCode className="mr-2 h-4 w-4" />
                Zobacz Review B
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Voting Section */}
      {canVote && (
        <Card>
          <CardHeader>
            <CardTitle>Głosowanie</CardTitle>
            <CardDescription>
              Który schemat był lepszy? Twój głos zaktualizuje rankingi ELO.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3">
              <Button
                variant={selectedWinner === 'A' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setSelectedWinner('A')}
              >
                Schema A
              </Button>
              <Button
                variant={selectedWinner === 'tie' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setSelectedWinner('tie')}
              >
                Remis
              </Button>
              <Button
                variant={selectedWinner === 'B' ? 'default' : 'outline'}
                className="flex-1"
                onClick={() => setSelectedWinner('B')}
              >
                Schema B
              </Button>
            </div>

            <div>
              <Label htmlFor="comment">Komentarz (opcjonalnie)</Label>
              <Textarea
                id="comment"
                placeholder="Dlaczego ten schemat jest lepszy?"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
                className="mt-1.5"
              />
            </div>

            <Button
              onClick={() => voteMutation.mutate()}
              disabled={!selectedWinner || voteMutation.isPending}
              className="w-full"
            >
              {voteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Zapisywanie...
                </>
              ) : (
                <>
                  <Trophy className="mr-2 h-4 w-4" />
                  Zapisz Głos
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
