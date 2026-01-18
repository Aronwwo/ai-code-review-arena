import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/useAuth';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Code2, Users, MessageSquare, Shield } from 'lucide-react';

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
          Jednoagentowy przegląd kodu z czytelnym raportem. Agent skupia się na
          rzeczywistych błędach, które blokują uruchomienie lub powodują crash.
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
            <CardTitle>Skupiona analiza</CardTitle>
            <CardDescription>
              Jeden agent analizuje poprawność kodu i raportuje realne błędy.
            </CardDescription>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader>
            <MessageSquare className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Jasny raport</CardTitle>
            <CardDescription>
              Zwięzłe podsumowanie i lista problemów z kontekstem.
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

        <Card>
          <CardHeader>
            <Shield className="h-10 w-10 text-primary mb-2" />
            <CardTitle>Bezpieczny przepływ</CardTitle>
            <CardDescription>
              Uwierzytelnianie z cookies, CSRF i rate‑limit. Kod pozostaje lokalnie.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* How it Works */}
      <div className="space-y-6">
        <h2 className="text-3xl font-bold text-center">Jak to działa</h2>
        <div className="grid gap-4 md:grid-cols-3">
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
                <h3 className="font-semibold">Uruchom analizę</h3>
                <p className="text-sm text-muted-foreground">
                  Wybierz providera i model
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

        </div>
      </div>
    </div>
  );
}
