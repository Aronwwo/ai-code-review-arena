import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import {
  Bot,
  Shield,
  Zap,
  Code,
  MessageSquare,
  ArrowRight,
  Upload,
  Play,
  FileSearch,
  CheckCircle,
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
        <div className="max-w-3xl mx-auto space-y-6">
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
            Wieloagentowy przegląd kodu AI
            <br />
            <span className="text-primary">Napędzany lokalnymi modelami LLM</span>
          </h1>
          <p className="text-xl text-muted-foreground">
            Wgraj swój kod i uzyskaj kompleksowe przeglądy od wyspecjalizowanych agentów AI.
            Obserwuj ich debaty w trybie Rady lub Areny. 100% darmowy i lokalny z Ollama.
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
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Funkcje</h2>
          <p className="text-muted-foreground">
            Wszystko, czego potrzebujesz do profesjonalnego przeglądu kodu z AI
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Bot className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Wieloagentowy przegląd</h3>
            <p className="text-muted-foreground">
              Wyspecjalizowani agenci analizują kod z różnych perspektyw: Ogólnej, Bezpieczeństwa,
              Wydajności i Stylu.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <MessageSquare className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Konwersacje agentów</h3>
            <p className="text-muted-foreground">
              Tryb Rady dla wspólnej dyskusji lub Tryb Areny dla debaty oskarżyciel vs obrońca
              z werdyktem moderatora.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Shield className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Bezpieczny i prywatny</h3>
            <p className="text-muted-foreground">
              Autoryzacja JWT, limitowanie zapytań, walidacja danych. Twój kod pozostaje na Twoim
              komputerze z lokalnymi LLM.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Zap className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Darmowy i lokalny</h3>
            <p className="text-muted-foreground">
              Działa z Ollama, darmowym Groq, Gemini lub całkowicie offline. Bez kosztownych API.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <Code className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Nowoczesny interfejs</h3>
            <p className="text-muted-foreground">
              Zbudowany z React, TypeScript, TailwindCSS i shadcn/ui dla profesjonalnego wyglądu.
            </p>
          </Card>
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <FileSearch className="h-10 w-10 text-primary mb-4" />
            <h3 className="text-xl font-semibold mb-2">Kompleksowe wyniki</h3>
            <p className="text-muted-foreground">
              Filtruj i sortuj problemy według ważności i kategorii. Przeglądaj szczegółowe
              rekomendacje i fragmenty kodu.
            </p>
          </Card>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="container mx-auto px-4 py-16 bg-muted/30 rounded-lg">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold mb-4">Jak to działa</h2>
          <p className="text-muted-foreground">Zacznij w czterech prostych krokach</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="p-6 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground mb-4 text-xl font-bold">
              1
            </div>
            <Upload className="h-8 w-8 mx-auto mb-3 text-primary" />
            <h3 className="text-lg font-semibold mb-2">Wgraj kod</h3>
            <p className="text-sm text-muted-foreground">
              Utwórz projekt i wgraj pliki z kodem
            </p>
          </Card>
          <Card className="p-6 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground mb-4 text-xl font-bold">
              2
            </div>
            <Play className="h-8 w-8 mx-auto mb-3 text-primary" />
            <h3 className="text-lg font-semibold mb-2">Uruchom przegląd</h3>
            <p className="text-sm text-muted-foreground">
              Wybierz tryb Rady lub Areny i wybierz agentów
            </p>
          </Card>
          <Card className="p-6 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground mb-4 text-xl font-bold">
              3
            </div>
            <Bot className="h-8 w-8 mx-auto mb-3 text-primary" />
            <h3 className="text-lg font-semibold mb-2">Analiza AI</h3>
            <p className="text-sm text-muted-foreground">
              Agenci analizują i dyskutują o Twoim kodzie
            </p>
          </Card>
          <Card className="p-6 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary text-primary-foreground mb-4 text-xl font-bold">
              4
            </div>
            <CheckCircle className="h-8 w-8 mx-auto mb-3 text-primary" />
            <h3 className="text-lg font-semibold mb-2">Zobacz wyniki</h3>
            <p className="text-sm text-muted-foreground">
              Otrzymaj szczegółowe problemy, rekomendacje i wnioski
            </p>
          </Card>
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
                href="http://localhost:8080/docs"
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
