import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import {
  Users, Swords, Bot, MessageSquare, Loader2,
  CheckCircle, XCircle, Gavel
} from 'lucide-react';
import { toast } from 'sonner';

interface Message {
  id: number;
  conversation_id: number;
  sender_type: string;
  sender_name: string;
  turn_index: number;
  content: string;
  is_summary: boolean;
  meta_info?: any;
  created_at: string;
}

interface Conversation {
  id: number;
  review_id: number;
  mode: 'council' | 'arena';
  topic_type: string;
  topic_id?: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  summary?: string;
  meta_info?: {
    verdict?: string;
    final_severity?: string;
    confidence?: number;
  };
  created_at: string;
  completed_at?: string;
}

interface ConversationViewProps {
  reviewId: number;
  issueId?: number;
  mode?: 'council' | 'arena';
  onClose?: () => void;
}

const AGENT_COLORS: Record<string, string> = {
  general: 'bg-blue-500',
  security: 'bg-red-500',
  performance: 'bg-yellow-500',
  style: 'bg-purple-500',
  prosecutor: 'bg-red-600',
  defender: 'bg-green-600',
  moderator: 'bg-indigo-600',
};

const AGENT_NAMES: Record<string, string> = {
  general: 'Ogólny',
  security: 'Bezpieczeństwo',
  performance: 'Wydajność',
  style: 'Styl',
  prosecutor: 'Prokurator',
  defender: 'Obrońca',
  moderator: 'Moderator',
};

