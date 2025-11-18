// frontend/src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GPT 대화 로그 웹",
  description: "GPT와의 대화를 저장/검색하는 웹앱",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="bg-zinc-50">
        {children}
      </body>
    </html>
  );
}
