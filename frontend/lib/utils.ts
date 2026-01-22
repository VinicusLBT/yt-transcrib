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
