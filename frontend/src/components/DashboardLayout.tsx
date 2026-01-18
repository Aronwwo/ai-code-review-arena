import { Link, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/useAuth';
import { useTheme } from '@/contexts/useTheme';
import { Button } from '@/components/ui/Button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/DropdownMenu';
import {
  Bot,
  FolderGit2,
  Settings,
  LogOut,
  User,
  Moon,
  Sun,
  Menu,
  X,
  Trophy,
  Clock,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import { useSessionTimer } from '@/hooks/useSessionTimer';
import { Badge } from '@/components/ui/Badge';

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const { setTheme, resolvedTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const sessionTimer = useSessionTimer();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const navItems = [
    { path: '/dashboard', icon: FolderGit2, label: 'Projekty' },
    { path: '/rankings', icon: Trophy, label: 'Rankingi' },
    { path: '/settings', icon: Settings, label: 'Ustawienia' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar - Desktop & Tablet */}
      <aside className="fixed inset-y-0 left-0 z-50 hidden w-56 flex-col border-r bg-card md:flex lg:w-64">
        <div className="flex h-16 items-center border-b px-4 lg:px-6">
          <Link to="/dashboard" className="flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            <span className="text-base font-bold lg:text-lg">AI Code Review Arena</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 p-4">
          {navItems.map((item) => (
            <Link key={item.path} to={item.path}>
              <Button
                variant={isActive(item.path) ? 'default' : 'ghost'}
                className={cn(
                  'w-full justify-start gap-3',
                  isActive(item.path) && 'bg-primary text-primary-foreground'
                )}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </Button>
            </Link>
          ))}
        </nav>
        <div className="border-t p-4">
          <Button
            variant="ghost"
            className="w-full justify-start gap-3 text-destructive hover:text-destructive hover:bg-destructive/10"
            onClick={handleLogout}
          >
            <LogOut className="h-5 w-5" />
            Wyloguj
          </Button>
        </div>
      </aside>

      {/* Mobile Sidebar */}
      {sidebarOpen && (
        <aside className="fixed inset-0 z-50 flex flex-col bg-background md:hidden">
          <div className="flex h-16 items-center justify-between border-b px-4">
            <Link to="/dashboard" className="flex items-center gap-2">
              <Bot className="h-6 w-6 text-primary" />
              <span className="text-lg font-bold">AI Code Review Arena</span>
            </Link>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          <nav className="flex-1 space-y-1 p-4">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
              >
                <Button
                  variant={isActive(item.path) ? 'default' : 'ghost'}
                  className="w-full justify-start gap-3"
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Button>
              </Link>
            ))}
          </nav>
          <div className="border-t p-4">
            <Button
              variant="ghost"
              className="w-full justify-start gap-3 text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={handleLogout}
            >
              <LogOut className="h-5 w-5" />
              Wyloguj
            </Button>
          </div>
        </aside>
      )}

      {/* Main Content Area */}
      <div className="md:pl-56 lg:pl-64">
        {/* Top Header */}
        <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:px-6 lg:px-8">
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="flex-1" />

          {/* Session Timer - Visible when authenticated */}
          {sessionTimer.timeRemaining > 0 && (
            <div className="flex items-center gap-2 mr-2">
              <Badge 
                variant={sessionTimer.isExpiringSoon ? "destructive" : "secondary"} 
                className="gap-1.5 px-2 py-1"
                title={`Sesja wygasa za ${sessionTimer.formattedTime}`}
              >
                <Clock className={`h-3 w-3 ${sessionTimer.isExpiringSoon ? 'animate-pulse' : ''}`} />
                <span className="font-mono text-xs">
                  {sessionTimer.formattedTime}
                </span>
              </Badge>
              {sessionTimer.isExpiringSoon && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={sessionTimer.refreshSession}
                  className="text-xs h-7"
                  title="Odśwież sesję"
                >
                  Odśwież
                </Button>
              )}
            </div>
          )}

          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
            }
          >
            {resolvedTheme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2">
                <User className="h-5 w-5" />
                <span className="hidden md:inline">{user?.username}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user?.username}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate('/settings')}>
                <Settings className="mr-2 h-4 w-4" />
                Ustawienia
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                Wyloguj
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Page Content */}
        <main className="p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