export function ConversationView({ reviewId, issueId }: ConversationViewProps) {
  const queryClient = useQueryClient();
  const [activeConversation, setActiveConversation] = useState<number | null>(null);

  // Fetch conversations for this review
  const { data: conversations, isLoading: conversationsLoading } = useQuery<Conversation[]>({
    queryKey: ['conversations', reviewId],
    queryFn: async () => {
      const response = await api.get(`/reviews/${reviewId}/conversations`);
      return response.data;
    },
  });

  // Fetch messages for active conversation
  const { data: messages, isLoading: messagesLoading } = useQuery<Message[]>({
    queryKey: ['messages', activeConversation],
    queryFn: async () => {
      if (!activeConversation) return [];
      const response = await api.get(`/conversations/${activeConversation}/messages`);
      return response.data;
    },
    enabled: !!activeConversation,
    refetchInterval: () => {
      const conv = conversations?.find(c => c.id === activeConversation);
      return conv?.status === 'running' ? 2000 : false;
    },
  });

  // Start conversation mutation
  const startConversationMutation = useMutation({
    mutationFn: async (params: { mode: 'council' | 'arena'; issueId?: number }) => {
      const response = await api.post(`/reviews/${reviewId}/conversations`, {
        mode: params.mode,
        topic_type: params.issueId ? 'issue' : 'review',
        topic_id: params.issueId,
      });
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['conversations', reviewId] });
      setActiveConversation(data.id);
      toast.success('Rozpoczęto dyskusję agentów');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Nie udało się rozpocząć dyskusji');
    },
  });

  const handleStartConversation = (conversationMode: 'council' | 'arena') => {
    // Arena mode requires an issue
    if (conversationMode === 'arena' && !issueId) {
      toast.error('Tryb Areny wymaga wybrania konkretnego problemu. Otwórz dyskusję z poziomu konkretnego issue.');
      return;
    }
    startConversationMutation.mutate({ mode: conversationMode, issueId });
  };

  const selectedConversation = conversations?.find(c => c.id === activeConversation);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success"><CheckCircle className="h-3 w-3 mr-1" />Zakończona</Badge>;
      case 'running':
        return <Badge variant="warning"><Loader2 className="h-3 w-3 mr-1 animate-spin" />W toku</Badge>;
      case 'failed':
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Błąd</Badge>;
      default:
        return <Badge variant="outline">Oczekująca</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with actions */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Dyskusje Agentów AI
          </h3>
          <p className="text-sm text-muted-foreground">
            Zobacz jak agenci analizują i dyskutują nad kodem
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleStartConversation('council')}
            disabled={startConversationMutation.isPending}
          >
            <Users className="h-4 w-4 mr-2" />
            Rada
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleStartConversation('arena')}
            disabled={startConversationMutation.isPending || !issueId}
            title={!issueId ? 'Arena wymaga wybrania konkretnego issue' : 'Rozpocznij debatę Arena'}
          >
            <Swords className="h-4 w-4 mr-2" />
            Arena
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {/* Conversations List */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">Historia Dyskusji</h4>
          {conversationsLoading ? (
            <div className="flex items-center justify-center p-4">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : conversations && conversations.length > 0 ? (
            <div className="space-y-2">
              {conversations.map((conv) => (
                <Card
                  key={conv.id}
                  className={`cursor-pointer transition-all ${activeConversation === conv.id ? 'ring-2 ring-primary' : 'hover:border-primary/50'}`}
                  onClick={() => setActiveConversation(conv.id)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {conv.mode === 'council' ? (
                          <Users className="h-4 w-4 text-blue-500" />
                        ) : (
                          <Swords className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-sm font-medium capitalize">{conv.mode}</span>
                      </div>
                      {getStatusBadge(conv.status)}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(conv.created_at).toLocaleString()}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="p-4 text-center text-muted-foreground">
                <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Brak dyskusji</p>
                <p className="text-xs mt-1">Rozpocznij Radę lub Arenę</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Messages View */}
        <div className="md:col-span-2">
          {selectedConversation ? (
            <Card className="h-[500px] flex flex-col">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {selectedConversation.mode === 'council' ? (
                      <Users className="h-5 w-5 text-blue-500" />
                    ) : (
                      <Swords className="h-5 w-5 text-red-500" />
                    )}
                    <CardTitle className="text-base capitalize">
                      Tryb {selectedConversation.mode === 'council' ? 'Rady' : 'Areny'}
                    </CardTitle>
                    {getStatusBadge(selectedConversation.status)}
                  </div>
                  {selectedConversation.status === 'running' && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                </div>
              </CardHeader>

              <CardContent className="flex-1 overflow-y-auto space-y-3 pb-4">
                {messagesLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="h-8 w-8 animate-spin" />
                  </div>
                ) : messages && messages.length > 0 ? (
                  <>
                    {messages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`p-3 rounded-lg ${msg.is_summary ? 'bg-primary/10 border border-primary/20' : 'bg-muted/50'}`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`w-2 h-2 rounded-full ${AGENT_COLORS[msg.sender_type] || 'bg-gray-500'}`} />
                          <span className="text-sm font-medium capitalize">
                            {AGENT_NAMES[msg.sender_type] || msg.sender_name}
                          </span>
                          {msg.is_summary && (
                            <Badge variant="outline" className="text-xs">
                              <Gavel className="h-3 w-3 mr-1" />
                              Podsumowanie
                            </Badge>
                          )}
                          <span className="text-xs text-muted-foreground ml-auto">
                            Runda {msg.turn_index + 1}
                          </span>
                        </div>
                        <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                      </div>
                    ))}

                    {/* Verdict for completed conversations */}
                    {selectedConversation.status === 'completed' && selectedConversation.meta_info?.verdict && (
                      <div className="mt-4 p-4 bg-green-500/10 border border-green-500/20 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <Gavel className="h-5 w-5 text-green-600" />
                          <span className="font-semibold text-green-600">Werdykt Moderatora</span>
                        </div>
                        <p className="text-sm">{selectedConversation.meta_info.verdict}</p>
                        {selectedConversation.meta_info.final_severity && (
                          <div className="mt-2">
                            <Badge variant={
                              selectedConversation.meta_info.final_severity === 'error' ? 'destructive' :
                              selectedConversation.meta_info.final_severity === 'warning' ? 'warning' : 'default'
                            }>
                              Ważność: {selectedConversation.meta_info.final_severity === 'error' ? 'Błąd' :
                                        selectedConversation.meta_info.final_severity === 'warning' ? 'Ostrzeżenie' : 'Info'}
                            </Badge>
                          </div>
                        )}
                      </div>
                    )}

                    {selectedConversation.summary && (
                      <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                        <div className="flex items-center gap-2 mb-2">
                          <CheckCircle className="h-5 w-5 text-blue-600" />
                          <span className="font-semibold text-blue-600">Podsumowanie</span>
                        </div>
                        <p className="text-sm">{selectedConversation.summary}</p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <Bot className="h-12 w-12 mb-2 opacity-50" />
                    <p>Oczekiwanie na odpowiedzi agentów...</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card className="h-[500px] flex items-center justify-center">
              <CardContent className="text-center text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Wybierz dyskusję z listy lub rozpocznij nową</p>
                <div className="flex gap-2 justify-center mt-4">
                  <Button
                    variant="outline"
                    onClick={() => handleStartConversation('council')}
                    disabled={startConversationMutation.isPending}
                  >
                    <Users className="h-4 w-4 mr-2" />
                    Rozpocznij Radę
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => handleStartConversation('arena')}
                    disabled={startConversationMutation.isPending || !issueId}
                    title={!issueId ? 'Arena wymaga wybrania konkretnego issue' : 'Rozpocznij debatę Arena'}
                  >
                    <Swords className="h-4 w-4 mr-2" />
                    Rozpocznij Arenę
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
