import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/useAuth';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Code2, Users, MessageSquare, Shield, Zap, Target } from 'lucide-react';

export function Home() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="space-y-12">
      {/* Hero */}
      <div className="text-center space-y-4 py-12">
        <h1 className="text-5xl font-bold tracking-tight">
          AI Code Review Arena
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Wieloagentowy przegląd kodu z trybem Rady i Areny. Agenci analizują kod z różnych
          perspektyw, a moderator podsumowuje najważniejsze wnioski.
        </p>
        <div className="flex justify-center gap-4 mt-8">
          {isAuthenticated ? (
            <Link to="/projects">
              <Button size="lg">
                Przejdź do projektów
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/register">
                <Button size="lg">Rozpocznij</Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline">
                  Zaloguj się
                </Button>
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Features */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <Users className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Wieloagentowa analiza</CardTitle>
            <CardDescription>
              Cztery role: ogólny, bezpieczeństwo, wydajność i styl. Każda ma własny model.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <MessageSquare className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Tryb Rady</CardTitle>
            <CardDescription>
              Jeden zespół agentów dochodzi do wspólnego wniosku i raportu.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <Target className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Tryb Areny</CardTitle>
            <CardDescription>
              Dwa zespoły analizują kod, a Ty wybierasz lepszy wynik. Głosy budują ranking.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <Shield className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Bezpieczeństwo przede wszystkim</CardTitle>
            <CardDescription>
              Dedykowany agent bezpieczeństwa identyfikuje podatności, ryzyko wstrzyknięć
              i niebezpieczne wzorce w kodzie.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <Zap className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Optymalizacja wydajności</CardTitle>
            <CardDescription>
              Agent wydajności wykrywa nieefektywności algorytmiczne, zapytania N+1
              i możliwości optymalizacji.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <Code2 className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Elastyczne modele</CardTitle>
            <CardDescription>
              Działa z mockiem do testów, Ollamą lokalnie lub zewnętrznymi API.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* How it Works */}
      <div className="space-y-6">
        <h2 className="text-3xl font-bold text-center">Jak to działa</h2>
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-2">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center mx-auto font-bold text-lg">
                  1
                </div>
                <h3 className="font-semibold">Utwórz projekt</h3>
                <p className="text-sm text-muted-foreground">
                  Dodaj pliki z kodem do analizy
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-2">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center mx-auto font-bold text-lg">
                  2
                </div>
                <h3 className="font-semibold">Wybierz tryb</h3>
                <p className="text-sm text-muted-foreground">
                  Rada dla konsensusu lub Arena dla porównania
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-2">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center mx-auto font-bold text-lg">
                  3
                </div>
                <h3 className="font-semibold">Zobacz wyniki</h3>
                <p className="text-sm text-muted-foreground">
                  Raport moderatora, problemy i sugestie
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="text-center space-y-2">
                <div className="bg-primary text-primary-foreground rounded-full w-12 h-12 flex items-center justify-center mx-auto font-bold text-lg">
                  4
                </div>
                <h3 className="font-semibold">Głębsza analiza</h3>
                <p className="text-sm text-muted-foreground">
                  Debaty i dyskusje agentów dla wybranych problemów
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
