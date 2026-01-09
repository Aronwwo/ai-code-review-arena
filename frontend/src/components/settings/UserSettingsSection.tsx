import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/Card';
import { Label } from '@/components/ui/Label';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { User, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '@/lib/api';
import { parseApiError } from '@/lib/errorParser';
import { validatePassword } from '@/lib/validation';

interface UserSettingsSectionProps {
  userEmail: string;
  userName: string;
}

export function UserSettingsSection({ userEmail, userName }: UserSettingsSectionProps) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const handleChangePassword = async () => {
    // Validation
    if (!currentPassword) {
      toast.error('Wprowadź obecne hasło');
      return;
    }

    const { valid, errors } = validatePassword(newPassword);
    if (!valid) {
      toast.error(`Nowe hasło musi zawierać: ${errors.join(', ')}`);
      return;
    }

    if (newPassword !== confirmNewPassword) {
      toast.error('Nowe hasła nie są identyczne');
      return;
    }

    setIsChangingPassword(true);
    try {
      await api.patch('/auth/me/password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success('Hasło zostało zmienione');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (error: any) {
      if (error.response?.status === 422) {
        toast.error(parseApiError(error, 'Nieprawidłowe dane hasła'));
      } else if (error.response?.status !== 401) {
        toast.error(parseApiError(error, 'Nie udało się zmienić hasła'));
      }
    } finally {
      setIsChangingPassword(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <User className="h-5 w-5" />
          <CardTitle>Ustawienia Konta</CardTitle>
        </div>
        <CardDescription>Zarządzaj swoim kontem i bezpieczeństwem</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* User Info */}
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Email</Label>
            <Input value={userEmail} disabled className="bg-muted" />
          </div>
          <div className="space-y-2">
            <Label>Nazwa użytkownika</Label>
            <Input value={userName} disabled className="bg-muted" />
          </div>
        </div>

        {/* Password Change */}
        <div className="space-y-4 pt-4 border-t">
          <h3 className="font-medium">Zmień Hasło</h3>
          <div className="space-y-2">
            <Label htmlFor="current-password">Obecne Hasło</Label>
            <Input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              disabled={isChangingPassword}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-password">Nowe Hasło</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isChangingPassword}
            />
            <p className="text-xs text-muted-foreground">
              Minimum 8 znaków, wielka litera, mała litera, cyfra
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Potwierdź Nowe Hasło</Label>
            <Input
              id="confirm-password"
              type="password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              disabled={isChangingPassword}
            />
          </div>
        </div>
      </CardContent>
      <CardFooter>
        <Button onClick={handleChangePassword} disabled={isChangingPassword}>
          {isChangingPassword && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Zmień Hasło
        </Button>
      </CardFooter>
    </Card>
  );
}
