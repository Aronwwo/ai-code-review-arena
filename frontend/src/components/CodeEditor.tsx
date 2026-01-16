import Editor from '@monaco-editor/react';
import type { editor as MonacoEditor } from 'monaco-editor';
import { useState, useRef } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Save, RotateCcw, Copy, Check, Maximize2, Minimize2 } from 'lucide-react';
import { toast } from 'sonner';

interface CodeEditorProps {
  code: string;
  language?: string;
  filename?: string;
  readOnly?: boolean;
  onSave?: (code: string) => void;
  onChange?: (code: string) => void;
  height?: string;
  highlightLines?: number[];
}

const languageMap: Record<string, string> = {
  'py': 'python',
  'python': 'python',
  'js': 'javascript',
  'javascript': 'javascript',
  'ts': 'typescript',
  'typescript': 'typescript',
  'tsx': 'typescript',
  'jsx': 'javascript',
  'json': 'json',
  'html': 'html',
  'css': 'css',
  'scss': 'scss',
  'md': 'markdown',
  'sql': 'sql',
  'sh': 'shell',
  'bash': 'shell',
  'yaml': 'yaml',
  'yml': 'yaml',
  'xml': 'xml',
  'java': 'java',
  'c': 'c',
  'cpp': 'cpp',
  'go': 'go',
  'rust': 'rust',
  'ruby': 'ruby',
  'php': 'php',
};

export function CodeEditor({
  code,
  language = 'python',
  filename,
  readOnly = false,
  onSave,
  onChange,
  height = '400px',
  highlightLines = [],
}: CodeEditorProps) {
  const [currentCode, setCurrentCode] = useState(code);
  const [hasChanges, setHasChanges] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);

  const mappedLanguage = languageMap[language.toLowerCase()] || language;

  const handleEditorDidMount = (
    editor: MonacoEditor.IStandaloneCodeEditor,
    monaco: typeof import('monaco-editor')
  ) => {
    editorRef.current = editor;

    // Add decorations for highlighted lines
    if (highlightLines.length > 0) {
      const decorations = highlightLines.map(line => ({
        range: new monaco.Range(line, 1, line, 1),
        options: {
          isWholeLine: true,
          className: 'highlighted-line',
          glyphMarginClassName: 'highlighted-glyph',
        },
      }));
      editor.deltaDecorations([], decorations);
    }
  };

  const handleChange = (value: string | undefined) => {
    const newCode = value || '';
    setCurrentCode(newCode);
    setHasChanges(newCode !== code);
    onChange?.(newCode);
  };

  const handleSave = () => {
    onSave?.(currentCode);
    setHasChanges(false);
    toast.success('Plik zapisany pomyślnie');
  };

  const handleReset = () => {
    setCurrentCode(code);
    setHasChanges(false);
    toast.info('Zmiany odrzucone');
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentCode);
      setCopied(true);
      toast.success('Kod skopiowany do schowka');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Nie udało się skopiować kodu');
    }
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const containerClass = isFullscreen
    ? 'fixed inset-0 z-50 bg-background p-4'
    : '';

  return (
    <div className={containerClass}>
      <Card className={`overflow-hidden ${isFullscreen ? 'h-full flex flex-col' : ''}`}>
        {/* Toolbar */}
        <div className="flex items-center justify-between border-b bg-muted/50 px-4 py-2">
          <div className="flex items-center gap-2">
            {filename && (
              <span className="text-sm font-medium">{filename}</span>
            )}
            <span className="text-xs text-muted-foreground px-2 py-0.5 bg-muted rounded">
              {mappedLanguage}
            </span>
            {hasChanges && (
              <span className="text-xs text-orange-500 font-medium">
                (niezapisane zmiany)
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-8 gap-1"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              <span className="hidden sm:inline">{copied ? 'Skopiowano' : 'Kopiuj'}</span>
            </Button>
            {!readOnly && hasChanges && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleReset}
                  className="h-8 gap-1"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span className="hidden sm:inline">Resetuj</span>
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSave}
                  className="h-8 gap-1"
                >
                  <Save className="h-4 w-4" />
                  <span className="hidden sm:inline">Zapisz</span>
                </Button>
              </>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleFullscreen}
              className="h-8"
            >
              {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        {/* Editor */}
        <div className={isFullscreen ? 'flex-1 overflow-hidden' : 'overflow-hidden'} style={isFullscreen ? {} : { height }}>
          <Editor
            height={isFullscreen ? '100%' : height}
            language={mappedLanguage}
            value={currentCode}
            onChange={handleChange}
            onMount={handleEditorDidMount}
            theme="vs-dark"
            options={{
              readOnly,
              minimap: { enabled: !isFullscreen ? false : true },
              fontSize: 14,
              lineNumbers: 'on',
              scrollBeyondLastLine: true,
              automaticLayout: true,
              tabSize: 2,
              wordWrap: 'off',
              padding: { top: 10, bottom: 10 },
              renderLineHighlight: 'all',
              scrollbar: {
                verticalScrollbarSize: 10,
                horizontalScrollbarSize: 10,
                alwaysConsumeMouseWheel: true,
              },
              folding: true,
              bracketPairColorization: { enabled: true },
            }}
          />
        </div>
      </Card>
    </div>
  );
}
