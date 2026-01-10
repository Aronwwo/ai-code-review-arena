import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { Label } from '@/components/ui/Label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Sword, Trophy, AlertCircle, ThumbsUp, ChevronRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { parseApiError } from '@/lib/errorParser';
import { cn } from '@/lib/utils';

interface EvaluationCandidate {
  id: number;
  session_id: number;
  position: string;
  provider: string;
  model: string;
  agent_role: string;
  review_id: number | null;
  issues_found: number;
  parsed_successfully: boolean;
  created_at: string;
}

interface EvaluationVote {
  id: number;
  session_id: number;
  round_number: number;
  choice: 'candidate_a' | 'candidate_b' | 'tie';
  comment: string | null;
  voter_id: number;
  created_at: string;
}

interface EvaluationSession {
  id: number;
  project_id: number;
  created_by: number;
  status: string;
  num_rounds: number;
  current_round: number;
  created_at: string;
  completed_at: string | null;
  candidates: EvaluationCandidate[];
  votes: EvaluationVote[];
}

interface Issue {
  id: number;
  severity: 'info' | 'warning' | 'error';
  category: string;
  title: string;
  description: string;
  file_name: string | null;
  line_start: number | null;
  line_end: number | null;
}

export function ModelDuelCompare() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedWinner, setSelectedWinner] = useState<'candidate_a' | 'candidate_b' | 'tie' | null>(null);
  const [comment, setComment] = useState('');

  // Fetch evaluation session
  const { data: session, isLoading } = useQuery<EvaluationSession>({
    queryKey: ['evaluation', sessionId],
    queryFn: async () => {
      const response = await api.get(`/evaluations/${sessionId}`);
      return response.data;
    },
    refetchInterval: (query) => {
      // Refetch every 3 seconds if reviews are still running
      const data = query.state.data;
      const candidates = data?.candidates || [];
      const allReviewsComplete = candidates.every((c: EvaluationCandidate) => c.review_id !== null);
      return allReviewsComplete ? false : 3000;
    },
  });

  const candidateA = session?.candidates.find(c => c.position === 'A');
  const candidateB = session?.candidates.find(c => c.position === 'B');

  // Fetch issues for candidate A
  const { data: issuesA } = useQuery<Issue[]>({
    queryKey: ['issues', candidateA?.review_id],
    queryFn: async () => {
      if (!candidateA?.review_id) return [];
      const response = await api.get(`/reviews/${candidateA.review_id}/issues`);
      return response.data;
    },
    enabled: !!candidateA?.review_id,
  });

  // Fetch issues for candidate B
  const { data: issuesB } = useQuery<Issue[]>({
    queryKey: ['issues', candidateB?.review_id],
    queryFn: async () => {
      if (!candidateB?.review_id) return [];
      const response = await api.get(`/reviews/${candidateB.review_id}/issues`);
      return response.data;
    },
    enabled: !!candidateB?.review_id,
  });

  // Submit vote mutation
  const voteMutation = useMutation({
    mutationFn: async (data: { choice: string; comment: string | null }) => {
      const response = await api.post(`/evaluations/${sessionId}/vote`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evaluation', sessionId] });
      toast.success('Głos zapisany!');
      setSelectedWinner(null);
      setComment('');

      // Check if session is completed
      if (session && session.current_round + 1 >= session.num_rounds) {
        toast.success('Model Duel zakończony! Przejdź do rankingów.');
        navigate('/rankings');
      }
    },
    onError: (error: unknown) => {
      toast.error(parseApiError(error, 'Nie udało się zapisać głosu'));
    },
  });

  const handleVote = () => {
    if (!selectedWinner) {
      toast.error('Wybierz zwycięzcę');
      return;
    }

    voteMutation.mutate({
      choice: selectedWinner,
      comment: comment || null,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (!session || !candidateA || !candidateB) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <AlertCircle className="h-12 w-12 text-muted-foreground" />
        <p className="text-xl text-muted-foreground">Sesja nie znaleziona</p>
        <Button onClick={() => navigate('/model-duel/setup')}>
          Utwórz nową sesję
        </Button>
      </div>
    );
  }

  const reviewsComplete = candidateA.review_id !== null && candidateB.review_id !== null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sword className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Model Duel</h1>
            <p className="text-muted-foreground">
              Runda {session.current_round + 1} z {session.num_rounds}
            </p>
          </div>
        </div>
        <Badge variant={reviewsComplete ? 'default' : 'secondary'}>
          {reviewsComplete ? 'Gotowe do głosowania' : 'Przegląd w toku...'}
        </Badge>
      </div>

      {/* Comparison Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Candidate A */}
        <CandidateCard
          candidate={candidateA}
          issues={issuesA || []}
          position="A"
          color="blue"
          selected={selectedWinner === 'candidate_a'}
          onSelect={() => setSelectedWinner('candidate_a')}
          disabled={!reviewsComplete || voteMutation.isPending}
        />

        {/* Candidate B */}
        <CandidateCard
          candidate={candidateB}
          issues={issuesB || []}
          position="B"
          color="green"
          selected={selectedWinner === 'candidate_b'}
          onSelect={() => setSelectedWinner('candidate_b')}
          disabled={!reviewsComplete || voteMutation.isPending}
        />
      </div>

      {/* Tie Option */}
      {reviewsComplete && (
        <Card
          className={cn(
            'cursor-pointer transition-all border-2',
            selectedWinner === 'tie' ? 'border-yellow-500 bg-yellow-50' : 'border-transparent hover:border-gray-300'
          )}
          onClick={() => !voteMutation.isPending && setSelectedWinner('tie')}
        >
          <CardContent className="flex items-center justify-center py-6">
            <div className="flex items-center gap-3">
              <Trophy className="h-6 w-6 text-yellow-600" />
              <span className="text-lg font-medium">Remis - oba równie dobre</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comment & Vote */}
      {reviewsComplete && (
        <Card>
          <CardHeader>
            <CardTitle>Twój głos</CardTitle>
            <CardDescription>Dodaj komentarz (opcjonalnie) i zagłosuj</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="comment">Komentarz</Label>
              <Textarea
                id="comment"
                placeholder="Dlaczego wybrałeś tego kandydata?"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                disabled={voteMutation.isPending}
                rows={3}
              />
            </div>

            <div className="flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => navigate('/rankings')}
                disabled={voteMutation.isPending}
              >
                Pomiń
              </Button>
              <Button
                onClick={handleVote}
                disabled={!selectedWinner || voteMutation.isPending}
              >
                {voteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Zagłosuj
                {session.current_round + 1 < session.num_rounds && (
                  <ChevronRight className="ml-2 h-4 w-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Previous Votes */}
      {session.votes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Historia głosów</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {session.votes.map((vote) => (
                <div key={vote.id} className="flex items-center gap-3 text-sm">
                  <Badge variant="outline">Runda {vote.round_number}</Badge>
                  <span>
                    Zwycięzca: <strong>{vote.choice === 'tie' ? 'Remis' : `Kandydat ${vote.choice.slice(-1).toUpperCase()}`}</strong>
                  </span>
                  {vote.comment && <span className="text-muted-foreground">- {vote.comment}</span>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

interface CandidateCardProps {
  candidate: EvaluationCandidate;
  issues: Issue[];
  position: string;
  color: 'blue' | 'green';
  selected: boolean;
  onSelect: () => void;
  disabled: boolean;
}

function CandidateCard({ candidate, issues, position, color, selected, onSelect, disabled }: CandidateCardProps) {
  const colorClasses = {
    blue: {
      border: 'border-blue-500',
      bg: 'bg-blue-50',
      text: 'text-blue-600',
    },
    green: {
      border: 'border-green-500',
      bg: 'bg-green-50',
      text: 'text-green-600',
    },
  };

  const colors = colorClasses[color];

  const severityCounts = {
    error: issues.filter(i => i.severity === 'error').length,
    warning: issues.filter(i => i.severity === 'warning').length,
    info: issues.filter(i => i.severity === 'info').length,
  };

  return (
    <Card
      className={cn(
        'cursor-pointer transition-all border-2',
        selected ? `${colors.border} ${colors.bg}` : 'border-transparent hover:border-gray-300',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
      onClick={() => !disabled && onSelect()}
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className={colors.text}>
            Kandydat {position}
          </CardTitle>
          {selected && <ThumbsUp className={`h-5 w-5 ${colors.text}`} />}
        </div>
        <CardDescription>
          {candidate.provider} / {candidate.model}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-medium mb-2">Rola: {candidate.agent_role}</p>
        </div>

        {candidate.review_id ? (
          <>
            <div className="flex items-center justify-between text-sm">
              <span>Znalezione problemy:</span>
              <Badge variant="secondary">{candidate.issues_found}</Badge>
            </div>

            {candidate.issues_found > 0 && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-red-600">Błędy</span>
                  <Badge variant="destructive">{severityCounts.error}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-yellow-600">Ostrzeżenia</span>
                  <Badge variant="outline" className="border-yellow-600 text-yellow-600">{severityCounts.warning}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-blue-600">Informacje</span>
                  <Badge variant="outline" className="border-blue-600 text-blue-600">{severityCounts.info}</Badge>
                </div>
              </div>
            )}

            {candidate.parsed_successfully ? (
              <Badge variant="default" className="bg-green-500">
                Parsowanie udane
              </Badge>
            ) : (
              <Badge variant="destructive">
                Błąd parsowania
              </Badge>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Trwa przegląd...</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
