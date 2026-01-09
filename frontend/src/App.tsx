import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { Toaster } from '@/components/ui/Toaster';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { DashboardLayout } from '@/components/DashboardLayout';
import { Loader2 } from 'lucide-react';

// Lazy load pages for code splitting
const Landing = lazy(() => import('@/pages/Landing').then(m => ({ default: m.Landing })));
const Login = lazy(() => import('@/pages/Login').then(m => ({ default: m.Login })));
const Register = lazy(() => import('@/pages/Register').then(m => ({ default: m.Register })));
const Projects = lazy(() => import('@/pages/Projects').then(m => ({ default: m.Projects })));
const ProjectDetail = lazy(() => import('@/pages/ProjectDetail').then(m => ({ default: m.ProjectDetail })));
const ReviewDetail = lazy(() => import('@/pages/ReviewDetail').then(m => ({ default: m.ReviewDetail })));
const Settings = lazy(() => import('@/pages/Settings').then(m => ({ default: m.Settings })));
const ModelDuelSetup = lazy(() => import('@/pages/ModelDuelSetup').then(m => ({ default: m.ModelDuelSetup })));
const ModelDuelCompare = lazy(() => import('@/pages/ModelDuelCompare').then(m => ({ default: m.ModelDuelCompare })));
const Rankings = lazy(() => import('@/pages/Rankings').then(m => ({ default: m.Rankings })));
const ArenaDetail = lazy(() => import('@/pages/ArenaDetail').then(m => ({ default: m.ArenaDetail })));
const ArenaRankings = lazy(() => import('@/pages/ArenaRankings').then(m => ({ default: m.ArenaRankings })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Loading fallback for lazy-loaded components
function PageLoader() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Ładowanie...</p>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading while checking auth
  if (isLoading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected dashboard routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route path="dashboard" element={<Projects />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/:id" element={<ProjectDetail />} />
          <Route path="reviews/:id" element={<ReviewDetail />} />
          <Route path="model-duel/setup" element={<ModelDuelSetup />} />
          <Route path="model-duel/:sessionId" element={<ModelDuelCompare />} />
          <Route path="rankings" element={<Rankings />} />
          <Route path="arena/sessions/:id" element={<ArenaDetail />} />
          <Route path="arena/rankings" element={<ArenaRankings />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <ThemeProvider>
            <AuthProvider>
              <AppRoutes />
              <Toaster />
            </AuthProvider>
          </ThemeProvider>
        </BrowserRouter>
        <ReactQueryDevtools initialIsOpen={false} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
