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
import { validatePassword, validateEmail, validateUsername } from '@/lib/validation';

export function Register() {
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Real-time validation errors
  const [emailError, setEmailError] = useState('');
  const [usernameError, setUsernameError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmPasswordError, setConfirmPasswordError] = useState('');

  const { register } = useAuth();
  const navigate = useNavigate();

  // Real-time validation handlers
  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (value && !validateEmail(value)) {
      setEmailError('Nieprawidłowy format adresu email');
    } else {
      setEmailError('');
    }
  };

  const handleUsernameChange = (value: string) => {
    setUsername(value);
    const result = validateUsername(value);
    setUsernameError(result.valid ? '' : result.error || '');
  };

  const handlePasswordChange = (value: string) => {
    setPassword(value);
    const { valid, errors } = validatePassword(value);
    setPasswordError(valid ? '' : errors.join(', '));

    // Re-validate confirm password if it's already filled
    if (confirmPassword && value !== confirmPassword) {
      setConfirmPasswordError('Hasła nie są identyczne');
    } else if (confirmPassword) {
      setConfirmPasswordError('');
    }
  };

  const handleConfirmPasswordChange = (value: string) => {
    setConfirmPassword(value);
    if (value && value !== password) {
      setConfirmPasswordError('Hasła nie są identyczne');
    } else {
      setConfirmPasswordError('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate email
    if (!validateEmail(email)) {
      toast.error('Nieprawidłowy format adresu email');
      return;
    }

    // Validate username
    const usernameCheck = validateUsername(username);
    if (!usernameCheck.valid) {
      toast.error(`Nazwa użytkownika: ${usernameCheck.error}`);
      return;
    }

    // Validate password
    const { valid, errors } = validatePassword(password);
    if (!valid) {
      toast.error(`Hasło musi zawierać: ${errors.join(', ')}`);
      return;
    }

    if (password !== confirmPassword) {
      toast.error('Hasła nie są identyczne');
      return;
    }

    setIsLoading(true);

    try {
      await register({ email, username, password });
      toast.success('Konto utworzone pomyślnie!');
      navigate('/projects');
    } catch (error: unknown) {
      // Handle different error types
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 422) {
        // Pydantic validation error (e.g., invalid email format)
        toast.error(parseApiError(error, 'Nieprawidłowe dane rejestracji'));
      } else if (status !== 401) {
        // Other errors (401 is handled by interceptor)
        toast.error(parseApiError(error, 'Rejestracja nie powiodła się'));
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
            <CardTitle className="text-2xl">Utwórz konto</CardTitle>
            <CardDescription>Zarejestruj się, aby przeglądać kod z agentami AI</CardDescription>
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
                <Label htmlFor="username">Nazwa użytkownika</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="jankowalski"
                  value={username}
                  onChange={(e) => handleUsernameChange(e.target.value)}
                  required
                  minLength={3}
                  disabled={isLoading}
                  className={usernameError ? 'border-destructive' : ''}
                />
                {usernameError && (
                  <p className="text-sm text-destructive">{usernameError}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Hasło</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => handlePasswordChange(e.target.value)}
                  required
                  minLength={8}
                  disabled={isLoading}
                  className={passwordError ? 'border-destructive' : ''}
                />
                {passwordError && (
                  <p className="text-sm text-destructive">Wymagane: {passwordError}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  Minimum 8 znaków, wielka litera, mała litera, cyfra
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Potwierdź hasło</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => handleConfirmPasswordChange(e.target.value)}
                  required
                  disabled={isLoading}
                  className={confirmPasswordError ? 'border-destructive' : ''}
                />
                {confirmPasswordError && (
                  <p className="text-sm text-destructive">{confirmPasswordError}</p>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4">
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? 'Tworzenie konta...' : 'Utwórz Konto'}
              </Button>
              <p className="text-sm text-muted-foreground text-center">
                Masz już konto?{' '}
                <Link to="/login" className="text-primary hover:underline font-medium">
                  Zaloguj się
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
