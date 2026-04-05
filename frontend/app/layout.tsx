import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

const mono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "CloudGuard",
  description: "AWS Cloud Security Posture Management",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={mono.variable} suppressHydrationWarning>
      <body className="bg-[#0a0a0f] text-slate-200 antialiased min-h-screen flex">
        <Sidebar />
        <main className="flex-1 ml-56 min-h-screen">{children}</main>
      </body>
    </html>
  );
}
