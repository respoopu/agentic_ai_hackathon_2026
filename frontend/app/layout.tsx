import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hobbi — plan a first try",
  description: "A trusted first step into something new.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
