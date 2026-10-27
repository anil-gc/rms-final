import { useCallback, useState } from "react";
import { ActionError, Button, Dialog, Notice } from "../../components/ui";
import {
  PageHeading,
  ResourceStatus,
  TextArea,
} from "../../components/workspace-ui";
import { useAction } from "../../hooks/useAction";
import { useResource } from "../../hooks/useResource";
import { ApiError } from "../../lib/api";
import { BatchCard } from "./BatchCard";
import { orderApi } from "./api";
import type { Batch, BatchStatus } from "./api";
import "./orders.css";

function ReviewDialog({
  batch,
  decision,
  close,
  saved,
}: {
  batch: Batch;
  decision: "approve" | "reject";
  close: () => void;
  saved: () => Promise<void>;
}) {
  const action = useAction();
  const [reason, setReason] = useState("");
  async function review() {
    await action.run(async () => {
      try {
        if (decision === "approve") await orderApi.approve(batch.id);
        else await orderApi.reject(batch.id, reason.trim());
      } catch (cause) {
        if (cause instanceof ApiError && cause.status === 409) await saved();
        throw cause;
      }
      await saved();
      close();
    });
  }
  return (
    <Dialog
      title={`${decision === "approve" ? "Approve" : "Reject"} batch ${batch.sequence}?`}
      onClose={close}
      busy={action.pending}
    >
      <form
        className="dialog-body form-stack"
        onSubmit={(e) => {
          e.preventDefault();
          void review();
        }}
      >
        <p>
          {batch.table_name} · Submitted by {batch.submitted_by_name}. The
          submitted items and prices will stay unchanged.
        </p>
        <BatchCard batch={batch} />
        <ActionError error={action.error} remaining={action.remaining} />
        {decision === "reject" && (
          <TextArea
            label="Rejection reason"
            required
            maxLength={500}
            value={reason}
            error={action.error?.fields.reason}
            onChange={(e) => setReason(e.target.value)}
          />
        )}
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
            variant={decision === "reject" ? "danger" : "primary"}
            loading={action.pending}
            disabled={
              action.remaining > 0 ||
              (decision === "reject" && !reason.trim()) ||
              action.error?.status === 409
            }
          >
            {decision === "approve" ? "Confirm approval" : "Confirm rejection"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function Queue({ status }: { status: BatchStatus | "all" }) {
  const [page, setPage] = useState(1);
  const loader = useCallback(
    () => orderApi.batches(status, page),
    [status, page],
  );
  const resource = useResource(loader);
  const [review, setReview] = useState<{
    batch: Batch;
    decision: "approve" | "reject";
  } | null>(null);
  const [notice, setNotice] = useState("");
  const current = resource.data;
  async function saved() {
    setNotice("Queue refreshed.");
    await resource.load();
  }
  return (
    <>
      <div className="order-batch-heading">
        <p>
          {current
            ? `${current.count} ${current.count === 1 ? "batch" : "batches"} · Page ${page}`
            : "Checking queue…"}
        </p>
        <Button
          variant="secondary"
          onClick={() => void resource.load()}
          disabled={resource.loading}
        >
          Refresh queue
        </Button>
      </div>
      {notice && <Notice kind="success">{notice}</Notice>}
      <ResourceStatus
        loading={resource.loading}
        error={resource.error}
        retry={() => void resource.load()}
      />
      {!resource.loading && !resource.error && current && (
        <>
          {!current.results.length && (
            <Notice kind="info">No batches in this view.</Notice>
          )}
          <div className="order-batches">
            {current.results.map((batch) => (
              <BatchCard key={batch.id} batch={batch}>
                {batch.status === "pending" && (
                  <div className="order-review-actions">
                    <Button
                      onClick={() => setReview({ batch, decision: "approve" })}
                    >
                      Approve batch {batch.sequence}
                    </Button>
                    <Button
                      variant="danger"
                      onClick={() => setReview({ batch, decision: "reject" })}
                    >
                      Reject batch {batch.sequence}
                    </Button>
                  </div>
                )}
              </BatchCard>
            ))}
          </div>
        </>
      )}
      <div className="order-review-actions">
        <Button
          variant="secondary"
          disabled={page <= 1 || resource.loading}
          onClick={() => setPage((value) => value - 1)}
        >
          Previous page
        </Button>
        <Button
          variant="secondary"
          disabled={!current?.next || resource.loading || !!resource.error}
          onClick={() => setPage((value) => value + 1)}
        >
          Next page
        </Button>
      </div>
      {review && (
        <ReviewDialog {...review} close={() => setReview(null)} saved={saved} />
      )}
    </>
  );
}

export function CashierOrdersPage() {
  const [status, setStatus] = useState<BatchStatus | "all">("pending");
  return (
    <div className="page-enter">
      <PageHeading
        eyebrow="REVIEW NEW SUBMISSIONS"
        title="Cashier approvals"
        description="Review each batch once. Additional items arrive as separate pending batches."
      />
      <div className="field order-filter">
        <label htmlFor="approval-status">Show batches</label>
        <select
          id="approval-status"
          className="input"
          value={status}
          onChange={(e) => setStatus(e.target.value as BatchStatus | "all")}
        >
          <option value="pending">Pending approval</option>
          <option value="approved">Approved history</option>
          <option value="rejected">Rejected history</option>
          <option value="all">All batches</option>
        </select>
      </div>
      <Queue key={status} status={status} />
    </div>
  );
}
