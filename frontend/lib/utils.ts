export interface TranscriptEntry {
  text: string;
  start: number;
  duration: number;
}

export function cleanTranscript(transcript: TranscriptEntry[]): string {
  return transcript.map(entry => entry.text).join(' ').replace(/\s+/g, ' ').trim();
}

export function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return [
    h > 0 ? h : null,
    m.toString().padStart(2, '0'),
    s.toString().padStart(2, '0')
  ].filter(Boolean).join(':');
}

/**
 * Extrai o ID do vídeo de várias formas de URL do YouTube
 * Suporta: youtube.com/watch?v=, youtu.be/, youtube.com/embed/, youtube.com/shorts/
 */
export function extractYouTubeVideoId(url: string): string | null {
  if (!url) return null;

  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtube\.com\/watch\?.+&v=)([^&\s]+)/,
    /youtu\.be\/([^?\s]+)/,
    /youtube\.com\/embed\/([^?\s]+)/,
    /youtube\.com\/shorts\/([^?\s]+)/,
    /youtube\.com\/v\/([^?\s]+)/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match && match[1]) {
      return match[1];
    }
  }
  return null;
}

/**
 * Traduz texto usando a API gratuita MyMemory
 * Limite: ~1000 palavras/dia para uso anônimo
 */
export async function translateText(
  text: string,
  targetLang: string
): Promise<string> {
  if (!text || targetLang === 'original') return text;

  // MyMemory detecta automaticamente o idioma de origem
  const langPair = `autodetect|${targetLang}`;

  try {
    // Dividir texto em partes menores (limite de 500 chars por request)
    const chunks = splitTextIntoChunks(text, 500);
    const translatedChunks: string[] = [];

    for (const chunk of chunks) {
      const response = await fetch(
        `https://api.mymemory.translated.net/get?q=${encodeURIComponent(chunk)}&langpair=${langPair}`
      );

      if (!response.ok) throw new Error('Falha na tradução');

      const data = await response.json();
      if (data.responseStatus === 200 && data.responseData?.translatedText) {
        translatedChunks.push(data.responseData.translatedText);
      } else {
        // Se falhar, retorna o texto original
        translatedChunks.push(chunk);
      }
    }

    return translatedChunks.join(' ');
  } catch (error) {
    console.error('Erro na tradução:', error);
    return text; // Fallback: retorna texto original
  }
}

function splitTextIntoChunks(text: string, maxLength: number): string[] {
  const words = text.split(' ');
  const chunks: string[] = [];
  let currentChunk = '';

  for (const word of words) {
    if ((currentChunk + ' ' + word).length > maxLength) {
      if (currentChunk) chunks.push(currentChunk.trim());
      currentChunk = word;
    } else {
      currentChunk += ' ' + word;
    }
  }
  if (currentChunk) chunks.push(currentChunk.trim());

  return chunks;
}
