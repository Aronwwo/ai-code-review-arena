import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';
import { Trophy, Medal, Award, TrendingUp, Sword } from 'lucide-react';

interface RatingConfig {
  id: number;
  provider: string;
  model: string;
  agent_role: string;
  elo_rating: number;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  created_at: string;
  updated_at: string;
}

interface RatingModel {
  id: number;
  provider: string;
  model: string;
  elo_rating: number;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  created_at: string;
  updated_at: string;
}

const ROLES = ['general', 'security', 'performance', 'style'];

export function Rankings() {
  const [selectedRole, setSelectedRole] = useState<string | null>(null);

  // Fetch config rankings
  const { data: configRankings, isLoading: loadingConfigs } = useQuery<RatingConfig[]>({
    queryKey: ['rankings', 'configs', selectedRole],
    queryFn: async () => {
      const params = selectedRole ? `?agent_role=${selectedRole}` : '';
      const response = await api.get(`/evaluations/rankings/configs${params}`);
      return response.data;
    },
  });

  // Fetch model rankings
  const { data: modelRankings, isLoading: loadingModels } = useQuery<RatingModel[]>({
    queryKey: ['rankings', 'models'],
    queryFn: async () => {
      const response = await api.get('/evaluations/rankings/models');
      return response.data;
    },
  });

  const getRankIcon = (index: number) => {
    if (index === 0) return <Trophy className="h-5 w-5 text-yellow-500" />;
    if (index === 1) return <Medal className="h-5 w-5 text-gray-400" />;
    if (index === 2) return <Award className="h-5 w-5 text-orange-600" />;
    return <span className="text-sm font-medium text-muted-foreground">#{index + 1}</span>;
  };

  const getWinRate = (wins: number, losses: number, ties: number) => {
    const total = wins + losses + ties;
    if (total === 0) return 0;
    return Math.round((wins / total) * 100);
  };

  const getRatingColor = (rating: number) => {
    if (rating >= 1600) return 'text-green-600 font-bold';
    if (rating >= 1500) return 'text-blue-600 font-semibold';
    if (rating >= 1400) return 'text-gray-600';
    return 'text-red-600';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Trophy className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-3xl font-bold">Rankingi ELO</h1>
            <p className="text-muted-foreground">Najlepsze modele AI w przeglądach kodu</p>
          </div>
        </div>
        <Link to="/model-duel/setup">
          <Button>
            <Sword className="mr-2 h-4 w-4" />
            Nowy Duel
          </Button>
        </Link>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="models" className="space-y-6">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="models">Modele (ogólne)</TabsTrigger>
          <TabsTrigger value="configs">Konfiguracje (per rola)</TabsTrigger>
        </TabsList>

        {/* Models Tab */}
        <TabsContent value="models" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Ranking modeli</CardTitle>
              <CardDescription>
                Agregowane rankingi ELO dla modeli (średnia ze wszystkich ról)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingModels ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-6 w-6" />
                      <Skeleton className="h-6 flex-1" />
                    </div>
                  ))}
                </div>
              ) : modelRankings?.length === 0 ? (
                <div className="text-center py-12">
                  <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    Brak danych rankingowych. Rozpocznij Model Duel, aby zbudować rankingi!
                  </p>
                  <Link to="/model-duel/setup">
                    <Button className="mt-4">
                      <Sword className="mr-2 h-4 w-4" />
                      Rozpocznij Duel
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {modelRankings?.map((model, index) => (
                    <div
                      key={model.id}
                      className="flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent transition-colors"
                    >
                      <div className="w-8 flex items-center justify-center">
                        {getRankIcon(index)}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold">{model.model}</span>
                          <Badge variant="outline">{model.provider}</Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{model.games_played} gier</span>
                          <span>{getWinRate(model.wins, model.losses, model.ties)}% win rate</span>
                          <span>{model.wins}W-{model.losses}L-{model.ties}T</span>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className={`text-2xl ${getRatingColor(model.elo_rating)}`}>
                          {Math.round(model.elo_rating)}
                        </div>
                        <div className="text-xs text-muted-foreground">ELO</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Configs Tab */}
        <TabsContent value="configs" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Ranking konfiguracji</CardTitle>
                  <CardDescription>
                    Rankingi ELO dla konkretnych ról agentów
                  </CardDescription>
                </div>
                <Select
                  value={selectedRole || 'all'}
                  onValueChange={(value) => setSelectedRole(value === 'all' ? null : value)}
                >
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Wszystkie role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Wszystkie role</SelectItem>
                    {ROLES.map((role) => (
                      <SelectItem key={role} value={role}>
                        {role}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {loadingConfigs ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-6 w-6" />
                      <Skeleton className="h-6 flex-1" />
                    </div>
                  ))}
                </div>
              ) : configRankings?.length === 0 ? (
                <div className="text-center py-12">
                  <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    {selectedRole
                      ? `Brak danych dla roli: ${selectedRole}`
                      : 'Brak danych rankingowych. Rozpocznij Model Duel!'}
                  </p>
                  <Link to="/model-duel/setup">
                    <Button className="mt-4">
                      <Sword className="mr-2 h-4 w-4" />
                      Rozpocznij Duel
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {configRankings?.map((config, index) => (
                    <div
                      key={config.id}
                      className="flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent transition-colors"
                    >
                      <div className="w-8 flex items-center justify-center">
                        {getRankIcon(index)}
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold">{config.model}</span>
                          <Badge variant="outline">{config.provider}</Badge>
                          <Badge variant="secondary">{config.agent_role}</Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{config.games_played} gier</span>
                          <span>{getWinRate(config.wins, config.losses, config.ties)}% win rate</span>
                          <span>{config.wins}W-{config.losses}L-{config.ties}T</span>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className={`text-2xl ${getRatingColor(config.elo_rating)}`}>
                          {Math.round(config.elo_rating)}
                        </div>
                        <div className="text-xs text-muted-foreground">ELO</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <TrendingUp className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-blue-900 mb-1">Jak działa ranking ELO?</p>
              <p className="text-blue-700">
                System ELO (znany z szachów) porównuje wydajność modeli w Model Duel. Zwycięzca zdobywa punkty,
                przegrany traci, a remis oznacza małą zmianę. Nowe modele zaczynają z 1500 punktami.
                Im więcej gier, tym stabilniejszy rating.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
