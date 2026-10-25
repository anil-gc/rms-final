import { useState } from "react";
import type { FormEvent } from "react";
import { FolderPlus, Pencil, Plus, Search, Utensils } from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { ActionError, Button, Dialog, Field, Notice } from "../components/ui";
import {
  EmptyRecords,
  PageHeading,
  ReadOnlyNote,
  RecordBadge,
  ResourceStatus,
  SetupNotice,
  TextArea,
  Toggle,
} from "../components/workspace-ui";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { canManageWorkspace, formatNpr, workspace } from "../lib/workspace";
import type {
  Category,
  CategoryInput,
  ItemInput,
  MenuItem,
} from "../lib/workspace";

function CategoryDialog({
  category,
  close,
  saved,
}: {
  category?: Category;
  close: () => void;
  saved: () => void;
}) {
  const [form, setForm] = useState<CategoryInput>({
    name: category?.name || "",
    description: category?.description || "",
    sort_order: category?.sort_order || 0,
    is_active: category?.is_active ?? true,
  });
  const action = useAction();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await action.run(() => workspace.saveCategory(form, category?.id)))
      saved();
  }
  return (
    <Dialog
      title={category ? "Edit category" : "Add category"}
      onClose={close}
      busy={action.pending}
    >
      <form onSubmit={submit} className="dialog-body form-stack">
        <ActionError error={action.error} remaining={action.remaining} />
        <Field
          label="Category name"
          required
          maxLength={100}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          error={action.error?.fields.name}
          placeholder="e.g. Momo"
        />
        <TextArea
          label="Category description"
          rows={2}
          maxLength={500}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          error={action.error?.fields.description}
        />
        <Field
          label="Display order"
          type="number"
          min={0}
          max={32767}
          step={1}
          required
          value={form.sort_order}
          onChange={(e) =>
            setForm({ ...form, sort_order: Number(e.target.value) })
          }
          error={action.error?.fields.sort_order}
          hint="Smaller numbers appear first."
        />
        <Toggle
          label="Category active"
          checked={form.is_active}
          onChange={(value) => setForm({ ...form, is_active: value })}
          hint="Archived categories and their items are hidden from staff. Records are kept."
        />
        <div className="dialog-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={close}
            disabled={action.pending}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={action.pending}
            disabled={action.remaining > 0}
          >
            Save category
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function ItemDialog({
  item,
  categories,
  close,
  saved,
}: {
  item?: MenuItem;
  categories: Category[];
  close: () => void;
  saved: () => void;
}) {
  const [form, setForm] = useState<ItemInput>({
    name: item?.name || "",
    description: item?.description || "",
    category:
      item?.category ||
      categories.find((category) => category.is_active)?.id ||
      categories[0]?.id ||
      0,
    price: item?.price || "",
    is_available: item?.is_available ?? true,
    is_active: item?.is_active ?? true,
  });
  const action = useAction();
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await action.run(() => workspace.saveItem(form, item?.id))) saved();
  }
  return (
    <Dialog
      title={item ? "Edit menu item" : "Add menu item"}
      onClose={close}
      busy={action.pending}
    >
      <form onSubmit={submit} className="dialog-body form-stack">
        <ActionError error={action.error} remaining={action.remaining} />
        <Field
          label="Item name"
          required
          maxLength={150}
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          error={action.error?.fields.name}
          placeholder="e.g. Vegetable momo"
        />
        <div className="field">
          <label htmlFor="item-category">Category</label>
          <select
            id="item-category"
            className="input"
            required
            value={form.category}
            aria-invalid={!!action.error?.fields.category || undefined}
            aria-describedby={
              action.error?.fields.category ? "item-category-error" : undefined
            }
            onChange={(e) =>
              setForm({ ...form, category: Number(e.target.value) })
            }
          >
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
                {!category.is_active ? " (archived)" : ""}
              </option>
            ))}
          </select>
          {action.error?.fields.category && (
            <span id="item-category-error" className="field-error">
              {action.error.fields.category}
            </span>
          )}
        </div>
        <Field
          label="Price (NPR)"
          required
          type="number"
          min="0.01"
          max="99999999.99"
          step="0.01"
          inputMode="decimal"
          value={form.price}
          onChange={(e) => setForm({ ...form, price: e.target.value })}
          error={action.error?.fields.price}
        />
        <TextArea
          label="Item description"
          rows={3}
          maxLength={1000}
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          error={action.error?.fields.description}
        />
        <Toggle
          label="Available"
          checked={form.is_available}
          onChange={(value) => setForm({ ...form, is_available: value })}
          hint="Turn off when this item is temporarily unavailable."
        />
        <Toggle
          label="Item active"
          checked={form.is_active}
          onChange={(value) => setForm({ ...form, is_active: value })}
          hint="Archive to hide the item from staff while keeping its record."
        />
        <div className="dialog-actions">
          <Button
            type="button"
            variant="secondary"
            onClick={close}
            disabled={action.pending}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            loading={action.pending}
            disabled={action.remaining > 0}
          >
            Save item
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

type Editor =
  { type: "category"; category?: Category } | { type: "item"; item?: MenuItem };

