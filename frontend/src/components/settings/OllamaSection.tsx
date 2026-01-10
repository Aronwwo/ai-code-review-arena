import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Separator } from '@/components/ui/Separator';
import { Label } from '@/components/ui/Label';
import { RefreshCw, AlertCircle, Cpu } from 'lucide-react';

interface OllamaSectionProps {
  models: string[];
  isLoading: boolean;
  error: unknown;
  onRefresh: () => void;
  isCached?: boolean;
}

export function OllamaSection({ models, isLoading, error, onRefresh, isCached }: OllamaSectionProps) {
  return (
    <>
      <Separator />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-5 w-5" />
              <CardTitle>Ollama (Lokalny)</CardTitle>
            </div>
            <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Odśwież
            </Button>
          </div>
          <CardDescription>
            Darmowy LLM działający lokalnie na Twoim komputerze
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {error ? (
            <div className="flex items-start gap-3 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
              <AlertCircle className="h-5 w-5 text-destructive mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Nie można połączyć się z Ollama</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Upewnij się że Ollama jest uruchomiona: <code className="bg-muted px-1 rounded">ollama serve</code>
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <Label>Dostępne Modele</Label>
                {isCached && (
                  <span className="text-xs text-muted-foreground">Z cache</span>
                )}
              </div>
              {models.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Brak zainstalowanych modeli. Uruchom: <code className="bg-muted px-1 rounded">ollama pull qwen2.5-coder</code>
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {models.map((model) => (
                    <Badge key={model} variant="secondary">
                      {model}
                    </Badge>
                  ))}
                </div>
              )}
            </>
          )}

          <div className="pt-4 space-y-2">
            <Label className="text-sm font-medium">Instalacja Modelu</Label>
            <div className="bg-muted p-3 rounded-lg font-mono text-sm space-y-1">
              <div># Zainstaluj mały model (szybki)</div>
              <div className="text-primary">ollama pull qwen2.5-coder:0.5b</div>
              <div className="mt-2"># Lub średni model (lepszy)</div>
              <div className="text-primary">ollama pull qwen2.5-coder:1.5b</div>
            </div>
            <p className="text-xs text-muted-foreground">
              Po instalacji kliknij "Odśwież" aby zobaczyć nowe modele
            </p>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
