import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { Input, Label } from "@/components/ui/Field";

export interface FieldRow {
  name: string;
  selector: string;
  attr: string;
  transform: string;
}

const ATTR_OPTIONS = ["text", "href", "src", "alt", "title", "value"];
const TRANSFORM_OPTIONS = [
  "",
  "strip_currency",
  "strip_whitespace",
  "parse_int",
  "parse_float",
  "has_class_in-stock",
  "lowercase",
  "uppercase",
];

interface SelectorsEditorProps {
  itemsSelector: string;
  onItemsSelectorChange: (v: string) => void;
  fields: FieldRow[];
  onFieldsChange: (fields: FieldRow[]) => void;
}

export function SelectorsEditor({
  itemsSelector,
  onItemsSelectorChange,
  fields,
  onFieldsChange,
}: SelectorsEditorProps) {
  function updateField(index: number, patch: Partial<FieldRow>) {
    onFieldsChange(fields.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  }

  function removeField(index: number) {
    onFieldsChange(fields.filter((_, i) => i !== index));
  }

  function addField() {
    onFieldsChange([...fields, { name: "", selector: "", attr: "text", transform: "" }]);
  }

  return (
    <div>
      <Label htmlFor="items-selector">Item container selector</Label>
      <Input
        id="items-selector"
        value={itemsSelector}
        onChange={(e) => onItemsSelectorChange(e.target.value)}
        placeholder="div.product-card"
        className="font-mono text-xs"
      />
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        CSS selector matching each repeated item on the page (e.g. one card per product).
      </p>

      <div className="mt-4 flex items-center justify-between">
        <Label className="mb-0">Fields</Label>
        <Button type="button" variant="secondary" size="sm" onClick={addField}>
          <Plus className="size-3.5" />
          Add field
        </Button>
      </div>

      <div className="mt-2 space-y-2">
        {fields.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-300 p-4 text-center text-xs text-slate-400 dark:border-slate-700">
            No fields yet. Add one for each piece of data to extract per item.
          </p>
        )}
        {fields.map((field, i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_1.4fr_0.8fr_0.9fr_auto] items-center gap-2 rounded-lg border border-slate-200 p-2 dark:border-slate-800"
          >
            <Input
              value={field.name}
              onChange={(e) => updateField(i, { name: e.target.value })}
              placeholder="title"
              className="text-xs"
            />
            <Input
              value={field.selector}
              onChange={(e) => updateField(i, { selector: e.target.value })}
              placeholder="h3.title"
              className="font-mono text-xs"
            />
            <select
              value={field.attr}
              onChange={(e) => updateField(i, { attr: e.target.value })}
              className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
            >
              {ATTR_OPTIONS.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <select
              value={field.transform}
              onChange={(e) => updateField(i, { transform: e.target.value })}
              className="rounded-lg border border-slate-300 bg-white px-2 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
            >
              {TRANSFORM_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t || "no transform"}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => removeField(i)}
              className="rounded-md p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10"
            >
              <Trash2 className="size-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
