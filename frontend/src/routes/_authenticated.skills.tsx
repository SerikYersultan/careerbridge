import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { api, type SkillCandidate, type UserSkill } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import { Loader2, Plus, Upload, X } from "lucide-react";

export const Route = createFileRoute("/_authenticated/skills")({
  head: () => ({ meta: [{ title: "Навыки — CareerBridge" }] }),
  component: SkillsPage,
});

const CATEGORIES = ["language", "framework", "database", "tool", "cloud", "soft", "other"];

function SkillsPage() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [savedSkills, setSavedSkills] = useState<UserSkill[]>([]);
  const [draft, setDraft] = useState<SkillCandidate[]>([]);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCategory, setNewCategory] = useState("other");

  const loadSaved = async () => {
    try {
      const data = await api<UserSkill[]>("/profile/skills");
      setSavedSkills(data);
      if (draft.length === 0) {
        setDraft(data.map((s) => ({ display_name: s.display_name ?? s.name, category: s.category })));
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Не удалось загрузить навыки");
    }
  };

  useEffect(() => {
    loadSaved();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onUpload = async (file: File) => {
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api<{ skills: SkillCandidate[] }>("/profile/upload-resume", { method: "POST", formData: fd });
      const existing = new Map(draft.map((s) => [s.display_name.toLowerCase(), s]));
      for (const s of res.skills) {
        const k = s.display_name.toLowerCase();
        if (!existing.has(k)) existing.set(k, s);
      }
      setDraft(Array.from(existing.values()));
      toast.success(`Извлечено ${res.skills.length} навыков. Проверь и сохрани.`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Не удалось обработать PDF");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const removeSkill = (name: string) => {
    setDraft((prev) => prev.filter((s) => s.display_name !== name));
  };

  const addSkill = () => {
    const n = newName.trim();
    if (!n) return;
    if (draft.some((s) => s.display_name.toLowerCase() === n.toLowerCase())) {
      toast.error("Этот навык уже есть");
      return;
    }
    setDraft((prev) => [...prev, { display_name: n, category: newCategory }]);
    setNewName("");
  };

  const save = async () => {
    setSaving(true);
    try {
      await api("/profile/skills", {
        method: "POST",
        body: { skills: draft.map((s) => ({ display_name: s.display_name, category: s.category })) },
      });
      toast.success("Навыки сохранены");
      await loadSaved();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Не удалось сохранить");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Мои навыки</h1>
        <p className="text-muted-foreground mt-1">
          Загрузи резюме в PDF — AI извлечёт навыки. Затем отредактируй вручную и сохрани.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Загрузить резюме (PDF)</CardTitle>
          <CardDescription>Текст из PDF, навыки извлекает AI.</CardDescription>
        </CardHeader>
        <CardContent>
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onUpload(f);
            }}
          />
          <Button onClick={() => fileRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
            {uploading ? "Анализ..." : "Выбрать PDF"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Редактирование ({draft.length})</CardTitle>
          <CardDescription>Удаляй лишнее, добавляй своё. Не забудь сохранить.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {draft.length === 0 ? (
            <p className="text-sm text-muted-foreground">Список пустой.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {draft.map((s) => (
                <Badge key={s.display_name} variant="secondary" className="gap-1 pr-1">
                  <span>{s.display_name}</span>
                  <span className="text-xs text-muted-foreground">· {s.category}</span>
                  <button
                    type="button"
                    onClick={() => removeSkill(s.display_name)}
                    className="ml-1 rounded p-0.5 hover:bg-destructive/20"
                    aria-label={`Удалить ${s.display_name}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          )}

          <div className="flex gap-2 flex-wrap pt-2 border-t border-border">
            <Input
              placeholder="Например: PostgreSQL"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addSkill();
                }
              }}
              className="max-w-xs"
            />
            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <Button variant="outline" onClick={addSkill}>
              <Plus className="mr-2 h-4 w-4" /> Добавить
            </Button>
          </div>

          <div className="flex justify-end pt-4">
            <Button onClick={save} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Сохранить ({draft.length})
            </Button>
          </div>

          {savedSkills.length > 0 && (
            <p className="text-xs text-muted-foreground">
              Сейчас в БД: {savedSkills.length} навыков
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}