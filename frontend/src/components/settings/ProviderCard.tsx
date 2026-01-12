import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Edit, Trash2, Key, Globe, Check, X } from 'lucide-react';
import { useState } from 'react';
import { CustomProvider } from '@/lib/providers';

interface ProviderCardProps {
  provider: CustomProvider;
  onEdit: (provider: CustomProvider) => void;
  onDelete: (providerId: string) => void;
  onUpdateApiKey: (providerId: string, apiKey: string) => void;
}

export function ProviderCard({ provider, onEdit, onDelete, onUpdateApiKey }: ProviderCardProps) {
  const [isEditingKey, setIsEditingKey] = useState(false);
  const [tempApiKey, setTempApiKey] = useState(provider.apiKey || '');

  const handleSaveApiKey = () => {
    onUpdateApiKey(provider.id, tempApiKey);
    setIsEditingKey(false);
  };

  const handleCancelEditKey = () => {
    setTempApiKey(provider.apiKey || '');
    setIsEditingKey(false);
  };

  return (
    <Card key={provider.id}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <CardTitle className="text-lg">{provider.name}</CardTitle>
              {provider.isBuiltIn && (
                <Badge variant="secondary" className="text-xs">Wbudowany</Badge>
              )}
            </div>
            {provider.description && (
              <CardDescription className="mt-1">{provider.description}</CardDescription>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onEdit(provider)}
            >
              <Edit className="h-4 w-4" />
            </Button>
            {!provider.isBuiltIn && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  if (confirm(`Usunąć providera ${provider.name}?`)) {
                    onDelete(provider.id);
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Base URL */}
        {provider.baseUrl && (
          <div className="flex items-center gap-2 text-sm">
            <Globe className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground truncate">{provider.baseUrl}</span>
          </div>
        )}

        {/* API Key */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            API Key {provider.id === 'ollama' && '(opcjonalny)'}
          </Label>
          {isEditingKey ? (
            <div className="flex gap-2">
              <Input
                type="password"
                value={tempApiKey}
                onChange={(e) => setTempApiKey(e.target.value)}
                placeholder="Wprowadź API key..."
                className="flex-1"
              />
              <Button size="sm" variant="default" onClick={handleSaveApiKey}>
                <Check className="h-4 w-4" />
              </Button>
              <Button size="sm" variant="outline" onClick={handleCancelEditKey}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <div className="flex gap-2 items-center">
              <Input
                type="password"
                value={provider.apiKey || ''}
                disabled
                placeholder={provider.id === 'ollama' ? 'Brak' : 'Nie ustawiony'}
                className="flex-1 bg-muted"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setTempApiKey(provider.apiKey || '');
                  setIsEditingKey(true);
                }}
              >
                <Edit className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>

        {/* Models */}
        {provider.id === 'ollama' ? (
          // Ollama - models are fetched dynamically, shown in OllamaSection
          provider.models.length > 0 && (
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">
                Dostępne Modele ({provider.models.length})
              </Label>
              <div className="flex flex-wrap gap-1">
                {provider.models.slice(0, 5).map((model) => (
                  <Badge key={model} variant="outline" className="text-xs">
                    {model}
                  </Badge>
                ))}
                {provider.models.length > 5 && (
                  <Badge variant="outline" className="text-xs">
                    +{provider.models.length - 5} więcej
                  </Badge>
                )}
              </div>
            </div>
          )
        ) : (
          // Other providers - show models only if API key is set
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">
              Modele
            </Label>
            {!provider.apiKey ? (
              <p className="text-xs text-muted-foreground italic">
                Ustaw API key, aby używać tego providera
              </p>
            ) : provider.models.length > 0 ? (
              <div className="flex flex-wrap gap-1">
                {provider.models.slice(0, 5).map((model) => (
                  <Badge key={model} variant="outline" className="text-xs">
                    {model}
                  </Badge>
                ))}
                {provider.models.length > 5 && (
                  <Badge variant="outline" className="text-xs">
                    +{provider.models.length - 5} więcej
                  </Badge>
                )}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Edytuj providera, aby dodać modele
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
