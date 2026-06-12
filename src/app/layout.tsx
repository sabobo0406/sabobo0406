import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "くるくる｜競合巡回・数値ダッシュボード・記事下書き",
  description:
    "競合を毎朝巡回して伸びた投稿だけをレポート、売上とフォロワーを1画面に集約、動画/音声を記事の下書きに変換する運用ツール。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <Nav />
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-sub">
          くるくる — 競合巡回 / ダッシュボード / 文字起こし。APIキー未設定の項目はサンプルデータで動作します。
        </footer>
      </body>
    </html>
  );
}
