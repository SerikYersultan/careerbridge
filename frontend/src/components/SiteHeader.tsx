import { Link } from "@tanstack/react-router";
import { useAuth } from "../lib/auth";
import { Button } from "./ui/button";
import { GraduationCap } from "lucide-react";

export function SiteHeader() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <header className="border-b border-border bg-background/80 backdrop-blur sticky top-0 z-30">
      <div className="mx-auto max-w-6xl px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <GraduationCap className="h-5 w-5 text-primary" />
          <span>CareerBridge</span>
        </Link>
        <nav className="flex items-center gap-2">
          {isAuthenticated ? (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link to="/dashboard">Дашборд</Link>
              </Button>
              <Button asChild variant="ghost" size="sm">
                <Link to="/skills">Навыки</Link>
              </Button>
              <span className="text-sm text-muted-foreground hidden sm:inline">
                {user?.email}
              </span>
              <Button variant="outline" size="sm" onClick={logout}>
                Выйти
              </Button>
            </>
          ) : (
            <>
              <Button asChild variant="ghost" size="sm">
                <Link to="/login">Войти</Link>
              </Button>
              <Button asChild size="sm">
                <Link to="/register">Начать</Link>
              </Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}