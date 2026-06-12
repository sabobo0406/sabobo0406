"use client";

import { useState } from "react";
import Markdown from "@/components/Markdown";
import type { ArticleDraft, TranscriptionResult } from "@/lib/types";

export default function TranscribePage() {
  const [file, setFile] = useState<File | null>(null);
  const [wantDraft, setWantDraft] = useState(true);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [transcription, setTranscription] = useState<TranscriptionResult | null>(null);
  const [article, setArticle] = useState<ArticleDraft | null>(null);
  const [copied, setCopied] = useState(false);

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setTranscription(null);
    setArticle(null);
    setStage(wantDraft ? "文字起こし → 記事生成中…" : "文字起こし中…");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("draft", wantDraft ? "1" : "0");
      const res = await fetch("/api/transcribe", { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).error || "処理に失敗しました");
      const data = await res.json();
      setTranscription(data.transcription);
      setArticle(data.article ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラー");
    } finally {
      setBusy(false);
      setStage("");
    }
  }

  async function copyArticle() {
    if (!article) return;
    await navigator.clipboard.writeText(`# ${article.title}\n\n${article.body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold">文字起こし → 記事下書き</h1>
      <p className="text-sub text-sm mt-1 mb-6">
        動画・音声をアップロードすると、文字起こしして記事の下書きまで作ります。
      </p>

      <div className="rounded-xl bg-white border border-black/5 p-5 shadow-sm mb-6">
        <label className="block">
          <span className="text-sm font-medium">音声 / 動画ファイル</span>
          <input
            type="file"
            accept="audio/*,video/*"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="mt-2 block w-full text-sm file:mr-3 file:rounded-full file:border-0 file:bg-ink file:px-4 file:py-2 file:text-white file:text-sm hover:file:opacity-90"
          />
        </label>
        {file && (
          <p className="text-xs text-sub mt-2">
            {file.name} ({(file.size / 1024 / 1024).toFixed(1)} MB)
          </p>
        )}

        <label className="flex items-center gap-2 mt-4 text-sm">
          <input
            type="checkbox"
            checked={wantDraft}
            onChange={(e) => setWantDraft(e.target.checked)}
          />
          記事の下書きまで生成する（Claude）
        </label>

        <button
          onClick={run}
          disabled={!file || busy}
          className="mt-4 px-5 py-2 rounded-full bg-accent text-white text-sm hover:opacity-90 disabled:opacity-40"
        >
          {busy ? stage : "▶ 変換する"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 text-red-700 px-4 py-3 text-sm mb-4">{error}</div>
      )}

      {transcription && (
        <div className="rounded-xl bg-white border border-black/5 p-5 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold">文字起こし</h2>
            {transcription.source === "mock" && (
              <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                サンプル（OPENAI_API_KEY 未設定）
              </span>
            )}
          </div>
          <textarea
            readOnly
            value={transcription.text}
            className="w-full h-40 text-sm rounded-lg border border-black/10 p-3 bg-paper resize-y"
          />
        </div>
      )}

      {article && (
        <div className="rounded-xl bg-white border border-black/5 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">記事の下書き</h2>
            <div className="flex items-center gap-2">
              {article.source === "mock" && (
                <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                  サンプル（ANTHROPIC_API_KEY 未設定）
                </span>
              )}
              <button
                onClick={copyArticle}
                className="text-xs px-3 py-1 rounded-full border border-black/10 hover:bg-black/5"
              >
                {copied ? "コピーしました" : "Markdownをコピー"}
              </button>
            </div>
          </div>
          <h3 className="text-xl font-bold mb-3">{article.title}</h3>
          <Markdown source={article.body} />
        </div>
      )}
    </div>
  );
}
