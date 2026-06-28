import type { Metadata } from "next";
import { Nunito } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { QuantumBackground } from "@/components/QuantumBackground";
import { CustomCursor } from "@/components/CustomCursor";
import { SmoothScroll } from "@/components/SmoothScroll";

const nunito = Nunito({
  variable: "--font-nunito",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RNG Extractors | Analysis",
  description: "Quantum random number generator analysis tool",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${nunito.variable} font-sans antialiased min-h-screen flex flex-col`}
        suppressHydrationWarning
      >
        <SmoothScroll>
          <CustomCursor />
          <QuantumBackground />
          <Navbar />
          <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 relative z-10">
            {children}
          </main>
        </SmoothScroll>
      </body>
    </html>
  );
}
