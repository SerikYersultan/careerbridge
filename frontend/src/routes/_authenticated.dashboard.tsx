import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, type GapResponse, type RoadmapResponse, type UserSkill } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { toast } from "sonner";
import { Loader2, Sparkles, Target } from "lucide-react";
import { useAuth } from "../lib/auth";
import { RoadmapFlow } from "../components/RoadmapFlow";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({ meta: [{ title: "Дашборд — CareerBridge" }] }),
  component: DashboardPage,
});

const ROLES = ["Backend Developer", "Frontend Developer", "Data Analyst", "Data Scientist", "DevOps Engineer", "QA Engineer", "iOS Developer", "Android Developer", "Flutter Developer", "React Native Developer", "Full Stack Developer", "ML Engineer", "QA Automation Engineer", "System Analyst", "Cloud Engineer", "Database Administrator", "Go Backend Developer", "Java Backend Developer", "Node.js Backend Developer"];

function DashboardPage() {
  const { user } = useAuth();
  const [skills, setSkills] = useState<UserSkill[]>([]);
  const [role, setRole] = useState("Backend Developer");
  const [gap, setGap] = useState<GapResponse | null>(null);
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [loadingGap, setLoadingGap] = useState(false);
  const [loadingRoadmap, setLoadingRoadmap] = useState(false);

  useEffect(() => {
    api<UserSkill[]>("/profile/skills").then(setSkills).catch(() => setSkills([]));
    api<RoadmapResponse | null>("/roadmap/last").then(setRoadmap).catch(() => {});
  }, []);

  const runGap = async () => {
    setLoadingGap(true);
    setGap(null);
    try {
      const data = await api<GapResponse>("/roadmap/gap", { query: { target_role: role } });
      setGap(data);
      if (data.jobs_analyzed === 0) {
        toast.error(`Не нашли вакансий для роли «${role}»`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Ошибка анализа");
    } finally {
      setLoadingGap(false);
    }
  };

  const generateRoadmap = async () => {
    setLoadingRoadmap(true);
    try {
      const data = await api<RoadmapResponse>("/roadmap/generate", { method: "POST", query: { target_role: role } });
      setRoadmap(data);
      toast.success("Роадмап готов");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Не удалось сгенерировать роадмап");
    } finally {
      setLoadingRoadmap(false);
    }
  };

  const coverage = gap && gap.market_top.length > 0
    ? Math.round((gap.have.length / gap.market_top.length) * 100)
    : 0;

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Привет{user?.full_name ? `, ${user.full_name}` : ""}!</h1>
        <p className="text-muted-foreground mt-1">
          Выбери целевую роль и узнай, какие навыки нужно подтянуть.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Твои навыки</CardTitle>
          <CardDescription>
            {skills.length > 0
              ? `Сохранено ${skills.length} навыков`
              : "Пока пусто — загрузи резюме на вкладке «Навыки»"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {skills.slice(0, 30).map((s) => (
              <Badge key={s.id} variant="secondary">
                {s.name}
              </Badge>
            ))}
          </div>
          <div className="mt-4">
            <Button asChild variant="outline" size="sm">
              <Link to="/skills">Редактировать навыки</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            Целевая роль
          </CardTitle>
          <CardDescription>Сравним твои навыки с реальными вакансиями.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
            <div className="space-y-2">
              <Label>Роль</Label>
              <Input value={role} onChange={(e) => setRole(e.target.value)} list="roles" />
              <datalist id="roles">
                {ROLES.map((r) => (
                  <option key={r} value={r} />
                ))}
              </datalist>
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={runGap} disabled={loadingGap}>
                {loadingGap && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Skill-gap
              </Button>
              <Button onClick={generateRoadmap} disabled={loadingRoadmap} variant="default">
                {loadingRoadmap ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Sparkles className="mr-2 h-4 w-4" />}
                AI-роадмап
              </Button>
            </div>
          </div>

          {gap && gap.jobs_analyzed > 0 && (
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-muted-foreground">
                    Покрытие рынка ({gap.jobs_analyzed} вакансий)
                  </span>
                  <span className="font-medium">{coverage}%</span>
                </div>
                <Progress value={coverage} />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <h3 className="font-semibold mb-2 text-sm">У тебя есть ({gap.have.length})</h3>
                  <div className="flex flex-wrap gap-2">
                    {gap.have.map((s) => (
                      <Badge key={s.name} variant="secondary">
                        {s.name} · {Math.round(s.coverage * 100)}%
                      </Badge>
                    ))}
                    {gap.have.length === 0 && (
                      <span className="text-sm text-muted-foreground">— пока ничего —</span>
                    )}
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold mb-2 text-sm">Нужно изучить ({gap.missing.length})</h3>
                  <div className="flex flex-wrap gap-2">
                    {gap.missing.map((s) => (
                      <Badge key={s.name} className="bg-destructive/10 text-destructive border border-destructive/30">
                        {s.name} · {Math.round(s.coverage * 100)}%
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {roadmap && roadmap.nodes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Последний роадмап: {roadmap.target_role}</CardTitle>
            <CardDescription>{roadmap.nodes.length} шагов · {roadmap.edges.length} связей</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-sm border-2 border-emerald-500/60 bg-emerald-500/10" />
                beginner
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-sm border-2 border-amber-500/60 bg-amber-500/10" />
                intermediate
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-sm border-2 border-rose-500/60 bg-rose-500/10" />
                advanced
              </span>
            </div>
            <RoadmapFlow roadmap={roadmap} />
          </CardContent>
        </Card>
      )}
    </main>
  );
}