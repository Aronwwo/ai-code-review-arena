import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Review, IssueWithSuggestions, ReviewAgent, FileWithContent } from '@/types';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { CodeViewer } from '@/components/CodeViewer';
import { ConversationView } from '@/components/ConversationView';
import { useReviewWebSocket } from '@/hooks/useReviewWebSocket';
import { ArrowLeft, AlertCircle, AlertTriangle, Info, FileCode, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, MessageSquare, Loader2, CheckCircle2, XCircle, Radio, Clock, Bot } from 'lucide-react';
import { toast } from 'sonner';

interface ProjectWithFiles {
  id: number;
  name: string;
  files: FileWithContent[];
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface ConversationSummary {
  id: number;
  mode: 'council' | 'arena';
  status: 'pending' | 'running' | 'completed' | 'failed';
  summary?: string | null;
  created_at: string;
}

export function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [expandedIssues, setExpandedIssues] = useState<Set<number>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTab, setActiveTab] = useState('issues');
  const [expandedAgents, setExpandedAgents] = useState<Set<number>>(new Set());
  const [showAgentResponses, setShowAgentResponses] = useState(false);
  const pageSize = 10;

  const { data: review, isLoading: reviewLoading } = useQuery<Review>({
    queryKey: ['review', id],
    queryFn: async () => {
      const response = await api.get(`/reviews/${id}`);
      return response.data;
    },
    enabled: !!id,
    refetchInterval: (query) => {
      // Auto-refetch while running
      const data = query.state.data;
      return data?.status === 'running' || data?.status === 'pending' ? 3000 : false;
    },
  });

  // WebSocket for real-time updates
  const {
    isConnected,
    agentProgress,
  } = useReviewWebSocket({
    reviewId: id ? parseInt(id) : null,
    enabled: review?.status === 'running' || review?.status === 'pending',
    onEvent: (event) => {
      if (event.type === 'agent_completed') {
        toast.success(`Agent ${event.agent_role} zakończył analizę`);
        // Refetch issues
        queryClient.invalidateQueries({ queryKey: ['issues', id] });
      } else if (event.type === 'review_completed') {
        toast.success('Przegląd zakończony!');
        // Wait a bit for backend to finish processing, then refetch
        setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['review', id] });
        queryClient.invalidateQueries({ queryKey: ['issues', id] });
        queryClient.invalidateQueries({ queryKey: ['agents', id] });
          // Force refetch to ensure we get latest data
          queryClient.refetchQueries({ queryKey: ['agents', id] });
        }, 500);
      } else if (event.type === 'review_failed') {
        toast.error(`Przegląd nie powiódł się: ${event.error}`);
        setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['review', id] });
          queryClient.invalidateQueries({ queryKey: ['agents', id] });
          queryClient.refetchQueries({ queryKey: ['agents', id] });
        }, 500);
      }
    },
  });

  const { data: issuesData, isLoading: issuesLoading } = useQuery<PaginatedResponse<IssueWithSuggestions>>({
    queryKey: ['issues', id, severityFilter, categoryFilter, currentPage, pageSize],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (severityFilter) params.append('severity', severityFilter);
      if (categoryFilter) params.append('category', categoryFilter);
      params.append('page', currentPage.toString());
      params.append('page_size', pageSize.toString());
      const response = await api.get(`/reviews/${id}/issues?${params}`);
      return response.data;
    },
    enabled: !!id,
  });

  const issues = issuesData?.items || [];

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [severityFilter, categoryFilter]);

  const { data: agents } = useQuery<ReviewAgent[]>({
    queryKey: ['agents', id],
    queryFn: async () => {
      const response = await api.get(`/reviews/${id}/agents`);
      return response.data;
    },
    enabled: !!id,
    // Refetch agents when review status changes to ensure we have latest data
    refetchInterval: (query) => {
      const data = query.state.data;
      const reviewStatus = review?.status;
      // Auto-refetch while review is running or pending
      if (reviewStatus === 'running' || reviewStatus === 'pending') {
        return 2000; // Refetch every 2 seconds
      }
      // After review completes, refetch once more to get final agent responses
      if (reviewStatus === 'completed' || reviewStatus === 'failed') {
        return false; // Stop auto-refetching after completion
      }
      return false;
    },
  });

  // Refetch agents when review status changes from running to completed/failed
  useEffect(() => {
    if (review?.status === 'completed' || review?.status === 'failed') {
      // Wait a bit for backend to finish processing, then refetch agents
      const timer = setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['agents', id] });
        // Force immediate refetch to get latest agent data
        queryClient.refetchQueries({ queryKey: ['agents', id] });
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [review?.status, id, queryClient]);

  // Also refetch agents periodically while review is running or just completed
  useEffect(() => {
    if (!id) return;
    
    const interval = setInterval(() => {
      if (review?.status === 'running' || review?.status === 'pending') {
        queryClient.refetchQueries({ queryKey: ['agents', id] });
      } else if (review?.status === 'completed' || review?.status === 'failed') {
        // After completion, refetch once more after a delay to ensure all data is saved
        queryClient.refetchQueries({ queryKey: ['agents', id] });
      }
    }, 3000); // Refetch every 3 seconds

    return () => clearInterval(interval);
  }, [id, review?.status, queryClient]);

  // Query for conversations (used by ConversationView component internally)
  const { data: _conversations } = useQuery<ConversationSummary[]>({
    queryKey: ['conversations', id],
    queryFn: async () => {
      const response = await api.get(`/reviews/${id}/conversations`);
      return response.data;
    },
    enabled: !!id,
  });

  // Fetch project with files to show code snippets
  const { data: project } = useQuery<ProjectWithFiles>({
    queryKey: ['project', review?.project_id],
    queryFn: async () => {
      const response = await api.get(`/projects/${review?.project_id}`);
      return response.data;
    },
    enabled: !!review?.project_id,
  });

  const toggleIssue = (issueId: number) => {
    setExpandedIssues(prev => {
      const next = new Set(prev);
      if (next.has(issueId)) {
        next.delete(issueId);
      } else {
        next.add(issueId);
      }
      return next;
    });
  };

  const toggleAgent = (agentId: number) => {
    setExpandedAgents(prev => {
      const next = new Set(prev);
      if (next.has(agentId)) {
        next.delete(agentId);
      } else {
        next.add(agentId);
      }
      return next;
    });
  };

  const startArenaDebate = (event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent card toggle
    setActiveTab('discussions');
    toast.info('Otwarto zakładkę dyskusji AI.');
  };

  const getCodeSnippet = (fileName: string | null, lineStart: number | null, lineEnd: number | null) => {
    if (!fileName || !project?.files) return null;

    const file = project.files.find(f => f.name === fileName);
    if (!file?.content) return null;

    const lines = file.content.split('\n');
    const start = Math.max(0, (lineStart || 1) - 3);
    const end = Math.min(lines.length, (lineEnd || lineStart || 1) + 3);

    const snippet = lines.slice(start, end).join('\n');
    const highlightLines: number[] = [];

    if (lineStart) {
      for (let i = lineStart; i <= (lineEnd || lineStart); i++) {
        highlightLines.push(i - start);
      }
    }

    return { snippet, highlightLines, startLine: start + 1, language: file.language || 'python' };
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error': return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
      case 'info': return <Info className="h-5 w-5 text-blue-500" />;
      default: return <Info className="h-5 w-5" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error': return 'border-l-red-500 bg-red-500/5';
      case 'warning': return 'border-l-yellow-500 bg-yellow-500/5';
      case 'info': return 'border-l-blue-500 bg-blue-500/5';
      default: return 'border-l-gray-500';
    }
  };

  if (reviewLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!review) {
    return <div className="text-center py-12">Nie znaleziono przeglądu</div>;
  }

  // Helper to check if text contains placeholders
  // Only check for FULL placeholder phrases, not individual words
  const containsPlaceholders = (text: string): boolean => {
    if (!text || text.length < 20) return false; // Too short to be a real placeholder issue
    
    const textLower = text.toLowerCase();
    
    // Strong indicators - these are almost certainly placeholders (exact phrases)
    const strongPatterns = [
      'po polsku',  // Only if exact phrase appears (not "odpowiedz po polsku" which is valid)
      'wypełnij',
      'krótki tytuł',
      'szczegółowy opis po polsku',
      'opcjonalne podsumowanie',
      'ogólne podsumowanie przeglądu kodu',
      'sugestia naprawy po polsku',
      'opcjonalna sugestia poprawki po polsku',
      '"info" | "warning"',  // Example syntax from prompts
      '| "warning" | "error"',  // Example syntax
      'rzeczywisty tytuł problemu',  // Full phrase from prompt
      'rzeczywiste podsumowanie przeglądu kodu',  // Full phrase from prompt
      'szczegółowy opis znalezionego problemu po polsku',  // Full phrase from prompt
      'code_snippet': "fragment kodu',  // Placeholder in JSON
      'suggested_fix': "sugestia naprawy',  // Placeholder in JSON
    ];
    
    for (const pattern of strongPatterns) {
      if (textLower.includes(pattern)) {
        return true;
      }
    }
    
    // Weak indicators - check context (must appear together with context words)
    const weakPatterns = [
      { word: 'rzeczywisty', context: ['tytuł', 'problem', 'podsumowanie', 'opis'] },
      { word: 'rzeczywiste', context: ['podsumowanie', 'dane'] },
    ];
    
    for (const { word, context } of weakPatterns) {
      if (textLower.includes(word)) {
        // Check if word appears with context words nearby
        for (const ctx of context) {
          if (textLower.includes(ctx)) {
            const wordPos = textLower.indexOf(word);
            const ctxPos = textLower.indexOf(ctx);
            if (wordPos !== -1 && ctxPos !== -1) {
              const distance = Math.abs(wordPos - ctxPos);
              // If words are very close together (within 50 chars), it's likely a placeholder
              if (distance < 50) {
                // But check if it's part of a longer, valid sentence
                const contextBefore = textLower.substring(Math.max(0, wordPos - 20), wordPos);
                const contextAfter = textLower.substring(wordPos + word.length, Math.min(textLower.length, wordPos + word.length + 20));
                // If surrounded by actual content, it's probably valid
                if (contextBefore.trim().length > 5 && contextAfter.trim().length > 5) {
                  continue; // Skip this match - probably valid text
                }
                return true;
              }
            }
          }
        }
      }
    }
    
    return false;
  };

  // Raport moderatora z review.summary (nowy flow)
  const moderatorSummaryText = review?.summary || null;
  const parseModeratorSummary = (raw: string | null) => {
    if (!raw) return { text: null, summary: null, overallQuality: null, issues: null };
    
    // Check if it's an error message
    if (raw.trim().startsWith('[BŁĄD]') || raw.trim().startsWith('[ERROR]')) {
      return { text: raw, summary: null, overallQuality: null, issues: null };
    }
    
    // Check for placeholders in raw text
    if (containsPlaceholders(raw)) {
      return { text: '[BŁĄD] Odpowiedź zawiera placeholdery zamiast rzeczywistej analizy', summary: null, overallQuality: null, issues: null };
    }
    
    const cleaned = raw
      .trim()
      .replace(/^```json\s*/i, '')
      .replace(/^```/i, '')
      .replace(/```$/i, '')
      .replace(/^json\s*/i, '');

    try {
      const data = JSON.parse(cleaned);
      
      // Check parsed data for placeholders
      const summary = typeof data.summary === 'string' ? data.summary : null;
      if (summary && containsPlaceholders(summary)) {
        return { text: '[BŁĄD] Podsumowanie zawiera placeholdery zamiast rzeczywistej analizy', summary: null, overallQuality: null, issues: null };
      }
      
      const overallQuality = typeof data.overall_quality === 'string' ? data.overall_quality : null;
      const issues = Array.isArray(data.issues) 
        ? data.issues.filter((issue: any) => {
            const title = issue.title || '';
            const desc = issue.description || '';
            return !containsPlaceholders(title) && !containsPlaceholders(desc);
          })
        : null;
      
      if (summary || overallQuality || issues) {
        return { text: null, summary, overallQuality, issues };
      }
    } catch {
      // Fallback - check if it looks like JSON with placeholders
      if (cleaned.includes('PO POLSKU') || cleaned.includes('po polsku') || 
          cleaned.includes('"info" | "warning"') || cleaned.includes('| "warning" | "error"')) {
        return { text: '[BŁĄD] Odpowiedź zawiera placeholdery zamiast rzeczywistej analizy', summary: null, overallQuality: null, issues: null };
      }
    }

    // Don't return raw JSON if it looks like a template
    if (cleaned.includes('"info" | "warning"') || cleaned.includes('| "warning" | "error"')) {
      return { text: '[BŁĄD] Odpowiedź zawiera placeholdery zamiast rzeczywistej analizy', summary: null, overallQuality: null, issues: null };
    }

    return { text: null, summary: null, overallQuality: null, issues: null };
  };
  const moderatorParsed = parseModeratorSummary(moderatorSummaryText);

  // Helper to parse agent raw_output
  const parseAgentResponse = (rawOutput: string | null) => {
    if (!rawOutput || !rawOutput.trim()) {
      return { summary: 'Brak odpowiedzi', issues: [] };
    }
    
    // Clean markdown code blocks first
    let cleanedOutput = rawOutput.trim();
    
    // Remove markdown code block fences more thoroughly
    if (cleanedOutput.startsWith('```json')) {
      cleanedOutput = cleanedOutput.replace(/^```json\s*/i, '').trim();
    } else if (cleanedOutput.startsWith('```')) {
      cleanedOutput = cleanedOutput.replace(/^```\w*\s*/i, '').trim();
    }
    if (cleanedOutput.endsWith('```')) {
      cleanedOutput = cleanedOutput.replace(/\s*```$/i, '').trim();
    }
    
    // Check for placeholders in cleaned output (more lenient check)
    // Only reject if we're VERY sure it's a placeholder
    if (cleanedOutput.includes('"info" | "warning"') || 
        cleanedOutput.includes('| "warning" | "error"') ||
        cleanedOutput.includes('krótki tytuł po polsku') ||
        cleanedOutput.includes('szczegółowy opis po polsku') ||
        cleanedOutput.includes('sugestia naprawy po polsku')) {
      return { summary: '[BŁĄD] Odpowiedź zawiera placeholdery zamiast rzeczywistej analizy', issues: [] };
    }
    
    try {
      // Try to parse as JSON
      const data = JSON.parse(cleanedOutput);
      
      // Validate structure
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid JSON structure');
      }
      
      // Extract summary
      const summary = typeof data.summary === 'string' && data.summary.trim() 
        ? data.summary.trim() 
        : 'Brak podsumowania';
      
      // Check summary for placeholders (only strong matches)
      if (summary.includes('"info" | "warning"') || 
          summary.includes('krótki tytuł po polsku') ||
          summary.includes('szczegółowy opis po polsku')) {
        return { summary: '[BŁĄD] Podsumowanie zawiera placeholdery zamiast rzeczywistej analizy', issues: [] };
      }
      
      // Filter and clean issues
      const issues = Array.isArray(data.issues) 
        ? data.issues
            .map((issue: any) => {
              // Clean empty or placeholder code_snippet/suggested_fix
              if (issue.code_snippet && 
                  (issue.code_snippet.trim() === '' || 
                   issue.code_snippet.trim() === '1' ||
                   issue.code_snippet.toLowerCase().includes('fragment kodu') ||
                   issue.code_snippet.length < 10)) {
                issue.code_snippet = undefined;
              }
              
              if (issue.suggested_fix && 
                  (issue.suggested_fix.trim() === '' || 
                   issue.suggested_fix.trim() === '1' ||
                   issue.suggested_fix.toLowerCase().includes('sugestia naprawy') ||
                   issue.suggested_fix.length < 10)) {
                issue.suggested_fix = undefined;
              }
              
              return issue;
            })
            .filter((issue: any) => {
              // Only filter out obvious placeholders in title/description
              const title = (issue.title || '').toLowerCase();
              const description = (issue.description || '').toLowerCase();
              
              return !title.includes('krótki tytuł po polsku') &&
                     !description.includes('szczegółowy opis po polsku') &&
                     !title.includes('"info" | "warning"');
            })
        : [];
      
      return { summary, issues };
    } catch (e) {
      console.error("Failed to parse agent JSON response:", e);
      
      // Fallback: check if it's just a plain text response
      if (cleanedOutput.length > 50 && !cleanedOutput.includes('{') && !cleanedOutput.includes('[')) {
        // Plain text response - not JSON
        return { summary: cleanedOutput, issues: [] };
      }
      
      // Last resort: return error message
      return { summary: 'Nieprawidłowy format odpowiedzi (nie można sparsować JSON)', issues: [] };
    }
  };

  // Liczba agentów z timeout
  const timedOutAgents = agents?.filter(a => a.timed_out) || [];

  const categories = Array.from(new Set(issues.map((i) => i.category)));
  // Note: These counts are for the current page. For total counts, we'd need separate API calls.
  const errorCount = issues.filter(i => i.severity === 'error').length;
  const warningCount = issues.filter(i => i.severity === 'warning').length;
  const infoCount = issues.filter(i => i.severity === 'info').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to={`/projects/${review.project_id}`}>
          <Button variant="ghost" size="sm" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Powrót do projektu
          </Button>
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Przegląd kodu #{review.id}</h1>
            <p className="text-muted-foreground">
              {project?.name} - {new Date(review.created_at).toLocaleString()}
            </p>
          </div>
          <Badge variant={review.status === 'completed' ? 'success' : review.status === 'failed' ? 'destructive' : 'default'} className="text-sm px-3 py-1">
            {review.status}
          </Badge>
        </div>
      </div>

      {/* Real-time Progress (shown when review is running) */}
      {(review.status === 'running' || review.status === 'pending') && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Radio className="h-5 w-5 text-primary animate-pulse" />
              Przegląd w toku...
              {isConnected && (
                <Badge variant="outline" className="ml-2 text-xs">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                  Na żywo
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Agenci analizują kod w czasie rzeczywistym
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {Array.from(agentProgress.entries()).map(([role, status]) => (
                <div
                  key={role}
                  className={`flex items-center gap-2 p-3 rounded-lg border ${
                    status === 'running'
                      ? 'border-primary bg-primary/10'
                      : status === 'completed'
                      ? 'border-green-500/50 bg-green-500/10'
                      : status === 'failed'
                      ? 'border-red-500/50 bg-red-500/10'
                      : 'border-muted bg-muted/50'
                  }`}
                >
                  {status === 'running' && (
                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  )}
                  {status === 'completed' && (
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                  )}
                  {status === 'failed' && (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  {status === 'pending' && (
                    <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />
                  )}
                  <span className="text-sm font-medium capitalize">{role}</span>
                </div>
              ))}
              {agentProgress.size === 0 && (
                <div className="col-span-full flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Oczekiwanie na rozpoczęcie...</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-red-500">{errorCount}</div>
              <div className="text-sm text-muted-foreground">Błędy</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-yellow-500">{warningCount}</div>
              <div className="text-sm text-muted-foreground">Ostrzeżenia</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-blue-500">{infoCount}</div>
              <div className="text-sm text-muted-foreground">Informacje</div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="text-3xl font-bold">{agents?.length || 0}</div>
              <div className="text-sm text-muted-foreground">Agenci</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Moderator Summary - główny raport */}
      {review.status === 'completed' && moderatorSummaryText && (() => {
        // Check if this is a "no agent responses" message (not a real moderator report)
        const isNoAgentResponses = moderatorSummaryText.includes('Nie można przeprowadzić przeglądu kodu') ||
                                   moderatorSummaryText.includes('brak odpowiedzi od agentów') ||
                                   moderatorSummaryText.includes('nie można ocenić') && moderatorSummaryText.includes('brak odpowiedzi');
        
        // Check if summary contains placeholders or is an error
        const isError = moderatorSummaryText?.startsWith('[BŁĄD]') || 
                       moderatorSummaryText?.startsWith('[ERROR]');
        
        // If no agent responses, show as warning instead of moderator report
        if (isNoAgentResponses) {
          return (
            <Card className="border-2 border-yellow-500/30 bg-yellow-500/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-yellow-600">
                  <Bot className="h-5 w-5" />
                  Uwaga: Brak odpowiedzi od agentów
                </CardTitle>
                <CardDescription>
                  Przegląd nie mógł zostać przeprowadzony, ponieważ żaden z agentów nie zwrócił odpowiedzi.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 font-medium">
                      {moderatorParsed.summary || moderatorSummaryText}
                    </p>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p>• Sprawdź logi backendu, aby zobaczyć szczegóły błędów</p>
                    <p>• Sprawdź konfigurację API kluczy dla dostawców (Google Gemini, Groq, etc.)</p>
                    <p>• Sprawdź, czy limity czasu nie są zbyt krótkie</p>
                    <p>• Upewnij się, że dostawcy LLM są dostępni i działają poprawnie</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        }
        
        // Regular moderator report
        return (
        <Card className="border-2 border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              Raport Moderatora
            </CardTitle>
            <CardDescription>
              Końcowy raport na podstawie analizy wszystkich agentów
              {timedOutAgents.length > 0 && (
                <span className="ml-2 text-yellow-600">
                  ({timedOutAgents.length} agent(ów) przekroczyło limit czasu)
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
              {(() => {
                if (isError) {
                  return (
                    <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                      <p className="text-sm text-red-600 font-medium">{moderatorSummaryText}</p>
                    </div>
                  );
                }
              
              // Check for placeholders in parsed data
              const hasPlaceholders = moderatorParsed.summary && containsPlaceholders(moderatorParsed.summary);
              
              if (hasPlaceholders) {
                return (
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
                    <p className="text-sm text-yellow-600 font-medium">
                      [BŁĄD] Odpowiedź zawiera placeholdery zamiast rzeczywistej analizy
                    </p>
                  </div>
                );
              }
              
              // Display parsed content in readable format
              return (
                <div className="space-y-4">
                  {moderatorParsed.summary && (
                    <div>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {moderatorParsed.summary}
                    </p>
                    </div>
                  )}
                  
                  {moderatorParsed.overallQuality && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Ogólna jakość:</span>
                      <Badge variant="secondary">{moderatorParsed.overallQuality}</Badge>
                    </div>
                  )}
                  
                  {moderatorParsed.issues && moderatorParsed.issues.length > 0 && (
                    <div className="space-y-3">
                      <div className="text-sm font-semibold">
                      Wykryte problemy: {moderatorParsed.issues.length}
                    </div>
                      <div className="space-y-2">
                        {moderatorParsed.issues.map((issue: any, idx: number) => (
                          <div key={idx} className="border-l-2 border-border pl-3 py-2 bg-background/50 rounded">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge 
                                variant={
                                  issue.severity === 'error' ? 'destructive' :
                                  issue.severity === 'warning' ? 'warning' : 'default'
                                }
                                className="text-xs"
                              >
                                {issue.severity}
                              </Badge>
                              <span className="text-xs text-muted-foreground">{issue.category}</span>
                            </div>
                            <p className="text-sm font-medium">{issue.title}</p>
                            {issue.description && (
                              <p className="text-xs text-muted-foreground mt-1">{issue.description}</p>
                            )}
                            {issue.file_name && (
                              <p className="text-xs text-muted-foreground mt-1">
                                📄 {issue.file_name}
                                {issue.line_start && ` (linia ${issue.line_start}${issue.line_end && issue.line_end !== issue.line_start ? `-${issue.line_end}` : ''})`}
                              </p>
                            )}
                            {issue.code_snippet && 
                             issue.code_snippet.trim().length > 10 &&
                             !issue.code_snippet.toLowerCase().includes('fragment kodu') &&
                             issue.code_snippet.trim() !== '1' && (
                              <div className="mt-2">
                                <CodeViewer
                                  code={issue.code_snippet}
                                  language={issue.file_name ? (issue.file_name.split('.').pop() || 'python') : 'python'}
                                  showLineNumbers={true}
                                  filename="Fragment kodu"
                                />
                              </div>
                            )}
                            {issue.suggested_fix && 
                             issue.suggested_fix.trim().length > 10 &&
                             !issue.suggested_fix.toLowerCase().includes('sugestia naprawy') &&
                             issue.suggested_fix.trim() !== '1' && (
                              <div className="mt-2">
                                <span className="text-xs font-semibold">💡 Sugestia poprawki: </span>
                                {issue.suggested_fix.includes('\n') || issue.suggested_fix.length > 100 ? (
                                  <div className="mt-1">
                                    <CodeViewer
                                      code={issue.suggested_fix}
                                      language={issue.file_name ? (issue.file_name.split('.').pop() || 'python') : 'python'}
                                      showLineNumbers={true}
                                      filename="Sugerowany kod"
                                    />
                </div>
              ) : (
                                  <span className="text-xs">{issue.suggested_fix}</span>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {!moderatorParsed.summary && !moderatorParsed.overallQuality && (!moderatorParsed.issues || moderatorParsed.issues.length === 0) && (
                    <p className="text-sm text-muted-foreground italic">
                      {moderatorSummaryText || 'Brak danych'}
                </p>
              )}
            </div>
              );
              })()}
          </CardContent>
        </Card>
        );
      })()}

      {/* Agents - rozwijalna sekcja */}
      {agents && agents.length > 0 && (
        <Card>
          <CardHeader
            className="cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => setShowAgentResponses(!showAgentResponses)}
          >
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  Odpowiedzi agentów ({agents.length})
                </CardTitle>
                <CardDescription>
                  Kliknij, aby zobaczyć szczegółowe odpowiedzi każdego agenta
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm">
                {showAgentResponses ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-2">
              {agents.map((agent) => (
                <Badge
                  key={agent.id}
                  variant={agent.timed_out ? "destructive" : "secondary"}
                  className="px-3 py-1 flex items-center gap-1"
                >
                  {agent.timed_out && <Clock className="h-3 w-3" />}
                  {agent.role.charAt(0).toUpperCase() + agent.role.slice(1)}
                  <span className="text-xs opacity-70">({agent.provider}/{agent.model.split('/').pop()})</span>
                </Badge>
              ))}
            </div>
          </CardHeader>
          {showAgentResponses && (
            <CardContent className="space-y-4">
              {agents.map((agent) => (
                <Card
                  key={agent.id}
                  className={`overflow-hidden ${agent.timed_out ? 'border-yellow-500/50 bg-yellow-500/5' : ''}`}
                >
                  <CardHeader
                    className="cursor-pointer hover:bg-muted/30 transition-colors py-3"
                    onClick={() => toggleAgent(agent.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {agent.timed_out ? (
                          <Clock className="h-4 w-4 text-yellow-500" />
                        ) : agent.parsed_successfully ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="font-medium">
                          {agent.role.charAt(0).toUpperCase() + agent.role.slice(1)} Agent
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {agent.provider} / {agent.model}
                        </Badge>
                        {agent.timed_out && (
                          <Badge variant="destructive" className="text-xs">
                            TIMEOUT ({agent.timeout_seconds}s)
                          </Badge>
                        )}
                      </div>
                      <Button variant="ghost" size="sm">
                        {expandedAgents.has(agent.id) ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </Button>
                    </div>
                  </CardHeader>
                  {expandedAgents.has(agent.id) && (
                    <CardContent className="pt-0">
                      {(() => {
                        // Check if raw_output exists and is not empty
                        if (!agent.raw_output || !agent.raw_output.trim()) {
                          return (
                            <div className="space-y-2">
                        <p className="text-sm text-muted-foreground italic">Brak odpowiedzi</p>
                              {agent.timed_out && (
                                <p className="text-xs text-yellow-600">
                                  Agent przekroczył limit czasu ({agent.timeout_seconds}s)
                                </p>
                              )}
                              {!agent.timed_out && !agent.parsed_successfully && (
                                <p className="text-xs text-red-600">
                                  Agent nie zakończył się pomyślnie. Sprawdź logi backendu.
                                </p>
                              )}
                        </div>
                          );
                        }
                        
                        const rawOutput = agent.raw_output.trim();
                        
                        // Check if raw_output is an error message
                        const isError = rawOutput.startsWith('[BŁĄD]') || 
                                       rawOutput.startsWith('[ERROR]') ||
                                       rawOutput.startsWith('[TIMEOUT]') ||
                                       rawOutput.startsWith('[EMPTY]');
                        
                        if (isError) {
                          // Display error message directly with full details
                          return (
                            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 space-y-2">
                              <p className="text-sm text-red-600 font-medium">{rawOutput}</p>
                              {agent.timed_out && (
                                <p className="text-xs text-yellow-600 mt-2">
                                  ⏱️ Agent przekroczył limit czasu ({agent.timeout_seconds}s)
                                </p>
                              )}
                              {!agent.timed_out && (
                                <p className="text-xs text-muted-foreground mt-2">
                                  ℹ️ Sprawdź logi backendu, aby zobaczyć szczegóły błędu.
                                </p>
                              )}
                              <details className="mt-2 text-xs text-muted-foreground">
                                <summary className="cursor-pointer hover:text-foreground">Pokaż pełną odpowiedź</summary>
                                <pre className="mt-2 p-2 bg-background/50 rounded border overflow-auto max-h-48">
                                  {rawOutput}
                                </pre>
                              </details>
                            </div>
                          );
                        }
                        
                        // Try to parse as JSON response
                        const { summary, issues } = parseAgentResponse(rawOutput);
                        return (
                          <div className="bg-muted/50 rounded-lg p-4 max-h-96 overflow-y-auto space-y-3">
                            {summary && <p className="text-sm font-medium">{summary}</p>}
                            {issues.length > 0 && (
                              <div className="space-y-2">
                                <h5 className="text-sm font-semibold mt-2">Wykryte problemy:</h5>
                                {issues.map((issue: any, idx: number) => (
                                  <div key={idx} className="border-l-2 border-border pl-2">
                                    <p className="text-sm font-medium">{issue.title}</p>
                                    <p className="text-xs text-muted-foreground">{issue.description}</p>
                                    {issue.file_name && (
                                      <p className="text-xs text-muted-foreground">
                                        Plik: {issue.file_name} {issue.line_start && `linia ${issue.line_start}`}
                                      </p>
                                    )}
                                    {issue.code_snippet && 
                                     issue.code_snippet.trim().length > 10 &&
                                     !issue.code_snippet.toLowerCase().includes('fragment kodu') &&
                                     issue.code_snippet.trim() !== '1' && (
                                      <div className="mt-2">
                                        <CodeViewer
                                          code={issue.code_snippet}
                                          language={issue.file_name ? (issue.file_name.split('.').pop() || 'python') : 'python'}
                                          showLineNumbers={true}
                                          filename="Fragment kodu"
                                        />
                                      </div>
                                    )}
                                    {issue.suggested_fix && 
                                     issue.suggested_fix.trim().length > 10 &&
                                     !issue.suggested_fix.toLowerCase().includes('sugestia naprawy') &&
                                     issue.suggested_fix.trim() !== '1' && (
                                      <div className="mt-2">
                                        <h6 className="text-xs font-semibold">Sugerowana poprawka:</h6>
                                        {issue.suggested_fix.includes('\n') || issue.suggested_fix.length > 100 ? (
                                          <CodeViewer
                                            code={issue.suggested_fix}
                                            language={issue.file_name ? (issue.file_name.split('.').pop() || 'python') : 'python'}
                                            showLineNumbers={true}
                                            filename="Sugerowany kod"
                                          />
                                        ) : (
                                          <p className="text-xs text-muted-foreground mt-1">{issue.suggested_fix}</p>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                            {/* Show raw output if summary/issues parsing failed or is empty */}
                            {!summary && issues.length === 0 && (
                              <details className="mt-2 text-xs">
                                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Pokaż surową odpowiedź</summary>
                                <pre className="mt-2 p-2 bg-background/50 rounded border overflow-auto max-h-48 text-xs">
                                  {rawOutput}
                                </pre>
                              </details>
                            )}
                          </div>
                        );
                      })()}
                    </CardContent>
                  )}
                </Card>
              ))}
            </CardContent>
          )}
        </Card>
      )}

      {/* Tabs: Issues, Discussions, and Files */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="issues">Problemy ({issues?.length || 0})</TabsTrigger>
          <TabsTrigger value="discussions" className="flex items-center gap-1">
            <MessageSquare className="h-4 w-4" />
            Dyskusje i debaty
          </TabsTrigger>
          <TabsTrigger value="files">Pliki ({project?.files?.length || 0})</TabsTrigger>
        </TabsList>

          <TabsContent value="issues" className="space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Poziom ważności</label>
                  <div className="flex gap-2">
                    <Button variant={severityFilter === '' ? 'default' : 'outline'} size="sm" onClick={() => setSeverityFilter('')}>Wszystkie</Button>
                    <Button variant={severityFilter === 'error' ? 'default' : 'outline'} size="sm" onClick={() => setSeverityFilter('error')} className="text-red-600">Błędy ({errorCount})</Button>
                    <Button variant={severityFilter === 'warning' ? 'default' : 'outline'} size="sm" onClick={() => setSeverityFilter('warning')} className="text-yellow-600">Ostrzeżenia ({warningCount})</Button>
                    <Button variant={severityFilter === 'info' ? 'default' : 'outline'} size="sm" onClick={() => setSeverityFilter('info')} className="text-blue-600">Info ({infoCount})</Button>
                  </div>
                </div>
                {categories.length > 0 && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Kategoria</label>
                    <div className="flex gap-2 flex-wrap">
                      <Button variant={categoryFilter === '' ? 'default' : 'outline'} size="sm" onClick={() => setCategoryFilter('')}>Wszystkie</Button>
                      {categories.map((cat) => (
                        <Button key={cat} variant={categoryFilter === cat ? 'default' : 'outline'} size="sm" onClick={() => setCategoryFilter(cat)}>
                          {cat}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Issues List */}
          {issuesLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : issues.length > 0 ? (
            <>
              <div className="space-y-4">
                {issues.map((issue) => {
                  const codeInfo = getCodeSnippet(issue.file_name, issue.line_start, issue.line_end);
                  const isExpanded = expandedIssues.has(issue.id);

                  return (
                    <Card key={issue.id} className={`border-l-4 ${getSeverityColor(issue.severity)} overflow-hidden`}>
                      <CardHeader className="cursor-pointer" onClick={() => toggleIssue(issue.id)}>
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3 flex-1">
                            {getSeverityIcon(issue.severity)}
                            <div className="flex-1">
                              <CardTitle className="text-lg flex items-center gap-2">
                                {issue.title}
                              </CardTitle>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs">{issue.category}</Badge>
                                {issue.file_name && (
                                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                                    <FileCode className="h-3 w-3" />
                                    {issue.file_name}
                                    {issue.line_start && `:${issue.line_start}`}
                                    {issue.line_end && issue.line_end !== issue.line_start && `-${issue.line_end}`}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => startArenaDebate(e)}
                              title="Zobacz debatę i uzasadnienia"
                            >
                              <MessageSquare className="h-3 w-3 mr-1" />
                              Otwórz debatę
                            </Button>
                            <Button variant="ghost" size="sm">
                              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </Button>
                          </div>
                        </div>
                      </CardHeader>

                      <CardContent className={isExpanded ? '' : 'hidden'}>
                        {/* Description */}
                        <div className="mb-4 p-4 bg-muted/50 rounded-lg">
                          <p className="text-sm">{issue.description}</p>
                        </div>

                        {/* Code Snippet */}
                        {codeInfo && (
                          <div className="mb-4">
                            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                              <FileCode className="h-4 w-4" />
                              Fragment kodu
                            </h4>
                            <CodeViewer
                              code={codeInfo.snippet}
                              language={codeInfo.language}
                              filename={`${issue.file_name} (line ${codeInfo.startLine})`}
                              highlightLines={codeInfo.highlightLines}
                            />
                          </div>
                        )}

                        {/* Suggestion */}
                        {issue.suggestions && issue.suggestions.length > 0 && (
                          <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                            <h4 className="text-sm font-medium mb-2 text-green-600">Sugerowana Poprawka</h4>
                            {issue.suggestions[0].suggested_code && (
                              <div className="mb-3">
                                <CodeViewer
                                  code={issue.suggestions[0].suggested_code}
                                  language={codeInfo?.language || 'python'}
                                  showLineNumbers={false}
                                />
                              </div>
                            )}
                            <p className="text-sm text-muted-foreground">{issue.suggestions[0].explanation}</p>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              {/* Pagination Controls */}
              {issuesData && issuesData.total_pages > 1 && (
                <div className="flex items-center justify-center gap-4 mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={!issuesData.has_prev}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Poprzednia
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    Strona {issuesData.page} z {issuesData.total_pages} ({issuesData.total} problemów)
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.min(issuesData.total_pages, p + 1))}
                    disabled={!issuesData.has_next}
                  >
                    Następna
                    <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Info className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Brak problemów - Twój kod wygląda świetnie!</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="discussions" className="space-y-4">
          <ConversationView
            reviewId={parseInt(id || '0')}
            issueId={undefined}
          />
        </TabsContent>

        <TabsContent value="files" className="space-y-4">
          {project?.files && project.files.length > 0 ? (
            project.files.map((file) => (
              <Card key={file.id}>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileCode className="h-5 w-5" />
                    {file.name}
                  </CardTitle>
                  <CardDescription>
                    {file.language && <Badge variant="secondary" className="mr-2">{file.language}</Badge>}
                    {Math.round(file.size_bytes / 1024 * 10) / 10} KB
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <CodeViewer
                    code={file.content || '// No content available'}
                    language={file.language || 'text'}
                    filename={file.name}
                  />
                </CardContent>
              </Card>
            ))
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FileCode className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Brak plików w tym projekcie</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
