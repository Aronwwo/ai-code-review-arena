/**
 * ArenaRankings - Rankingi ELO dla pełnych schematów review
 *
 * Pokazuje:
 * - Ranking pełnych schematów konfiguracji (wszystkie 4 role razem)
 * - ELO rating, liczba gier, W-L-T record
 * - Szczegóły konfiguracji każdego schematu
 * - Statystyki (avg_issues_found)
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import type { SchemaRating } from '@/types';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Trophy, Medal, Award, TrendingUp, Swords, ChevronDown, ChevronUp,
  Zap, Shield, Gauge, Palette
} from 'lucide-react';

// Role icons mapping
const ROLE_ICONS = {
  general: Zap,
  security: Shield,
  performance: Gauge,
  style: Palette,
};

const ROLE_LABELS = {
  general: 'Ogólna jakość',
  security: 'Bezpieczeństwo',
  performance: 'Wydajność',
  style: 'Styl i konwencje',
};

export function ArenaRankings() {
  const navigate = useNavigate();
  const [expandedSchemas, setExpandedSchemas] = useState<Set<number>>(new Set());
  const [minGames, setMinGames] = useState<number>(0);

  // Fetch Arena Schema Rankings
  const { data: schemaRankings, isLoading } = useQuery<SchemaRating[]>({
    queryKey: ['arena-rankings', minGames],
    queryFn: async () => {
      const response = await api.get(`/arena/rankings?min_games=${minGames}`);
      return response.data;
    },
  });

  const toggleExpanded = (schemaId: number) => {
    setExpandedSchemas((prev) => {
      const next = new Set(prev);
      if (next.has(schemaId)) {
        next.delete(schemaId);
      } else {
        next.add(schemaId);
      }
      return next;
    });
  };

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

  const getSchemaName = (schemaConfig: Record<string, any>) => {
    // Generate a short name based on the models used
    const models = Object.values(schemaConfig).map((c: any) => c.model);
    const uniqueModels = [...new Set(models)];

    if (uniqueModels.length === 1) {
      return `${uniqueModels[0]} (All roles)`;
    }

    // Show first model + count if multiple
    return `${uniqueModels[0]} +${uniqueModels.length - 1}`;
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Trophy className="h-8 w-8 text-orange-500" />
          <div>
            <h1 className="text-3xl font-bold">Arena Rankings</h1>
            <p className="text-muted-foreground">Rankingi ELO dla pełnych schematów review</p>
          </div>
        </div>
        <Button onClick={() => navigate('/projects')}>
          <Swords className="mr-2 h-4 w-4" />
          Nowa Sesja Arena
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium">Minimalna liczba gier:</label>
            <div className="flex gap-2">
              {[0, 1, 3, 5, 10].map((num) => (
                <Button
                  key={num}
                  variant={minGames === num ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setMinGames(num)}
                >
                  {num === 0 ? 'Wszystkie' : `${num}+`}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Rankings List */}
      <Card>
        <CardHeader>
          <CardTitle>Ranking schematów</CardTitle>
          <CardDescription>
            Pełne schematy konfiguracji (4 role: general, security, performance, style)
            posortowane według ratingu ELO
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-6 w-6" />
                  <Skeleton className="h-20 flex-1" />
                </div>
              ))}
            </div>
          ) : schemaRankings?.length === 0 ? (
            <div className="text-center py-12">
              <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">
                {minGames > 0
                  ? `Brak schematów z co najmniej ${minGames} grami. Spróbuj zmniejszyć filtr.`
                  : 'Brak danych rankingowych. Rozpocznij Combat Arena, aby zbudować rankingi!'}
              </p>
              <Button className="mt-4" onClick={() => navigate('/projects')}>
                <Swords className="mr-2 h-4 w-4" />
                Rozpocznij Arena
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {schemaRankings?.map((schema, index) => {
                const isExpanded = expandedSchemas.has(schema.id);

                return (
                  <div
                    key={schema.id}
                    className="rounded-lg border bg-card transition-colors"
                  >
                    {/* Main Row */}
                    <div className="flex items-center gap-4 p-4 hover:bg-accent cursor-pointer"
                         onClick={() => toggleExpanded(schema.id)}>
                      {/* Rank */}
                      <div className="w-8 flex items-center justify-center flex-shrink-0">
                        {getRankIcon(index)}
                      </div>

                      {/* Schema Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold truncate">
                            {getSchemaName(schema.schema_config)}
                          </span>
                          <Badge variant="secondary" className="text-xs">
                            {schema.games_played} {schema.games_played === 1 ? 'gra' : 'gier'}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <span>{getWinRate(schema.wins, schema.losses, schema.ties)}% win rate</span>
                          <span>{schema.wins}W-{schema.losses}L-{schema.ties}T</span>
                          {schema.avg_issues_found !== null && (
                            <span>
                              ø {schema.avg_issues_found.toFixed(1)} issues
                            </span>
                          )}
                        </div>
                      </div>

                      {/* ELO Rating */}
                      <div className="text-right flex-shrink-0">
                        <div className={`text-2xl ${getRatingColor(schema.elo_rating)}`}>
                          {Math.round(schema.elo_rating)}
                        </div>
                        <div className="text-xs text-muted-foreground">ELO</div>
                      </div>

                      {/* Expand Icon */}
                      <div className="flex-shrink-0">
                        {isExpanded ? (
                          <ChevronUp className="h-5 w-5 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-muted-foreground" />
                        )}
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {isExpanded && (
                      <div className="border-t bg-muted/30 p-4 space-y-3">
                        <div className="text-sm font-medium text-muted-foreground mb-2">
                          Konfiguracja ról:
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {Object.entries(schema.schema_config).map(([role, config]: [string, any]) => {
                            const Icon = ROLE_ICONS[role as keyof typeof ROLE_ICONS] || Zap;
                            const label = ROLE_LABELS[role as keyof typeof ROLE_LABELS] || role;

                            return (
                              <div key={role} className="flex items-center gap-3 p-3 rounded-md bg-card border">
                                <Icon className="h-5 w-5 text-primary flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                  <div className="text-sm font-medium">{label}</div>
                                  <div className="text-xs text-muted-foreground truncate">
                                    {config.provider} / {config.model}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>

                        {/* Metadata */}
                        <div className="pt-3 border-t text-xs text-muted-foreground space-y-1">
                          <div>Schema Hash: <code className="bg-muted px-1 py-0.5 rounded">{schema.schema_hash.substring(0, 16)}...</code></div>
                          <div>Ostatnio użyty: {schema.last_used_at ? new Date(schema.last_used_at).toLocaleString('pl-PL') : 'Nigdy'}</div>
                          <div>Utworzony: {new Date(schema.created_at).toLocaleString('pl-PL')}</div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-orange-50 border-orange-200">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Swords className="h-5 w-5 text-orange-600 mt-0.5" />
            <div className="text-sm">
              <p className="font-medium text-orange-900 mb-1">Jak działa Combat Arena?</p>
              <p className="text-orange-700">
                Combat Arena porównuje dwa pełne schematy konfiguracji review (Schema A vs Schema B).
                Każdy schemat zawiera konfigurację dla wszystkich 4 ról: general, security, performance i style.
                Po wykonaniu obu review, głosujesz który schemat był lepszy. Zwycięzca zdobywa punkty ELO,
                przegrany traci, a remis oznacza małą zmianę. System ten pozwala odkryć najlepsze kombinacje
                modeli i ról dla review kodu.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
