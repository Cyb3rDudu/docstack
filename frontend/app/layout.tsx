import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocStack - RAG Document Management",
  description: "Manage multiple document stores with RAG integration",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
