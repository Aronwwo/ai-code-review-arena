import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import { Label } from '@/components/ui/Label';
import { Input } from '@/components/ui/Input';
import { Textarea } from '@/components/ui/Textarea';
import { Button } from '@/components/ui/Button';
import { CustomProvider } from '@/pages/Settings';
import { toast } from 'sonner';

interface ProviderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  provider: CustomProvider | null;
  onSave: (provider: CustomProvider) => void;
}

export function ProviderDialog({ open, onOpenChange, provider, onSave }: ProviderDialogProps) {
  const isEditing = !!provider;

  const [formData, setFormData] = useState<Partial<CustomProvider>>({
    name: '',
    baseUrl: '',
    apiKey: '',
    models: [],
    description: '',
    headerName: 'Authorization',
    headerPrefix: 'Bearer ',
  });
  const [modelsInput, setModelsInput] = useState('');

  // Load provider data when editing
  useEffect(() => {
    if (provider) {
      setFormData(provider);
      setModelsInput(provider.models.join('\n'));
    } else {
      setFormData({
        name: '',
        baseUrl: '',
        apiKey: '',
        models: [],
        description: '',
        headerName: 'Authorization',
        headerPrefix: 'Bearer ',
      });
      setModelsInput('');
    }
  }, [provider, open]);

  const handleSave = () => {
    // Validation
    if (!formData.name?.trim()) {
      toast.error('Nazwa providera jest wymagana');
      return;
    }

    if (!formData.baseUrl?.trim()) {
      toast.error('Base URL jest wymagany');
      return;
    }

    // Parse models from textarea
    const models = modelsInput
      .split('\n')
      .map(m => m.trim())
      .filter(m => m.length > 0);

    const providerToSave: CustomProvider = {
      id: provider?.id || `custom-${Date.now()}`,
      name: formData.name!,
      baseUrl: formData.baseUrl!,
      apiKey: formData.apiKey || '',
      models,
      description: formData.description,
      isBuiltIn: false,
      headerName: formData.headerName,
      headerPrefix: formData.headerPrefix,
    };

    onSave(providerToSave);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edytuj Providera' : 'Dodaj Nowego Providera'}
          </DialogTitle>
          <DialogDescription>
            Skonfiguruj własnego providera LLM z niestandardowym API
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="provider-name">Nazwa *</Label>
            <Input
              id="provider-name"
              placeholder="np. Mój Provider"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="base-url">Base URL *</Label>
            <Input
              id="base-url"
              placeholder="https://api.example.com/v1"
              value={formData.baseUrl}
              onChange={(e) => setFormData({ ...formData, baseUrl: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="api-key">API Key (opcjonalny)</Label>
            <Input
              id="api-key"
              type="password"
              placeholder="sk-..."
              value={formData.apiKey}
              onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="header-name">Header Name</Label>
              <Input
                id="header-name"
                placeholder="Authorization"
                value={formData.headerName}
                onChange={(e) => setFormData({ ...formData, headerName: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="header-prefix">Header Prefix</Label>
              <Input
                id="header-prefix"
                placeholder="Bearer "
                value={formData.headerPrefix}
                onChange={(e) => setFormData({ ...formData, headerPrefix: e.target.value })}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Opis (opcjonalny)</Label>
            <Input
              id="description"
              placeholder="Krótki opis providera"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="models">Modele (jeden na linię)</Label>
            <Textarea
              id="models"
              placeholder="gpt-4&#10;gpt-3.5-turbo&#10;claude-3-opus"
              value={modelsInput}
              onChange={(e) => setModelsInput(e.target.value)}
              rows={6}
              className="font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
              Wprowadź nazwy modeli, każdy w osobnej linii
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Anuluj
          </Button>
          <Button onClick={handleSave}>
            {isEditing ? 'Zapisz Zmiany' : 'Dodaj Providera'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
