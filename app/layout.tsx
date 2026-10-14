import type { ReactNode } from "react";
import "./style.css";
export const metadata = { title: "Agent Review Workbench" };
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
