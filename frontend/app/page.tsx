'use client';

import { useState, useEffect } from 'react';
import { TranscriptEntry, cleanTranscript, formatTimestamp, extractYouTubeVideoId, translateText } from '../lib/utils';

export default function Home() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[] | null>(null);
  const [cleanMode, setCleanMode] = useState(false);
  const [translateTo, setTranslateTo] = useState('original');
  const [videoId, setVideoId] = useState<string | null>(null);
  const [translating, setTranslating] = useState(false);
  const [translatedTranscript, setTranslatedTranscript] = useState<TranscriptEntry[] | null>(null);

  // Extrair videoId quando URL mudar
  useEffect(() => {
    setVideoId(extractYouTubeVideoId(url));
  }, [url]);

  // Traduzir quando mudar o idioma selecionado (após ter uma transcrição)
  useEffect(() => {
    const performTranslation = async () => {
      if (!transcript || translateTo === 'original') {
        setTranslatedTranscript(null);
        return;
      }

      setTranslating(true);
      try {
        const translatedEntries = await Promise.all(
          transcript.map(async (entry) => ({
            ...entry,
            text: await translateText(entry.text, translateTo)
          }))
        );
        setTranslatedTranscript(translatedEntries);
      } catch (err) {
        console.error('Erro na tradução:', err);
        setTranslatedTranscript(null);
      } finally {
        setTranslating(false);
      }
    };

    performTranslation();
  }, [translateTo, transcript]);

  const handleTranscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setError(null);
    setTranscript(null);

    try {
      const apiUrl = 'https://vinicuslbt-yt-transcrib-backendstreamlit-app-qpexzj.streamlit.app';

      // Streamlit requer a URL passada como query param (busca transcrição original)
      const response = await fetch(`${apiUrl}/?url=${encodeURIComponent(url)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Falha ao obter transcrição');
      }

      const data = await response.json();
      const originalTranscript = data.transcript;
      setTranscript(originalTranscript);
      setTranslatedTranscript(null);
      // A tradução será acionada automaticamente pelo useEffect quando translateTo mudar
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Falha ao obter transcrição');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    const activeTranscript = translatedTranscript || transcript;
    if (!activeTranscript) return;
    const text = cleanMode
      ? cleanTranscript(activeTranscript)
      : activeTranscript.map(e => `[${formatTimestamp(e.start)}] ${e.text}`).join('\n');
    navigator.clipboard.writeText(text);
    alert('Copiado para a área de transferência!');
  };

  const downloadText = () => {
    const activeTranscript = translatedTranscript || transcript;
    if (!activeTranscript) return;
    const text = cleanMode
      ? cleanTranscript(activeTranscript)
      : activeTranscript.map(e => `[${formatTimestamp(e.start)}] ${e.text}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const dlUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = dlUrl;
    a.download = `transcricao_${new Date().getTime()}.txt`;
    a.click();
  };

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto flex flex-col gap-8 animate-fade-in">
      <header className="text-center space-y-2">
        <h1 className="text-5xl font-bold gradient-text pb-2">YT Transcrib</h1>
        <p className="text-zinc-400">Transforme vídeos do YouTube em texto em segundos.</p>
      </header>

      <div className="glass p-6 space-y-4">
        <form onSubmit={handleTranscribe} className="flex flex-col gap-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Cole a URL do vídeo aqui (ex: https://youtube.com/watch?v=...)"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-red-500 transition-all text-white"
            />
            <button
              type="submit"
              disabled={loading}
              className="btn-primary px-6 py-2 rounded-lg font-semibold disabled:opacity-50 text-white"
            >
              {loading ? 'Processando...' : 'Transcrever'}
            </button>
          </div>
        </form>

        {/* Preview do Vídeo */}
        {videoId && (
          <div className="mt-4">
            <p className="text-sm text-zinc-400 mb-2">📺 Confirme o vídeo:</p>
            <div className="aspect-video rounded-lg overflow-hidden border border-zinc-800">
              <iframe
                src={`https://www.youtube.com/embed/${videoId}`}
                className="w-full h-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
                title="Preview do Vídeo"
              />
            </div>
          </div>
        )}
        {error && <p className="text-red-400 text-sm font-medium">⚠️ {error}</p>}
      </div>

      {transcript && (
        <div className="glass p-6 space-y-6 flex-1 flex flex-col">
          <div className="flex flex-col gap-3">
            {/* Barra de controles superior */}
            <div className="flex flex-wrap justify-between items-center bg-zinc-900/50 p-3 rounded-lg border border-zinc-800 gap-3">
              <div className="flex flex-wrap gap-4 items-center">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={cleanMode}
                    onChange={() => setCleanMode(!cleanMode)}
                    className="accent-red-500"
                  />
                  <span className="text-sm">Texto Corrido</span>
                </label>

                {/* Seletor de Tradução */}
                <div className="flex items-center gap-2">
                  <label className="text-sm text-zinc-400">Traduzir para:</label>
                  <select
                    value={translateTo}
                    onChange={(e) => setTranslateTo(e.target.value)}
                    className="bg-zinc-800 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-300 focus:outline-none focus:ring-1 focus:ring-red-500"
                  >
                    <option value="original">🌐 Original</option>
                    <option value="pt">🇧🇷 Português</option>
                    <option value="en">🇺🇸 Inglês</option>
                    <option value="es">🇪🇸 Espanhol</option>
                    <option value="fr">🇫🇷 Francês</option>
                    <option value="de">🇩🇪 Alemão</option>
                  </select>
                  {translating && (
                    <span className="text-xs text-yellow-400 animate-pulse">Traduzindo...</span>
                  )}
                </div>
              </div>

              <div className="flex gap-2">
                <button onClick={copyToClipboard} className="text-sm px-3 py-1 hover:bg-zinc-800 rounded transition-colors text-zinc-300 border border-zinc-700">Copiar</button>
                <button onClick={downloadText} className="text-sm px-3 py-1 hover:bg-zinc-800 rounded transition-colors text-zinc-300 border border-zinc-700">Baixar .TXT</button>
              </div>
            </div>

            {/* Nota sobre tradução */}
            {translatedTranscript && (
              <p className="text-xs text-green-400 px-1">✓ Texto traduzido. Mude para &quot;Original&quot; para ver o texto original.</p>
            )}
          </div>

          <div className="flex-1 overflow-y-auto max-h-[500px] pr-4 space-y-4 custom-scrollbar">
            {(() => {
              const activeTranscript = translatedTranscript || transcript;
              return cleanMode ? (
                <p className="leading-relaxed text-zinc-300">
                  {cleanTranscript(activeTranscript)}
                </p>
              ) : (
                activeTranscript.map((e, i) => (
                  <div key={i} className="flex gap-4 items-start group border-b border-zinc-800/30 pb-2 last:border-0">
                    <span className="text-xs font-mono text-zinc-500 pt-1 flex-shrink-0 w-12 text-right">
                      {formatTimestamp(e.start)}
                    </span>
                    <p className="text-zinc-300 group-hover:text-white transition-colors">
                      {e.text}
                    </p>
                  </div>
                ))
              );
            })()}
          </div>
        </div>
      )}

      <footer className="text-center text-zinc-600 text-xs py-10">
        Desenvolvido para facilitar seus estudos e pesquisas.
      </footer>
    </main>
  );
}
