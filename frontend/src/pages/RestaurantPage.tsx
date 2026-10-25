import { useState } from "react";
import type { FormEvent } from "react";
import { Clock3, ImagePlus, MapPin, Save, Store, Trash2 } from "lucide-react";
import { useAuth } from "../auth/auth-context";
import { ActionError, Button, Field, Notice } from "../components/ui";
import {
  PageHeading,
  ReadOnlyNote,
  RecordBadge,
  ResourceStatus,
  TextArea,
  Toggle,
} from "../components/workspace-ui";
import { useAction } from "../hooks/useAction";
import { useResource } from "../hooks/useResource";
import { ApiError } from "../lib/api";
import { canManageWorkspace, workspace } from "../lib/workspace";
import type { Restaurant, RestaurantInput } from "../lib/workspace";

const emptyProfile: RestaurantInput = {
  name: "",
  description: "",
  address: "",
  contact_phone: "",
  email: "",
  currency: "NPR",
  opening_time: null,
  closing_time: null,
  is_active: true,
};

function RestaurantForm({
  restaurant,
  saved,
  editable,
}: {
  restaurant: Restaurant | null;
  saved: () => void;
  editable: boolean;
}) {
  const [form, setForm] = useState<RestaurantInput>(
    restaurant
      ? {
          name: restaurant.name,
          description: restaurant.description,
          address: restaurant.address,
          contact_phone: restaurant.contact_phone,
          email: restaurant.email,
          currency: restaurant.currency,
          opening_time: restaurant.opening_time,
          closing_time: restaurant.closing_time,
          is_active: restaurant.is_active,
        }
      : emptyProfile,
  );
  const action = useAction();
  const update = <K extends keyof RestaurantInput>(
    key: K,
    value: RestaurantInput[K],
  ) => setForm((current) => ({ ...current, [key]: value }));
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await action.run(() => workspace.saveRestaurant(form, !!restaurant)))
      saved();
  }
  return (
    <form className="card workspace-form" onSubmit={submit}>
      <div className="section-header">
        <div>
          <h2>
            {restaurant ? "Restaurant details" : "Make this workspace yours"}
          </h2>
          <p>
            {restaurant
              ? "The essentials your team needs to know."
              : "Start with the name and details of your restaurant."}
          </p>
        </div>
        <Store size={21} />
      </div>
      <fieldset
        className="workspace-form-body form-stack"
        disabled={!editable || action.pending}
      >
        <ActionError error={action.error} remaining={action.remaining} />
        <Field
          label="Restaurant name"
          required
          maxLength={150}
          autoComplete="organization"
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
          error={action.error?.fields.name}
          placeholder="Your restaurant name"
        />
        <TextArea
          label="Description"
          rows={3}
          maxLength={2000}
          value={form.description}
          onChange={(e) => update("description", e.target.value)}
          error={action.error?.fields.description}
          placeholder="A few words about your restaurant"
        />
        <TextArea
          label="Address"
          rows={2}
          maxLength={500}
          autoComplete="street-address"
          value={form.address}
          onChange={(e) => update("address", e.target.value)}
          error={action.error?.fields.address}
        />
        <div className="form-columns">
          <Field
            label="Contact phone"
            type="tel"
            autoComplete="tel"
            maxLength={30}
            value={form.contact_phone}
            onChange={(e) => update("contact_phone", e.target.value)}
            error={action.error?.fields.contact_phone}
          />
          <Field
            label="Email"
            type="email"
            autoComplete="email"
            maxLength={254}
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            error={action.error?.fields.email}
          />
        </div>
        <div className="form-columns">
          <Field
            label="Opening time"
            type="time"
            value={form.opening_time?.slice(0, 5) || ""}
            onChange={(e) => update("opening_time", e.target.value || null)}
            error={action.error?.fields.opening_time}
          />
          <Field
            label="Closing time"
            type="time"
            value={form.closing_time?.slice(0, 5) || ""}
            onChange={(e) => update("closing_time", e.target.value || null)}
            error={action.error?.fields.closing_time}
          />
        </div>
        <p className="field-hint">
          Daily hours in Nepal time. Overnight closing times are supported.
          Leave both blank if not set.
        </p>
        <Field
          label="Currency"
          value="NPR — Nepalese rupee"
          disabled
          hint="Menu prices use Nepalese rupees."
        />
        <Toggle
          label="Restaurant active"
          checked={form.is_active}
          onChange={(value) => update("is_active", value)}
          hint="When inactive, menu items are shown as unavailable. Team sign-in remains available."
        />
        {editable && (
          <div className="workspace-form-footer">
            <Button
              type="submit"
              loading={action.pending}
              disabled={action.remaining > 0}
            >
              <Save size={16} />
              {restaurant ? "Save restaurant" : "Create restaurant profile"}
            </Button>
          </div>
        )}
      </fieldset>
    </form>
  );
}

