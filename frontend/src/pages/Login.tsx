import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/useAuth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { toast } from 'sonner';
import { Bot, ArrowLeft } from 'lucide-react';
import { parseApiError } from '@/lib/errorParser';
import { validateEmail } from '@/lib/validation';

export function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Real-time validation errors
  const [emailError, setEmailError] = useState('');

  const { login } = useAuth();
  const navigate = useNavigate();

  // Real-time validation handler
  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (value && !validateEmail(value)) {
      setEmailError('Nieprawidłowy format adresu email');
    } else {
      setEmailError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateEmail(email)) {
      toast.error('Nieprawidłowy format adresu email');
      return;
    }

    setIsLoading(true);

    try {
      await login({ email, password });
      toast.success('Zalogowano pomyślnie!');
      navigate('/projects');
    } catch (error: unknown) {
      // Handle validation errors (400) and authentication errors (401)
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        toast.error('Nieprawidłowy email lub hasło');
      } else if (status === 422) {
        // Pydantic validation error (e.g., invalid email format)
        toast.error(parseApiError(error, 'Nieprawidłowe dane logowania'));
      } else {
        toast.error(parseApiError(error, 'Logowanie nie powiodło się'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <div className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">AI Code Review Arena</span>
          </Link>
          <Link to="/">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Powrót
            </Button>
          </Link>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl">Witaj ponownie</CardTitle>
            <CardDescription>Wprowadź dane logowania, aby uzyskać dostęp do konta</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="twoj@email.com"
                  value={email}
                  onChange={(e) => handleEmailChange(e.target.value)}
                  required
                  disabled={isLoading}
                  className={emailError ? 'border-destructive' : ''}
                />
                {emailError && (
                  <p className="text-sm text-destructive">{emailError}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Hasło</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Logowanie...' : 'Zaloguj się'}
              </Button>
              <p className="text-sm text-muted-foreground text-center">
                Nie masz konta?{' '}
                <Link to="/register" className="text-primary hover:underline font-medium">
                  Zarejestruj się
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
