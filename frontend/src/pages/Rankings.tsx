import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Trophy } from 'lucide-react';
import type { TeamRating } from '@/types';

export function Rankings() {
  const { data: arenaRankings, isLoading: arenaLoading } = useQuery<TeamRating[]>({
    queryKey: ['arena-rankings'],
    queryFn: async () => {
      const response = await api.get('/arena/rankings');
      return response.data;
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Trophy className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">Ranking Areny</h1>
          <p className="text-muted-foreground">ELO tylko z trybu Arena (A vs B)</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Rankingi Arena (A vs B)</CardTitle>
          <CardDescription>Ranking konfiguracji modeli na podstawie głosów</CardDescription>
        </CardHeader>
        <CardContent>
          {arenaLoading ? (
            <div className="space-y-3">
              {[1, 2].map((row) => (
                <div key={row} className="flex items-center gap-4">
                  <Skeleton className="h-6 w-24" />
                  <Skeleton className="h-6 w-40" />
                  <Skeleton className="h-6 flex-1" />
                </div>
              ))}
            </div>
          ) : !arenaRankings || arenaRankings.length === 0 ? (
            <p className="text-sm text-muted-foreground">Brak głosów Arena.</p>
          ) : (
            <div className="space-y-3">
              {arenaRankings.map((team, index) => (
                <div key={team.id} className="flex items-center gap-4 p-3 rounded-lg border">
                  <div className="w-8 text-center font-semibold text-muted-foreground">#{index + 1}</div>
                  <div className="flex-1">
                    <div className="font-medium">
                      {team.config?.provider && team.config?.model
                        ? `${team.config.provider} / ${team.config.model}`
                        : 'Nieznany model'}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {team.wins} wygr. / {team.losses} przegr. / {team.ties} remis ({team.win_rate}% win rate)
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      ELO: {Math.round(team.elo_rating)}
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      Gry: {team.games_played}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
