import { ListChecks, Plus, Save, Trash2 } from "lucide-react";
import { useState } from "react";
import type { RuleSet } from "../api/client";
import { useDeleteRuleSet, useRuleSets, useSaveRuleSet } from "../api/hooks";
import RulesEditor from "../components/RulesEditor";
import { useToast } from "../components/Toaster";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Input,
  Label,
  Loading,
  Modal,
  PageHeader,
  Textarea,
} from "../components/ui";
import { timeAgo } from "../utils/format";

const TEMPLATE = `# Reusable rules. Apply them to any dataset from its "Rules & validation" tab.
columns:
  id:
    not_null: {}
    unique: {}
  email:
    regex: { pattern: "^[^@\\\\s]+@[^@\\\\s]+\\\\.[^@\\\\s]+$" }
dataset:
  row_count: { min: 1 }
`;

type Draft = { id?: string; name: string; description: string; rules_yaml: string };

export default function RuleSetsPage() {
  const { data, isLoading, error } = useRuleSets();
  const [picked, setSelected] = useState<string | "new" | null>(null);
  // Default to the most recently updated set until the user picks one.
  const selected = picked ?? data?.[0]?.id ?? null;

  const current = selected === "new" ? null : data?.find((r) => r.id === selected);

  return (
    <>
      <PageHeader
        icon={<ListChecks className="size-5" />}
        title="Rule sets"
        subtitle="Named, reusable collections of rules — e.g. one per data contract or source system."
        actions={
          <Button
            variant="primary"
            icon={<Plus className="size-4" />}
            onClick={() => setSelected("new")}
          >
            New rule set
          </Button>
        }
      />
      {error && <Alert title="Could not load rule sets">{error.message}</Alert>}
      {isLoading ? (
        <Loading />
      ) : !data?.length && selected !== "new" ? (
        <EmptyState
          icon={<ListChecks className="size-10" />}
          title="No rule sets yet"
          action={
            <Button
              variant="primary"
              icon={<Plus className="size-4" />}
              onClick={() => setSelected("new")}
            >
              Create one
            </Button>
          }
        >
          Create one here or use <b>Save as set</b> while editing a dataset's rules.
        </EmptyState>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <Card padded={false} className="self-start">
            <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data?.map((rs) => (
                <li key={rs.id}>
                  <button
                    onClick={() => setSelected(rs.id)}
                    className={
                      "w-full px-4 py-3 text-left transition-colors " +
                      (rs.id === selected
                        ? "bg-indigo-50 dark:bg-indigo-500/10"
                        : "hover:bg-zinc-50 dark:hover:bg-zinc-800/40")
                    }
                  >
                    <div className="truncate text-sm font-medium">{rs.name}</div>
                    <div className="truncate text-xs text-zinc-500">
                      updated {timeAgo(rs.updated_at)}
                    </div>
                  </button>
                </li>
              ))}
              {selected === "new" && (
                <li className="bg-indigo-50 px-4 py-3 text-sm font-medium dark:bg-indigo-500/10">
                  New rule set…
                </li>
              )}
            </ul>
          </Card>
          {(current || selected === "new") && (
            <Editor
              key={current?.id ?? "new"}
              initial={current ?? null}
              onSaved={(rs) => setSelected(rs.id)}
              onDeleted={() => setSelected(null)}
            />
          )}
        </div>
      )}
    </>
  );
}

function Editor({
  initial,
  onSaved,
  onDeleted,
}: {
  initial: RuleSet | null;
  onSaved: (rs: RuleSet) => void;
  onDeleted: () => void;
}) {
  const [draft, setDraft] = useState<Draft>(
    initial
      ? {
          id: initial.id,
          name: initial.name,
          description: initial.description,
          rules_yaml: initial.rules_yaml,
        }
      : { name: "", description: "", rules_yaml: TEMPLATE },
  );
  const [confirm, setConfirm] = useState(false);
  const save = useSaveRuleSet();
  const remove = useDeleteRuleSet();
  const toast = useToast();
  const dirty =
    !initial ||
    draft.name !== initial.name ||
    draft.description !== initial.description ||
    draft.rules_yaml !== initial.rules_yaml;

  return (
    <Card
      title={initial ? initial.name : "New rule set"}
      actions={
        <>
          {initial && (
            <Button
              variant="ghost"
              size="sm"
              icon={<Trash2 className="size-4" />}
              onClick={() => setConfirm(true)}
            >
              Delete
            </Button>
          )}
          <Button
            variant="primary"
            size="sm"
            icon={<Save className="size-4" />}
            disabled={!dirty || !draft.name.trim()}
            loading={save.isPending}
            onClick={() =>
              save.mutate(
                { ...draft, name: draft.name.trim() },
                {
                  onSuccess: (rs) => {
                    toast({ tone: "success", title: "Rule set saved" });
                    onSaved(rs);
                  },
                  onError: (e) => toast({ tone: "error", title: "Save failed", body: e.message }),
                },
              )
            }
          >
            Save
          </Button>
        </>
      }
    >
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <label className="block">
          <Label>Name</Label>
          <Input
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            placeholder="e.g. customers contract"
          />
        </label>
        <label className="block">
          <Label hint="optional">Description</Label>
          <Textarea
            rows={1}
            value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
            className="h-9 resize-none"
          />
        </label>
      </div>
      <RulesEditor
        value={draft.rules_yaml}
        onChange={(v) => setDraft({ ...draft, rules_yaml: v })}
        height="520px"
      />

      <Modal
        open={confirm}
        onClose={() => setConfirm(false)}
        title="Delete rule set?"
        footer={
          <>
            <Button onClick={() => setConfirm(false)}>Cancel</Button>
            <Button
              variant="danger"
              loading={remove.isPending}
              onClick={() =>
                initial &&
                remove.mutate(initial.id, {
                  onSuccess: () => {
                    setConfirm(false);
                    onDeleted();
                  },
                })
              }
            >
              Delete
            </Button>
          </>
        }
      >
        <p className="text-sm text-zinc-600 dark:text-zinc-300">
          <b>{initial?.name}</b> will be deleted. Past runs keep their own copy of the rules.
        </p>
      </Modal>
    </Card>
  );
}
