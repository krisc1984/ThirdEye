import type { ReactNode } from "react";

export const metadata = {
  title: "AI Tech Review",
  description: "Local project playbook distillation and technical proposal review."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

