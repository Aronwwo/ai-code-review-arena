import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { TeamRating } from '@/types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Trophy, Medal, Award, TrendingUp, Swords, Users } from 'lucide-react';

export function Rankings() {
  // Fetch Arena team rankings
  const { data: teamRankings, isLoading } = useQuery<TeamRating[]>({
    queryKey: ['arena-rankings'],
    queryFn: async () => {
      const response = await api.get('/arena/rankings');
      return response.data;
    },
  });

  const getRankIcon = (index: number) => {
    if (index === 0) return <Trophy className="h-5 w-5 text-yellow-500" />;
    if (index === 1) return <Medal className="h-5 w-5 text-gray-400" />;
    if (index === 2) return <Award className="h-5 w-5 text-orange-600" />;
    return <span className="text-sm font-medium text-muted-foreground">#{index + 1}</span>;
  };

  const getEloColor = (elo: number) => {
    if (elo >= 1600) return 'text-green-600 font-bold';
    if (elo >= 1500) return 'text-blue-600 font-semibold';
    if (elo >= 1400) return 'text-gray-600';
    return 'text-orange-600';
  };

  const formatTeamConfig = (config: TeamRating['config']) => {
    if (!config) return ['Brak konfiguracji'];
    const roles = ['general', 'security', 'performance', 'style'];
    return roles.map((role) => {
      const roleConfig = config[role as keyof typeof config] as { provider?: string; model?: string } | undefined;
      const provider = roleConfig?.provider || 'brak';
      const model = roleConfig?.model || 'brak';
      return `${role}: ${provider}/${model}`;
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Trophy className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Rankingi Areny</h1>
            <p className="text-muted-foreground">Ranking zespołów AI oparty o głosy w trybie Areny</p>
          </div>
        </div>
      </div>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Swords className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-blue-900 mb-1">Jak działają rankingi?</p>
              <p className="text-blue-700">
                Rankingi bazują na ELO. Każdy zespół (unikalna konfiguracja ról i modeli)
                startuje od 1500. Wygrana podnosi rating, przegrana go obniża.
                Tylko głosy z Areny wpływają na ranking.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Rankings List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Ranking zespołów
          </CardTitle>
          <CardDescription>
            Zespoły posortowane według ELO (najlepsze na górze)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-6 w-6" />
                  <Skeleton className="h-6 flex-1" />
                </div>
              ))}
            </div>
          ) : !teamRankings || teamRankings.length === 0 ? (
            <div className="text-center py-12">
              <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                Brak danych rankingowych. Uruchom sesję Areny i zagłosuj, aby zbudować ranking.
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Rankingi są budowane wyłącznie na podstawie głosów w trybie Areny.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {teamRankings.map((team, index) => (
                <div
                  key={team.id}
                  className="flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent transition-colors"
                >
                  <div className="w-8 flex items-center justify-center">
                    {getRankIcon(index)}
                  </div>

                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-semibold">Zespol #{team.id}</span>
                      <Badge variant="outline" className="text-xs">
                        {team.games_played} gier
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <div className="font-mono text-xs space-y-1">
                        {formatTeamConfig(team.config).map((line) => (
                          <div key={line}>{line}</div>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                      <span className="text-green-600">{team.wins}W</span>
                      <span className="text-red-600">{team.losses}L</span>
                      <span className="text-yellow-600">{team.ties}T</span>
                      <span>{team.win_rate}% win rate</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className={`text-2xl ${getEloColor(team.elo_rating)}`}>
                      {Math.round(team.elo_rating)}
                    </div>
                    <div className="text-xs text-muted-foreground">ELO</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Summary */}
      {teamRankings && teamRankings.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Laczna liczba zespolow</p>
                  <p className="text-2xl font-bold">{teamRankings.length}</p>
                </div>
                <Users className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Laczna liczba gier</p>
                  <p className="text-2xl font-bold">
                    {Math.floor(teamRankings.reduce((acc, t) => acc + t.games_played, 0) / 2)}
                  </p>
                </div>
                <Swords className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Najwyzszy ELO</p>
                  <p className="text-2xl font-bold">
                    {Math.round(Math.max(...teamRankings.map(t => t.elo_rating)))}
                  </p>
                </div>
                <Trophy className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
