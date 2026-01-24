import type { ReactNode } from "react";

import "./globals.css";

export const metadata = {
  title: "FairServe",
  description: "Fairness and policy review demo",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