export function MenuPage() {
  const { user } = useAuth();
  const editable = canManageWorkspace(user?.role);
  const profile = useResource(workspace.restaurant);
  const categories = useResource(workspace.categories);
  const items = useResource(workspace.items);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [query, setQuery] = useState("");
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [filter, setFilter] = useState("active");
  const [notice, setNotice] = useState("");
  const filtered = (items.data || []).filter(
    (item) =>
      (categoryId === null || item.category === categoryId) &&
      `${item.name} ${item.description}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (filter === "all" ||
        (filter === "active" ? item.is_active : !item.is_active)),
  );
  const failed = profile.error || categories.error || items.error;
  const loading =
    (categories.loading && !categories.data) ||
    (items.loading && !items.data) ||
    (profile.loading && profile.data === undefined);
  function refresh() {
    void categories.load();
    void items.load();
    void profile.load();
  }
  function saved() {
    setEditor(null);
    setNotice("Menu saved.");
    refresh();
  }
  function edit(value: Editor) {
    setNotice("");
    setEditor(value);
  }
  return (
    <div className="page-enter">
      <PageHeading
        eyebrow="WHAT MAKES YOUR PLACE SPECIAL"
        title="Menu catalogue"
        description="A clear home for your categories, prices, and availability."
      >
        {editable && (
          <div className="heading-actions">
            <Button
              variant="secondary"
              onClick={() => edit({ type: "category" })}
              disabled={!profile.data || !!failed}
            >
              <FolderPlus size={17} />
              Add category
            </Button>
            <Button
              onClick={() => edit({ type: "item" })}
              disabled={!profile.data || !categories.data?.length || !!failed}
            >
              <Plus size={17} />
              Add item
            </Button>
          </div>
        )}
      </PageHeading>
      {!editable && <ReadOnlyNote />}
      {notice && (
        <div className="mb-6">
          <Notice kind="success">{notice}</Notice>
        </div>
      )}
      <ResourceStatus loading={!!loading} error={failed} retry={refresh} />
      {profile.data === null && !failed && <SetupNotice />}
      {!loading && !failed && profile.data && (
        <>
          <div className="workspace-summary">
            <span>
              <Utensils size={17} />
              {items.data?.length} items
            </span>
            <span>{categories.data?.length} categories</span>
            <span>NPR · Nepalese rupees</span>
          </div>
          {!profile.data.is_active && (
            <div className="mb-6">
              <Notice kind="info">
                The restaurant is inactive. All items are currently unavailable.
              </Notice>
            </div>
          )}
          <div className="menu-layout">
            <aside className="card category-rail">
              <div className="category-rail-heading">
                <h2>Categories</h2>
                {editable && (
                  <button
                    className="icon-button"
                    aria-label="Add category"
                    onClick={() => edit({ type: "category" })}
                  >
                    <Plus size={17} />
                  </button>
                )}
              </div>
              <button
                className={`category-filter ${categoryId === null ? "selected" : ""}`}
                onClick={() => setCategoryId(null)}
              >
                All categories<span>{items.data?.length}</span>
              </button>
              {categories.data?.map((category) => (
                <div key={category.id} className="category-entry">
                  <button
                    className={`category-filter ${categoryId === category.id ? "selected" : ""}`}
                    onClick={() => setCategoryId(category.id)}
                  >
                    <span>
                      {category.name}
                      {!category.is_active && <small>Archived category</small>}
                    </span>
                    <span>
                      {
                        items.data?.filter(
                          (item) => item.category === category.id,
                        ).length
                      }
                    </span>
                  </button>
                  {editable && (
                    <button
                      className="icon-button category-edit"
                      aria-label={`Edit category ${category.name}`}
                      onClick={() => edit({ type: "category", category })}
                    >
                      <Pencil size={13} />
                    </button>
                  )}
                </div>
              ))}
              {!categories.data?.length && (
                <p className="category-empty">
                  Your first category starts here.
                </p>
              )}
            </aside>
            <section className="menu-content">
              <div className="card catalogue-toolbar">
                <div className="search-input">
                  <Search size={18} />
                  <input
                    aria-label="Search menu"
                    placeholder="Search menu items…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </div>
                {editable && (
                  <select
                    className="input filter-select"
                    aria-label="Filter menu status"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    <option value="active">Active items</option>
                    <option value="archived">Archived items</option>
                    <option value="all">All items</option>
                  </select>
                )}
              </div>
              {filtered.length ? (
                <div className="menu-item-grid">
                  {filtered.map((item) => (
                    <article className="card menu-item-card" key={item.id}>
                      <div className="menu-item-heading">
                        <span className="menu-category-label">
                          {item.category_name}
                        </span>
                        {editable && (
                          <button
                            className="icon-button"
                            aria-label={`Edit item ${item.name}`}
                            onClick={() => edit({ type: "item", item })}
                          >
                            <Pencil size={16} />
                          </button>
                        )}
                      </div>
                      <h2>{item.name}</h2>
                      <p>{item.description || "No description added."}</p>
                      <div className="menu-item-footer">
                        <strong>{formatNpr(item.price)}</strong>
                        <RecordBadge active={item.effective_available}>
                          {!item.is_active
                            ? "Archived"
                            : item.effective_available
                              ? "Available"
                              : "Unavailable"}
                        </RecordBadge>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="card">
                  <EmptyRecords
                    title={
                      items.data?.length
                        ? "No matching items."
                        : "A menu starts with one good dish."
                    }
                    description={
                      items.data?.length
                        ? "Try a different category, search, or status filter."
                        : categories.data?.length
                          ? "Add your first item with a price and availability."
                          : "Create a category, then add the items your team serves."
                    }
                    action={
                      editable && !items.data?.length
                        ? categories.data?.length
                          ? "Add menu item"
                          : "Add category"
                        : undefined
                    }
                    onAction={() =>
                      edit({
                        type: categories.data?.length ? "item" : "category",
                      })
                    }
                  />
                </div>
              )}
            </section>
          </div>
        </>
      )}
      {editor?.type === "category" && (
        <CategoryDialog
          category={editor.category}
          close={() => setEditor(null)}
          saved={saved}
        />
      )}
      {editor?.type === "item" && (
        <ItemDialog
          item={editor.item}
          categories={categories.data || []}
          close={() => setEditor(null)}
          saved={saved}
        />
      )}
    </div>
  );
}
