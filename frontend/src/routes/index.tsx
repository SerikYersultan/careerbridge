import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { SiteHeader } from "../components/SiteHeader";
import { Button } from "../components/ui/button";
import { ArrowRight, FileText, Target, Map } from "lucide-react";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main>
        <section className="mx-auto max-w-5xl px-4 pt-20 pb-16 text-center">
          <span className="inline-block px-3 py-1 text-xs font-medium rounded-full bg-secondary text-secondary-foreground mb-6">
            MVP · Қазақстан IT
          </span>
          <h1 className="text-4xl sm:text-6xl font-bold tracking-tight">
            Найди свой путь <span className="text-primary">в IT</span>
          </h1>
          <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
            Загрузи резюме, узнай каких навыков не хватает для целевой роли — и
            получи персональный AI-роадмап обучения с конкретными ресурсами.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Button asChild size="lg">
              <Link to="/register">
                Начать бесплатно <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link to="/login">У меня уже есть аккаунт</Link>
            </Button>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-4 pb-24 grid gap-6 sm:grid-cols-3">
          {[
            { icon: FileText, title: "Анализ резюме", desc: "Загрузи PDF — AI вытащит навыки и категории." },
            { icon: Target, title: "Skill-gap", desc: "Сравним с реальными вакансиями в Казахстане." },
            { icon: Map, title: "AI-роадмап", desc: "Пошаговый граф обучения под целевую роль." },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-lg border border-border bg-card p-6">
              <Icon className="h-6 w-6 text-primary mb-3" />
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{desc}</p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
