'use client';

import { useState } from 'react';
import { TranscriptEntry, cleanTranscript, formatTimestamp } from '../lib/utils';

export default function Home() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[] | null>(null);
  const [cleanMode, setCleanMode] = useState(false);
  const [language, setLanguage] = useState('pt');

  const handleTranscribe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setLoading(true);
    setError(null);
    setTranscript(null);

    try {
      const apiUrl = 'https://vinicuslbt-yt-transcrib-backendstreamlit-app-qpexzj.streamlit.app';

      // Streamlit requer a URL passada como query param
      const response = await fetch(`${apiUrl}/?url=${encodeURIComponent(url)}&lang=${language}`, {
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
      setTranscript(data.transcript);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!transcript) return;
    const text = cleanMode
      ? cleanTranscript(transcript)
      : transcript.map(e => `[${formatTimestamp(e.start)}] ${e.text}`).join('\n');
    navigator.clipboard.writeText(text);
    alert('Copiado para a área de transferência!');
  };

  const downloadText = () => {
    if (!transcript) return;
    const text = cleanMode
      ? cleanTranscript(transcript)
      : transcript.map(e => `[${formatTimestamp(e.start)}] ${e.text}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
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

          <div className="flex items-center gap-3">
            <label className="text-sm text-zinc-400">Idioma de Preferência:</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-sm text-zinc-300 focus:outline-none focus:ring-1 focus:ring-red-500"
            >
              <option value="pt">Português</option>
              <option value="en">Inglês</option>
              <option value="es">Espanhol</option>
              <option value="fr">Francês</option>
              <option value="de">Alemão</option>
            </select>
            <span className="text-[10px] text-zinc-500 italic">* Se disponível no vídeo</span>
          </div>
        </form>
        {error && <p className="text-red-400 text-sm font-medium">⚠️ {error}</p>}
      </div>

      {transcript && (
        <div className="glass p-6 space-y-6 flex-1 flex flex-col">
          <div className="flex justify-between items-center bg-zinc-900/50 p-3 rounded-lg border border-zinc-800">
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={cleanMode}
                  onChange={() => setCleanMode(!cleanMode)}
                  className="accent-red-500"
                />
                <span className="text-sm">Texto Corrido (Sem tempo)</span>
              </label>
            </div>
            <div className="flex gap-2">
              <button onClick={copyToClipboard} className="text-sm px-3 py-1 hover:bg-zinc-800 rounded transition-colors text-zinc-300 border border-zinc-700">Copiar</button>
              <button onClick={downloadText} className="text-sm px-3 py-1 hover:bg-zinc-800 rounded transition-colors text-zinc-300 border border-zinc-700">Baixar .TXT</button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto max-h-[500px] pr-4 space-y-4 custom-scrollbar">
            {cleanMode ? (
              <p className="leading-relaxed text-zinc-300">
                {cleanTranscript(transcript)}
              </p>
            ) : (
              transcript.map((e, i) => (
                <div key={i} className="flex gap-4 items-start group border-b border-zinc-800/30 pb-2 last:border-0">
                  <span className="text-xs font-mono text-zinc-500 pt-1 flex-shrink-0 w-12 text-right">
                    {formatTimestamp(e.start)}
                  </span>
                  <p className="text-zinc-300 group-hover:text-white transition-colors">
                    {e.text}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <footer className="text-center text-zinc-600 text-xs py-10">
        Desenvolvido para facilitar seus estudos e pesquisas.
      </footer>
    </main>
  );
}
