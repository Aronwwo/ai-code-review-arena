import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import {
  Bot,
  Shield,
  Code,
  MessageSquare,
  ArrowRight,
  Upload,
  Play,
  FileSearch,
  CheckCircle,
  Trophy,
  Zap,
  Users,
  TrendingUp,
  Swords,
} from 'lucide-react';

export function Landing() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <nav className="border-b border-border">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">AI Code Review Arena</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login">
              <Button variant="ghost">Zaloguj się</Button>
            </Link>
            <Link to="/register">
              <Button>Zarejestruj się</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary mb-4">
            <Trophy className="h-4 w-4" />
            <span className="text-sm font-medium">Porównuj modele AI w walce Arena</span>
          </div>
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
            Analiza kodu przez AI
            <br />
            <span className="text-primary">z rankingiem ELO</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Przeprowadź code review z wybranym modelem AI lub postaw dwa modele przeciwko sobie w Arena Mode.
            System rankingowy ELO pokazuje, który model najlepiej znajduje błędy.
          </p>
          <div className="flex gap-4 justify-center pt-4">
            <Link to="/register">
              <Button size="lg" className="gap-2">
                Rozpocznij <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/login">
              <Button size="lg" variant="outline">
                Zaloguj się
              </Button>
            </Link>
          </div>
          <div className="flex items-center justify-center gap-6 pt-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4" />
              <span>10+ providerów AI</span>
            </div>
            <div className="flex items-center gap-2">
              <Swords className="h-4 w-4" />
              <span>Arena battles</span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              <span>Ranking ELO</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Najważniejsze funkcje</h2>
          <p className="text-muted-foreground">
            Wszystko czego potrzebujesz do porównywania i testowania modeli AI
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Swords className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Arena Mode (A vs B)</h3>
            <p className="text-muted-foreground">
              Postaw dwa modele AI przeciwko sobie. Ten sam kod, różne analizy. Ty decydujesz, który wygrał.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Trophy className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Ranking ELO</h3>
            <p className="text-muted-foreground">
              System rankingowy jak w szachach. Każda walka aktualizuje rating. Zobacz, który model jest najlepszy.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Bot className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Code Review</h3>
            <p className="text-muted-foreground">
              Klasyczna analiza kodu przez wybrany model AI. Szybki raport błędów składniowych i logicznych.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Users className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">10+ providerów AI</h3>
            <p className="text-muted-foreground">
              OpenAI, Anthropic, Groq, Perplexity, Gemini, Ollama i więcej. Testuj wszystkie w jednym miejscu.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Zap className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Real-time updates</h3>
            <p className="text-muted-foreground">
              WebSocket - widzisz postęp analizy na żywo. Licznik sesji i status każdego modelu.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Shield className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Bezpieczny i prywatny</h3>
            <p className="text-muted-foreground">
              JWT w httponly cookies, CSRF protection, rate limiting. Twój kod zostaje u Ciebie.
            </p>
          </Card>
        </div>
      </section>

      {/* Arena Mode Highlight */}
      <section className="container mx-auto px-4 py-16">
        <div className="bg-gradient-to-br from-primary/10 via-primary/5 to-background border border-primary/20 rounded-2xl p-8 md:p-12">
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/20 text-primary mb-4 text-sm font-medium">
                <Swords className="h-4 w-4" />
                Arena Mode
              </div>
              <h2 className="text-3xl md:text-4xl font-bold mb-4">
                Porównuj modele AI w walce
              </h2>
              <p className="text-muted-foreground text-lg mb-6">
                Nie zgaduj, który model jest lepszy. Postaw dwa modele przeciwko sobie, zobacz ich analizy
                side-by-side i zagłosuj na lepszy wynik. System ELO automatycznie aktualizuje rankingi.
              </p>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium">Ten sam kod, różne analizy</p>
                    <p className="text-sm text-muted-foreground">Oba modele analizują identyczny kod</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium">Głosowanie użytkownika</p>
                    <p className="text-sm text-muted-foreground">Ty decydujesz, która analiza jest lepsza</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium">Automatyczny ranking ELO</p>
                    <p className="text-sm text-muted-foreground">Każdy głos aktualizuje rating modeli</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-background/50 backdrop-blur rounded-xl p-6 border">
              <div className="flex items-center justify-between mb-4">
                <div className="text-center flex-1">
                  <div className="font-bold text-lg">Model A</div>
                  <div className="text-sm text-muted-foreground">GPT-4</div>
                  <div className="text-2xl font-bold text-primary mt-2">3 błędy</div>
                </div>
                <div className="text-4xl font-bold text-muted-foreground px-4">VS</div>
                <div className="text-center flex-1">
                  <div className="font-bold text-lg">Model B</div>
                  <div className="text-sm text-muted-foreground">Claude</div>
                  <div className="text-2xl font-bold text-primary mt-2">5 błędów</div>
                </div>
              </div>
              <div className="border-t pt-4 mt-4">
                <div className="text-center text-sm text-muted-foreground mb-3">
                  Który model dał lepszą analizę?
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <Button variant="outline" size="sm">Model A</Button>
                  <Button variant="outline" size="sm">Remis</Button>
                  <Button variant="outline" size="sm">Model B</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Jak to działa</h2>
          <p className="text-muted-foreground">Wybierz tryb i zacznij testować modele AI</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          {/* Code Review Flow */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Bot className="h-5 w-5 text-primary" />
              <h3 className="text-xl font-semibold">Code Review Mode</h3>
            </div>
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0">1</div>
                <div>
                  <p className="font-medium">Upload kodu</p>
                  <p className="text-sm text-muted-foreground">Dodaj pliki do projektu</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0">2</div>
                <div>
                  <p className="font-medium">Wybierz model</p>
                  <p className="text-sm text-muted-foreground">Provider i model AI</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0">3</div>
                <div>
                  <p className="font-medium">Zobacz raport</p>
                  <p className="text-sm text-muted-foreground">Błędy i sugestie poprawek</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Arena Flow */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <Swords className="h-5 w-5 text-primary" />
              <h3 className="text-xl font-semibold">Arena Mode</h3>
            </div>
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0">1</div>
                <div>
                  <p className="font-medium">Wybierz 2 modele</p>
                  <p className="text-sm text-muted-foreground">Model A vs Model B</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0">2</div>
                <div>
                  <p className="font-medium">Zobacz walki side-by-side</p>
                  <p className="text-sm text-muted-foreground">Porównaj analizy obu modeli</p>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-start gap-3">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold shrink-0">3</div>
                <div>
                  <p className="font-medium">Zagłosuj na lepszy</p>
                  <p className="text-sm text-muted-foreground">ELO rating się automatycznie zaktualizuje</p>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Rankings CTA */}
        <div className="text-center bg-muted/30 rounded-xl p-8">
          <Trophy className="h-12 w-12 text-primary mx-auto mb-4" />
          <h3 className="text-2xl font-bold mb-2">Sprawdź aktualne rankingi</h3>
          <p className="text-muted-foreground mb-4">
            Zobacz, które modele AI najlepiej radzą sobie z analizą kodu
          </p>
          <Link to="/register">
            <Button size="lg" className="gap-2">
              Zobacz ranking <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border mt-20">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              <span className="font-semibold">AI Code Review Arena</span>
            </div>
            <div className="flex gap-6 text-sm text-muted-foreground">
              <a
                href="http://localhost:8000/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground transition-colors"
              >
                Dokumentacja API
              </a>
              <span>© 2025 AI Code Review Arena</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