function LogoForm({
  restaurant,
  saved,
  editable,
}: {
  restaurant: Restaurant;
  saved: () => void;
  editable: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const action = useAction();
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      action.setError(new ApiError("Choose an image of 2 MB or less.", 400));
      return;
    }
    if (await action.run(() => workspace.uploadLogo(file))) {
      setFile(null);
      saved();
    }
  }
  async function remove() {
    const done = await action.run(async () => {
      await workspace.removeLogo();
      return true;
    });
    if (done) saved();
  }
  return (
    <section className="card logo-card">
      <div className="section-header">
        <div>
          <h2>Restaurant logo</h2>
          <p>A familiar mark for your team.</p>
        </div>
        <ImagePlus size={21} />
      </div>
      <div className="logo-card-body">
        <div className="restaurant-logo-preview">
          {restaurant.logo_url ? (
            <img src={restaurant.logo_url} alt={`${restaurant.name} logo`} />
          ) : (
            <Store size={42} strokeWidth={1.3} />
          )}
        </div>
        <ActionError error={action.error} remaining={action.remaining} />
        {editable && (
          <form onSubmit={upload} className="form-stack">
            <Field
              label="Choose logo"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              hint="PNG, JPEG or WebP. Up to 2 MB and 2048 × 2048 pixels."
            />
            <Button
              type="submit"
              disabled={!file || action.remaining > 0}
              loading={action.pending}
            >
              <ImagePlus size={16} />
              Upload logo
            </Button>
            {restaurant.logo_url && (
              <Button
                type="button"
                variant="ghost"
                disabled={action.pending || action.remaining > 0}
                onClick={() => void remove()}
              >
                <Trash2 size={15} />
                Remove logo
              </Button>
            )}
          </form>
        )}
        <div className="workspace-note">
          <Clock3 size={17} />
          <span>Hours use Asia/Kathmandu time.</span>
        </div>
        <div className="workspace-note">
          <MapPin size={17} />
          <span>One restaurant. One shared workspace.</span>
        </div>
      </div>
    </section>
  );
}

export function RestaurantPage() {
  const { user } = useAuth();
  const resource = useResource(workspace.restaurant);
  const [notice, setNotice] = useState("");
  const editable = canManageWorkspace(user?.role);
  const restaurant = resource.data;
  function saved() {
    setNotice("Restaurant details saved.");
    void resource.load();
  }
  return (
    <div className="page-enter">
      <PageHeading
        eyebrow="THE PLACE BEHIND YOUR PEOPLE"
        title="Restaurant profile"
        description="Your identity, contact details, and everyday hours."
      >
        {restaurant && (
          <RecordBadge active={restaurant.is_active}>
            {restaurant.is_active ? "Active" : "Inactive"}
          </RecordBadge>
        )}
      </PageHeading>
      {notice && (
        <div className="mb-6">
          <Notice kind="success">{notice}</Notice>
        </div>
      )}
      {!editable && <ReadOnlyNote />}
      <ResourceStatus
        loading={resource.loading && restaurant === undefined}
        error={resource.error}
        retry={() => void resource.load()}
      />
      {restaurant !== undefined &&
        !resource.error &&
        (restaurant || editable ? (
          <div className="restaurant-grid">
            <RestaurantForm
              key={restaurant?.updated_at || "new"}
              restaurant={restaurant}
              saved={saved}
              editable={editable}
            />
            {restaurant ? (
              <LogoForm
                key={`logo-${restaurant.updated_at}`}
                restaurant={restaurant}
                saved={saved}
                editable={editable}
              />
            ) : (
              <aside className="card setup-aside">
                <Store size={35} />
                <h2>A home for your restaurant.</h2>
                <p>
                  Create your profile to start organising menu categories and
                  tables.
                </p>
                <span className="currency-tag">NPR · Nepal</span>
              </aside>
            )}
          </div>
        ) : (
          <div className="card empty-state">
            <h2>Your restaurant is not set up yet.</h2>
            <p>Ask your Owner or Manager to add the restaurant profile.</p>
          </div>
        ))}
    </div>
  );
}
